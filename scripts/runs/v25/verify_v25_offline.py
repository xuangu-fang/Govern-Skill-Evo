#!/usr/bin/env python3
"""Full fifteen-task synthetic round using real Docker and preset model responses."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tests.skill_evolution.v25.support import config,ActorResponses,MethodResponses
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25 import evolution as ev


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    out=args.output.resolve()
    if out.exists():raise ValueError('Use a new offline verification output directory')
    out.mkdir(parents=True);cfg=config(out/'synthetic_workbooks',n=15)
    actors=ActorResponses();methods=MethodResponses(conflict=True)
    adapter=SpreadsheetBenchAdapter(generate=actors);campaign=out/'campaign'
    with using_benchmark(adapter):
        result=ev.run_campaign(campaign,config=cfg,generate=methods,actor_runner=adapter.actor_task)
        final=ev.final_parent(campaign)
        ev.run_campaign(campaign,resume=True,generate=methods,actor_runner=adapter.actor_task)
    gate=ev.read(campaign/'rounds/R01/gate/result.json')['result']
    records=[ev.read(p) for p in campaign.rglob('trajectory.json')]
    checks={'campaign_complete':result['status']=='complete','paired_tasks_15':gate['compared']==15,
            'parent_executed_once_per_task':len(records)==30 and len(actors.calls)==30,
            'hard_strict_improvement':gate['decision']=='ACCEPT','all_submitted_without_feedback':all(len(r['messages'])==3 and r['attempts'][0]['feedback_to_actor'] is None for r in records),
            'all_actual_docker_programs':all(r['program_executions']==1 and r['executor']['backend']=='docker' for r in records),
            'one_targeted_repair_no_second_verifier':methods.calls.count('repair')==methods.calls.count('verifier')==1,
            'final_parent_exists':final.is_file()}
    assert all(checks.values()),checks
    report={'scope':'Synthetic workbooks with preset responses; not benchmark effectiveness evidence','real_model_requests':0,'dataset_tasks_executed':0,
            'synthetic_tasks':15,'program_executions':sum(r['program_executions'] for r in records),'preset_actor_responses':len(actors.calls),
            'method_stages':methods.calls,'gate':gate,'checks':checks,'runtime':ev.read(campaign/'runtime.json'),'candidate':'v25_spreadsheetbench_verified400_rc1'}
    ev.save(out/'result.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
