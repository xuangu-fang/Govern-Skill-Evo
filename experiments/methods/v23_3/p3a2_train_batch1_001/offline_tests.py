"""Synthetic transport tests only; never experimental model evidence."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch,MagicMock
import requests
from . import transport as t

def response(code=200,headers=None,body=None):
 r=requests.Response();r.status_code=code;r.headers.update(headers or {});r._content=json.dumps(body if body is not None else {'choices':[{'message':{'content':'test'},'finish_reason':'stop'}]}).encode();return r
class Fake:
 def __init__(self,items):self.items=items;self.bodies=[]
 def post(self,*a,**kw):
  self.bodies.append(kw['json']);v=self.items.pop(0)
  if isinstance(v,Exception):raise v
  return v

def main():
 results=[];original=t.HERE
 def case(label,items,expected,raises=False):
  with tempfile.TemporaryDirectory(dir=original,prefix='offline_') as temp:
   root=Path(temp);t.save(root/'config.json',{'timeout':[60,300],'minimum_request_interval_seconds':3});fake=Fake(items);d=root/'call';body={'messages':[{'role':'user','content':'immutable'}]}
   with patch.object(t,'HERE',root),patch.object(t,'ARCHIVE',root),patch.object(t,'reserve_start',return_value=0),patch.object(t,'sleep_until',return_value=0),patch.object(t.socket,'create_connection',return_value=MagicMock()):
    try:t.BoundedSession(fake,d).post('http://example.invalid',json=body);assert not raises
    except RuntimeError:assert raises
    except requests.ReadTimeout:assert raises
    assert len(fake.bodies)==expected and all(b==body for b in fake.bodies)
    st=t.read(d/'state.json');before=len(fake.bodies)
    if st['status']=='received':t.BoundedSession(fake,d).post('http://example.invalid',json=body)
    else:
     try:t.BoundedSession(fake,d).post('http://example.invalid',json=body);raise AssertionError('must block')
     except RuntimeError:pass
    assert len(fake.bodies)==before
   results.append({'case':label,'passed':True,'attempts':expected,'final_state':st['status']})
 err={'error':{'message':'temporary rate limit'}}
 case('429 then success',[response(429,{'Retry-After':'15'},err),response()],2)
 case('502 then success',[response(502,body=err),response()],2)
 case('503 then success',[response(503,body=err),response()],2)
 case('five 429 exhausted',[response(429,body=err) for _ in range(5)],5,True)
 case('quota no retry',[response(429,body={'error':'insufficient_quota'})],1)
 case('length no retry',[response(body={'choices':[{'message':{'content':'partial'},'finish_reason':'length'}]})],1)
 case('invalid JSON content no retry',[response(body={'choices':[{'message':{'content':'not JSON'},'finish_reason':'stop'}]})],1)
 case('ambiguous read timeout',[requests.ReadTimeout('test')],1,True)
 case('Retry-After over budget',[response(429,{'Retry-After':'601'},err)],1,True)
 assert t.retry_delay(429,{'Retry-After':'Thu, 01 Jan 1970 00:02:00 GMT'},'{}',1,100)==20
 assert t.retry_delay(429,{},'{}',4,0)==120
 assert t.retry_delay(429,{},json.dumps({'choices':[{'message':{'content':'answer'}}]}),1,0) is None
 results += [{'case':'HTTP date and exponential delay and error with answer','passed':True}]
 t.save(original/'offline_test_results.json',{'synthetic_only':True,'network_requests':0,'tests':results})
 print('Passed',len(results),'offline transport cases')
if __name__=='__main__':main()
