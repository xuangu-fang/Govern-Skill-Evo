"""Bounded transport only. Persistent call journals prevent resampling on restart."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import fcntl
from pathlib import Path
import socket
import time
import traceback
from urllib.parse import urlsplit
import requests
from src.adapters.alfworld.skill_runtime import write_record

from .archive_io import HERE,ARCHIVE

def now():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text())
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);write_record(p,v)
def sleep_until(deadline):
    start=time.time()
    while time.time()<deadline:time.sleep(min(30,deadline-time.time()))
    return time.time()-start

def rate_update(deadline, status=None):
    with (ARCHIVE/'rate.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        p=ARCHIVE/'throttle.json';v=read(p) if p.exists() else {'not_before':0}
        v['not_before']=max(v['not_before'],deadline)
        if status==429:
            v['consecutive_429']=v.get('consecutive_429',0)+1
            if v['consecutive_429']>=2:v['request_concurrency_limit']=1
        elif status is not None and 200<=status<300:v['consecutive_429']=0
        save(p,v)

def reserve_start(own_deadline, wait_deadline=None):
    start=time.time()
    while True:
        with (ARCHIVE/'rate.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            p=ARCHIVE/'throttle.json';v=read(p) if p.exists() else {'not_before':0}
            deadline=max(v['not_before'],own_deadline)
            if wait_deadline is not None and max(time.time(),deadline)>wait_deadline:raise RuntimeError('Shared queue wait budget exhausted')
            if deadline<=time.time():
                v['not_before']=time.time()+read(HERE/'config.json')['minimum_request_interval_seconds'];save(p,v)
                return time.time()-start
        sleep_until(deadline)

class RequestSlot:
    def __enter__(self):
        started=time.time()
        while True:
            if time.time()-started>600:raise RuntimeError('Request slot wait exceeded 600 seconds')
            state=read(ARCHIVE/'throttle.json') if (ARCHIVE/'throttle.json').exists() else {}
            limit=state.get('request_concurrency_limit',read(HERE/'config.json').get('concurrency',1))
            for i in range(limit):
                f=(ARCHIVE/f'request_slot_{i}.lock').open('a')
                try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);self.file=f;return self
                except BlockingIOError:f.close()
            time.sleep(.1)
    def __exit__(self,*args):self.file.close()

def retry_delay(status,headers,text,index,current):
    if status not in {429,502,503}:return None
    if any(x in text.lower() for x in ['insufficient_quota','quota_exceeded','quota exhausted','permission_denied','额度耗尽','余额不足']):return None
    # Never discard an answer embedded in a nominal error response.
    try:
        value=json.loads(text)
        if any(c.get('message',{}).get('content') or c.get('message',{}).get('reasoning_content') for c in value.get('choices',[])):return None
    except (ValueError,TypeError,AttributeError):pass
    ra=headers.get('Retry-After') or headers.get('retry-after')
    if ra:
        try:return max(0,float(ra))
        except ValueError:
            try:return max(0,parsedate_to_datetime(ra).timestamp()-current)
            except (ValueError,TypeError,OverflowError):pass
    return [15,30,60,120][min(index-1,3)]

class BoundedSession:
    def __init__(self,session,directory,*,record=None,output=None):
        self.session=session;self.directory=Path(directory);self.record=record;self.output=output
    def post(self,endpoint,**kwargs):
        d=self.directory;d.mkdir(parents=True,exist_ok=True)
        cfg=read(HERE/'config.json');body=kwargs['json'];kwargs['timeout']=tuple(cfg['timeout']);kwargs['allow_redirects']=False
        chars=len(json.dumps(body['messages'],ensure_ascii=False));assert chars<=cfg.get('max_input_chars',4000000)
        req={'message_characters':chars,'rough_input_tokens_chars_div_3':round(chars/3),'estimate_not_provider_tokenizer':True,'endpoint':endpoint,'body':body,'timeout':cfg['timeout'],'actual_body_bytes':len(requests.Request('POST',endpoint,json=body).prepare().body)}
        if (d/'request.json').exists():assert read(d/'request.json')==req,'Cannot change a logical request'
        else:save(d/'request.json',req)
        state=read(d/'state.json') if (d/'state.json').exists() else {'logical_call_id':str(d.relative_to(ARCHIVE if d.is_relative_to(ARCHIVE) else HERE)),'status':'ready','attempts':[],'wait_seconds':0,'started_at':now()}
        if state['status']=='received':
            row=state['attempts'][-1];response=requests.Response();response.status_code=row['http_status'];response._content=(d/f"attempt_{row['attempt_index']:02}/response.bin").read_bytes();response.headers.update(row['headers']);return response
        if state['status'] not in {'ready','waiting'}:raise RuntimeError('Archived call is exhausted, stopped, or has uncertain outcome; no retry budget reset')
        while len(state['attempts'])<5:
            waited=sleep_until(state.get('not_before',0))
            state['wait_seconds']+=waited
            if state['wait_seconds']>600:
                state['status']='wait_budget_exhausted';save(d/'state.json',state);raise RuntimeError('Cumulative wait exceeds 600 seconds')
            index=len(state['attempts'])+1;attempt=d/f'attempt_{index:02}';attempt.mkdir(exist_ok=False)
            row={'logical_call_id':state['logical_call_id'],'attempt_index':index,'started_at':now(),'actual_wait_before_seconds':waited,'http_status':None,'usage':None,'request_sent':False}
            state['attempts'].append(row);state['status']='in_flight';save(d/'state.json',state)
            response=None;presend=False
            try:
                # Reserve concurrency before the shared start/cooldown gate.
                queued=time.time()
                with RequestSlot():
                    reserve_start(state.get('not_before',0), queued+max(0,600-state['wait_seconds']))
                    extra=time.time()-queued;state['wait_seconds']+=extra;row['actual_wait_before_seconds']+=extra
                    if state['wait_seconds']>600:raise RuntimeError('Cumulative wait exceeds 600 seconds')
                    u=urlsplit(endpoint)
                    with socket.create_connection((u.hostname,u.port or (443 if u.scheme=='https' else 80)),timeout=10):pass
                    presend=True;row['request_sent']=True;row['request_started_at']=now();save(d/'state.json',state)
                    response=self.session.post(endpoint,**kwargs)
                    early_delay=retry_delay(response.status_code,response.headers,response.text,index,time.time())
                    if early_delay is not None:rate_update(time.time()+early_delay)
                (attempt/'response.bin').write_bytes(response.content)
                row.update(http_status=response.status_code,headers=dict(response.headers),retry_after=response.headers.get('Retry-After'),request_id=response.headers.get('x-request-id') or response.headers.get('request-id'))
                try:row['usage']=response.json().get('usage')
                except (ValueError,AttributeError):pass
                delay=retry_delay(response.status_code,response.headers,response.text,index,time.time())
                if self.record is not None:
                    event=self.record['steps'][-1];event['transport_attempts'][-1]['usage']=row['usage'];save(self.output,self.record)
                if delay is None:
                    state['status']='received';save(d/'state.json',state);return response
            except (Exception,KeyboardInterrupt) as exc:
                (attempt/'traceback.txt').write_text(traceback.format_exc())
                row.update(error_type=type(exc).__name__,error=str(exc),result_uncertain=presend)
                if not presend and isinstance(exc,(OSError,requests.ConnectionError)):
                    delay=[15,30,60,120][min(index-1,3)]
                else:
                    state['status']='uncertain' if presend else 'stopped';save(d/'state.json',state);raise
            finally:
                row['finished_at']=now();save(attempt/'attempt.json',row);save(d/'state.json',state)
                rate_update(time.time()+cfg['minimum_request_interval_seconds'],row['http_status'])
            if index>=5 or state['wait_seconds']+delay>600:
                state['status']='retry_exhausted' if index>=5 else 'retry_after_exceeds_wait_budget';save(d/'state.json',state)
                raise RuntimeError(state['status'])
            state.update(status='waiting',not_before=time.time()+max(delay,cfg['minimum_request_interval_seconds']))
            save(d/'state.json',state);rate_update(state['not_before'])
            print(f"RETRY {state['logical_call_id']} attempt={index} HTTP={row['http_status']} wait={delay}s",flush=True)
        raise RuntimeError('Retry budget exhausted')
