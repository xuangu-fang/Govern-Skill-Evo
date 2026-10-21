"""User-authorized four-Episode coordination, with shared transport cooldown."""
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
import fcntl
import os
import subprocess
import sys
from .run import HERE,ROOT,read,save,verify,episode,COMPLETE,now
PYTHON='/Users/didi/miniforge3/envs/alfworld/bin/python'
def batch(condition):
 verify();tasks=read(HERE/'tasks.json');jobs=[]
 for task in tasks:
  arms=['Parent'] if condition=='parents' else read(HERE/'editor_gate.json')['valid_candidates']
  for arm in arms:
   path=HERE/f"episodes/{arm}/{task['ref']}/trajectory.json"
   if path.exists():continue
   jobs.append((arm,task['ref']))
 def one(job):
  arm,ref=job
  with (HERE/f'{condition}_{arm}_{ref}.log').open('x') as log:
   p=subprocess.run([PYTHON,'-B','-u','-m','experiments.methods.v23_3.p3a2_train_batch1_001.parallel','worker',arm,ref],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  path=HERE/f'episodes/{arm}/{ref}/trajectory.json';r=read(path) if path.exists() else {}
  row={'arm':arm,'ref':ref,'exit':p.returncode,'status':r.get('status','setup_error'),'at':now()};print(row,flush=True);return row
 results=[];index=0
 with ThreadPoolExecutor(max_workers=4) as pool:
  pending=set()
  while pending or index<len(jobs):
   throttle=read(HERE/'throttle.json') if (HERE/'throttle.json').exists() else {}
   limit=throttle.get('request_concurrency_limit',4)
   while len(pending)<limit and index<len(jobs):pending.add(pool.submit(one,jobs[index]));index+=1
   done,pending=wait(pending,return_when=FIRST_COMPLETED)
   for f in done:results.append(f.result())
   save(HERE/f'{condition}_parallel_progress.json',results)
 if condition=='parents':
  complete=all((HERE/f"episodes/Parent/{t['ref']}/trajectory.json").exists() and read(HERE/f"episodes/Parent/{t['ref']}/trajectory.json")['status'] in COMPLETE for t in tasks)
  save(HERE/'parent_gate.json',{'all_six_complete':complete,'downstream_allowed':complete,'criterion':'All six normal outcomes required.'})
if __name__=='__main__':
 if sys.argv[1]=='worker':episode(sys.argv[2],next(t for t in read(HERE/'tasks.json') if t['ref']==sys.argv[3]))
 else:
  with (HERE/'process.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);batch(sys.argv[1])
