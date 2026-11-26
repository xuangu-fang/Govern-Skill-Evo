#!/usr/bin/env python3
"""Run only R01 of an unchanged v25 candidate, including on explicit resume."""
import argparse
import fcntl
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from src.skill_evolution.v25 import evolution as ev
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.cli import adapter_for


def run_pilot(campaign, *, config=None, resume=False, generate=None, actor_runner=None):
    root=Path(campaign).resolve();root.mkdir(parents=True,exist_ok=True)
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if config is not None:
            ev.require(not (root/'state.json').exists(),'Existing pilot requires resume')
            ev.initialize(root,config)
        else:ev.require(resume,'Existing pilot requires explicit resume')
        cfg=ev._config(root);ev._check_contract(root);ev.check_runtime(root)
        scope={'stop_after_round':1,'tasks':cfg['batches'][0],'test_tasks_enabled':False}
        if (root/'pilot_scope.json').exists():ev.require(ev.read(root/'pilot_scope.json')==scope,'Pilot scope changed')
        else:ev.save(root/'pilot_scope.json',scope)
        source=Path(__file__).read_text();snapshot=root/'pilot_entrypoint.py'
        if snapshot.exists():ev.require(snapshot.read_text()==source,'Pilot entrypoint changed')
        else:snapshot.write_text(source)
        state=ev.read(root/'state.json');ev.require(state['next_round'] in (1,2),'Pilot advanced beyond its scope')
        if state['next_round']==1:
            if (root/'stop.json').exists():
                stop=ev.read(root/'stop.json')
                ev.require(resume,'Stopped pilot requires explicit resume')
                ev.require(stop['kind']!='semantic','Semantic blocker cannot be resampled')
            ev.save(root/'pilot_progress.json',{'status':'running','started_at':ev.now()})
            try:
                ev.run_round(root,resume=resume,generate=generate,actor_runner=actor_runner or ev.actor_task)
            except BaseException as exc:
                ev.save(root/'pilot_progress.json',{'status':'stopped','error_type':type(exc).__name__,'at':ev.now()})
                raise
        result=ev.read(root/'rounds/R01/result.json')
        ev.require(result['status']=='completed' and ev.read(root/'state.json')['next_round']==2,'First round was not published')
        ev.require(not (root/'rounds/R02').exists(),'Unexpected second round')
        summary={'status':'pilot_complete','rounds_completed':1,'next_round_started':False,
                 'tasks':scope['tasks'],'outcome':result['outcome'],'cost':ev.cost_summary(root),'at':ev.now()}
        ev.save(root/'pilot_summary.json',summary);ev.save(root/'pilot_progress.json',{'status':'pilot_complete','at':ev.now()})
        return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['run','resume']);parser.add_argument('--campaign',type=Path,required=True)
    parser.add_argument('--config',type=Path);args=parser.parse_args()
    ev.require((args.action=='run')==(args.config is not None),'run needs --config; resume uses saved config')
    cfg=ev.read(args.config if args.config else args.campaign/'config.json')
    with using_benchmark(adapter_for(cfg)):
        ev.check_live_environment(cfg)
        result=run_pilot(args.campaign,config=cfg if args.action=='run' else None,resume=args.action=='resume')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
