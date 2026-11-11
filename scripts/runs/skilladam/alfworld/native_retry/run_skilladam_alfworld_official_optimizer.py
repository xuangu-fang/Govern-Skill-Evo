#!/usr/bin/env python3
"""ALFWorld: official DeepSeek optimizer, unchanged October 29 Actor and method.

Prepare/check are offline. Training requires --start; Test is never automatic.
"""
import argparse
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / 'experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/config'
sys.path[:0] = [str(ROOT / 'scripts/runs'), str(ROOT)]
from src.skill_evolution.skilladam.alfworld.shared_actor.paths import default_upstream, historical_input
sys.path.insert(0, str(default_upstream()))
from scripts.runs.alfworld.alfworld_aligned_common import read, write, sha, require
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from src.skill_evolution.skilladam.alfworld.native_retry.backend import (
    POLICY, backend_type, context_for, native_transport, transport_settings,
)
from src.skill_evolution.skilladam.alfworld.native_retry.layout import (
    current_binding, is_method_config, launch_files, output_binding,
)


from src.skill_evolution.skilladam.alfworld.native_retry.official_optimizer import desired_actor, desired_config


def bridge_module():
    path = ROOT / 'scripts/runs/skilladam/alfworld/shared_actor/run_skilladam_aligned.py'
    spec = importlib.util.spec_from_file_location('alfworld_original_bridge', path)
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    return bridge


def check(experiment):
    experiment = resolve_experiment_path(Path(experiment).resolve())
    manifest = read(experiment / 'manifest.json')
    require(sys.executable == manifest['python_executable'] and sys.version == manifest['python_version'],
            'Optimizer Python runtime changed')
    for p, expected in manifest['files'].items():
        path = Path(p) if manifest.get('canonical_paths') else historical_input(p, default_upstream())
        require(sha(path) == expected, f'Frozen file changed: {p}')
    for name, version in manifest['packages'].items():
        require(importlib.metadata.version(name) == version, f'Optimizer package changed: {name}')
    bridge = bridge_module()
    original_report = bridge.check()  # Original source/environment/commit/split checks, no model/env run.
    cfg, actor = read(experiment / 'skilladam.json'), read(experiment / 'actor.json')
    require(current_binding(cfg) == desired_config(read(SOURCE / 'skilladam.json'), experiment), 'Unexpected configuration change')
    transport_settings(cfg)
    require(actor == desired_actor(read(SOURCE / 'actor.json')), 'Unexpected Actor configuration change')
    for name in ('initial_skill.md', 'optimization_items.json',
                 'splits/train/items.json', 'splits/val/items.json', 'splits/test/items.json'):
        require((experiment / name).read_bytes() == (SOURCE / name).read_bytes(), f'Alignment differs: {name}')
    require(cfg['native']['feedback_loop']['patch_attempts'] == 3, 'Native patch retries changed')
    require(cfg['automatic_test'] is False and cfg['stage0_enabled'] is False and cfg['momentum'] is True,
            'Method initialization/Test policy changed')
    # Inspect runtime metadata only; do not import or initialize ALFWorld environments.
    runtime = json.loads(subprocess.check_output([actor['python'], '-c',
        'import sys,json,importlib.metadata as m;print(json.dumps({"python":sys.version,"packages":'
        '{d.metadata["Name"]:d.version for d in m.distributions()}}))'], text=True))
    require(runtime == read(experiment / 'actor_runtime.json'), 'Actor Python/packages changed')
    bridge.EXPERIMENT = experiment
    context = context_for(bridge, actor, cfg)
    runner = bridge.AlignedRunner(config=bridge.native_config(cfg), adapter=bridge.ALFWorldAdapter(experiment / 'splits'),
        backend=None, context=context, output_dir=resolve_experiment_path(cfg['output_root']))
    cases = runner._validate_cases(bridge.cases_for(cfg))
    batches = list(runner._build_sampler(cases))
    require([list(b.training_case_ids) for b in batches] == read(ROOT / actor['reference_campaign'])['batches'],
            'Batch order changed')
    require(all(b.training_case_ids == b.validation_case_ids for b in batches), 'Gate batch changed')
    return {**original_report, 'optimizer_retry_policy': POLICY, 'sdk_max_retries': 2, 'patch_attempts': 3,
            'native_method_settings_unchanged': True,
            'actor_config_byte_identical': (experiment / 'actor.json').read_bytes() == (SOURCE / 'actor.json').read_bytes(),
            'actor_changes': {}, 'workers': actor['workers'],
            'optimizer_model': cfg['optimizer_transport']['model'],
            'optimizer_base_url': cfg['optimizer_transport']['base_url'],
            'campaign_present': (resolve_experiment_path(cfg['output_root'])).exists(), 'dataset_tasks_executed': 0}


