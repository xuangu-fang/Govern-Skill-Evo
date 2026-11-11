"""Detached one-shot training supervisor. No retry or test dispatch is automatic."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import execution_dir, frozen_file, load_plan

def now(): return datetime.now(timezone.utc).isoformat()
def read(p): return json.loads(p.read_text())
def write(p,v):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job',choices=['v24_1','skilladam'])
    parser.add_argument('--launch',action='store_true')
    parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    plan=load_plan(HERE/'plan.json');job=plan['jobs'][args.job]
    folder=execution_dir(args.job)
    state_path=folder/(args.job+'.state.json')
    if not args.launch and not args.worker:
        print(json.dumps(read(state_path) if state_path.exists() else {'status':'not_dispatched'}));return
    folder.mkdir(parents=True, exist_ok=True)
    if datetime.now(timezone.utc)<datetime.fromisoformat(plan['not_before_utc'].replace('Z','+00:00')):
        raise ValueError('Start deadline has not arrived')
    for name, expected in plan['frozen_inputs_sha256'].items():
        if hashlib.sha256(frozen_file(name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Frozen input changed: '+name)
    if args.worker:
        with (folder/(args.job+'.worker.lock')).open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if (ROOT/job['training_output']).exists():
                raise ValueError('Training output already exists; explicit recovery required')
            state={'job':args.job,'status':'starting','supervisor_pid':os.getpid(),
                   'started_at':now(),'command':job['train_command'],'training_output':job['training_output']}
            write(state_path,state)
            try:
                proc=subprocess.Popen(job['train_command'],cwd=ROOT,stdin=subprocess.DEVNULL,
                    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'})
                state.update(status='running',pid=proc.pid);write(state_path,state)
                code=proc.wait()
                state.update(status='process_exited',exit_code=code,finished_at=now())
                write(state_path,state)
                raise SystemExit(code)
            except Exception as exc:
                state.update(status='dispatch_failed',error_type=type(exc).__name__,finished_at=now())
                write(state_path,state)
                raise
    else:
        with (folder/(args.job+'.launch.lock')).open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            receipt=folder/(args.job+'.process.json')
            if receipt.exists() or state_path.exists() or (ROOT/job['training_output']).exists():
                raise ValueError('Already dispatched or output exists; do not repeat launch')
            command=[job['python'],str(Path(__file__).resolve()),args.job,'--worker']
            log_path=folder/(args.job+'.log')
            with log_path.open('xb') as log:
                proc=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,
                    stderr=subprocess.STDOUT,start_new_session=True,
                    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'})
            record={'pid':proc.pid,'started_at':now(),'command':command,'log':str(log_path),
                    'plan_sha256':hashlib.sha256((HERE/'plan.json').read_bytes()).hexdigest()}
            write(receipt,record)
            keepawake=subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(proc.pid)],
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            record['caffeinate_pid']=keepawake.pid;write(receipt,record)
            print(json.dumps(record))

if __name__=='__main__':main()
