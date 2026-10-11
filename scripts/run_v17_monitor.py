"""Matched one-rollout Monitor. --run explicitly starts paid Agent execution."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'external/tau2-bench/src'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--round-id',default='round-1')
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if args.output.exists():raise ValueError('new output directory required')
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env',override=True)
    from src.skill_evolution.monitor_benchmark_v17 import CurrentBenchmarkMonitor
    from src.skill_evolution.monitor_v17 import run_monitor
    # decode bytes rather than universal-newline normalization of Skill files.
    adapter=CurrentBenchmarkMonitor(artifact_dir=args.output/'backend',
        parent_skill=args.parent.read_bytes().decode('utf-8'),candidate_skill=args.candidate.read_bytes().decode('utf-8'))
    value=adapter.monitor_input(args.round_id)
    if not args.run:
        report={'status':'PREFLIGHT','tasks':len(value.tasks),'rollouts_per_task':1,
                'planned_agent_calls':2*len(value.tasks),'benchmark_config_digest':value.benchmark_config_digest}
        (args.output/'preflight.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
        return
    print(json.dumps(run_monitor(value,backend=adapter,artifact_dir=args.output/'monitor')))


if __name__=='__main__':main()
