#!/usr/bin/env python3
"""Prepare and preflight SkillOpt; live native training/Test requires run --start."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / 'external/SkillOpt'
DEFAULT = ROOT / 'experiments/baselines/skillopt_spreadsheetbench_official_actor48k_20261029'
V25 = ROOT / 'experiments/evaluations/v25_official_full280_r08_dualcheck_20261029_002'
OLD = ROOT / 'experiments/evaluations/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001'
ACTOR_PYTHON = Path('/tmp/govern-skill-v25-venv/bin/python')
WORKER = Path(__file__).with_name('skillopt_spreadsheetbench_actor.py')
sys.path[:0] = [str(ROOT), str(UPSTREAM)]
from skillopt.config import flatten_config, load_config
from skillopt.envs.spreadsheetbench.adapter import SpreadsheetBenchAdapter


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_defaults():
    return flatten_config(load_config(str(UPSTREAM / 'configs/spreadsheetbench/default.yaml')))


def overrides(root, shared):
    return {'model_backend': 'openai_compatible', 'optimizer_backend': 'openai_compatible',
            'target_backend': 'openai_compatible', 'optimizer_model': shared['actor_model'],
            'target_model': shared['actor_model'], 'reasoning_effort': shared['call_config']['reasoning_effort'],
            'skill_init': str(root / 'initial_skill.md'), 'out_root': str(root / 'campaign'),
            'split_dir': str(root / 'splits'),
            'data_root': str(Path(next(iter(shared['task_items'].values()))['input_path']).parent.parent),
            'workers': shared['actor_max_workers'], 'max_turns': shared['actor_profile']['max_code_attempts'],
            'max_completion_tokens': shared['actor_profile']['actor_max_output_tokens'],
            'exec_timeout': shared['actor_profile']['program_timeout_seconds'],
            'eval_final_skill': False}  # User requested Initial + Best Test only.


class SharedActorAdapter(SpreadsheetBenchAdapter):
    def __init__(self, root, *, runner=None):
        self.root = Path(root)
        self.shared = read(self.root / 'shared_config.json')
        cfg = read(self.root / 'skillopt.json')
        self.runner = runner or self.invoke
        super().__init__(**{key: cfg[key] for key in (
            'split_dir', 'split_mode', 'data_root', 'mode', 'max_turns', 'exec_timeout',
            'workers', 'analyst_workers', 'failure_only', 'minibatch_size', 'edit_budget',
            'seed', 'max_completion_tokens')})
        self.by_id = {task['dataset_id']: key for key, task in self.shared['task_items'].items()}

    @property
    def _env_name(self):
        # Keep upstream SpreadsheetBench prompt overrides when subclassing outside its package.
        return 'spreadsheetbench'

    def invoke(self, directory):
        proc = subprocess.run([str(ACTOR_PYTHON), str(WORKER), 'actor', str(directory)],
                              capture_output=True, text=True)
        (directory / 'worker.log').write_text(proc.stdout + proc.stderr)
        require(proc.returncode == 0, f'Shared Actor interrupted; inspect {directory}/worker.log')
        return read(directory / 'native_result.json')

    def rollout(self, env_manager, skill_content, out_dir, **kwargs):
        require(not kwargs.get('diagnostic_mode'), 'Shared Actor does not permit diagnostic interventions')
        # Native Trainer requests training-time eval feedback. The shared Actor
        # deliberately returns it only AFTER completion to the optimizer, like
        # V25/SkillAdam, never to the solving model.
        items = list(env_manager)
        keys = [self.by_id[str(item['id'])] for item in items]
        require(len(keys) == len(set(keys)) and bool(keys), 'Empty or duplicate batch')
        splits = {self.shared['task_items'][key]['split'] for key in keys}
        require(len(splits) == 1, 'Mixed train/Selection/Test batch')
        # Native Trainer only evaluates Test after all steps and final Selection promotion.
        if splits == {'test'}:
            require((self.root / 'campaign/history.json').is_file(), 'Test is forbidden before training')
            history = read(self.root / 'campaign/history.json')
            require(len(history) == 8 and [x['step'] for x in history] == list(range(1, 9)),
                    'Test is forbidden before all eight native optimization steps finish')
        directory = Path(out_dir)
        directory.mkdir(parents=True, exist_ok=True)
        signature = {'tasks': keys, 'skill': skill_content,
                     'shared_sha256': sha(self.root / 'shared_config.json'),
                     'native_use_eval_feedback': bool(kwargs.get('use_eval_feedback')),
                     'actor_receives_eval_feedback': False}
        binding = directory / 'shared_binding.json'
        if binding.exists():
            require(read(binding) == signature, 'Saved rollout task/Skill/config changed')
        else:
            write(binding, signature)

        def one(item):
            tid = str(item['id'])
            folder = directory / 'predictions' / tid
            folder.mkdir(parents=True, exist_ok=True)
            request = {'shared': self.shared, 'task': self.by_id[tid], 'skill': skill_content}
            if (folder / 'input.json').exists():
                require(read(folder / 'input.json') == request, 'Saved Actor inputs changed')
            else:
                write(folder / 'input.json', request)
            result = self.runner(folder)
            require(str(result['id']) == tid and result['hard'] in (0, 1)
                    and 0 <= result['soft'] <= 1, 'Malformed shared Actor result')
            return result

        rows, pending, todo = {}, {}, iter(items)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            for _ in range(min(self.workers, len(items))):
                item = next(todo)
                pending[pool.submit(one, item)] = str(item['id'])
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    rows[pending.pop(future)] = future.result()
                for _ in done:
                    item = next(todo, None)
                    if item is not None:
                        pending[pool.submit(one, item)] = str(item['id'])
        results = [rows[str(item['id'])] for item in items]
        (directory / 'results.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in results))
        return results


def configure_model(shared):
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    require(os.environ.get('OPENAI_BASE_URL', '').rstrip('/') == shared['actor_base_url'], 'Credential route mismatch')
    require(bool(os.environ.get('OPENAI_API_KEY')), 'Missing API credential')
    from skillopt.model.openai_compatible_backend import configure_openai_compatible
    call = shared['call_config']
    # Keep per-stage native output requests (up to native rewrite's 64000), not Actor's 48K budget.
    configure_openai_compatible(base_url=shared['actor_base_url'], api_key=os.environ['OPENAI_API_KEY'],
        model=shared['actor_model'], temperature=call['temperature'], timeout_seconds=call['timeout_seconds'], max_tokens=64000)
    for prefix in ('', 'OPTIMIZER_', 'TARGET_'):
        os.environ[prefix + 'OPENAI_COMPATIBLE_EXTRA_BODY'] = json.dumps({k: call[k] for k in ('thinking', 'reasoning_effort', 'stream')})
        # Native call sites request their own retries; do not impose a foreign method retry budget.
        os.environ.pop(prefix + 'OPENAI_COMPATIBLE_MAX_ATTEMPTS', None)
    os.environ.pop('OPENAI_COMPATIBLE_CONNECT_TIMEOUT_SECONDS', None)


def prepare(root):
    require(not root.exists(), 'Preparation requires a new directory')
    shared = read(V25 / 'config.json')
    root.mkdir(parents=True)
    write(root / 'references.json', {'v25_test': str(V25), 'skilladam_test': str(OLD),
                                  'actor_python': str(ACTOR_PYTHON), 'optimizer_python': sys.executable})
    write(root / 'shared_config.json', shared)
    native = native_defaults()
    write(root / 'native_defaults.json', native)
    write(root / 'skillopt.json', {**native, **overrides(root, shared)})
    (root / 'initial_skill.md').write_text(shared['initial_skill']['text'])
    for split in ('train', 'val', 'test'):
        original = read(UPSTREAM / f'data/spreadsheetbench_id_split/{split}/items.json')
        write(root / f'splits/{split}/items.json', original)
    write(root / 'test_plan.json', {'engine': 'skillopt.engine.trainer.ReflACTTrainer',
        'eval_test': True, 'eval_final_skill': False, 'tasks': shared['test_tasks'], 'denominator': 280,
        'roles': ['initial', 'best_selection'], 'primary_result': 'best_selection',
        'native_final_selection_and_best_promotion': True, 'identical_skill_reuse': 'native Trainer policy',
        'test_used_for_selection': False, 'launch_requires': 'run --start',
        'extra_technical_recoveries': 'not automatic; stop and retain interrupted Actor state'})
    (root / 'README.md').write_text((ROOT / 'docs/methods/skillopt/RUNNING.md').read_text())
    proc = subprocess.run([str(ACTOR_PYTHON), str(WORKER), 'check', str(root)], capture_output=True, text=True)
    require(proc.returncode == 0, 'Shared worker preflight failed: ' + proc.stderr[-2000:])
    write(root / 'actor_environment.json', json.loads(proc.stdout))
    files = [p for base in (UPSTREAM / 'skillopt', UPSTREAM / 'configs', ROOT / 'src/skill_evolution/v25')
             for p in base.rglob('*') if p.is_file() and p.suffix in ('.py', '.md', '.yaml')]
    files += list((ROOT / 'scripts/runs').glob('*.py'))
    files += [ROOT / 'docs/methods/skillopt/RUNNING.md',
              ROOT / 'tests/skill_evolution/v25/skillopt_native_preflight.py',
              ROOT / 'tests/skill_evolution/v25/test_skillopt_actor_bridge.py']
    files += [V25 / n for n in ('config.json', 'runtime.json', 'contract.json')]
    files += [OLD / n for n in ('controls/config.json', 'controls/contract.json', 'controls/runtime.json',
                                'four_way/final_arms_execution_manifest.json')]
    files += [Path(t[k]) for t in shared['task_items'].values() for k in ('input_path', 'answer_path')]
    files += [p for p in root.rglob('*') if p.is_file()]
    write(root / 'manifest.json', {'files': {str(p): sha(p) for p in sorted(set(files))},
        'optimizer_python': sys.executable, 'python_version': sys.version,
        'packages': {n: importlib.metadata.version(n) for n in ('openai', 'httpx', 'PyYAML')}})
    return check(root)


def check(root):
    manifest = read(root / 'manifest.json')
    # The October manifest included every top-level run script, even ALFWorld launchers.
    historical_paths = {}
    original_bridge = ROOT / 'scripts/runs/run_skilladam_aligned.py'
    if str(original_bridge) in manifest['files']:
        from src.skill_evolution.skilladam.alfworld.shared_actor.paths import historical_input
        scheduler = ROOT / 'scripts/runs/launch_alfworld_overnight.py'
        historical_paths = {
            original_bridge: historical_input(original_bridge),
            scheduler: historical_input(scheduler),
            **{ROOT / 'scripts/runs' / name: historical_input(ROOT / 'scripts/runs' / name)
               for name in ('run_alfworld_aligned.py', 'alfworld_aligned_common.py')},
            Path(__file__).resolve(): DEFAULT / 'configuration_revisions/002_alfworld_shared_actor_layout'
                / 'before/scripts/runs/run_skillopt_spreadsheetbench_aligned.py',
        }
    for path, digest in manifest['files'].items():
        source = historical_paths.get(Path(path), Path(path))
        require(source.is_file() and sha(source) == digest, 'Frozen file changed: ' + path)
    require(sys.executable == manifest['optimizer_python'] and sys.version == manifest['python_version'], 'Optimizer Python changed')
    for name, version in manifest['packages'].items():
        require(importlib.metadata.version(name) == version, 'Optimizer dependency changed: ' + name)
    shared, cfg = read(root / 'shared_config.json'), read(root / 'skillopt.json')
    require(shared == read(V25 / 'config.json'), 'Current V25 environment differs')
    require(cfg == {**native_defaults(), **overrides(root, shared)}, 'Native training rules changed')
    require(cfg['eval_test'] is True and cfg.get('eval_final_skill') is False, 'Expected Initial + Best Test only')
    test_plan = read(root / 'test_plan.json')
    require(test_plan['roles'] == ['initial', 'best_selection'] and test_plan['eval_final_skill'] is False
            and test_plan['tasks'] == shared['test_tasks'], 'Test plan differs from authorized policy')
    require((root / 'initial_skill.md').read_bytes() == (UPSTREAM / 'skillopt/envs/spreadsheetbench/skills/initial.md').read_bytes(), 'Initial Skill differs')
    # Validate the exact shared implementation against both frozen final Test archives.
    for reference in (V25, OLD / 'controls'):
        for relative, content in read(reference / 'contract.json').items():
            if relative.startswith('src/skill_evolution/v25/benchmarks/spreadsheetbench/') and (
                    Path(relative).name in ('actor.py', 'adapter.py', 'executor.py', 'protocol.py', 'transport.py', 'scoring.py')
                    or '/prompts/actor' in relative):
                require((ROOT / relative).read_text() == content, 'Shared Actor/scoring source drift: ' + relative)
    output_validation = ROOT / 'scripts/runs/repair_spreadsheetbench_output_submission.py'
    require(sha(output_validation) == read(OLD / 'four_way/final_arms_execution_manifest.json')['output_validation_sha256'], 'Output validation differs')
    old = read(OLD / 'controls/config.json')
    for key in ('actor_profile', 'actor_max_workers', 'executor', 'task_items', 'test_tasks', 'initial_skill'):
        require(shared[key] == old[key], 'SkillAdam shared condition differs: ' + key)
    adapter = SharedActorAdapter(root)
    adapter.setup(cfg)
    loader = adapter.get_dataloader()
    schedule = []
    all_ids = set()
    for split, expected in (('train', 80), ('val', 40), ('test', 280)):
        items = loader.get_split_items(split)
        ids = [str(t['id']) for t in items]
        require(len(ids) == len(set(ids)) == expected and not all_ids.intersection(ids), 'Invalid native splits')
        require(ids == [t['dataset_id'] for t in shared['task_items'].values() if t['split'] == split], 'Native/shared task order differs')
        all_ids.update(ids)
    for epoch in range(1, 5):
        batches = loader.plan_train_epoch(epoch=epoch, steps_per_epoch=2, accumulation=1, batch_size=40, seed=42)
        ids = [str(t['id']) for b in batches for t in b.payload]
        require(len(ids) == len(set(ids)) == 80 and set(ids) == {str(t['id']) for t in loader.train_items}, 'Epoch is not a Train-only pass')
        schedule.append({'epoch': epoch, 'batches': [[str(t['id']) for t in b.payload] for b in batches]})
    proc = subprocess.run([str(ACTOR_PYTHON), str(WORKER), 'check', str(root)], capture_output=True, text=True)
    require(proc.returncode == 0, 'Shared worker preflight failed: ' + proc.stderr[-2000:])
    worker = json.loads(proc.stdout)
    require(worker == read(root / 'actor_environment.json'), 'Actor runtime, dependencies or dataset audit changed')
    report = {'status': 'passed', 'model_requests': 0, 'benchmark_rollouts': 0,
        'training_started': (root / 'campaign').exists(), 'split_counts': {'train': 80, 'selection': 40, 'test': 280},
        'native_schedule': schedule, 'native_rules_unchanged': True, 'shared_worker': worker,
        'historical_route_difference': {'skilladam': [old['actor_base_url'], old['actor_model']],
                                      'v25_and_skillopt': [shared['actor_base_url'], shared['actor_model']]},
        'native_slow_update_gate_with_selection': cfg['slow_update_gate_with_selection'],
        'test_roles': test_plan['roles'], 'eval_final_skill': False,
        'note': 'Shared config batches describe the reference environment; only SkillOpt native loader drives training.'}
    write(root / 'preflight.json', report)
    return report


def run(root, *, resume=False):
    check(root)
    campaign = root / 'campaign'
    require(campaign.exists() == resume, 'Use explicit --resume only for an existing campaign')
    with (root / 'campaign.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        configure_model(read(root / 'shared_config.json'))
        from skillopt.engine.trainer import ReflACTTrainer
        try:
            return ReflACTTrainer(deepcopy(read(root / 'skillopt.json')), SharedActorAdapter(root)).train()
        finally:
            # Native token_summary only sees optimizer calls in this process.
            # Shared Actor processes retain independent cost records, including interrupted work.
            proc = subprocess.run([str(ACTOR_PYTHON), str(WORKER), 'cost', str(campaign)], capture_output=True, text=True)
            if proc.returncode == 0:
                write(root / 'actor_cost.json', json.loads(proc.stdout))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=('prepare', 'check', 'run'), default='check')
    parser.add_argument('--experiment', type=Path, default=DEFAULT)
    parser.add_argument('--start', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.action == 'run' and not args.start:
        parser.error('Live training and Test require explicit --start; use check for zero-request preflight')
    root = args.experiment.resolve()
    result = prepare(root) if args.action == 'prepare' else check(root) if args.action == 'check' else run(root, resume=args.resume)
    print(json.dumps({k: v for k, v in result.items() if k not in ('native_schedule', 'shared_worker')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
