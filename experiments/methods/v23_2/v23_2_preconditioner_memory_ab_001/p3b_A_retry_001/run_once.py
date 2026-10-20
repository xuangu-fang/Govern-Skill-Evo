"""User-authorized A-only retry: original frozen request, one HTTP attempt, no automatic retries."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import time
from unittest.mock import patch
import requests
from dotenv import dotenv_values
from src.skill_evolution.v23 import grouping, preconditioner as pc, memory, evolution as ev
from src.skill_evolution.v22.diagnosis_editor import parse_json_response

E=Path(__file__).resolve().parent
P=E.parent
ROOT=P.parents[3]
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x): ev.save(p,x)

def preflight():
    for manifest in ['freeze.json','input_manifest.json']:
        for p,h in read(P/'config'/manifest)['files_sha256'].items():assert sha(P/p)==h,p
    for p,h in read(P/'config/source_hashes.json').items():assert sha(ROOT/p)==h,p
    r={a:read(P/f'requests/{a}_UNSENT.json') for a in ['A','B']}
    payloads={a:json.loads(x['body']['messages'][1]['content']) for a,x in r.items()}
    assert payloads['A']['memory']==memory.empty_memory()
    active=ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/memory'
    assert payloads['B']['memory']==memory.load_memory(active)==read(P/'config/memory_B.json')
    assert [e['id'] for e in payloads['B']['memory']['entries']]==['M1','M2','M3','M6','M7','M8','M9']
    a,b=deepcopy(r['A']),deepcopy(r['B'])
    for x in [a,b]:
        j=json.loads(x['body']['messages'][1]['content']);j.pop('memory');x['body']['messages'][1]['content']=j
    assert a==b
    cfg=read(P/'config/call_config.json')['call_config']
    for arm,req in r.items():
        assert req['endpoint']==cfg['endpoint'] and req['timeout_seconds']==cfg['timeout_seconds']
        assert {k:v for k,v in req['body'].items() if k!='messages'}=={k:v for k,v in cfg.items() if k not in ['endpoint','timeout_seconds']}
        assert payloads[arm]['plan']==read(P/'config/original_plan.json')
        assert [x['ref'] for x in payloads[arm]['runs']]==['P1','P3','P6','P7','P8','P10']
        memory.validate_memory(payloads[arm]['memory'])
    receipt={'at':ev.now(),'request_hashes':{a:sha(P/f'requests/{a}_UNSENT.json') for a in r},
             'freeze_hashes_pass':True,'source_hashes_pass':True,'only_memory_diff':True,'active_memory_exact':True,
             'no_capacity_probe':True,'automatic_retries':0,'request_model':cfg['model'],'endpoint':cfg['endpoint'],
             'runner_sha256':sha(Path(__file__))}
    save(E/'config/preflight.json',receipt)
    return r,payloads,cfg

def run():
    assert (E/'config/protected_before.json').exists(), 'Protection snapshot must precede calls'
    # Atomic one-shot claim: an interrupted process may not be silently rerun.
    with (E/'config/execution_claim.json').open('x') as f:json.dump({'at':ev.now(),'order':['A'],'maximum_requests':1,'automatic_retries':0},f)
    frozen,payloads,cfg=preflight()
    vals=dotenv_values(ROOT/'.env')
    key=os.environ.get('OPENAI_API_KEY') or vals.get('OPENAI_API_KEY')
    assert key,'Credential missing; no request sent'
    base=cfg['endpoint'].removesuffix('/chat/completions')
    generate=grouping.live_generator(base_url=base,key=key,model=cfg['model'],max_tokens=cfg['max_tokens'],timeout=cfg['timeout_seconds'])
    assert generate.call_config==cfg
    summaries={};original_post=requests.Session.post
    total=0
    for arm in ['A']:
        dest=E/'runs'/arm;dest.mkdir(exist_ok=False)
        req=frozen[arm];count=0;stage='transport';started=time.monotonic()
        meta={'arm':arm,'started_at':ev.now(),'request_model':cfg['model'],'status':'requesting','automatic_retries':0}
        save(dest/'run.json',meta)
        print('START '+arm,flush=True)
        def guarded_post(session,url,**kwargs):
            nonlocal count,total
            assert count==0 and total<1,'HTTP attempt budget exceeded'
            assert url==req['endpoint'] and kwargs['json']==req['body']
            assert kwargs['timeout']==(10,req['timeout_seconds']) and kwargs['allow_redirects'] is False
            assert session.trust_env is False
            assert all(adapter.max_retries.total==0 for adapter in session.adapters.values())
            assert read(dest/'request.json')==req
            assert sha(dest/'request.json')==sha(P/f'requests/{arm}_UNSENT.json')
            count+=1;total+=1
            save(dest/'dispatch.json',{'at':ev.now(),'attempt':count,'total_attempts':total,'request_sha256':sha(dest/'request.json'),'body_equals_frozen':True,'transport_retries':0})
            return original_post(session,url,**kwargs)
        common=False
        try:
            with patch.object(requests.Session,'post',guarded_post):
                response=generate(req['body']['messages'],dest)
            save(dest/'response.json',response)
            (dest/'raw_output.txt').write_text(response.get('content') or '')
            save(dest/'usage.json',{'usage':response.get('usage'),'response_model':response.get('response_model'),'finish_reason':response.get('finish_reason')})
            stage='completion'
            if response.get('finish_reason')!='stop':raise ValueError('Model response did not finish normally')
            stage='json_parse';parsed=parse_json_response(response['content']);save(dest/'parsed.json',parsed)
            stage='schema_compile';effective=pc.compile_effective_plan(parsed,payloads[arm])
            save(dest/'preconditioner.json',parsed);save(dest/'effective_plan.json',effective)
            if effective is not None:
                assert effective['goal']==payloads[arm]['plan']['goal']
                assert pc.compile_effective_plan(parsed,payloads[arm])==effective
            save(dest/'validation.json',{'valid':True,'decision':parsed['decision'],'effective_null':effective is None,'deterministic_recompile':True})
            meta.update(status='valid',decision=parsed['decision'],response_model=response.get('response_model'),finish_reason=response.get('finish_reason'),usage=response.get('usage'))
        except Exception as exc:
            err={'type':type(exc).__name__,'message':str(exc),'stage':stage,'automatic_retries':0}
            save(dest/'error.json',err);save(dest/'validation.json',{'valid':False,**err})
            meta.update(status='technical_failure',error=err)
            http=read(dest/'http_status.json')['status_code'] if (dest/'http_status.json').exists() else None
            common=(count==0 and isinstance(exc,AssertionError)) or http in [401,403,404] or (isinstance(exc,requests.ConnectionError) and not isinstance(exc,requests.Timeout))
            if (dest/'http_response.txt').exists():
                try:
                    raw=read(dest/'http_response.txt')
                    meta['usage']=raw.get('usage');meta['response_model']=raw.get('model')
                    if http==400:
                        message=json.dumps(raw.get('error',{})).lower()
                        common=common or any(x in message for x in ['model not found','invalid model','unsupported model','invalid api key'])
                    save(dest/'usage.json',{'usage':raw.get('usage'),'response_model':raw.get('model'),'finish_reason':None})
                except (ValueError,AttributeError): pass
            meta['common_configuration_block']=common
        finally:
            meta.update(finished_at=ev.now(),elapsed_seconds=time.monotonic()-started,http_attempts=count)
            save(dest/'run.json',meta);summaries[arm]=meta
            save(E/'results/summary.json',{'groups':summaries,'logical_calls_started':len(summaries),'http_attempts':total,'automatic_retries':0,'complete':True})
            print('FINISH '+arm+' '+meta['status']+' '+str(round(meta['elapsed_seconds'],2))+'s',flush=True)
        if common:
            save(E/'results/stop.json',{'after_arm':arm,'kind':'shared_transport_or_configuration_block','remaining_arm_not_sent':arm=='A','reason':meta.get('error')})
            break
    assert total<=1

if __name__=='__main__':run()
