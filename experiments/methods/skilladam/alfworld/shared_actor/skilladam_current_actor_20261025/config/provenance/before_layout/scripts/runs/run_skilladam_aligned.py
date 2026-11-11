#!/usr/bin/env python3
"""Frozen SkillAdam bridge. Offline by default; smoke requires --start."""
import argparse
from collections import defaultdict
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from alfworld_aligned_common import (configure_runtime, read, require, run_batch, sha, write)
from skilladam.benchmarks.alfworld.adapter import ALFWorldAdapter
from skilladam.core.feedback_loop import EditBudgetConfig, FeedbackLoopConfig
from skilladam.execution.contracts import BackendContext, GenerationResult, RawRollout
from skilladam.methods.skilladam import SkillAdamRunConfig, SkillAdamRunner
from skilladam.types import BenchmarkCase
from skilladam.usage import normalize_usage

EXPERIMENT = ROOT / 'experiments/baselines/skilladam_current_actor_20261025'
UPSTREAM = ROOT / 'external/SkillAdam'
COMMIT = 'b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


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
        require(sha(ROOT / relative) == expected, f'Frozen input changed: {relative}')
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
    require(actor == read(ROOT / 'experiments/baselines/alfworld_current_actor_20261025/actor.json'),
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


def convert_record(row):
    record = read(row['trajectory'])
    conversation = [{'role': 'user', 'content': record['goal']}]
    previous = record['initial_observation']
    for event in record['steps']:
        if event['phase'] != 'executed':
            continue
        action = event['action']
        call_id = f"step_{event['step']}"
        # Message/tool representation is required by the native condenser.
        # Do not synthesize chain-of-thought from hidden provider reasoning.
        conversation.append({'role': 'assistant', 'content': '', 'action': action,
                             'tool_calls': [{'id': call_id, 'type': 'function', 'function': {
                                 'name': 'alfworld_action', 'arguments': json.dumps({'action': action})}}]})
        conversation.append({'role': 'tool', 'tool_call_id': call_id,
                             'name': 'alfworld_action', 'action': action,
                             'content': event['observation'], 'pre_observation': previous,
                             'reward': event['reward'], 'done': event['done']})
        previous = event['observation']
    usages = [asdict(normalize_usage(a.get('usage'), requests=1))
              for step in record['steps'] for a in step.get('transport_attempts', [])]
    result = {**row, 'conversation': conversation}
    if usages:
        result['usage_records'] = usages
    return result


class SmokePause(RuntimeError):
    """Intentional, checkpoint-safe interruption before Momentum generation."""


class SharedBackend:
    def __init__(self, actor, cfg, output, *, pause=False, client=None):
        self.actor, self.cfg, self.output = actor, cfg, Path(output)
        self.pause, self.client = pause, client
        self.iteration = 0
        self.rollout_counts = defaultdict(int)
        self.new_generations = 0
        self.allowed = {t['id']: t for t in read(EXPERIMENT / 'optimization_items.json')}

    def execute_batch(self, execution):
        key = (self.iteration, execution.stage)
        index = self.rollout_counts[key]
        self.rollout_counts[key] += 1
        requests = execution.requests
        ids = [r.case.case_id for r in requests]
        require(set(ids) <= set(self.cfg['native']['optimization_case_ids']), 'Unexpected rollout cases')
        require(all(r.skill == requests[0].skill for r in requests), 'Mixed skills in one batch')
        require(bool(requests[0].skill), 'SkillAdam requires an initial Skill')
        output = self.output / 'shared_actor' / f'iter_{self.iteration:03d}' / f'{execution.stage}_{index}'
        signature = {'case_ids': ids, 'skill_sha256': digest(requests[0].skill), 'actor': self.actor}
        receipt = output / 'batch.json'
        if receipt.exists():
            require(read(receipt) == signature, 'Saved batch inputs differ')
        else:
            write(receipt, signature)
        rows = run_batch(self.actor, [self.allowed[key] for key in ids], requests[0].skill, output)
        values = [convert_record(row) for row in rows]
        write(output / 'skilladam_results.json', values)
        return tuple(RawRollout(row['id'], row) for row in values)

    def generate(self, request):
        from skilladam.backends.openai_compatible import (
            OpenAICompatibleConfig, _generation_payload, _generation_result)
        if self.pause and request.stage == 'momentum_update':
            require((self.output / 'checkpoint.json').exists(), 'Pause is not checkpoint-safe')
            raise SmokePause('Gate saved; resume to complete Momentum')
        transport = self.cfg['optimizer_transport']
        options = OpenAICompatibleConfig(max_completion_tokens=transport['max_tokens'],
                                        token_limit_field='max_tokens', reasoning_mode='top_level')
        payload = _generation_payload(request, options)
        payload['extra_body'] = {'thinking': {'type': 'enabled'}}
        payload['stream'] = False
        signature = {'iteration': self.iteration, 'stage': request.stage, 'payload': payload}
        directory = self.output / 'model_calls' / f'{request.stage}_{digest(signature)}'
        cached = directory / 'success.json'
        if cached.exists():
            saved = read(cached)
            require(saved['signature'] == signature, 'Cached generation signature differs')
            result = _generation_result(saved['response'])
            return replace(result, usage=tuple(normalize_usage(u) for u in saved['usage']))
        attempts = sorted(directory.glob('attempt_*.json')) if directory.exists() else []
        require(not attempts, 'Incomplete optimizer call requires explicit recovery; no silent retry reset')
        write(directory / 'request.json', signature)
        if self.client is None:
            import httpx
            from openai import OpenAI
            self.client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=self.actor['base_url'],
                                 max_retries=0, timeout=httpx.Timeout(300, connect=10))
        usage = []
        for attempt in range(1, transport['request_attempts'] + 1):
            path = directory / f'attempt_{attempt:02d}.json'
            evidence = {'started_at': now(), 'status': 'requesting'}
            write(path, evidence)
            started = time.monotonic()
            print(json.dumps({'event': 'model_request', 'stage': request.stage, 'attempt': attempt}), flush=True)
            try:
                self.new_generations += 1
                response = self.client.chat.completions.create(**payload)
                raw = response.model_dump(mode='json')
                evidence['response'] = raw
                usage.append(normalize_usage(raw.get('usage'), requests=1))
                require(len(raw.get('choices', [])) == 1, 'Unexpected choice count')
                require(raw['choices'][0].get('finish_reason') in ('stop', 'tool_calls'),
                        'Truncated or unfinished optimizer output')
                result = _generation_result(raw)
                evidence['status'] = 'complete'
                write(cached, {'signature': signature, 'response': raw, 'usage': [asdict(u) for u in usage]})
                return replace(result, usage=tuple(usage))
            except Exception as exc:
                evidence.update(status='error', error_type=type(exc).__name__)
                if 'response' not in evidence:
                    usage.append(normalize_usage(None, requests=1))
                if attempt == transport['request_attempts']:
                    raise RuntimeError(f'Optimizer {request.stage} exhausted attempts; inspect {directory}') from None
            finally:
                evidence['elapsed_seconds'] = time.monotonic() - started
                evidence['finished_at'] = now()
                write(path, evidence)
        raise AssertionError('unreachable')

    def public_metadata(self):
        return {'backend': 'current-shared-actor', 'optimizer_transport': self.cfg['optimizer_transport']}


