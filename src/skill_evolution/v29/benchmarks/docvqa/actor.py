"""Durable one-round Actor; explicit credentials and six shared request attempts."""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import time
import requests

from src.skill_evolution.v27.transport import RequestFailure, http_failure
from src.skill_evolution.v27.benchmarks.lmb.actor import parse_response, usage_view
from ...storage import read, save, freeze, now
from . import protocol as p
from .scoring import score


@contextmanager
def locked(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.execution.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def request_record(messages, config):
    p.validate_config(config)
    return {'endpoint': config['endpoint'], 'body': {
        **{k: deepcopy(config[k]) for k in
           ('model', 'temperature', 'max_tokens', 'reasoning_effort', 'thinking')},
        'messages': deepcopy(messages), 'stream': False}}


class ChatTransport:
    def __init__(self, api_key, *, session_factory=requests.Session):
        p.nonempty_text(api_key, 'Explicit API key')
        self.api_key = api_key
        self.session_factory = session_factory

    def metadata(self):
        return p.actor_config()

    def __call__(self, messages, directory):
        directory = Path(directory)
        config = self.metadata()
        request = request_record(messages, config)
        freeze(directory / 'request.json', request)
        try:
            with self.session_factory() as session:
                for prefix in ('http://', 'https://'):
                    session.mount(prefix, requests.adapters.HTTPAdapter(max_retries=0))
                response = session.post(request['endpoint'], json=request['body'],
                    headers={'Authorization': 'Bearer ' + self.api_key},
                    timeout=(config['connect_timeout_seconds'], config['timeout_seconds']),
                    allow_redirects=False)
        except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError) as error:
            raise RequestFailure(type(error).__name__) from None
        (directory / 'http_response.txt').write_bytes(response.content)
        save(directory / 'http_status.json', {'status_code': response.status_code})
        if not 200 <= response.status_code < 300:
            raise http_failure(response.status_code, response.text)
        try:
            return response.json()
        except ValueError:
            raise RequestFailure('Malformed API JSON') from None


def _response(slot):
    raw = read(slot / 'response.json') if (slot / 'response.json').exists() else None
    if (slot / 'http_status.json').exists():
        status = read(slot / 'http_status.json')['status_code']
        body = (slot / 'http_response.txt').read_text(encoding='utf-8')
        if not 200 <= status < 300:
            p.require(raw is None, 'Failed HTTP request has a decoded success response')
            raise http_failure(status, body)
        try:
            decoded = json.loads(body)
        except ValueError:
            p.require(raw is None, 'Decoded response conflicts with malformed HTTP JSON')
            raise RequestFailure('Malformed API JSON') from None
        p.require(raw is None or raw == decoded, 'Response copies differ')
        return decoded
    p.require(not (slot / 'http_response.txt').exists(), 'Missing HTTP status')
    return raw


def _signature(case, skill, config, messages):
    return {'case_id': case.case_id, 'payload': dict(case.payload), 'reference': case.reference,
            'metadata': dict(case.metadata), 'skill': skill, 'actor': config,
            'messages': messages, 'prompt': p.PROMPT_PROFILE, 'scorer': p.SCORER_PROFILE}


def _attempt(slot, number, messages, config):
    """Read-only classification, including interrupted and prepared requests."""
    started = (slot / 'request_started.json').exists()
    if started or (slot / 'request.json').exists():
        freeze(slot / 'request.json', request_record(messages, config), read_only=True)
    receipt = read(slot / 'error.json') if (slot / 'error.json').exists() else None
    if not started:
        p.require(receipt is None and not any((slot / name).exists() for name in
                  ('response.json', 'http_status.json', 'http_response.txt')), 'Response without started request')
        return None, None
    marker = read(slot / 'request_started.json')
    p.require(marker.get('attempt') == number and isinstance(marker.get('at'), str), 'Invalid attempt marker')
    raw, failure = None, None
    try:
        raw = _response(slot)
        if raw is not None:
            parse_response(raw)
        elif receipt is None:
            failure = RequestFailure('Interrupted request; outcome unknown')
    except RequestFailure as error:
        failure = error
    if receipt is not None:
        p.require(set(receipt) == {'error', 'retryable'} and type(receipt['retryable']) is bool
                  and isinstance(receipt['error'], str), 'Invalid failure record')
        if raw is not None or (slot / 'http_status.json').exists():
            p.require(failure is not None and receipt == _failure_record(failure),
                      'Failure record differs from saved response')
        failure = RequestFailure(receipt['error'], retryable=receipt['retryable'])
    return raw, failure


def _failure_record(error):
    return {'error': str(error), 'retryable': error.retryable}


