"""Shared ALFWorld rollouts, optimizer transport and native SkillAdam hooks."""
from collections import defaultdict
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

from scripts.runs.alfworld.alfworld_aligned_common import read, require, run_batch, write
from src.skill_evolution.shared.experiment_paths import resolve_artifact_path
from skilladam.execution.contracts import RawRollout
from skilladam.methods.skilladam import SkillAdamRunner
from skilladam.usage import normalize_usage


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def convert_record(row):
    record = read(resolve_artifact_path(row['trajectory']))
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
    def __init__(self, actor, cfg, output, *, experiment, pause=False, client=None):
        self.actor, self.cfg, self.output = actor, cfg, Path(output)
        self.pause, self.client = pause, client
        self.iteration = 0
        self.rollout_counts = defaultdict(int)
        self.new_generations = 0
        self.allowed = {t['id']: t for t in read(experiment / 'optimization_items.json')}

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
