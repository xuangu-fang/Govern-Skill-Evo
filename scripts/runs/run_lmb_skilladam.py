"""Default to offline preflight; training requires an explicit run subcommand."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
from src.adapters.lmb.skilladam import DEFAULT_CONFIG, prepare, run


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('command', choices=('preflight', 'run'), nargs='?', default='preflight')
    parser.add_argument('--config', default=str(DEFAULT_CONFIG))
    parser.add_argument('--output')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if Path(sys.prefix).name != 'LiveMathematicianBench':
        parser.error('Use the independent LiveMathematicianBench environment')
    if args.command == 'preflight':
        _, dataset, _, native, context, snapshot = prepare(args.config)
        print(json.dumps({'status': 'ready_offline', 'python': sys.executable,
            'optimization_cases': len(dataset.splits['train']), 'test_cases': len(dataset.splits['test']),
            'batch_sizes': [len(b) for b in snapshot['batches']], 'model': context.model,
            'native': native.to_dict(), 'model_requests': 0}, ensure_ascii=False, indent=2))
    else:
        if not args.output:
            parser.error('run requires --output')
        run(args.config, args.output, resume=args.resume)


if __name__ == '__main__':
    main()
