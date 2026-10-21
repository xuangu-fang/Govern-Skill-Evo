"""Complete the final Parent/P7 after user-confirmed network recovery."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse
from experiments.methods.v23_3.p3c1_r05_replay_restart_003 import run as prior, resume
HERE=Path(__file__).resolve().parent
ROOT=prior.ROOT
read,save,now=prior.read,prior.save,prior.now
COMPLETE=prior.COMPLETE
WORKER=prior.prior.previous

def prepare():
    resume.verify();a=read(prior.HERE/'analysis.json')
    assert [(r['condition'],r['ref']) for r in a['rows'] if r['status'] not in COMPLETE]==[('Parent','P7')]
    paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    save(HERE/'baseline.json',{'at':now(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'git_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
        'git_diff':subprocess.check_output(['git','diff'],cwd=ROOT,text=True),
        'files':{str(ROOT/p):[(ROOT/p).stat().st_size,(ROOT/p).stat().st_mtime_ns] for p in paths if (ROOT/p).is_file() and not (ROOT/p).is_relative_to(HERE)}})
    save(HERE/'config.json',{'at':now(),'original_config':prior.verify()['original_config'],
        'previous_actor_http':a['cumulative_including_editors']['decisions'],'cumulative_actor_http_max':600,
        'backoff_seconds':[120,240,300],'task':['Parent','P7'],'max_steps':50,'per_decision_http_attempts':1,
        'authorization':'User confirmed network recovery and explicitly authorized continuing the final task.'})
    paths=[HERE/'run.py',HERE/'PROTOCOL.md',HERE/'config.json',prior.HERE/'analysis.json']
    save(HERE/'freeze.json',{'at':now(),'files':{str(p):WORKER.original.sha(p) for p in paths}})

def verify():
    resume.verify()
    for path,h in read(HERE/'freeze.json')['files'].items():assert WORKER.original.sha(path)==h,path
    return read(HERE/'config.json')

def episode(attempt):
    cfg=verify();WORKER.HERE=HERE/f'attempt_{attempt}'
    WORKER.verify=lambda:{'original_config':cfg['original_config']}
    WORKER.episode('Parent','P7')

def batch():
    cfg=verify();(HERE/'batch.claim').open('x').close();results=[];spent=0;attempt=1;stop='budget_reservation';checks=[]
    target=urlparse(cfg['original_config']['endpoint'])
    while cfg['previous_actor_http']+spent+50<=cfg['cumulative_actor_http_max']:
        try:
            socket.getaddrinfo(target.hostname,target.port or 80)
            with socket.create_connection((target.hostname,target.port or 80),timeout=10):pass
            checks.append({'at':now(),'status':'dns_tcp_ok','model_call':False})
        except OSError as exc:
            checks.append({'at':now(),'status':'unavailable','error_type':type(exc).__name__,'model_call':False})
            stop='network_unavailable';save(HERE/'connectivity_checks.json',checks);break
        save(HERE/'connectivity_checks.json',checks)
        folder=HERE/f'attempt_{attempt}';folder.mkdir(exist_ok=False)
        with (folder/'Parent_P7.log').open('x') as log:
            proc=subprocess.run([WORKER.original.PYTHON,'-B','-m','experiments.methods.v23_3.p3c1_r05_replay_restart_004.run','episode',str(attempt)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        path=folder/'episodes/Parent/P7/trajectory.json';r=read(path) if path.exists() else {}
        transports=[t for s in r.get('steps',[]) for t in s.get('transport_attempts',[])]
        status=r.get('status','setup_error');http=transports[-1].get('http_status') if transports else None;spent+=len(transports)
        row={'attempt':attempt,'at':now(),'exit':proc.returncode,'status':status,'last_http_status':http,'error_type':r.get('error_type'),'http_requests':len(transports),'trajectory':str(path)}
        results.append(row);save(HERE/'progress.json',{'at':now(),'results':results,'spent_http':spent});print(row,flush=True)
        if not proc.returncode and status in COMPLETE:stop='all_tasks_completed';break
        transient=r.get('error_stage')=='model_request' and r.get('error_type') in {'ReadTimeout','ConnectTimeout','ConnectionError','ChunkedEncodingError'} and r['steps'][-1].get('model_response') is None
        if proc.returncode or status!='error' or not (http==429 or transient):stop='other_technical_error';break
        if cfg['previous_actor_http']+spent+50>cfg['cumulative_actor_http_max']:break
        delay=cfg['backoff_seconds'][min(attempt-1,2)]
        print(f'Transport interruption: wait {delay}s before retrying Parent/P7',flush=True)
        for _ in range(delay//30):time.sleep(30)
        attempt+=1
    save(HERE/'results.json',{'at':now(),'stop_reason':stop,'results':results,'spent_http':spent})

if __name__=='__main__':
    if sys.argv[1]=='episode':episode(sys.argv[2])
    else:globals()[sys.argv[1]]()
