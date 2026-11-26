#!/usr/bin/env python3
"""SkillAdam-only Actor task budgets; native optimization and shared Actor stay unchanged."""
import argparse
from contextlib import contextmanager
from copy import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.runs import run_officeqa_skilladam_deepseek as base
from src.adapters.officeqa import launchers as launch
from src.adapters.officeqa.runtime import Runtime
from src.adapters.officeqa.history import validate_history


class TaskBudgetRuntime(Runtime):
    def __init__(self, parsed_root, limits):
        super().__init__(parsed_root)
        self.limits = dict(limits)

    def run(self, case, skill, transport, *, owner, directory):
        limit = self.limits.get(case.case_id)
        if limit is not None:
            # A private transport per call prevents concurrent tasks sharing a changed budget.
            transport = copy(transport)
            transport.config = replace(transport.config, max_completion_tokens=limit)
        return super().run(case, skill, transport, owner=owner, directory=directory)


@contextmanager
def runtime_binding(config):
    previous = launch.Runtime
    launch.Runtime = lambda path: TaskBudgetRuntime(path, config['actor_task_output_limits'])
    try:
        yield
    finally:
        launch.Runtime = previous


def prepare(config, directory):
    launch.require(config['method'] == 'skilladam', 'SkillAdam only')
    launch.require(config['actor_task_output_limits'] == {'UID0007': 65536}, 'Unexpected task budget policy')
    launch.require(config['launch_adapter'] == {'path': str(Path(__file__).resolve()),
                   'sha256': launch.digest(Path(__file__))}, 'Task-budget launcher identity changed')
    launch.require(config['base_launcher_sha256'] == launch.digest(Path(base.__file__)), 'Base launcher changed')
    launch.require(config['optimizer']['thinking'] == {'type': 'enabled'}, 'Thinking must remain enabled')
    launch.require(config['optimizer']['backend_config']['reasoning_mode'] == 'top_level' and
                   config['optimizer']['backend_config']['token_limit_field'] == 'max_tokens', 'Wrong DeepSeek protocol')
    launch.require(launch.read(config['actor_config'])['max_completion_tokens'] == 32768, 'Default Actor budget changed')
    with runtime_binding(config):
        return launch.prepare(config, directory)