def _journal(directory, case, skill, config, messages):
    freeze(directory / 'signature.json', _signature(case, skill, config, messages), read_only=True)
    attempts = directory / 'attempts'
    slots = sorted(q for q in attempts.iterdir() if q.is_dir()) if attempts.exists() else []
    p.require(len(slots) <= 6 and [q.name for q in slots] == [f'{n:03}' for n in range(1, len(slots) + 1)],
              'Invalid attempt sequence')
    states = [_attempt(slot, n, messages, config) for n, slot in enumerate(slots, 1)]
    for slot, (_, failure) in zip(slots[:-1], states[:-1]):
        p.require((slot / 'error.json').exists() and failure is not None and failure.retryable,
                  'A completed, prepared or terminal attempt cannot have a later request')
    return slots, states


def _result(skill, config, messages, raw, states):
    content, termination = parse_response(raw)
    return {'skill': skill, 'actor': deepcopy(config), 'initial_messages': deepcopy(messages),
            'content': content, 'termination': termination,
            'api_requests': len(states), 'usage_records': [usage_view(r) for r, _ in states]}


def _scored_result(case, skill, config, messages, raw, states):
    result = _result(skill, config, messages, raw, states)
    result['answer'], result['metrics'] = score(result['content'], case.reference)
    return result


def read_completed(case, skill, directory, config=None):
    config = p.validate_config(p.actor_config() if config is None else config)
    messages = p.messages_for_case(case, skill)
    directory = Path(directory)
    slots, states = _journal(directory, case, skill, config, messages)
    p.require(bool(states) and states[-1][0] is not None and states[-1][1] is None,
              'No completed stop response')
    expected = _scored_result(case, skill, config, messages, states[-1][0], states)
    freeze(directory / 'result.json', expected, read_only=True)
    return expected


def validate_pending(case, skill, directory, config=None):
    config = p.validate_config(p.actor_config() if config is None else config)
    messages = p.messages_for_case(case, skill)
    directory = Path(directory)
    if not directory.exists() or not any(q.name != '.execution.lock' for q in directory.iterdir()):
        return
    if (directory / 'result.json').exists() or (directory / 'trajectory.json').exists():
        read_completed(case, skill, directory, config)
    else:
        _, states = _journal(directory, case, skill, config, messages)
        if states and states[-1][1] is not None and not states[-1][1].retryable:
            raise states[-1][1]
        if len(states) == 6 and states[-1][1] is not None:
            raise RequestFailure('Actor total request budget exhausted; resume does not reset it', retryable=False)


def execute(case, skill, directory, transport):
    """Execute or resume one task. No score-based retries or hidden SDK retries."""
    config = p.validate_config(transport.metadata())
    messages = p.messages_for_case(case, skill)
    directory = Path(directory)
    with locked(directory):
        if (directory / 'result.json').exists() or (directory / 'trajectory.json').exists():
            return read_completed(case, skill, directory, config)
        if any(q.name != '.execution.lock' for q in directory.iterdir()):
            p.require((directory / 'signature.json').exists(), 'Missing task identity for existing journal')
        freeze(directory / 'signature.json', _signature(case, skill, config, messages))
        slots, states = _journal(directory, case, skill, config, messages)
        for number in range(1, 7):
            slot = directory / 'attempts' / f'{number:03}'
            slot.mkdir(parents=True, exist_ok=True)
            raw, failure = states[number - 1] if number <= len(states) else (None, None)
            if failure is not None and (slot / 'error.json').exists():
                if not failure.retryable:
                    raise failure
                continue
            try:
                if failure is not None:
                    raise failure
                if raw is None:
                    freeze(slot / 'request.json', request_record(messages, config))
                    save(slot / 'request_started.json', {'at': now(), 'attempt': number})
                    raw = transport(deepcopy(messages), slot)
                    save(slot / 'response.json', raw)
                # Validate HTTP/decoded copies before committing a scored result.
                raw, failure = _attempt(slot, number, messages, config)
                if failure is not None:
                    raise failure
                parse_response(raw)
                current = (raw, None)
                if number <= len(states):
                    states[number - 1] = current
                else:
                    states.append(current)
                result = _scored_result(case, skill, config, messages, raw, states[:number])
                freeze(directory / 'result.json', result)
                return result
            except RequestFailure as error:
                save(slot / 'error.json', _failure_record(error))
                # Length responses remain raw execution records, never optimizer evidence.
                current = (raw, error)
                if number <= len(states):
                    states[number - 1] = current
                else:
                    states.append(current)
                if not error.retryable:
                    raise
                if number < 6:
                    time.sleep(config['retry_delay_seconds'] * number)
        raise RequestFailure('Actor total request budget exhausted; resume does not reset it', retryable=False)
