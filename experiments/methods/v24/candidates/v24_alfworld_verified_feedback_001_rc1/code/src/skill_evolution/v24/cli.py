"""Composition boundary: select an explicit benchmark outside the method core."""
import argparse
import json
from pathlib import Path

from .benchmark import using_benchmark
from .facts import require


def adapter_for(config):
    from .benchmarks.alfworld.adapter import ALFWorldAdapter, IDENTITY
    require(config.get('benchmark') == IDENTITY, 'Unknown benchmark/adapter/profile version')
    return ALFWorldAdapter()


def main():
    from . import evolution as ev
    parser = argparse.ArgumentParser(description='V24 frozen verified skill evolution')
    parser.add_argument('action', choices=['audit-baseline', 'prepare', 'run', 'resume', 'status'])
    parser.add_argument('--campaign', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'audit-baseline':
        from .baseline import audit
        evidence, _ = audit()
        result = {'baseline': evidence['baseline'], 'source_files': len(evidence['source_files']), 'valid': True}
    elif args.action == 'prepare':
        require(args.output is not None, 'prepare requires --output')
        from .baseline import prepare
        result = prepare(args.output)
    else:
        require(args.campaign is not None, 'Specify --campaign')
        if args.action == 'run':
            require(args.config is not None, 'run requires --config')
            require(not args.campaign.exists() or not any(args.campaign.iterdir()), 'run requires an empty campaign')
            config = ev.read(args.config)
        else:
            require(args.config is None, 'Resume/status use the frozen campaign config')
            config = ev.read(args.campaign/'config.json')
        with using_benchmark(adapter_for(config)):
            if args.action == 'status':
                result = ev.status(args.campaign)
            else:
                result = ev.run_campaign(args.campaign, config=config if args.action == 'run' else None,
                                         resume=args.action == 'resume')
    print(json.dumps(result, ensure_ascii=False, indent=2))


def evaluation_main():
    from . import evaluation as evaluation, evolution as ev
    parser = argparse.ArgumentParser(description='V24 final evaluation; no method/Memory updates')
    parser.add_argument('action', choices=['run', 'resume', 'status'])
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--experiment', required=True, type=Path)
    parser.add_argument('--campaign', required=True, type=Path)
    args = parser.parse_args()
    config = ev.read(args.experiment/'config/campaign.json')
    with using_benchmark(adapter_for(config)):
        if args.action == 'status':
            result = {'completed': len(list((args.root/'episodes').glob('*/result.json'))),
                      'progress': ev.read(args.root/'progress.json') if (args.root/'progress.json').exists() else None}
        else:
            result = evaluation.run(args.root, experiment=args.experiment, campaign=args.campaign,
                                    resume=args.action == 'resume')
    print(json.dumps(result, ensure_ascii=False, indent=2))
