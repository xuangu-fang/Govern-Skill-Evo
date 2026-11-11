#!/usr/bin/env python3
"""Shared Actor SkillAdam bridge. Offline by default; training requires --start."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.skilladam.alfworld.shared_actor.paths import (
    COMMIT, CONFIG, default_upstream, historical_input,
)
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path

# Dynamic consumers choose their own upstream before loading this bridge.
if __name__ == '__main__' or __package__:
    sys.path.insert(0, str(default_upstream()))
import skilladam
from skilladam.benchmarks.alfworld.adapter import ALFWorldAdapter
from skilladam.core.feedback_loop import EditBudgetConfig, FeedbackLoopConfig
from skilladam.execution.contracts import BackendContext
from skilladam.types import BenchmarkCase
from skilladam.methods.skilladam import SkillAdamRunConfig, SkillAdamRunner
from skilladam.usage import normalize_usage

from scripts.runs.alfworld.alfworld_aligned_common import configure_runtime, read, require, sha, write
from src.skill_evolution.skilladam.alfworld.shared_actor import backend
from src.skill_evolution.skilladam.alfworld.shared_actor.backend import (
    AlignedRunner, SmokePause, convert_record, digest, now,
)

EXPERIMENT = CONFIG
UPSTREAM = Path(skilladam.__file__).resolve().parents[1]


class SharedBackend(backend.SharedBackend):
    """Bind the active bridge configuration, including derived experiments."""
    def __init__(self, actor, cfg, output, *, pause=False, client=None):
        super().__init__(actor, cfg, output, experiment=EXPERIMENT, pause=pause, client=client)


def configuration(mode):
    return read(EXPERIMENT / ('smoke.json' if mode == 'smoke' else 'skilladam.json'))


def native_config(cfg):
    value = dict(cfg['native'])
    loop = dict(value.pop('feedback_loop'))
    loop['edit_budget'] = EditBudgetConfig(**loop['edit_budget'])
    return SkillAdamRunConfig(**value, feedback_loop=FeedbackLoopConfig(**loop))


def cases_for(cfg):
    items = {item['id']: item for item in read(EXPERIMENT / 'optimization_items.json')}
    # Native same-batch sampling uses one logical train pool. Original split/id
    # remain intact for the shared Actor's lookup and access policy.
    return tuple(BenchmarkCase(case_id=key, payload=items[key], metadata={
        'split': 'train', 'original_split': key.split(':')[0]})
        for key in cfg['native']['optimization_case_ids'])


def check():
    lock = read(EXPERIMENT / 'manifest.json')
    for relative, expected in lock['files'].items():
        require(sha(historical_input(relative, UPSTREAM)) == expected, f'Frozen input changed: {relative}')
    actor = read(EXPERIMENT / 'actor.json')
    for relative, expected in lock['environment_files'].items():
        require(sha(Path(actor['environment_root']) / relative) == expected,
                f'Environment changed: {relative}')
    actual = subprocess.check_output(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD'], text=True).strip()
    require(actual == COMMIT, 'SkillAdam commit changed')
    for name, version in lock['packages'].items():
        require(importlib.metadata.version(name) == version, f'Package changed: {name}')
    campaign = read(ROOT / actor['reference_campaign'])
    require((EXPERIMENT / 'initial_skill.md').read_text() == campaign['initial_skill']['text'],
            'Initial Skill differs from own method')
    require(actor == read(ROOT / 'experiments/baselines/alfworld/alfworld_current_actor_20261025/actor.json'),
            'Shared Actor settings differ')
    cfg = configuration('formal')
    context = BackendContext('alfworld', 'skilladam', actor['model'], 'medium', 8, 42)
    runner = SkillAdamRunner(config=native_config(cfg), adapter=ALFWorldAdapter(EXPERIMENT / 'splits'),
                            backend=None, context=context, output_dir=Path('/unused'))
    cases = runner._validate_cases(cases_for(cfg))
    batches = list(runner._build_sampler(cases))
    require([list(b.training_case_ids) for b in batches] == campaign['batches'], 'Batch order differs')
    require(all(b.training_case_ids == b.validation_case_ids for b in batches), 'Gate is not same-batch')
    tests = read(EXPERIMENT / 'splits/test/items.json')
    require(len(tests) == 134 and not {c.case_id for c in cases} & {t['id'] for t in tests},
            'Test leakage or incorrect test count')
    for mode in ('formal', 'smoke'):
        c = configuration(mode)
        require(c['automatic_test'] is False, 'Automatic Test must remain disabled')
        require(native_config(c).gate_profile == 'main-result', 'Wrong gate profile')
    require(set(configuration('smoke')['native']['optimization_case_ids']) <=
            {c.case_id for c in cases if c.case_id.startswith('train:')}, 'Smoke must use training tasks')
    return {'status': 'passed', 'mode': 'offline', 'model_requests': 0,
            'optimization_tasks': len(cases), 'test_tasks': len(tests),
            'batch_sizes': [len(b.training_case_ids) for b in batches],
            'initial_skill_sha256': sha(EXPERIMENT / 'initial_skill.md'),
            'gate': 'accept-hard-non-regression', 'commit': actual}


def run(mode, *, resume=False, pause=False):
    actor, cfg = read(EXPERIMENT / 'actor.json'), configuration(mode)
    original = ROOT / cfg['output_root']
    output = resolve_experiment_path(original)
    receipt = resolve_experiment_path(original.with_suffix('.launch.json'))
    signature = {'manifest_sha256': sha(EXPERIMENT / 'manifest.json'), 'config': cfg}
    if resume:
        require(read(receipt) == signature, 'Resume frozen configuration differs')
        require((output / 'checkpoint.json').is_file(), 'No completed Gate checkpoint to resume')
    else:
        lock = resolve_experiment_path(original.with_suffix('.lock'))
        fresh = not output.exists() or (output.is_dir() and all(
            p in (lock, lock.parent) for p in output.rglob('*')))
        require(not receipt.exists() and fresh,
                'Output exists; use explicit resume')
        output.parent.mkdir(parents=True, exist_ok=True)
        write(receipt, signature)
    configure_runtime(actor)
    backend = SharedBackend(actor, cfg, output, pause=pause)
    context = BackendContext('alfworld', 'skilladam', actor['model'], 'medium', actor['workers'], 42)
    runner = AlignedRunner(config=native_config(cfg), adapter=ALFWorldAdapter(EXPERIMENT / 'splits'), backend=backend,
                           context=context, output_dir=output)
    try:
        result = runner.run(cases=cases_for(cfg), initial_skill=(EXPERIMENT / 'initial_skill.md').read_text(),
                            resume=resume)
    except SmokePause:
        write(output / 'smoke_pause.json', {'status': 'paused_after_gate', 'time': now(),
                                          'new_optimizer_requests': backend.new_generations})
        print('Smoke paused after saved Gate; no final Test was started.', flush=True)
        return 0
    write(output / 'completion.json', {'status': 'complete', 'mode': mode, 'finished_at': now(),
                                     'iterations': [r.to_dict() for r in result.feedback_loop.iterations],
                                     'resumed_from_iteration': result.feedback_loop.resumed_from_iteration,
                                     'new_optimizer_requests': backend.new_generations,
                                     'automatic_test': False})
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', nargs='?', choices=['check', 'read-archive', 'smoke', 'formal'], default='check')
    parser.add_argument('--start', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--pause-after-gate', action='store_true')
    args = parser.parse_args(argv)
    if args.mode == 'read-archive':
        if args.start or args.resume or args.pause_after_gate:
            parser.error('read-archive only reads completed records')
        from src.skill_evolution.skilladam.alfworld.shared_actor.archive import read_archive
        print(json.dumps(read_archive(), ensure_ascii=False, indent=2))
        return 0
    report = check()
    if not args.start:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    require(args.mode != 'check', 'Select smoke or formal')
    require(not args.pause_after_gate or (args.mode == 'smoke' and not args.resume),
            'Pause injection is only for the first smoke invocation')
    # Prevent two writers from spending budget on the same output.
    import fcntl
    original = ROOT / configuration(args.mode)['output_root']
    lock = resolve_experiment_path(original.with_suffix('.lock'))
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run(args.mode, resume=args.resume, pause=args.pause_after_gate)


if __name__ == '__main__':
    raise SystemExit(main())