def import_first_batch(config, source, destination):
    """Reuse unchanged cases byte-for-byte; UID0007 is an explicitly new 65536 execution."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    launch.require(not destination.exists(), 'Continuation destination must be new')
    old_plan = launch.read(source / 'plan.json')
    plan, dataset, runtime, transport, initial = prepare(config, destination)
    old_config = old_plan['config']
    comparable = {k: v for k, v in config.items() if k not in
                  ('actor_task_output_limits', 'launch_adapter', 'base_launcher_sha256')}
    launch.require(comparable == {k: v for k, v in old_config.items() if k != 'launch_adapter'},
                   'Only task budget and launcher identity may change')
    for field in ('actor', 'runtime', 'sources', 'installed_native_sources', 'native_config',
                  'train_ids', 'selection_ids', 'initial_skill_sha256'):
        launch.require(plan[field] == old_plan[field], f'Prior run differs: {field}')
    launch.require(not any(p.is_file() for p in (source / 'native').rglob('*')),
                   'First-batch import cannot migrate optimizer progress')
    old_batch = source / 'actor/iter_000/training'
    all_batches = list((source / 'actor').glob('iter_*/*/run.json'))
    launch.require(all_batches == [old_batch / 'run.json'], 'Unexpected later Actor stages')
    batch = launch.read(old_batch / 'run.json')
    expected = config['native']['optimization_case_ids'][:10]
    launch.require(batch['ids'] == expected, 'First batch task IDs changed')
    rows = [json.loads(line) for line in (old_batch / 'results.jsonl').read_text().splitlines()]
    launch.require(len({r['id'] for r in rows}) == len(rows) and
                   all(r['id'] != 'UID0007' and r['id'] in expected for r in rows), 'Unexpected completed task')
    state_files = list((old_batch / 'cases').glob('*/actor_state.json'))
    states = {}
    for path in state_files:
        state = launch.read(path); uid = state['identity']['task_id']
        launch.require(uid in expected and uid not in states, 'Unexpected Actor state')
        validate_history(state, reasoning=True)
        initial_messages, _ = runtime.prepare(dataset.case(uid), initial)
        expected_identity = {'profile': state['identity']['profile'], 'method': 'skilladam',
            'task_id': uid, 'skill': initial, 'actor': plan['actor'],
            'input_sha256': hashlib.sha256(json.dumps({'messages': initial_messages,
                'reference': list(dataset.case(uid).reference)}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
        launch.require(state['identity'] == expected_identity and state['initial'] == initial_messages,
                       'Prior case identity changed')
        states[uid] = (path, state)
    launch.require(set(states) == set(expected), 'First batch states missing')
    for row in rows:
        launch.require(states[row['id']][1].get('record') == row['record'] and
                       states[row['id']][1]['status'] == 'completed', 'Journal/state mismatch')
    destination.mkdir()
    new_batch = destination / 'actor/iter_000/training'
    shutil.copytree(old_batch, new_batch)
    excluded = states['UID0007'][0].parent.relative_to(old_batch)
    shutil.rmtree(new_batch / excluded)  # Only the new disposable copy; source is preserved.
    inherited = {str(p.relative_to(old_batch)): launch.digest(p) for p in old_batch.rglob('*')
                 if p.is_file() and not p.is_relative_to(states['UID0007'][0].parent)}
    for path, digest in inherited.items():
        launch.require(launch.digest(new_batch / path) == digest, 'Imported file changed')
    launch.atomic_json(destination / 'plan.json', plan)
    (destination / 'initial_skill.md').write_text(initial)
    receipt = {'source': str(source), 'completed_task_ids': [r['id'] for r in rows],
        'continued_incomplete_ids': [uid for uid, (_, s) in states.items()
                                     if uid != 'UID0007' and not s['complete']],
        'new_execution_ids': ['UID0007'], 'new_execution_output_limit': 65536,
        'old_uid0007_state_sha256': launch.digest(states['UID0007'][0]),
        'inherited_file_sha256': inherited,
        'policy': 'Old UID0007 attempts remain in source; other cases retain every consumed attempt. All future UID0007 stages use 65536.'}
    launch.atomic_json(destination / 'task_budget_import.json', receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'train'))
    parser.add_argument('directory'); parser.add_argument('--config', required=True)
    parser.add_argument('--env-file', default=str(ROOT / '.env'))
    parser.add_argument('--start', action='store_true'); parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv); config = launch.read(args.config)
    plan = prepare(config, args.directory)[0]
    if args.command == 'preflight':
        print(json.dumps({'status': 'passed', 'tasks': len(plan['train_ids']),
                          'task_output_limits': config['actor_task_output_limits'], 'requests': 0}))
        return
    launch.require(args.start, 'Training requires --start')
    credentials = base.read_credentials(args.env_file)
    endpoint = credentials.get('OPENAI_BASE_URL', '').rstrip('/')
    launch.require(endpoint == config['optimizer']['base_url'].rstrip('/') and
                   plan['actor']['endpoint'] == endpoint + '/chat/completions', 'Endpoint differs')
    key_name = 'OFFICEQA_SKILLADAM_ACTOR_KEY'; previous = os.environ.get(key_name)
    os.environ[key_name] = credentials['OPENAI_API_KEY']
    try:
        backend = base.generation_backend(config, args.directory, credentials['OPENAI_API_KEY'])
        with runtime_binding(config):
            result = launch.train(config, args.directory, actor_key_env=key_name,
                                  resume=args.resume, optimizer_backend=backend)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if previous is None: os.environ.pop(key_name, None)
        else: os.environ[key_name] = previous


if __name__ == '__main__':
    main()
