"""Durable single-turn Actor with six total technical attempts and content-only output."""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import time
import requests
from .protocol import require
from ...storage import freeze, read, save, now
from ....v27.transport import RequestFailure, http_failure as legacy_http_failure
from . import protocol as p
from .scoring import score


@contextmanager
def locked(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    with (root/'.execution.lock').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield


def parse_response(raw):
    try:
        require(isinstance(raw,dict) and isinstance(raw['choices'],list) and len(raw['choices'])==1,'Malformed choices')
        choice=raw['choices'][0]; message=choice['message'];finish=choice['finish_reason']
        require(isinstance(message,dict) and message.get('role')=='assistant','Malformed message')
        if message.get('refusal') or finish not in ('stop','length'):
            raise RequestFailure('Refusal or unsupported finish reason',retryable=False)
        if finish == 'length':
            raise RequestFailure('Truncated Actor response')
        if message.get('tool_calls') or message.get('function_call'):
            raise RequestFailure('Tools are not available',retryable=False)
        require('content' in message,'Missing content')
        content=message['content']
        require(isinstance(content,str),'Malformed content')
        return content,finish
    except (KeyError,TypeError,IndexError,ValueError):
        raise RequestFailure('Malformed API response envelope') from None


def usage_view(raw):
    u=raw.get('usage') if isinstance(raw,dict) else None
    u=u if isinstance(u,dict) else {}; details=u.get('completion_tokens_details')
    details=details if isinstance(details,dict) else {}
    values={'input_tokens':u.get('prompt_tokens'),'output_tokens':u.get('completion_tokens'),
            'total_tokens':u.get('total_tokens'),'reasoning_tokens':details.get('reasoning_tokens')}
    return {k:v if type(v) is int and v>=0 else None for k,v in values.items()}


def request_record(messages, config):
    return {'endpoint': config['endpoint'], 'body': {
        'model': config['model'], 'messages': messages, 'temperature': config['temperature'],
        'max_tokens': config['max_tokens'], 'reasoning_effort': config['reasoning_effort'],
        'thinking': config['thinking'], 'stream': False}}


ARCHIVE_FILES = ('request.json', 'request_started.json', 'response.json',
                 'http_status.json', 'http_response.txt')


def archive_hashes(slot):
    return {name: p.file_digest(slot/name) if (slot/name).is_file() else None for name in ARCHIVE_FILES}


def http_failure(status, body, *, retry_http_520=False):
    if status == 520 and retry_http_520:
        return RequestFailure('HTTP 520', retryable=not any(
            token in body for token in ('insufficient_quota', 'quota_exceeded')))
    return legacy_http_failure(status, body)


def archived_response(slot, *, verify_hashes=True):
    """Cross-check raw and decoded representations before classifying a response."""
    raw = read(slot/'response.json') if (slot/'response.json').exists() else None
    if (slot/'http_status.json').exists():
        status = read(slot/'http_status.json')['status_code']
        require(type(status) is int and 100 <= status <= 599 and (slot/'http_response.txt').is_file(),
                'Incomplete HTTP archive')
        body = (slot/'http_response.txt').read_bytes()
        if not 200 <= status < 300:
            require(not (slot/'response.json').exists(), 'Unexpected decoded failed HTTP response')
            raise http_failure(status, body.decode('utf-8', errors='replace'), retry_http_520=not verify_hashes)
        try: decoded = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            require(not (slot/'response.json').exists(), 'Decoded response conflicts with malformed HTTP body')
            raise RequestFailure('Malformed API JSON') from None
        require(not (slot/'response.json').exists() or p.equal(raw, decoded), 'Actor response archives differ')
        return decoded
    require(not ((slot/'http_response.txt').exists() and (slot/'response.json').exists()),
            'Missing HTTP status for decoded response')
    return raw


def validate_slot(slot, messages, config, number, *, allow_prepared=False, verify_hashes=True):
    started = (slot/'request_started.json').exists()
    if started or (slot/'request.json').exists():
        freeze(slot/'request.json', request_record(messages, config), read_only=True)
    if not started:
        require(allow_prepared and not any((slot/name).exists() for name in
                ('response.json','http_status.json','http_response.txt','error.json')),
                'Missing Actor request marker')
        return
    marker = read(slot/'request_started.json')
    require(set(marker) == {'at','attempt'} and marker['attempt'] == number
            and isinstance(marker['at'], str), 'Actor request marker differs')
    if (slot/'error.json').exists():
        error = read(slot/'error.json')
        fields = ('retryable', 'error', 'status', 'archive', 'checksum') if verify_hashes else ('retryable', 'error', 'status')
        p.fields(error, fields, 'Actor failure')
        if verify_hashes:
            require(error['checksum'] == p.digest({k:v for k,v in error.items() if k!='checksum'}),
                    'Actor failure receipt changed')
        require(type(error['retryable']) is bool and isinstance(error['error'], str), 'Invalid Actor failure')
        if verify_hashes:
            require(error['archive'] == archive_hashes(slot), 'Failed Actor archive changed')
        expected_status = 'unknown' if 'outcome unknown' in error['error'] else 'failed'
        require(error['status'] == expected_status, 'Actor failure status differs')
        if (slot/'response.json').exists() or (slot/'http_status.json').exists():
            try:
                parse_response(archived_response(slot, verify_hashes=verify_hashes))
            except RequestFailure as failure:
                require(error['error'] == str(failure) and error['retryable'] == failure.retryable,
                        'Actor failure classification differs')
            else:
                raise ValueError('Failed Actor slot contains an accepted response')
    else:
        # In-flight protocol failures are valid recovery inputs; inconsistent disk copies are not.
        try: archived_response(slot, verify_hashes=verify_hashes)
        except RequestFailure: pass


def validate_pending(case, skill, directory, config, *, verify_hashes=True):
    """Read-only preflight of unfinished journals, before any batch worker starts."""
    p.validate_case(case);p.background(config)
    directory = Path(directory)
    if not directory.exists(): return
    messages = p.messages(case.payload, skill)
    freeze(directory/'signature.json', {'case_id':case.case_id,'payload':case.payload,
        'reference':case.reference,'metadata':case.metadata,'skill':skill,'actor':config,
        'messages':messages,'protocol':p.implementation_identity()}, read_only=True)
    attempts = directory/'attempts'
    if not attempts.exists(): return  # Interrupted after signature, before slot allocation.
    slots = sorted(q for q in attempts.iterdir() if q.is_dir())
    require(len(slots) <= 6 and [q.name for q in slots] == [f'{i:03}' for i in range(1,len(slots)+1)],
            'Invalid Actor slots')
    for i, slot in enumerate(slots, 1):
        validate_slot(slot, messages, config, i, allow_prepared=i==len(slots), verify_hashes=verify_hashes)
        if i < len(slots):
            require((slot/'error.json').is_file() and read(slot/'error.json')['retryable'] is True,
                    'Invalid prior Actor failure')


class ChatTransport:
    def __init__(self,api_key,*,metadata=None,session_factory=requests.Session,retry_http_520=False):
        require(isinstance(api_key,str) and bool(api_key),'Explicit Actor key required')
        self.api_key=api_key;self.config=deepcopy(p.ACTOR if metadata is None else metadata)
        self.retry_http_520=retry_http_520
        p.background(self.config);self.session_factory=session_factory
    def metadata(self):return deepcopy(self.config)
    def __call__(self,messages,directory):
        c=self.config
        request=request_record(messages,c);body=request['body']
        freeze(directory/'request.json',request)
        try:
            with self.session_factory() as session:
                for prefix in ('http://','https://'):session.mount(prefix,requests.adapters.HTTPAdapter(max_retries=0))
                response=session.post(c['endpoint'],json=body,headers={'Authorization':'Bearer '+self.api_key},
                                      timeout=(c['connect_timeout_seconds'],c['timeout_seconds']),allow_redirects=False)
        except (requests.Timeout,requests.ConnectionError,requests.exceptions.ChunkedEncodingError) as e:
            raise RequestFailure(type(e).__name__) from None
        (directory/'http_response.txt').write_bytes(response.content)
        save(directory/'http_status.json',{'status_code':response.status_code})
        if not 200<=response.status_code<300:
            raise http_failure(response.status_code,response.text,retry_http_520=self.retry_http_520)
        try:return response.json()
        except ValueError:raise RequestFailure('Malformed API JSON') from None


def read_completed(case,skill,directory,config, *, verify_hashes=True):
    """Revalidate a completed journal, with no writes, recovery or transport calls."""
    p.validate_case(case)
    directory=Path(directory);messages=p.messages(case.payload,skill)
    p.background(config)
    signature={'case_id':case.case_id,'payload':case.payload,'reference':case.reference,'metadata':case.metadata,
               'skill':skill,'actor':config,'messages':messages,'protocol':p.implementation_identity()}
    freeze(directory/'signature.json',signature,read_only=True)
    require((directory/'result.json').is_file(), 'Missing completed Actor result')
    committed=read(directory/'result.json');count=committed.get('api_requests')
    require(type(count) is int and 1<=count<=6, 'Invalid completed Actor request count')
    attempts=directory/'attempts'
    require(attempts.is_dir(), 'Missing completed Actor attempts')
    paths=sorted(q for q in attempts.iterdir() if q.is_dir())
    require([q.name for q in paths]==[f'{i:03}' for i in range(1,count+1)], 'Completed Actor request slots differ')
    usages=[]
    for n,slot in enumerate(paths,1):
        validate_slot(slot,messages,config,n,verify_hashes=verify_hashes)
        if n<count:
            require((slot/'error.json').is_file() and read(slot/'error.json')['retryable'] is True,
                    'Invalid prior Actor failure')
            usages.append(usage_view(read(slot/'response.json') if (slot/'response.json').exists() else {}))
            continue
        require(not (slot/'error.json').exists(), 'Accepted Actor slot has an error')
        raw=archived_response(slot,verify_hashes=verify_hashes)
        require(raw is not None, 'Completed Actor has lost its response archive')
        content,termination=parse_response(raw)
        usages.append(usage_view(raw));answer,metrics=score(content,case.reference)
        expected={'skill':skill,'actor':config,'initial_messages':messages,'content':content,'termination':termination,
                  'answer':answer,'metrics':metrics,'api_requests':count,'usage_records':usages}
        require(p.equal(committed,expected), 'Completed Actor result differs from response archive')
    return committed


def _execute(case,skill,directory,transport, *, verify_hashes=True):
    """Retry truncation/technical failures in six shared slots; score only stop."""
    p.validate_case(case)
    directory=Path(directory);messages=p.messages(case.payload,skill);config=transport.metadata()
    p.background(config)
    signature={'case_id':case.case_id,'payload':case.payload,'reference':case.reference,'metadata':case.metadata,
               'skill':skill,'actor':config,'messages':messages,'protocol':p.implementation_identity()}
    # A trajectory is also a completion marker. Losing result/response files
    # must not turn an already scored task into an unknown request to retry.
    if (directory/'result.json').exists() or (directory/'trajectory.json').exists():
        return read_completed(case,skill,directory,config,verify_hashes=verify_hashes)
    if directory.exists() and any(q.name != '.execution.lock' for q in directory.iterdir()):
        require((directory/'signature.json').is_file(), 'Missing Actor signature for existing journal')
    freeze(directory/'signature.json',signature)
    validate_pending(case,skill,directory,config,verify_hashes=verify_hashes)
    attempts=directory/'attempts';attempts.mkdir(exist_ok=True)
    paths=sorted(path for path in attempts.iterdir() if path.is_dir())
    require([p.name for p in paths]==[f'{i:03}' for i in range(1,len(paths)+1)] and len(paths)<=6,'Invalid Actor slots')
    usages=[]
    for n in range(1,7):
        slot=attempts/f'{n:03}';existing=slot.exists()
        if existing and (slot/'error.json').exists():
            error=read(slot/'error.json');usages.append(usage_view(read(slot/'response.json') if (slot/'response.json').exists() else {}))
            require(error['retryable'],'Preserved terminal Actor error')
            continue
        if not existing:slot.mkdir()
        raw=None
        try:
            if (slot/'response.json').exists() or (slot/'http_status.json').exists():
                raw=archived_response(slot,verify_hashes=verify_hashes)
                if not (slot/'response.json').exists():save(slot/'response.json',raw)
            elif (slot/'request_started.json').exists():
                raise RequestFailure('Interrupted request; outcome unknown')
            else:
                freeze(slot/'request.json',request_record(messages,config))
                save(slot/'request_started.json',{'at':now(),'attempt':n})
                raw=transport(deepcopy(messages),slot)
                save(slot/'response.json',raw) # Raw hidden fields remain only in this audit directory.
            validate_slot(slot,messages,config,n,verify_hashes=verify_hashes)
            content,termination=parse_response(raw)
            usages.append(usage_view(raw));answer,metrics=score(content,case.reference)
            result={'skill':skill,'actor':config,'initial_messages':messages,'content':content,'termination':termination,
                    'answer':answer,'metrics':metrics,'api_requests':n,'usage_records':usages}
            freeze(directory/'result.json',result)
            return result
        except RequestFailure as error:
            usages.append(usage_view(raw))
            receipt={'retryable':error.retryable,'error':str(error),
                     'status':'unknown' if 'outcome unknown' in str(error) else 'failed'}
            if verify_hashes:
                receipt['archive'] = archive_hashes(slot)
                receipt['checksum'] = p.digest(receipt)
            save(slot/'error.json',receipt)
            if not error.retryable:raise
            if n<6:time.sleep(config['retry_delay_seconds']*n)
    raise RequestFailure('Actor total request budget exhausted; resume does not reset it',retryable=False)


def execute(case, skill, directory, transport, *, verify_hashes=True):
    """One exclusive task journal; batch recovery also preflights all siblings."""
    p.validate_case(case); p.background(transport.metadata()); p.implementation_identity()
    with locked(directory):
        return _execute(case, skill, directory, transport, verify_hashes=verify_hashes)
