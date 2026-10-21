"""Batch-1 only. Isolated coordination; production policies and engines unchanged."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import requests
from dotenv import dotenv_values
from .transport import HERE,now,read,save,BoundedSession
from src.adapters.alfworld.skill_runtime import digest,load_skill,make_record,execution_protocol,implementation_metadata
from src.adapters.alfworld.run_task_skill import environment_modules,installed_versions,run_episode,RecordingSession
from src.adapters.alfworld.run_task_upstream import chat
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v23 import grouping,editor,preconditioner as oldpc
from src.skill_evolution.v23.facts import build_facts
from src.skill_evolution.v23_3 import diagnosis,preconditioner as pc
from src.skill_evolution.v23_3.memory_view import project_messages,FORMAT
from src.skill_evolution.v23_3.update_patch import normalize_update_patches
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
ROOT=HERE.parents[3];OLD=HERE.parent/'p3c1_r05_replay_001';MEM=HERE.parent/'memory_v3_integration_001'
COMPLETE={'success','step_limit','environment_ended'}
def sha(p):return digest(Path(p).read_bytes())
def creds():
    v={**dotenv_values(ROOT/'.env'),**os.environ};return v['OPENAI_API_KEY'],v['OPENAI_BASE_URL'].rstrip('/')+'/chat/completions'
def config():return read(HERE/'config.json')
def cc(stage):
    c=config();return {'endpoint':c['endpoint'],'model':c['model'],'temperature':1.0,'thinking':{'type':'enabled'},'reasoning_effort':'medium','stream':False,'max_tokens':c['max_tokens'][stage],'timeout_seconds':300}
def verify():
    for path,h in read(HERE/'freeze.json')['files'].items():assert sha(path)==h,path
    assert creds()[1]==config()['endpoint']
def prepare():
    assert not (HERE/'config.json').exists()
    key,endpoint=creds();assert key and '.intra.' in endpoint
    save(HERE/'config.json',{'endpoint':endpoint,'model':'deepseek-v4.1-flash','max_tokens':{'grouping':8192,'diagnosis':16384,'preconditioner':32768,'editor':16384,'actor':16384},'timeout':[60,300],'minimum_request_interval_seconds':3,'concurrency':1,'max_attempts_per_call':5,'max_wait_seconds_per_call':600,'max_modules':6,'max_episodes':18,'max_actor_decisions':900,'seed':42,'max_steps':50,'max_input_chars':4000000})
    prereg=read(OLD/'new_train_cases.json');items=[x for x in prereg['tasks'] if x['batch']==1];assert len(items)==6 and len({x['instance'] for x in items})==6
    excluded={x['identity'] for x in read(OLD/'new_train_exclusions.json')};assert not excluded & {x['instance'] for x in items}
    save(HERE/'manifest.json',items)
    (HERE/'parent.md').write_bytes((OLD/'parent.md').read_bytes())
    memory=read(MEM/'config/full_payload.json')['memory'];assert [e['id'] for e in memory['entries']]==['M1','M2','M3','M6','M7','M8','M9'];save(HERE/'memory.json',memory)
    assert (HERE/'parent.md').read_text()==read(MEM/'config/full_payload.json')['parent']
    tw,wrapper=environment_modules();tasks=[]
    for i,item in enumerate(items,1):
        game=Path('/Users/didi/.cache/alfworld')/item['gamefile'];resets=[]
        for _ in range(2):
            env=tw.start(str(game),tw.EnvInfos(won=True,admissible_commands=True),wrappers=[wrapper(shuffle=False)])
            try:
                env.seed(42);s=env.reset();resets.append({'observation':s.feedback,'commands':list(s.admissible_commands)})
            finally:env.close()
        assert resets[0]==resets[1]
        tasks.append({'ref':f'P{i}','item':item,'task_request':resets[0]['observation'].split('Your task is to: ',1)[1].strip(),'gamefile':str(game),'game_sha256':sha(game),'reset':resets[0]})
    save(HERE/'tasks.json',tasks);save(HERE/'preflight.json',{'at':now(),'versions':installed_versions(),'protocol':execution_protocol(50),'implementation':implementation_metadata(),'train_source':str(OLD/'new_train_cases.json'),'overlap_with_frozen_exclusions':False,'independence_limit':'Prior screening used bounded text prefixes; unknown aliases or external exposure not excluded.','reset_only':True})
    print([(t['ref'],t['task_request']) for t in tasks],flush=True)
def freeze():
    files=[HERE/x for x in ['run.py','transport.py','PROTOCOL.md','config.json','tasks.json','preflight.json','manifest.json','memory.json','parent.md','offline_test_results.json']]
    for folder in ['src/skill_evolution/v23','src/skill_evolution/v23_3','src/adapters/alfworld']:
        files += [p for p in (ROOT/folder).iterdir() if p.suffix in {'.py','.md'}]
    files += [Path(t['gamefile']) for t in read(HERE/'tasks.json')]+[OLD/'new_train_cases.json',OLD/'new_train_exclusions.json',OLD/'parent.md',MEM/'config/full_payload.json']
    assert not (HERE/'freeze.json').exists();save(HERE/'freeze.json',{'at':now(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'files':{str(p):sha(p) for p in files}})
def budget(messages,stage,out):
    body={k:v for k,v in cc(stage).items() if k not in {'endpoint','timeout_seconds'}};body['messages']=messages
    chars=len(json.dumps(messages,ensure_ascii=False));assert chars<=config()['max_input_chars']
    nbytes=len(json.dumps(body,ensure_ascii=False).encode());save(out/'input_budget.json',{'at':now(),'message_characters':chars,'utf8_body_bytes':nbytes,'rough_input_tokens_chars_div_3':round(chars/3),'estimate_not_provider_tokenizer':True,'max_output_tokens':body['max_tokens'],'service_context_limit_not_independently_asserted':True,'no_evidence_trimming':True})
    return body
def generate(messages,stage,out):
    body=budget(messages,stage,out);key,endpoint=creds()
    with requests.Session() as session:
        session.trust_env=False;s=BoundedSession(session,out/'call')
        response=s.post(endpoint,json=body,headers={'Authorization':f'Bearer {key}'})
    if not response.ok:raise RuntimeError(f'HTTP {response.status_code}')
    return grouping.response_value(response.json())
def episode(condition,task):
    verify();ref=task['ref'];out=HERE/'episodes'/condition/ref;output=out/'trajectory.json'
    if output.exists():
        r=read(output);print('REUSE/STOP',condition,ref,r['status'],flush=True);return r
    out.mkdir(parents=True,exist_ok=True)
    skill=HERE/'parent.md' if condition=='Parent' else HERE/'editors'/condition/'candidate.md'
    rec=make_record(item=task['item'],split='train',purpose='learning',skill=load_skill(skill),model=config()['model'],max_steps=50,gamefile=Path(task['gamefile']),manifest_path=HERE/'manifest.json',versions=installed_versions(),backend_id=digest(config()['endpoint'].encode()))
    assert rec['versions']==read(HERE/'preflight.json')['versions']
    rec['request_policy']={'max_attempts':5,'strict_response':True};save(output,rec)
    tw,wrapper=environment_modules();env=tw.start(task['gamefile'],tw.EnvInfos(won=True,admissible_commands=True),wrappers=[wrapper(shuffle=False)])
    try:
        env.seed(42);key,endpoint=creds()
        with requests.Session() as session:
            session.trust_env=False;recording=RecordingSession(session,rec,output,archive_responses=True)
            def actor(messages):
                assert rec['initial_observation']==task['reset']['observation'] and rec['initial_admissible_commands']==task['reset']['commands']
                step=rec['steps'][-1]['step'];bounded=BoundedSession(recording,out/f'calls/step_{step:02}',record=rec,output=output)
                result=chat(bounded,endpoint,key,config()['model'],messages,max_attempts=1,strict_response=True)
                count=len(rec['steps'][-1].get('transport_attempts',[]));result.update(api_attempts=count,transport_retries=count-1)
                return result
            run_episode(env,actor,rec,output)
    finally:env.close()
    save(out/'audit.json',verify_record(rec));print('EPISODE',condition,ref,rec['status'],len(rec['steps']),flush=True);return rec
def parents():
    verify();results=[]
    for t in read(HERE/'tasks.json'):
        r=episode('Parent',t);results.append({'ref':t['ref'],'status':r['status'],'steps':len(r['steps'])});save(HERE/'parent_progress.json',results)
    records=[read(HERE/f"episodes/Parent/{t['ref']}/trajectory.json") for t in read(HERE/'tasks.json')]
    complete=all(r['status'] in COMPLETE for r in records)
    save(HERE/'parent_gate.json',{'all_six_complete':complete,'downstream_allowed':complete,'criterion':'All six normal outcomes required; no deletion or replacement of incomplete tasks.'})
def stage(name):
    verify();assert read(HERE/'parent_gate.json')['downstream_allowed'];out=HERE/'runs'/name
    if name=='grouping':
        records=[read(HERE/f"episodes/Parent/P{i}/trajectory.json") for i in range(1,7)];bundle=build_facts(records);saved=bundle;messages=grouping.messages_for(bundle);kind='grouping';meta={'round_id':'P3A2_BATCH1'}
    elif name=='diagnosis':
        saved=grouping.load_grouping(HERE/'runs/grouping');messages=diagnosis.messages_for(saved);kind='diagnosis';meta={'grouping_round_id':saved['round_id'],'grouping_directory':str(HERE/'runs/grouping')}
    else:
        assert read(HERE/'diagnosis_gate.json')['comparable_multiline'];saved={**diagnosis.load_diagnosis(HERE/'runs/diagnosis'),'memory':read(HERE/'memory.json')}
        a=project_messages(oldpc.messages_for(saved));b=pc.messages_for(saved);assert a[1]==b[1]
        save(HERE/'common_preconditioner_input.json',{'full':oldpc.preconditioner_input(saved),'model':pc.model_input(saved),'same_user_content':True})
        messages=a if name=='A' else b;kind='preconditioner';meta={'round_id':saved['round_id'],'grouping_directory':str(HERE/'runs/grouping'),'diagnosis_directory':str(HERE/'runs/diagnosis'),'memory':saved['memory'],'memory_contract':'entries_sources','memory_view':FORMAT}
    out.mkdir(parents=True,exist_ok=True)
    if (out/'run.json').exists() and read(out/'run.json')['status'] in {'valid','invalid'}:
        print('REUSE/STOP',name,read(out/'run.json')['status'],flush=True);return
    for file,value in [('input',saved),('messages',messages)]:save(out/f'{file}.json',value)
    if name in {'A','B'}:save(out/'model_input.json',pc.model_input(saved))
    (out/'prompt.md').write_text(messages[0]['content']);meta.update(status='requesting',started_at=now(),call_config=cc(kind));save(out/'run.json',meta)
    try:
        response=generate(messages,kind,out);save(out/'response.json',response);(out/'raw_output.txt').write_text(response.get('content') or '')
        assert response['finish_reason']=='stop','Incomplete model response'
        parsed=parse_json_response(response['content']);save(out/'parsed.json',parsed)
        if name=='grouping':grouping.validate_grouping(parsed,bundle['facts']);save(out/'grouping.json',parsed)
        elif name=='diagnosis':diagnosis.validate_diagnosis(parsed,diagnosis.diagnosis_input(saved));save(out/'diagnosis.json',parsed)
        else:
            normalized,effective=(parsed,oldpc.compile_effective_plan(parsed,oldpc.preconditioner_input(saved))) if name=='A' else normalize_update_patches(parsed,oldpc.preconditioner_input(saved))
            save(out/'preconditioner.json',normalized);save(out/'effective_plan.json',effective)
        meta['status']='valid';save(out/'validation.json',{'valid':True})
    except Exception as exc:
        (out/'traceback.txt').write_text(traceback.format_exc());meta.update(status='invalid',error_type=type(exc).__name__,error=str(exc));save(out/'validation.json',{'valid':False,'error_type':type(exc).__name__,'error':str(exc)})
    finally:meta['finished_at']=now();save(out/'run.json',meta)
    if meta['status']=='valid':
        if name=='grouping':grouping.load_grouping(out)
        elif name=='diagnosis':diagnosis.load_diagnosis(out)
        elif name=='B':pc.load_preconditioner(out)
        else:load_pc('A')
    print('STAGE',name,meta['status'],flush=True)
def load_pc(arm):
    if arm=='B':return pc.load_preconditioner(HERE/'runs/B')
    from experiments.methods.v23_3.memory_v3_integration_001.run import load_a
    saved={**diagnosis.load_diagnosis(HERE/'runs/diagnosis'),'memory':read(HERE/'memory.json')};return load_a(HERE/'runs/A',saved)
def editor_call(arm):
    verify();up=load_pc(arm);assert up['effective_plan'] is not None;out=HERE/'editors'/arm
    if (out/'run.json').exists():
        print('REUSE/STOP editor',arm,read(out/'run.json')['status'],flush=True);return
    out.mkdir(parents=True,exist_ok=True);messages=editor.messages_for(up)
    for name,value in [('upstream',up),('input',editor.editor_input(up)),('background',up['background']),('messages',messages)]:save(out/f'{name}.json',value)
    (out/'prompt.md').write_text(messages[0]['content']);meta={'round_id':up['round_id'],'call_config':cc('editor'),'started_at':now(),'status':'requesting'};save(out/'run.json',meta)
    try:
        response=generate(messages,'editor',out);save(out/'response.json',response);(out/'raw_output.txt').write_text(response.get('content') or '');assert response['finish_reason']=='stop'
        parsed=parse_json_response(response['content']);save(out/'parsed.json',parsed)
        if isinstance(parsed.get('patch'),str):(out/'patch.diff').write_text(parsed['patch'])
        status,candidate=editor.validate_editor(parsed,up['facts']['parent']);save(out/'editor.json',parsed)
        if candidate is not None:(out/'candidate.md').write_text(candidate);(out/'actual.diff').write_text(editor.actual_diff(up['facts']['parent'],candidate))
        save(out/'validation.json',{'valid':True});meta.update(status='valid',outcome=status)
    except Exception as exc:
        (out/'traceback.txt').write_text(traceback.format_exc());save(out/'validation.json',{'valid':False,'error':str(exc)});meta.update(status='invalid',error_type=type(exc).__name__,error=str(exc))
    finally:meta['finished_at']=now();save(out/'run.json',meta)
    if meta['status']=='valid':editor.load_editor(out,expected_preconditioner=up)
    print('EDITOR',arm,meta['status'],meta.get('outcome'),flush=True)
def candidates():
    verify();gate=read(HERE/'editor_gate.json')
    for t in read(HERE/'tasks.json'):
        for arm in ['A','B']:
            if arm in gate['valid_candidates']:editor.load_editor(HERE/'editors'/arm);episode(arm,t)
if __name__=='__main__':
    with (HERE/'process.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        cmd=sys.argv[1]
        if cmd=='stage':stage(sys.argv[2])
        elif cmd=='editor':editor_call(sys.argv[2])
        else:globals()[cmd]()
