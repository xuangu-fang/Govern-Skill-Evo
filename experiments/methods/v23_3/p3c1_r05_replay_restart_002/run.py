"""Three user-authorized serial continuation rounds, retrying only HTTP 429."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from experiments.methods.v23_3.p3c1_r05_replay_restart_001 import run as previous

HERE=Path(__file__).resolve().parent
ROOT=previous.original.ROOT
read,save,now=previous.read,previous.save,previous.now
JOBS=previous.JOBS
COMPLETE={'success','step_limit','environment_ended'}

from experiments.methods.v23_3.archive_io import resolve

def prepare():
    cfg=previous.verify()
    files=set(subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines())
    protected={str(ROOT/p):[resolve(ROOT / p).stat().st_size,resolve(ROOT / p).stat().st_mtime_ns] for p in files if resolve(ROOT / p).is_file() and not (ROOT/p).is_relative_to(HERE)}
    save(HERE/'baseline.json',{'at':now(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'git_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
        'git_diff':subprocess.check_output(['git','diff'],cwd=ROOT,text=True),'files':protected})
    save(HERE/'config.json',{'at':now(),'original_config':cfg['original_config'],'jobs':JOBS,
        'max_rounds':3,'backoff_seconds':60,'concurrency':1,'per_decision_http_attempts':1,
        'max_new_episode_attempts':9,'max_new_actor_http':450,'previous_actor_http':90,'max_cumulative_actor_http':540,
        'authorization':'Continue restarting on server rate limit, at most three attempts in this turn.'})
    frozen=[HERE/'run.py',HERE/'PROTOCOL.md',HERE/'config.json',previous.HERE/'freeze.json']
    save(HERE/'freeze.json',{'at':now(),'files':{str(p):previous.original.sha(p) for p in frozen}})

def verify():
    previous.verify()
    for path,h in read(HERE/'freeze.json')['files'].items():assert previous.original.sha(path)==h,path
    return read(HERE/'config.json')

def episode(round_no,condition,ref):
    cfg=verify()
    previous.HERE=HERE/f'attempt_{round_no}'
    previous.verify=lambda:{'original_config':cfg['original_config']}
    previous.episode(condition,ref)

def batch():
    cfg=verify();(resolve(HERE/'batch.claim')).open('x').close()
    completed=set();results=[];stop='round_limit'
    for round_no in range(1,cfg['max_rounds']+1):
        folder=HERE/f'attempt_{round_no}';resolve(folder).mkdir(exist_ok=False)
        rate_limited=False
        for condition,ref in JOBS:
            if (condition,ref) in completed:continue
            with (resolve(folder/f'{condition}_{ref}.log')).open('w') as log:
                proc=subprocess.run([previous.original.PYTHON,'-B','-m','experiments.methods.v23_3.p3c1_r05_replay_restart_002.run','episode',str(round_no),condition,ref],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            path=folder/f'episodes/{condition}/{ref}/trajectory.json'
            r=read(path) if resolve(path).exists() else {}
            status=r.get('status','setup_error')
            transport=[t for s in r.get('steps',[]) for t in s.get('transport_attempts',[])]
            http_status=transport[-1].get('http_status') if transport else None
            row={'round':round_no,'condition':condition,'ref':ref,'exit':proc.returncode,'status':status,'last_http_status':http_status,'trajectory':str(path),'at':now()}
            results.append(row)
            if not proc.returncode and status in COMPLETE:completed.add((condition,ref))
            save(HERE/'progress.json',{'at':now(),'results':results,'remaining':[j for j in JOBS if j not in completed]})
            print(json.dumps(row,ensure_ascii=False),flush=True)
            if proc.returncode or status not in COMPLETE:
                rate_limited=(status=='error' and http_status==429)
                if not rate_limited:stop='non_429_technical_error'
                break
            time.sleep(2)
        if len(completed)==len(JOBS):stop='all_completed';break
        if not rate_limited:break
        if round_no<cfg['max_rounds']:
            print(f'HTTP429: cooldown {cfg["backoff_seconds"]} seconds before round {round_no+1}',flush=True)
            time.sleep(cfg['backoff_seconds'])
    save(HERE/'results.json',{'at':now(),'stop_reason':stop,'results':results,'remaining':[j for j in JOBS if j not in completed]})

if __name__=='__main__':
    if sys.argv[1]=='episode':episode(*sys.argv[2:5])
    else:globals()[sys.argv[1]]()