class AlignedRunner(SkillAdamRunner):
    def _propose_patch(self, context):
        self.backend.iteration = context.iteration
        return super()._propose_patch(context)

    def _generate_momentum(self, context):
        self.backend.iteration = context.record.iteration
        return super()._generate_momentum(context)

    def _condense(self, case, evaluated, *, allow_llm=False):
        # Path manifests do not contain the environment's natural-language goal.
        case = replace(case, payload={**case.payload, 'task': evaluated.result.metadata['task_description']})
        return super()._condense(case, evaluated, allow_llm=allow_llm)


def run(mode, *, resume=False, pause=False):
    actor, cfg = read(EXPERIMENT / 'actor.json'), configuration(mode)
    output = ROOT / cfg['output_root']
    receipt = output.with_suffix('.launch.json')
    signature = {'manifest_sha256': sha(EXPERIMENT / 'manifest.json'), 'config': cfg}
    if resume:
        require(read(receipt) == signature, 'Resume frozen configuration differs')
        require((output / 'checkpoint.json').is_file(), 'No completed Gate checkpoint to resume')
    else:
        require(not output.exists() and not receipt.exists(), 'Output exists; use explicit resume')
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
    parser.add_argument('mode', nargs='?', choices=['check', 'smoke', 'formal'], default='check')
    parser.add_argument('--start', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--pause-after-gate', action='store_true')
    args = parser.parse_args(argv)
    report = check()
    if not args.start:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    require(args.mode != 'check', 'Select smoke or formal')
    require(not args.pause_after_gate or (args.mode == 'smoke' and not args.resume),
            'Pause injection is only for the first smoke invocation')
    # Prevent two writers from spending budget on the same output.
    import fcntl
    output = ROOT / configuration(args.mode)['output_root']
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.with_suffix('.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run(args.mode, resume=args.resume, pause=args.pause_after_gate)


if __name__ == '__main__':
    raise SystemExit(main())