def prepare(experiment):
    experiment = resolve_experiment_path(Path(experiment).resolve())
    require(not experiment.exists(), 'Preparation requires a new directory')
    original = read(SOURCE / 'skilladam.json')
    require(sys.executable == original['python'], 'Use the original SkillAdam Python environment')
    bridge = bridge_module()
    bridge.check()
    # Retain historical result evidence; snapshot the source bundle without writing it.
    old_output = resolve_experiment_path(original['output_root'])
    preserved = read(SOURCE / 'preserved_results.json')
    source_files = {str(p): sha(p) for p in SOURCE.rglob('*') if p.is_file()}
    for name in ('actor.json', 'initial_skill.md', 'optimization_items.json',
                 'splits/train/items.json', 'splits/val/items.json', 'splits/test/items.json'):
        dest = experiment / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / name, dest)
    cfg = desired_config(original, experiment)
    require(not (resolve_experiment_path(cfg['output_root'])).exists(), 'New output already exists')
    write(experiment / 'skilladam.json', cfg)
    write(experiment / 'source_config.json', original)
    write(experiment / 'preserved_results.json', preserved)
    write(experiment / 'source_files.json', source_files)
    write(experiment / 'actor.json', desired_actor(read(SOURCE / 'actor.json')))
    actor = read(experiment / 'actor.json')
    runtime = json.loads(subprocess.check_output([actor['python'], '-c',
        'import sys,json,importlib.metadata as m;print(json.dumps({"python":sys.version,"packages":'
        '{d.metadata["Name"]:d.version for d in m.distributions()}}))'], text=True))
    write(experiment / 'actor_runtime.json', runtime)
    packages = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}
    (experiment / 'requirements.lock').write_text(''.join(f'{k}=={v}\n' for k, v in sorted(packages.items())))
    write(experiment / 'alignment.json', {'source_experiment': str(SOURCE), 'source_results': str(old_output),
        'optimizer_retry_policy': POLICY, 'native_method_settings_unchanged': cfg['native'] == original['native'],
        'optimizer_changes': {'model': {'before': original['optimizer_transport']['model'], 'after': 'deepseek-flash'},
                              'base_url': {'before': actor['base_url'], 'after': 'https://api.deepseek.com'},
                              'api_key_env': 'ALFWORLD_OPTIMIZER_KEY'},
        'sdk_max_retries': 2, 'patch_attempts': 3, 'historical_manual_recovery_not_inherited': True,
        'actor_changes': {}, 'actor_config_byte_identical': True,
        'model_requests': 0, 'dataset_tasks_executed': 0})
    source_manifest = read(SOURCE / 'manifest.json')
    files = {str(Path(p) if source_manifest.get('canonical_paths') else historical_input(p, default_upstream())): h
             for p, h in source_manifest['files'].items()}
    files.update(source_files)
    files[str(SOURCE / 'manifest.json')] = sha(SOURCE / 'manifest.json')
    files[str(Path(__file__).resolve())] = sha(__file__)
    files.update({str(p): sha(p) for p in experiment.rglob('*') if p.is_file()})
    write(experiment / 'manifest.json', {'canonical_paths': True, 'files': files, 'packages': packages,
        'python_executable': sys.executable, 'python_version': sys.version})
    report = check(experiment)
    results = experiment.parent / 'results' if is_method_config(experiment) else experiment
    write(results / 'preflight.json', report)
    return report


def start(experiment, *, resume=False):
    import fcntl
    experiment = resolve_experiment_path(Path(experiment).resolve())
    bridge = bridge_module()
    bridge.EXPERIMENT = experiment
    actor, cfg = read(experiment / 'actor.json'), read(experiment / 'skilladam.json')
    output = resolve_experiment_path(cfg['output_root'])
    # Configure the unchanged intranet Actor separately; never use its key for the official optimizer.
    bridge.configure_runtime(actor)
    require(os.environ.get(cfg['optimizer_transport']['api_key_env']),
            'ALFWORLD_OPTIMIZER_KEY is missing (official optimizer only)')
    lock_path, receipt = launch_files(output)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        signature = {'manifest_sha256': sha(experiment / 'manifest.json'), 'config': cfg}
        if resume:
            require(read(receipt) == signature and (output / 'checkpoint.json').is_file(), 'Resume configuration/checkpoint differs')
        else:
            require(not output.exists() and not receipt.exists(), 'Output exists; use explicit resume')
            write(receipt, signature)
        backend = backend_type(bridge)(actor, cfg, output)
        runner = bridge.AlignedRunner(config=bridge.native_config(cfg), adapter=bridge.ALFWorldAdapter(experiment / 'splits'),
            backend=backend, context=context_for(bridge, actor, cfg), output_dir=output)
        result = runner.run(cases=bridge.cases_for(cfg), initial_skill=(experiment / 'initial_skill.md').read_text(), resume=resume)
        write(output / 'completion.json', {'status': 'complete', 'automatic_test': False,
            'iterations': [r.to_dict() for r in result.feedback_loop.iterations],
            'resumed_from_iteration': result.feedback_loop.resumed_from_iteration,
            'new_optimizer_logical_calls': backend.new_generations})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', required=True, type=Path)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--prepare', action='store_true')
    actions.add_argument('--check', action='store_true')
    actions.add_argument('--start', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    require(not args.resume or args.start, '--resume requires --start')
    report = prepare(args.experiment) if args.prepare else check(args.experiment)
    if args.start:
        start(args.experiment, resume=args.resume)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
