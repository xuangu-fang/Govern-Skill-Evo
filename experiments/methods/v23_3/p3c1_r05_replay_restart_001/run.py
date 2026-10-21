"""Authorized restart of four transport failures plus three queued R05 cases."""
import os
from pathlib import Path
import subprocess
import sys
import time
import requests
from experiments.methods.v23_3.p3c1_r05_replay_001 import run as original
from src.adapters.alfworld.skill_runtime import load_skill,make_record,digest

HERE=Path(__file__).resolve().parent
OLD=original.HERE
read,save,now=original.read,original.save,original.now
JOBS=[('Parent','P7'),('A','P7'),('A','P10'),('B','P3'),('B','P6'),('B','P7'),('B','P10')]

def prepare():
    cfg=original.verify_freeze()
    selection=[]
    for condition,ref in JOBS:
        path=OLD/f'episodes/{condition}/{ref}/trajectory.json'
        if path.exists():
            record=read(path)
            assert record['status']=='error' and record['steps'][-1]['transport_attempts'][-1]['http_status']==429
            kind='restart_429'
        else:kind='previously_not_started'
        selection.append({'condition':condition,'ref':ref,'kind':kind,'old_trajectory':str(path) if path.exists() else None})
    save(HERE/'config.json',{'at':now(),'original_config':cfg,'jobs':selection,
        'concurrency':1,'minimum_request_gap_seconds':2,'attempts_per_decision':1,
        'new_episodes_max':7,'new_decisions_max':350,'original_decisions':76,
        'combined_decisions_max':426,'original_episode_attempts':9,'combined_episode_attempts_max':16,
        'authorization':'User explicitly authorized restarting interrupted failures; continue previously authorized unstarted cases.'})
    files=[HERE/'run.py',HERE/'PROTOCOL.md',HERE/'config.json',OLD/'freeze.json',OLD/'parent.md',
        OLD/'editors/A/candidate.md',OLD/'editors/B/candidate.md',OLD/'tasks.json',OLD/'preflight.json']
    save(HERE/'freeze.json',{'at':now(),'files':{str(p):original.sha(p) for p in files}})

def verify():
    original.verify_freeze()
    for path,h in read(HERE/'freeze.json')['files'].items():assert original.sha(path)==h,path
    return read(HERE/'config.json')

def episode(condition,ref):
    from src.adapters.alfworld.run_task_skill import environment_modules,installed_versions,run_episode,RecordingSession
    from src.adapters.alfworld.run_task_upstream import chat
    from src.adapters.alfworld.verify_skill_run import verify_record
    rcfg=verify();cfg=rcfg['original_config'];assert (condition,ref) in JOBS
    key,base=original.credentials();assert cfg['endpoint']==base+'/chat/completions'
    skillfile=OLD/'parent.md' if condition=='Parent' else OLD/f'editors/{condition}/candidate.md'
    if condition!='Parent':
        saved=original.editor.load_editor(OLD/'editors'/condition)
        assert saved['editor_status']=='candidate' and saved['candidate_text']==skillfile.read_text()
    task=next(t for t in read(OLD/'tasks.json') if t['ref']==ref)
    out=HERE/f'episodes/{condition}/{ref}';out.mkdir(parents=True,exist_ok=False)
    record=make_record(item=task['item'],split='val',purpose='optimization',skill=load_skill(skillfile),
        model=cfg['model'],max_steps=50,gamefile=Path(task['gamefile']),manifest_path=Path(task['manifest']),
        versions=installed_versions(),backend_id=digest(cfg['endpoint'].encode()))
    assert record['versions']==read(OLD/'preflight.json')['versions']
    record['request_policy']={'max_attempts':1,'strict_response':True};output=out/'trajectory.json'
    tw,wrapper=environment_modules();env=tw.start(task['gamefile'],tw.EnvInfos(won=True,admissible_commands=True),wrappers=[wrapper(shuffle=False)])
    try:
        env.seed(42)
        with requests.Session() as session:
            session.trust_env=False;recording=RecordingSession(session,record,output,archive_responses=True)
            expected=next(t['reset'] for t in read(OLD/'preflight.json')['tasks'] if t['ref']==ref)
            def generate(messages):
                assert record['initial_observation']==expected['observation']
                assert record['initial_admissible_commands']==expected['commands']
                time.sleep(2)
                return chat(recording,cfg['endpoint'],key,cfg['model'],messages,max_attempts=1,strict_response=True)
            run_episode(env,generate,record,output)
    finally:env.close()
    save(out/'audit.json',verify_record(record))
    print(condition,ref,record['status'],len(record['steps']),flush=True)

def batch():
    verify();(HERE/'batch.claim').open('x').close();results=[]
    for condition,ref in JOBS:
        log=HERE/f'{condition}_{ref}.log'
        with log.open('w') as output:
            proc=subprocess.run([original.PYTHON,'-B','-m','experiments.methods.v23_3.p3c1_r05_replay_restart_001.run','episode',condition,ref],cwd=original.ROOT,stdout=output,stderr=subprocess.STDOUT,
                                env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        path=HERE/f'episodes/{condition}/{ref}/trajectory.json'
        status=read(path)['status'] if path.exists() else 'setup_error'
        results.append({'condition':condition,'ref':ref,'exit':proc.returncode,'status':status})
        save(HERE/'progress.json',{'at':now(),'results':results,'remaining':JOBS[len(results):]})
        print(condition,ref,status,flush=True)
        if proc.returncode or status not in {'success','step_limit','environment_ended'}:break
        time.sleep(2)
    save(HERE/'results.json',results)

if __name__=='__main__':
    if sys.argv[1]=='episode':episode(*sys.argv[2:4])
    else:globals()[sys.argv[1]]()
