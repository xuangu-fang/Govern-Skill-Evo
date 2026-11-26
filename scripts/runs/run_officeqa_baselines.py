#!/usr/bin/env python3
"""OfficeQA native training launchers and one final-Test entry for five arms."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    from src.adapters.officeqa import launchers as launch
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('preflight', 'train'):
        command = sub.add_parser(name)
        command.add_argument('directory')
        command.add_argument('--config', required=True)
        if name == 'train':
            command.add_argument('--start', action='store_true', help='Explicitly enable real training requests')
            command.add_argument('--resume', action='store_true')
            command.add_argument('--actor-key-env')
    evaluate = sub.add_parser('evaluate', help='Forward all five arms to the fixed-172 evaluate engine')
    evaluate.add_argument('directory')
    evaluate.add_argument('--arm', choices=launch.ARMS, required=True)
    for name in ('actor-config', 'prepared-root', 'parsed-root'):
        evaluate.add_argument('--' + name, required=True)
    evaluate.add_argument('--skill'); evaluate.add_argument('--training-run')
    evaluate.add_argument('--resume', action='store_true'); evaluate.add_argument('--actor-key-env')
    report = sub.add_parser('report'); report.add_argument('directory')
    args = parser.parse_args(argv)
    if args.command in ('evaluate', 'report'):
        from src.skill_evolution.v26.cli import main as evaluate_main
        if args.command == 'report':
            return evaluate_main(['report', args.directory])
        values = vars(args).copy(); values.pop('command'); values.pop('directory'); values.pop('arm')
        return evaluate_main(launch.evaluation_args(args.arm, args.directory, **values))
    config = launch.read(args.config)
    if args.command == 'preflight':
        plan = launch.prepare(config, args.directory)[0]
        summary = {'method': plan['method'], 'workers': plan['workers'],
            'train_cases': len(plan['train_ids']), 'selection_cases': len(plan['selection_ids']),
            'native_config': plan['native_config'], 'actor': plan['actor'],
            'test_during_training': False, 'stage0': False, 'requests': 0}
        if 'test_task_output_limits' in config:
            summary.update(initial_skill_sha256=plan['initial_skill_sha256'],
                           test_workers=config['test_workers'],
                           test_task_output_limits=config['test_task_output_limits'],
                           optimizer=config['optimizer'])
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        launch.require(args.start, 'Training requires --start; use preflight for offline validation')
        result = launch.train(config, args.directory, actor_key_env=args.actor_key_env, resume=args.resume)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
