"""Prepare or resume SpreadsheetBench v25.4, then evaluate the published final Skill."""
import argparse
import fcntl
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.runs.v25_3 import run_v25_3_train_test as pipeline
from src.skill_evolution.v25_4 import PACKAGE, engine
from src.skill_evolution.v25_4.stages import freeze, read

DESIGN = ROOT / 'docs/methods/v25_4/design_manifest.json'
EXPERIMENT = ROOT / 'artifacts/methods/v25_4/v25_4_spreadsheetbench_proxy'


def checked_file(ref):
    path = ROOT / ref['path']
    if pipeline.sha(path) != ref['sha256']:
        raise ValueError(f'Frozen file differs: {path}')
    return path


def configurations():
    design = read(DESIGN)
    paths = {key: checked_file(ref) for key, ref in design['baseline'].items()}
    for path, sha in read(paths['method_contract']).items():
        checked_file({'path': pipeline.recorded_contract_path(path), 'sha256': sha})
    templates = dict(design['stage_templates'], execution_context=design['shared_execution_context'])
    for stage, ref in templates.items():
        path = checked_file(ref)
        if (PACKAGE / 'prompts' / (stage + '.md')).read_bytes() != path.read_bytes():
            raise ValueError(f'Runtime template differs: {stage}')
    train, test = (pipeline.read_config(paths[name]) for name in ('training_config', 'evaluation_config'))
    for config in (train, test):
        config['candidate'] = design['candidate']
        config['method']['version'] = design['method_version']
        pipeline.SpreadsheetBenchAdapter().validate_config(config)
    return train, test


def prepare(root):
    train, test = configurations()
    # Verify the Actor's transitive frozen imports and the actual workbook bytes.
    engine.configuration()
    expected_runtime = read(checked_file(read(DESIGN)['baseline']['evaluation_runtime']))
    runtime = dict(python=sys.executable, docker=pipeline.SpreadsheetBenchAdapter().runtime_snapshot(train),
                   evaluation_scorer_sha256=pipeline.sha(Path(pipeline.scoring.__file__)))
    if runtime != expected_runtime:
        raise ValueError('Interpreter, Docker or scoring differs from v25.3')
    files = (DESIGN, Path(__file__).resolve(), Path(pipeline.__file__))
    freeze(root / 'entry_contract.json', {str(f.relative_to(ROOT)): pipeline.sha(f) for f in files})
    engine.prepare(root / 'campaign', train)
    freeze(root / 'evaluation/config.json', test)
    freeze(root / 'runtime.json', runtime)
    return train, test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run'))
    parser.add_argument('--output', type=Path, default=EXPERIMENT, help='campaign and test output directory')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.pipeline.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        train, test = prepare(output)
        if args.action == 'run':
            pipeline.train_test(output, train, test, pipeline.credentials(), run_campaign=engine.run)
        else:
            print(f"Prepared v25.4: {len(train['batches'])} batches, {len(test['test_tasks'])} test tasks.")


if __name__ == '__main__':
    main()
