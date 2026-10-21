"""Isolated, bounded R05 Editor and Actor orchestration; no policy changes."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

from dotenv import dotenv_values
import requests
from src.skill_evolution.v23 import editor, preconditioner as old_pc
from src.skill_evolution.v23_3 import preconditioner as pc
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.adapters.alfworld.skill_runtime import load_skill, make_record, digest, write_record
from experiments.methods.v23_3.memory_v3_integration_001.run import load_a

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = HERE.parent / 'memory_v3_integration_001'
FORMAL = ROOT / 'artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05'
PYTHON = '/Users/didi/miniforge3/envs/alfworld/bin/python'

def read(p):
    return json.loads(Path(p).read_text())

def save(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    write_record(p, value)

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(p):
    return digest(Path(p).read_bytes())

def credentials():
    values = {**dotenv_values(ROOT / '.env'), **os.environ}
    return values['OPENAI_API_KEY'], values['OPENAI_BASE_URL'].rstrip('/')

def verify_freeze():
    frozen = read(HERE / 'freeze.json')
    for path, expected in frozen['files'].items():
        assert sha(ROOT / path) == expected, path
    return read(HERE / 'config.json')

def upstreams():
    saved = read(SOURCE / 'config/common_saved.json')
    a = load_a(SOURCE / 'runs/A', saved)
    b = pc.load_preconditioner(SOURCE / 'runs/B')
    assert a['facts'] == b['facts'] and a['diagnosis'] == b['diagnosis']
    assert old_pc.preconditioner_input(a) == read(SOURCE / 'config/full_payload.json')
    assert b['effective_plan'] == read(SOURCE / 'config/model_input.json')['plan']
    assert len(a['preconditioner']['adjustments']) == 2
    assert b['preconditioner']['adjustments'] == []
    return {'A': a, 'B': b}

def prepare():
    key, base = credentials()
    assert '.intra.' in base and key
    cfg = {'endpoint': base + '/chat/completions', 'model': 'deepseek-v4.1-flash',
           'editor_max_tokens': 16384, 'actor_max_tokens': 16384,
           'temperature': 1.0, 'thinking': {'type': 'enabled'}, 'reasoning_effort': 'medium',
           'stream': False, 'editor_timeout': [60,300], 'actor_timeout': [10,300],
           'http_attempts_per_logical_call': 1, 'max_editors': 2, 'max_episodes': 12,
           'max_steps': 50, 'max_actor_decisions': 600, 'concurrency': 4,
           'actor_python': PYTHON, 'seed': 42, 'reuse_historical_parent': False}
    save(HERE/'config.json',cfg)
    ups = upstreams()
    parent = ups['A']['facts']['parent']
    (HERE/'parent.md').write_text(parent)
    for arm,saved in ups.items():
        save(HERE/f'inputs/{arm}_upstream.json',saved)
        save(HERE/f'inputs/{arm}_effective.json',saved['effective_plan'])
        save(HERE/f'inputs/{arm}_messages.json',editor.messages_for(saved))
    assert editor.messages_for(ups['A'])[0] == editor.messages_for(ups['B'])[0]
    grouping=read(FORMAL/'grouping/attempts/002/input.json')
    from src.adapters.alfworld.run_task import SPLIT_ROOT
    manifest=read(SPLIT_ROOT/'val/items.json')
    tasks=[]
    for ref in ['P3','P6','P7','P10']:
        source=next(s for s in grouping['sources'] if s['ref']==ref)
        paths=list((FORMAL/'parent_runs'/source['task_id'].replace(':','_')).rglob('trajectory.json'))
        path=next(p for p in paths if read(p)['run_id']==source['run_id'])
        record=read(path)
        assert record['skill']['text']==parent
        item=next(x for x in manifest if x['id']==source['task_id'])
        assert item==record['task']
        tasks.append({'ref':ref,'item':item,'goal':record['goal'],'historical_trajectory':str(path),
                      'gamefile':record['gamefile'],'game_sha256':sha(record['gamefile']),
                      'manifest':str(SPLIT_ROOT/'val/items.json')})
    save(HERE/'tasks.json',tasks)
    print('Prepared source handoffs and four task identities',flush=True)

def preflight():
    from src.adapters.alfworld.run_task_skill import environment_modules,installed_versions
    from src.adapters.alfworld.skill_runtime import execution_protocol,implementation_metadata
    from src.adapters.alfworld.verify_skill_run import verify_record
    tw,wrapper=environment_modules();results=[]
    for task in read(HERE/'tasks.json'):
        old=read(task['historical_trajectory']);verify_record(old)
        resets=[]
        for _ in range(2):
            env=tw.start(task['gamefile'],tw.EnvInfos(won=True,admissible_commands=True),wrappers=[wrapper(shuffle=False)])
            try:
                env.seed(42);state=env.reset()
                resets.append({'observation':state.feedback,'commands':list(state.admissible_commands)})
            finally:env.close()
        assert resets[0]==resets[1]
        assert resets[0]['observation']==old['initial_observation']
        assert resets[0]['commands']==old['initial_admissible_commands']
        assert old['protocol']==execution_protocol(50)
        results.append({'ref':task['ref'],'reset':resets[0],'same_historical_reset':True,
                        'historical_trace_valid':True,'historical_model':old['model'],
                        'implementation_equal':old['implementation']['files']==implementation_metadata()['files']})
    save(HERE/'preflight.json',{'at':now(),'versions':installed_versions(),
         'protocol':execution_protocol(50),'implementation':implementation_metadata(),'tasks':results})
    print('Four deterministic resets match historical initial states',flush=True)

def freeze():
    assert (HERE/'NEW_TRAIN_CASES.md').is_file() and (HERE/'preflight.json').is_file()
    files=[HERE/'run.py',HERE/'select_train.py',HERE/'PROTOCOL.md',HERE/'NEW_TRAIN_CASES.md',HERE/'new_train_cases.json',
           HERE/'config.json',HERE/'tasks.json',HERE/'preflight.json',HERE/'parent.md']
    files+=list((HERE/'inputs').glob('*.json'))
    files+=list((ROOT/'src/skill_evolution/v23').glob('*.py'))+list((ROOT/'src/skill_evolution/v23').glob('*.md'))
    files+=list((ROOT/'src/skill_evolution/v23_3').glob('*.py'))+list((ROOT/'src/skill_evolution/v23_3').glob('*.md'))
    files+=list((ROOT/'src/adapters/alfworld').glob('*.py'))
    files += [Path(t['gamefile']) for t in read(HERE/'tasks.json')]
    files += [Path(read(HERE/'tasks.json')[0]['manifest'])]
    # Absolute external game paths are legal keys; ROOT/path preserves them.
    save(HERE/'freeze.json',{'at':now(),'files':{str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p) for p in files}})
    print('Stage 0 frozen',flush=True)

def editor_call(arm):
    cfg=verify_freeze();key,base=credentials();assert cfg['endpoint']==base+'/chat/completions'
    upstream=upstreams()[arm]
    assert upstream==read(HERE/f'inputs/{arm}_upstream.json')
    out=HERE/'editors'/arm;out.mkdir(parents=True,exist_ok=False)
    messages=editor.messages_for(upstream);assert messages==read(HERE/f'inputs/{arm}_messages.json')
    cc={'endpoint':cfg['endpoint'],'model':cfg['model'],'max_tokens':cfg['editor_max_tokens'],
        'timeout_seconds':300,'temperature':cfg['temperature'],'thinking':cfg['thinking'],
        'reasoning_effort':cfg['reasoning_effort'],'stream':False}
    for name,value in [('upstream',upstream),('input',editor.editor_input(upstream)),
                       ('background',upstream['background']),('messages',messages)]:save(out/f'{name}.json',value)
    (out/'prompt.md').write_text(messages[0]['content'])
    meta={'round_id':upstream['round_id'],'call_config':cc,'started_at':now(),'status':'requesting'}
    save(out/'run.json',meta)
    try:
        from experiments.methods.v23_3.p3a_transport_retry_001.run import send_once
        body={k:v for k,v in cc.items() if k not in ('endpoint','timeout_seconds')};body['messages']=messages
        http=out/'http/001';http.mkdir(parents=True)
        response=send_once({'endpoint':cfg['endpoint'],'body':body},key,http,
                           {'connect_upload_timeout_seconds':60,'read_timeout_seconds':300})
        save(out/'response.json',response);(out/'raw_output.txt').write_text(response.get('content') or '')
        assert response.get('finish_reason')=='stop'
        parsed=parse_json_response(response['content']);save(out/'parsed.json',parsed)
        if isinstance(parsed,dict) and isinstance(parsed.get('patch'),str):(out/'patch.diff').write_text(parsed['patch'])
        status,candidate=editor.validate_editor(parsed,upstream['facts']['parent'])
        save(out/'editor.json',parsed)
        if candidate is not None:
            (out/'candidate.md').write_text(candidate)
            (out/'actual.diff').write_text(editor.actual_diff(upstream['facts']['parent'],candidate))
        save(out/'validation.json',{'valid':True,'error':None});meta.update(status='valid',outcome=status)
    except Exception as exc:
        (out/'traceback.txt').write_text(traceback.format_exc())
        save(out/'validation.json',{'valid':False,'error_type':type(exc).__name__,'error':str(exc)})
        meta.update(status='invalid',error_type=type(exc).__name__)
    finally:
        meta['finished_at']=now();save(out/'run.json',meta)
    if meta['status']=='valid':
        editor.load_editor(out,expected_preconditioner=upstream,expected_call_config=cc)
    print(arm,meta['status'],meta.get('outcome'),flush=True)

def episode(condition,ref):
    from src.adapters.alfworld.run_task_skill import environment_modules,installed_versions,run_episode,RecordingSession
    from src.adapters.alfworld.run_task_upstream import chat
    from src.adapters.alfworld.verify_skill_run import verify_record
    cfg=verify_freeze();key,base=credentials();assert cfg['endpoint']==base+'/chat/completions'
    for arm in ['A','B']:assert (HERE/f'editors/{arm}/run.json').is_file()
    skillfile=HERE/'parent.md' if condition=='Parent' else HERE/f'editors/{condition}/candidate.md'
    if condition!='Parent':
        saved=editor.load_editor(HERE/'editors'/condition)
        assert saved['editor_status']=='candidate' and skillfile.read_text()==saved['candidate_text']
    task=next(t for t in read(HERE/'tasks.json') if t['ref']==ref)
    out=HERE/'episodes'/condition/ref;out.mkdir(parents=True,exist_ok=False)
    record=make_record(item=task['item'],split='val',purpose='optimization',skill=load_skill(skillfile),
        model=cfg['model'],max_steps=50,gamefile=Path(task['gamefile']),manifest_path=Path(task['manifest']),
        versions=installed_versions(),backend_id=digest(cfg['endpoint'].encode()))
    assert record['versions']==read(HERE/'preflight.json')['versions']
    record['request_policy']={'max_attempts':1,'strict_response':True};output=out/'trajectory.json'
    tw,wrapper=environment_modules();env=tw.start(task['gamefile'],tw.EnvInfos(won=True,admissible_commands=True),wrappers=[wrapper(shuffle=False)])
    try:
        env.seed(42)
        with requests.Session() as session:
            session.trust_env=False
            recording=RecordingSession(session,record,output,archive_responses=True)
            expected=next(t['reset'] for t in read(HERE/'preflight.json')['tasks'] if t['ref']==ref)
            def generate(messages):
                assert record['initial_observation']==expected['observation']
                assert record['initial_admissible_commands']==expected['commands']
                return chat(recording,cfg['endpoint'],key,cfg['model'],messages,max_attempts=1,strict_response=True)
            run_episode(env,generate,record,output)
    finally:env.close()
    save(out/'audit.json',verify_record(record))
    print(condition,ref,record['status'],len(record['steps']),flush=True)

def batch():
    verify_freeze()
    # Explicit Editor-result audit gate; no requests before both arms reviewed.
    assert read(HERE/'editor_gate.json')['replay_allowed']
    jobs=[(c,t['ref']) for c in ['Parent','A','B'] for t in read(HERE/'tasks.json')
          if c=='Parent' or (HERE/f'editors/{c}/candidate.md').is_file()]
    assert len(jobs)<=12
    (HERE/'batch.claim').open('x').close()
    def one(job):
        c,r=job;log=HERE/f'episodes/{c}_{r}.log';log.parent.mkdir(exist_ok=True)
        with log.open('w') as output:
            result=subprocess.run([PYTHON,'-m','experiments.methods.v23_3.p3c1_r05_replay_001.run','episode',c,r],
                                   cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
        print(c,r,'exit',result.returncode,flush=True)
        trajectory=HERE/f'episodes/{c}/{r}/trajectory.json'
        return {'condition':c,'ref':r,'exit':result.returncode,
                'status':read(trajectory)['status'] if trajectory.exists() else 'setup_error'}
    results=[];index=0;stop=False
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending=set()
        while pending or (index<len(jobs) and not stop):
            while len(pending)<4 and index<len(jobs) and not stop:
                pending.add(pool.submit(one,jobs[index]));index+=1
            done,pending=wait(pending,return_when=FIRST_COMPLETED)
            for future in done:
                result=future.result();results.append(result)
                # Conservative: any technical failure stops further scheduling.
                if result['exit'] or result['status'] not in {'success','step_limit','environment_ended'}:stop=True
            save(HERE/'batch_progress.json',{'at':now(),'results':results,'stop_scheduling':stop,'not_started':jobs[index:]})
    save(HERE/'batch_results.json',results)

if __name__=='__main__':
    action=sys.argv[1]
    if action=='editor':editor_call(sys.argv[2])
    elif action=='episode':episode(sys.argv[2],sys.argv[3])
    else:globals()[action]()
