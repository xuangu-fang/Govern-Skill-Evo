"""Explicit LMB entry points; validation never loads credentials or starts a run."""
import argparse
import json
from pathlib import Path
import sys


def credentials():
    from dotenv import dotenv_values
    from .facts import require
    from .benchmarks.lmb import protocol as p
    root=Path(__file__).resolve().parents[3]
    cfg=json.loads((root/'benchmarks/livemathematicianbench/model_access.json').read_text())
    value=dotenv_values(root/'.env')
    require(value.get('OPENAI_API_KEY'),'Missing OPENAI_API_KEY')
    require(value.get('OPENAI_BASE_URL','').rstrip('/')==cfg['base_url']=='https://api.deepseek.com','Model endpoint mismatch')
    require(cfg['model']==p.ACTOR['model'] and cfg['temperature']==p.ACTOR['temperature']
            and cfg['reasoning_effort']==p.ACTOR['reasoning_effort'] and cfg['thinking']==p.ACTOR['thinking']
            and cfg['timeout_seconds']==p.ACTOR['timeout_seconds'] and cfg['max_tokens']==p.ACTOR['max_tokens'],'Existing LMB model access differs')
    return value['OPENAI_API_KEY']


def main(argv=None):
    parser=argparse.ArgumentParser(description='v27 LMB; no implicit execution')
    sub=parser.add_subparsers(dest='command',required=True)
    prepare=sub.add_parser('prepare',help='Materialize independent 53/124 data view without model calls')
    prepare.add_argument('--prepared-root',required=True);prepare.add_argument('--output',required=True)
    validate=sub.add_parser('validate',help='Read-only configuration validation')
    run=sub.add_parser('run',help='Start or resume an explicitly configured campaign')
    for cmd in (validate,run):
        cmd.add_argument('--config',required=True);cmd.add_argument('--prepared-root',required=True)
    run.add_argument('directory');run.add_argument('--resume',action='store_true');run.add_argument('--archive-only',action='store_true')
    evaluate=sub.add_parser('evaluate',help='Independent frozen Test evaluation')
    evaluate.add_argument('directory');evaluate.add_argument('--prepared-root',required=True);evaluate.add_argument('--skill',required=True)
    evaluate.add_argument('--resume',action='store_true')
    report=sub.add_parser('report',help='Revalidate Test records without new requests')
    report.add_argument('directory');report.add_argument('--prepared-root',required=True)
    status=sub.add_parser('status');status.add_argument('directory')
    args=parser.parse_args(argv)
    if Path(sys.prefix).name!='LiveMathematicianBench':parser.error('Use the new LiveMathematicianBench environment')
    from .training import load_dataset
    from .benchmark import using_benchmark
    from .benchmarks.lmb.adapter import LMBAdapter
    from .benchmarks.lmb.actor import ChatTransport
    from .benchmarks.lmb import protocol as p
    from .evaluation import ArchiveTransport,run_evaluation,report_evaluation
    if args.command=='status':
        from .monitoring import status
        print(json.dumps(status(args.directory),ensure_ascii=False,indent=2));return
    data=load_dataset(args.prepared_root)
    if args.command=='prepare':print(data.export_view(args.output));return
    live=args.command in ('run','evaluate') and not getattr(args,'archive_only',False)
    key=credentials() if live else None
    adapter=LMBAdapter(data,ChatTransport(key) if live else ArchiveTransport(),
                       gate_metric=p.EM_GATE if args.command in ('run','validate') else None)
    with using_benchmark(adapter):
        if args.command=='evaluate':result=run_evaluation(args.directory,adapter=adapter,skill_file=args.skill,resume=args.resume)
        elif args.command=='report':result=report_evaluation(args.directory,adapter=adapter)
        else:
            from .config import validate_config
            config=json.loads(Path(args.config).read_text());validate_config(config)
            if args.command=='validate':result={'valid':True,'model_requests':0,'campaign_created':False}
            else:
                from .evolution import run_campaign
                from .transport import HTTPGenerator
                if args.archive_only:
                    from .facts import require
                    require(args.resume and (Path(args.directory)/'state.json').exists(),'Archive-only needs existing state and resume')
                result=run_campaign(args.directory,config=config,generate=HTTPGenerator(key) if live else None,resume=args.resume)
        print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
