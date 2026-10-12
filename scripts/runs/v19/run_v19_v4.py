"""Independent v19 benchmark-v4 campaign. Default: no-model preflight only."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'external/tau2-bench/src')]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generation-protocol',choices=('local','separated','legacy'),default='separated')
    parser.add_argument('--attribution-protocol',choices=('pair','legacy'),default='pair')
    parser.add_argument('--run',action='store_true',help='Execute real models; otherwise preflight only')
    parser.add_argument('--resume',action='store_true',help='Revalidate and continue this exact run')
    parser.add_argument('--diagnosis-recovery',type=Path,help='Explicit audited Diagnosis representation recovery receipt')
    parser.add_argument('--pilot',action='store_true',help='At most 2 full-split rounds instead of 4 formal rounds')
    parser.add_argument('--output',type=Path,help='New campaign directory, or existing one with --resume')
    parser.add_argument('--preflight-output',type=Path,help='New no-model preflight directory')
    parser.add_argument('--max-workers',type=int,default=8)
    args=parser.parse_args()
    if args.resume and not args.run:
        parser.error('--resume requires --run')
    if args.diagnosis_recovery and not (args.run and args.resume):
        parser.error('--diagnosis-recovery requires --run --resume')
    if args.preflight_output and args.run:
        parser.error('--preflight-output is only for no-model preflight')
    from loguru import logger
    logger.remove();logger.add(sys.stderr,level='WARNING')
    from src.skill_evolution.v19.campaign_v19 import campaign_config, preflight_campaign, run_campaign_v19
    from src.skill_evolution.v19.evolution_benchmark_v19 import BenchmarkEvolutionV19
    from src.skill_evolution.v19.monitor_campaign_v19 import BenchmarkMonitorV19
    from src.skill_evolution.v19.edit_tracking_v19 import encode
    config=campaign_config(pilot=args.pilot,max_workers=args.max_workers,generation_protocol=args.generation_protocol,attribution_protocol=args.attribution_protocol)
    from src.skill_evolution.v19.source_recovery_v19 import DiagnosisSourceRecovery
    recovery=DiagnosisSourceRecovery(args.diagnosis_recovery) if args.diagnosis_recovery else None
    evolution=BenchmarkEvolutionV19(source_recovery=recovery);monitor=BenchmarkMonitorV19(source_recovery=recovery)
    initial=(evolution.freeze/'S0.md').read_bytes().decode('utf-8')
    if not args.run:
        from datetime import datetime
        path=args.preflight_output or ROOT/'artifacts/methods/v19'/('v19_campaign_preflight_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
        print(encode(preflight_campaign(evolution_backend=evolution,monitor_backend=monitor,
              initial_skill=initial,config=config,artifact_dir=path)),flush=True)
        return
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env',override=True)
    prefix='v19_v4_local' if args.generation_protocol=='local' else 'v19_v4_separated'
    default_name=prefix+('_pilot_001' if args.pilot else '_formal_001')
    output=(args.output or ROOT / 'artifacts/methods/v19'/('pilot' if args.pilot else 'formal')/default_name).resolve()
    result=run_campaign_v19(output=output,config=config,run_id=output.name,initial_skill=initial,
        evolution_backend=evolution,monitor_backend=monitor,resume=args.resume,source_recovery=recovery)
    print(encode(result),flush=True)


if __name__=='__main__':
    main()
