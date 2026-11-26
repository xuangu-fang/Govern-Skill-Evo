"""Default to offline preflight; run/evaluate require explicit subcommands."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
from src.adapters.searchqa.skilladam import DEFAULT_CONFIG, prepare, run


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('command', choices=('preflight', 'run', 'evaluate'), nargs='?', default='preflight')
    parser.add_argument('--config', default=str(DEFAULT_CONFIG))
    parser.add_argument('--output')
    parser.add_argument('--skill', help='Explicit fixed Skill for independent Test evaluation')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if Path(sys.prefix).name != 'SearchQA':
        parser.error('Use the independent SearchQA environment')
    if args.command == 'preflight':
        _, dataset, _, native, context, snapshot = prepare(args.config)
        print(json.dumps({'status': 'ready_offline', 'python': sys.executable,
            'optimization_cases': len(dataset.splits['train']), 'test_cases': len(dataset.splits['test']),
            'batch_sizes': [len(b) for b in snapshot['batches']], 'model': context.model,
            'native': {k: v for k, v in native.to_dict().items() if k != 'optimization_case_ids'},
            'model_requests': 0}, ensure_ascii=False, indent=2))
        return
    if not args.output:
        parser.error('run/evaluate requires --output')
    if args.command == 'run':
        if args.skill:
            parser.error('run uses the frozen v28 initial Skill; --skill is only for evaluate')
        run(args.config, args.output, resume=args.resume)
        return
    if not args.skill:
        parser.error('evaluate requires --skill; Test never selects or updates the Skill')
    from src.skill_evolution.v28.evaluation import run_evaluation
    from src.skill_evolution.v28.benchmarks.searchqa.actor import ChatTransport
    from src.adapters.searchqa.skilladam import actor_adapter
    cfg, dataset, _, _, _, _ = prepare(args.config)
    output = Path(args.output).resolve()
    allowed = ROOT / 'experiments/evaluations/searchqa_skilladam'
    if not output.is_relative_to(allowed) or output == allowed:
        parser.error('Use a dedicated directory under experiments/evaluations/searchqa_skilladam')
    transport = ChatTransport(os.environ[cfg['optimizer']['backend_config']['api_key_env']], metadata=cfg['actor'])
    report = run_evaluation(output, adapter=actor_adapter(dataset, transport,
                            workers=cfg['workers'], test_workers=cfg['test_workers']),
                            skill_file=args.skill, resume=args.resume)
    print(json.dumps({k: v for k, v in report.items() if k != 'cases'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
