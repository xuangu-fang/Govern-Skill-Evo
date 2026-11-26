"""Composition boundary: select an explicit benchmark outside the method core."""
import argparse
import json
from pathlib import Path

from .benchmark import using_benchmark
from .facts import require


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = ROOT / 'experiments/methods/v25_1/v25_v25_1_common_actor_no_review_20261030_001_v25_1'


def read_config(path):
    config = json.loads(Path(path).read_text())
    # The published receipts retain absolute paths from the original checkout.
    data = Path('external/Trace2Skill/data/spreadsheetbench_verified/spreadsheetbench_verified_400')
    for task in config['task_items'].values():
        for key in ('input_path', 'answer_path'):
            prefix, marker, suffix = task[key].partition(data.as_posix() + '/')
            if marker and (not prefix or prefix.endswith('/')):
                task[key] = str(ROOT / data / suffix)
    return config


def adapter_for(config):
    from .benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter, IDENTITY
    require(config.get('benchmark') == IDENTITY, 'Unknown benchmark/adapter/profile version')
    return SpreadsheetBenchAdapter()


def prepare(output):
    from shutil import copyfile
    from tempfile import TemporaryDirectory

    from .storage import write_record

    output = Path(output)
    require(not output.exists(), 'Preparation requires a new directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        staged = Path(temporary) / 'experiment'
        destination = staged / 'config'
        (destination / 'evaluation').mkdir(parents=True)
        for name in ('config.json', 'evaluation/config.json'):
            write_record(destination / name, read_config(EXPERIMENT / 'config' / name))
        for name in ('initial_skill.md', 'evaluation/scoring.py'):
            copyfile(EXPERIMENT / 'config' / name, destination / name)
        staged.rename(output)
    return {'experiment': str(output), 'configuration': str(output / 'config/config.json')}


def main():
    from . import evolution as ev
    parser = argparse.ArgumentParser(description='SpreadsheetBench v25.1')
    parser.add_argument('action', choices=['prepare', 'run', 'resume', 'status'])
    parser.add_argument('--campaign', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        require(args.output is not None, 'prepare requires --output')
        result = prepare(args.output)
    else:
        require(args.campaign is not None, 'Specify --campaign')
        if args.action == 'run':
            require(args.config is not None, 'run requires --config')
            require(not args.campaign.exists() or not any(args.campaign.iterdir()), 'run requires an empty campaign')
            config = read_config(args.config)
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
    parser = argparse.ArgumentParser(description='V25 final evaluation; no method/Memory updates')
    parser.add_argument('action', choices=['run', 'resume', 'status'])
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--experiment', required=True, type=Path)
    parser.add_argument('--campaign', required=True, type=Path)
    args = parser.parse_args()
    config = read_config(args.experiment/'config/config.json')
    with using_benchmark(adapter_for(config)):
        if args.action == 'status':
            result = {'completed': len(list((args.root/'episodes').glob('*/result.json'))),
                      'progress': ev.read(args.root/'progress.json') if (args.root/'progress.json').exists() else None}
        else:
            result = evaluation.run(args.root, experiment=args.experiment, campaign=args.campaign,
                                    resume=args.action == 'resume')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
