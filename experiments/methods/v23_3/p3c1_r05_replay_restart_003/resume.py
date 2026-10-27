"""Continue after a documented response-less ReadTimeout; never retry model outputs."""
import os
import subprocess
import time
from . import run
HERE=run.HERE
read,save,now=run.read,run.save,run.now

from experiments.methods.v23_3.archive_io import resolve

def verify():
    cfg=run.verify()
    for path,h in read(HERE/'resume_freeze.json')['files'].items():assert run.prior.previous.original.sha(path)==h,path
    return cfg

def main():
    cfg=verify();(resolve(HERE/'resume.claim')).open('x').close()
    prev=read(HERE/'results.json');results=list(prev['results']);spent=prev['spent_http'];stop='budget_reservation'
    assert prev['stop_reason']=='non_429_technical_error'
    r=read(results[-1]['trajectory']);assert r['error_type']=='ReadTimeout' and r['error_stage']=='model_request'
    print('ReadTimeout archived; cooldown 60 seconds before attempt 3',flush=True);time.sleep(60)
    attempt=len(results)+1
    while cfg['previous_actor_http']+spent+50<=cfg['cumulative_actor_http_max']:
        folder=HERE/f'attempt_{attempt}';resolve(folder).mkdir(exist_ok=False)
        with (resolve(folder/'Parent_P7.log')).open('x') as log:
            proc=subprocess.run([run.prior.previous.original.PYTHON,'-B','-m','experiments.methods.v23_3.p3c1_r05_replay_restart_003.run','episode',str(attempt)],cwd=run.ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        path=folder/'episodes/Parent/P7/trajectory.json';r=read(path) if resolve(path).exists() else {}
        transports=[t for s in r.get('steps',[]) for t in s.get('transport_attempts',[])]
        status=r.get('status','setup_error');http=transports[-1].get('http_status') if transports else None
        spent+=len(transports)
        row={'attempt':attempt,'at':now(),'exit':proc.returncode,'status':status,'last_http_status':http,'error_type':r.get('error_type'),'http_requests':len(transports),'trajectory':str(path)}
        results.append(row);save(HERE/'resume_progress.json',{'at':now(),'results':results,'spent_http':spent});print(row,flush=True)
        if not proc.returncode and status in run.COMPLETE:stop='all_tasks_completed';break
        timeout=r.get('error_type')=='ReadTimeout' and r.get('error_stage')=='model_request' and r['steps'][-1].get('model_response') is None
        if proc.returncode or status!='error' or not (http==429 or timeout):stop='other_technical_error';break
        if cfg['previous_actor_http']+spent+50>cfg['cumulative_actor_http_max']:break
        delay=60 if timeout else cfg['backoff_seconds'][min(attempt-1,2)]
        print(f'Transport interruption: cooldown {delay}s before next attempt',flush=True)
        for _ in range(delay//30):time.sleep(30)
        attempt+=1
    save(HERE/'final_results.json',{'at':now(),'stop_reason':stop,'results':results,'spent_http':spent,'response_less_read_timeout_recovery':True})

if __name__=='__main__':main()
