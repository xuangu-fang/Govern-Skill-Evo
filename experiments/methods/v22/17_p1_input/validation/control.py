"""Frozen, once-only P1/v3 probes. No environment, live Skill or Memory publication."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlparse

import fixtures
REPO=fixtures.ROOT
REVISION=fixtures.REVISION
ROOT=fixtures.OUT
from dotenv import load_dotenv
import requests
from src.adapters.alfworld.run_task_skill import RecordingSession,timestamp
from src.adapters.alfworld.skill_runtime import digest,object_digest,write_record
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v22.grouped_update import grouped_messages,realize_editor
from src.skill_evolution.v22.grouped_representation import grouping_messages
from src.skill_evolution.v22.compact_cycle import make_diff
from src.skill_evolution.v22.effective_memory import apply_effective_memory,effective_consumption_payload
from src.skill_evolution.v22 import p1_input


def read(path):return json.loads(Path(path).read_text())
def save(path,value):
    with Path(path).open('x') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def check_originals():
    original=read(ROOT.parent/'baseline.json')['files']
    changed=[name for name,h in original.items() if not (REPO/name).is_file() or digest((REPO/name).read_bytes())!=h]
    if changed:raise ValueError('Preexisting source/archive changed: '+repr(changed))
    return len(original)


def case_data(case):
    d=ROOT/'cases'/case['id']; c=deepcopy(case);c['payload']=read(d/'payload.json')
    b=d/'classification_binding.json';c['classification_binding']=read(b) if b.exists() else None
    return c


def messages_for(case):
    c=case_data(case)
    return (grouping_messages(c['payload'],fixtures.GROUP_PROMPT.read_text(),profile=c['profile'])
            if c['stage']=='classification' else grouped_messages(c['stage'],c['payload']))


def freeze():
    protocol=read(ROOT/'protocol.json')
    assert len(protocol['cases'])==8 and not list((ROOT/'cases').glob('*/attempt.lock'))
    for c in protocol['cases']:
        d=ROOT/'cases'/c['id'];messages=read(d/'messages.json');request=read(d/'request.json')
        assert messages_for(c)==messages
        assert request==dict(c['parameters'],messages=messages)
        assert len(json.dumps(messages,ensure_ascii=False,separators=(',',':')))<=400000
        if c['profile']==p1_input.PROFILE:
            packed=json.loads(messages[1]['content']);decoded=p1_input.decode(packed)
            assert p1_input.decode(p1_input.encode(decoded))==decoded
    files=[p for top in (ROOT,REVISION,Path(__file__).parent) for p in top.rglob('*')
           if p.is_file() and '__pycache__' not in p.parts]
    files+=list((ROOT.parent/'offline').glob('*.json'))+list((ROOT.parent/'offline').glob('*.log'))
    manifest={str(p.relative_to(REPO)):digest(p.read_bytes()) for p in sorted(set(files))}
    save(ROOT/'freeze.json',{'frozen_at':timestamp(),'files':manifest,'manifest_sha256':object_digest(manifest),
        'original_files_verified':check_originals(),'cases':8,'max_calls':8,'max_http_attempts':8,
        'max_concurrent_requests':2,'new_environment_episodes':0,'publication':False})
    print(json.dumps({'frozen_files':len(manifest),'cases':8}),flush=True)


def verify():
    f=read(ROOT/'freeze.json');assert object_digest(f['files'])==f['manifest_sha256']
    for name,h in f['files'].items():assert digest((REPO/name).read_bytes())==h,name
    return check_originals()


def validate(case,value,d):
    case=case_data(case)
    accepted=fixtures.validate_output(case,value)
    save(d/'contract_result.json',{'validation_only':True,'accepted':accepted})
    if case['stage']=='editor' and value['decision']!='needs_revision':
        candidate,plan=realize_editor(value,case['payload'])
        save(d/'realization.json',{'unexecuted_probe_only':True,'candidate':candidate,'plan':plan})
        if candidate:(d/'actual.diff').write_text(make_diff(case['payload']['parent'],candidate))
    elif case['stage']=='learn':
        p=case['payload'];context='p1-validation-only-'+object_digest(p)
        memory=apply_effective_memory(p['memory'],value,context,p)
        save(d/'probe_memory.json',{'not_published':True,'context_id':context,'memory':memory})
        view=deepcopy(p);view['memory']=memory
        save(d/'probe_memory_view.json',effective_consumption_payload(view))


def run_one(case,endpoint,key):
    verify();d=ROOT/'cases'/case['id'];save(d/'attempt.lock',{'reserved_at':timestamp(),'maximum_attempts':1})
    request=read(d/'request.json');record={'schema_version':'v22.p1_semantic_probe_call.v1','stage':case['stage'],
       'case_id':case['id'],'model':request['model'],'profile':case['profile'],'status':'requesting',
       'started_at':timestamp(),'request_sha256':object_digest(request),'messages_sha256':object_digest(request['messages']),
       'endpoint_host':urlparse(endpoint).hostname,'retries':0,'steps':[{'phase':'requesting','messages_sha256':object_digest(request['messages'])}]}
    result={'case_id':case['id'],'strict_json':False,'production_json':False,'contract_valid':False,
            'model_semantics':'requires separate evidence review'}
    started=time.monotonic();print(json.dumps({'started':case['id'],'at':record['started_at']}),flush=True)
    try:
        with requests.Session() as session:
            session.trust_env=False;session.mount('https://',requests.adapters.HTTPAdapter(max_retries=0))
            response=RecordingSession(session,record,d/'call.json',archive_responses=True).post(endpoint,
                headers={'Authorization':'Bearer '+key},json=request,timeout=(10,case['timeout_seconds']),allow_redirects=False)
        result['http_status']=response.status_code
        if not 200<=response.status_code<300:raise RuntimeError('HTTP failure')
        body=response.json();save(d/'response.json',body);result['usage']=body.get('usage')
        record['steps'][0]['transport_attempts'][-1]['usage']=body.get('usage')
        result['provider_model']=body.get('model');choice=body['choices'][0];result['finish_reason']=choice.get('finish_reason')
        content=choice['message'].get('content');(d/'content.txt').write_text(content if isinstance(content,str) else repr(content))
        record['status']='responded';record['steps'][0]['phase']='responded'
        if choice.get('finish_reason')=='length':raise RuntimeError('Completion truncated')
        try:json.loads(content);result['strict_json']=True
        except (ValueError,TypeError):pass
        value=parse_json_response(content);result['production_json']=True;save(d/'parsed.json',value)
        try:validate(case,value,d)
        except Exception as e:result.update(validation_error_type=type(e).__name__,validation_error=str(e))
        else:result['contract_valid']=True
        result['decision']=value.get('decision')
    except Exception as e:
        result['error_type']=type(e).__name__;record['status']='error';record['error_type']=type(e).__name__
        # Only known pure validation exceptions may be recorded with text.
        if isinstance(e,ValueError) and result.get('http_status')==200:result['parse_error']=str(e)
    finally:
        record['finished_at']=timestamp();record['elapsed_seconds']=time.monotonic()-started
        result['elapsed_seconds']=record['elapsed_seconds'];result['attempts']=len(record['steps'][0].get('transport_attempts',[]))
        write_record(d/'call.json',record);save(d/'result.json',result)
        print(json.dumps({'finished':case['id'],**result},ensure_ascii=False),flush=True)
    return result


def run():
    verify();cases=read(ROOT/'protocol.json')['cases'];assert len(cases)==8
    assert not list((ROOT/'cases').glob('*/attempt.lock')),'Never resample an already reserved case'
    save(ROOT/'execution_claim.json',{'started_at':timestamp(),'pid':os.getpid(),'maximum_attempts':8})
    load_dotenv(REPO/'.env',override=False)
    base=os.environ.get('OPENAI_BASE_URL','').rstrip('/');key=os.environ.get('OPENAI_API_KEY')
    assert key and urlparse(base).hostname=='llm-proxy.intra.xiaojukeji.com'
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(run_one,c,base+'/chat/completions',key) for c in cases]
        results=[job.result() for job in jobs]
    save(ROOT/'run_summary.json',{'completed_at':timestamp(),'results':results,
        'total_attempts':sum(x['attempts'] for x in results),'environment_episodes':0,'publication':False,
        'original_files_verified':verify()})

if __name__=='__main__':{'freeze':freeze,'verify':lambda:print(verify()),'run':run}[sys.argv[1]]()
