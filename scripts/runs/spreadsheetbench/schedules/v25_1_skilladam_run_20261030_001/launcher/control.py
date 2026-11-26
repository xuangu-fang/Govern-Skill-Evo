"""Single supervisor: train both arms, validate both, then test both once."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[6]))
from scripts.runs.spreadsheetbench.schedules.v25_1_skilladam_run_20261030_001.launcher.common import load_settings, record_folder, HOME,read,save,sha,now,require,verify,barrier


def alive(pid):
    try:os.kill(pid,0);return True
    except (ProcessLookupError,TypeError):return False


def launch(settings,side,phase):
    dest=HOME/side;dest.mkdir(exist_ok=True)
    receipt=dest/(phase+'_launch.json')
    require(not receipt.exists(),'Persistent launch receipt already exists: '+side+' '+phase)
    token=uuid.uuid4().hex
    argv=[settings['python'],'-B','-u',str(Path(__file__).with_name('worker.py')),phase,'--side',side,'--token',token]
    value={'status':'reserved','token':token,'argv':argv,'at':now()}
    save(receipt,value)
    with (dest/(phase+'.log')).open('ab',buffering=0) as log:
        proc=subprocess.Popen(argv,cwd=HOME,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
            start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    save(receipt,{**value,'status':'launched','pid':proc.pid})
    return proc


def run_phase(settings,phase):
    if phase=='test':barrier(settings)
    children={side:launch(settings,side,phase) for side in settings['arms']}
    exits={}
    while len(exits)<len(children):
        for side,child in children.items():
            if side in exits:continue
            rc=child.poll()
            if rc is not None:
                exits[side]=rc
                save(HOME/side/(phase+'_exit.json'),{'returncode':rc,'at':now()})
        save(HOME/'supervisor_status.json',{'status':'running','phase':phase,'pid':os.getpid(),
            'exits':exits,'at':now()})
        if len(exits)<len(children):time.sleep(settings['poll_seconds'])
    require(all(x==0 for x in exits.values()),phase+' worker failed; no automatic retry or next phase')


def supervise(token):
    require(read(HOME/'supervisor_launch.json')['token']==token,'Supervisor launch token differs')
    with (HOME/'.supervisor.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not (HOME/'supervisor_started.json').exists(),'Supervisor already consumed launch')
        save(HOME/'supervisor_started.json',{'at':now(),'pid':os.getpid()})
        try:
            settings=verify()
            run_phase(settings,'train')
            # Re-enter each frozen runtime independently for full final validation.
            for side in settings['arms']:
                subprocess.run([settings['python'],'-B',str(Path(__file__).with_name('worker.py')),'validate','--side',side],
                    cwd=HOME,check=True)
            save(HOME/'training_validation.json',{'status':'validated','arms':barrier(settings),'at':now()})
            run_phase(settings,'test')
            results={}
            for side,info in settings['arms'].items():
                folder=record_folder(info);r=read(folder/'test_complete.json');summary=read(folder/'test/summary.json')
                require(r['status']=='complete' and r['completed']==280 and summary['completed']==280
                        and len(summary['tasks'])==280,'Missing full Test completion')
                require(sha(folder/'test/summary.json')==r['summary_sha256'],'Test summary changed')
                results[side]=r
            barrier(settings)
            save(HOME/'final_results.json',{'status':'complete','results':results,'at':now()})
            save(HOME/'supervisor_status.json',{'status':'complete','at':now(),'pid':os.getpid()})
        except BaseException as exc:
            save(HOME/'supervisor_status.json',{'status':'stopped','error_type':type(exc).__name__,
                'error':str(exc)[:500],'pid':os.getpid(),'at':now()})
            raise


def start():
    with (HOME/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        settings=verify()
        require(not (HOME/'supervisor_launch.json').exists(),'Supervisor launch already reserved')
        for side,info in settings['arms'].items():
            require(read(HOME/side/'preflight.json')['status']=='passed','Preflight missing')
            folder=record_folder(info)
            require(not (folder/'campaign').exists() and not (folder/'test').exists(),'Output already exists')
        token=uuid.uuid4().hex
        argv=[settings['python'],'-B','-u',str(Path(__file__).resolve()),'supervise','--token',token]
        receipt={'token':token,'argv':argv,'at':now()}
        save(HOME/'supervisor_launch.json',receipt)
        with (HOME/'supervisor.log').open('ab',buffering=0) as log:
            proc=subprocess.Popen(argv,cwd=HOME,stdout=log,stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,start_new_session=True)
        save(HOME/'supervisor_launch.json',{**receipt,'pid':proc.pid})
        return {'status':'launched','supervisor_pid':proc.pid,'at':now()}


def status():
    settings=load_settings();output={}
    for side,info in settings['arms'].items():
        folder=record_folder(info);result={}
        for phase in ['train','test']:
            path=HOME/side/(phase+'_process.json');r=read(path) if path.exists() else {'status':'not_started'}
            result[phase]={**r,'pid_alive':alive(r.get('pid'))}
        if (folder/'campaign/state.json').exists():
            state=read(folder/'campaign/state.json');result['rounds_completed']=state['next_round']-1
            progress=folder/'campaign/rounds'/f"R{state['next_round']:02}"/'progress.json'
            if progress.exists():result['stage']=read(progress)
        if (folder/'campaign/checkpoint.json').exists():
            cp=read(folder/'campaign/checkpoint.json')
            result['next_iteration']=cp['next_iteration'];result['pending_post_decision']=cp['pending_post_decision']
        for name in ['training_complete','test_complete']:
            if (folder/(name+'.json')).exists():result[name]=read(folder/(name+'.json'))
        done=[]
        for path in (folder/'test/episodes').glob('*/result.json'):
            marker=read(path)
            trajectory = Path(marker['trajectory'])
            if side == 'v25_1':
                # Each episode's published path ends in attempts/<number>/trajectory.json.
                trajectory = path.parent / trajectory.relative_to(trajectory.parents[2])
            record = read(trajectory)
            done.append(record['score']['hard'])
        result['test_tasks_completed']=len(done);result['test_successes']=sum(done)
        output[side]=result
    sup=read(HOME/'supervisor_status.json') if (HOME/'supervisor_status.json').exists() else {'status':'not_started'}
    return {'supervisor':sup,'arms':output}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','supervise','status'])
    parser.add_argument('--token');args=parser.parse_args()
    if args.action=='supervise':supervise(args.token)
    else:
        import json
        print(json.dumps(start() if args.action=='start' else status(),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
