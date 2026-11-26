#!/usr/bin/env python3
"""SkillAdam with the frozen V25 SpreadsheetBench environment; offline by default."""
import argparse
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
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

ROOT = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.skilladam.spreadsheetbench.layout import UPSTREAM
EXPERIMENT = ROOT / 'artifacts/methods/skilladam/spreadsheetbench/shared_actor/skilladam_spreadsheetbench_v25matched_20261026'
sys.path[:0] = [str(ROOT), str(UPSTREAM)]

from skilladam.backends.openai_compatible import _generation_payload, _generation_result, OpenAICompatibleConfig
from skilladam.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from skilladam.core.diff_apply import apply_patch_with_fallback
from skilladam.core.feedback_loop import EditBudgetConfig, FeedbackLoopConfig
from skilladam.execution.contracts import BackendContext, RawRollout
from skilladam.execution.backend import BackendProtocolError
from skilladam.methods.skilladam import SkillAdamRunConfig, SkillAdamRunner, _validate_momentum_tool_calls
from skilladam.methods.skilladam_prompts import IterationGeneration
from skilladam.types import BenchmarkCase, RolloutRequest
from skilladam.usage import normalize_usage
from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.prepared.actor_runtime import evolution as ev
from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.prepared.actor_runtime import output_feedback as feedback
from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.prepared.actor_runtime.feedback_retry import RequestFailure, request_failure
from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.prepared.actor_runtime.benchmarks.spreadsheetbench import actor, executor, protocol, facts
from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.prepared.actor_runtime.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter as SharedAdapter


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ev.save(path, value)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def native_config(cfg):
    native = deepcopy(cfg['native'])
    loop = native.pop('feedback_loop')
    loop['edit_budget'] = EditBudgetConfig(**loop['edit_budget'])
    return SkillAdamRunConfig(**native, feedback_loop=FeedbackLoopConfig(**loop))


def cases_for(shared, cfg):
    # One logical native pool; retain original identities, never expose gold paths.
    return tuple(BenchmarkCase(case_id=key, payload={'instruction': shared['task_items'][key]['instruction']},
                               metadata={'split': 'train', 'original_split': shared['task_items'][key]['split']})
                 for key in cfg['native']['optimization_case_ids'])


def context_for(shared, cfg):
    return BackendContext('spreadsheetbench', 'skilladam', cfg['optimizer_transport'].get('model', shared['actor_model']),
                          cfg['optimizer_transport']['reasoning_effort'], shared['actor_max_workers'],
                          cfg['native']['seed'])


def validate_actor_protocol(shared, cfg):
    """Freeze the environment and evidence view without changing native method knobs."""
    SharedAdapter().validate_config(shared)
    if 'comparison_profile' in shared or 'comparison_profile' in cfg:
        from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.prepared.actor_runtime.baseline import validate_latest_configuration, COMPARISON_PROFILE
        validate_latest_configuration(shared)
        require(cfg.get('comparison_profile')==COMPARISON_PROFILE,'SkillAdam comparison profile differs')
        require(cfg.get('stage0_enabled') is False and cfg.get('automatic_test') is False and cfg.get('momentum') is True,
                'Unexpected Stage0, Test or Momentum condition')
        require(cfg['optimizer_transport']['max_tokens']==16384,'SkillAdam native optimizer output budget differs')
    view=cfg.get('actor_evidence_view','raw_attempts_v1')
    expected=protocol.EXECUTION_HISTORY if protocol.execution_history(shared['actor_profile']) else 'raw_attempts_v1'
    require(view==expected, 'SkillAdam evidence view differs from shared Actor history policy')
    require(cfg['optimizer_transport']['request_attempts_total']==shared['max_attempts']
            and cfg['optimizer_transport']['sdk_max_retries']==0
            and cfg['native']['feedback_loop']['patch_attempts']==1, 'Nested or mismatched retry budget')
    return {'actor_history_policy':shared['actor_profile'].get('actor_history_policy','cumulative_responses_v1'),
            'actor_evidence_view':view}


class AlignedAdapter(SpreadsheetBenchAdapter):
    def build_rollout_request(self, case, *, method, split, skill, seed):
        require(method == 'skilladam' and split == 'train' and skill, 'Unexpected rollout request')
        return RolloutRequest(case, method, split, skill, seed, {'environment': 'v25-shared'})


def convert_record(record):
    # New protocol uses exactly the V25 audited view, before native condensation.
    # Legacy archives retain their original response and evidence semantics.
    filtered=protocol.execution_history(record['protocol'])
    run=facts.build_facts([record])['facts']['runs'][0] if filtered else None
    events=run['attempts'] if filtered else record['attempts']
    messages = deepcopy(record['initial_messages'])
    for event in events:
        # Native condensation recognizes assistant/tool records. These tools are
        # evidence serialization only; they are never sent to the shared Actor.
        messages.append({'role': 'assistant', 'content': event['response']})
        execution={'executed': event['executed'], 'execution': event['execution'],
                   'response_in_history': event.get('response_in_history', True),
                   'code_attempt': event.get('code_attempt', event.get('number'))}
        if filtered:
            execution.update(ref=event['ref'],executed_code=event['executed_code'],
                             request_context=event['request_context'])
        messages.append({'role': 'tool', 'name': 'harness_execution_not_actor_feedback',
                         'content': json.dumps(execution,ensure_ascii=False)})
        messages.append({'role': 'tool', 'name': 'actual_feedback_to_actor',
                         'content': json.dumps(event['feedback_to_actor'], ensure_ascii=False)})
    if filtered:
        messages.append({'role':'tool','name':'post_execution_outcome_not_actor_feedback',
                         'content':json.dumps(run['outcome'],ensure_ascii=False)})
    score = record['score']
    return {'id': record['task']['id'], 'messages': messages, 'hard': score['hard'],
            'per_cell_pass_rate': score['per_cell_pass_rate'],
            'exec_pass': int(record['termination'] == 'valid_workbook_submitted'),
            'n_turns': record['code_attempts'], 'n_cells_total': score['total_cells'],
            'n_cells_match': score['correct_cells'], 'fail_reason': record['termination'],
            'code': events[-1]['executed_code'] or '' if events else '',
            'usage_records': [asdict(normalize_usage((r.get('response') or {}).get('usage'), requests=1))
                              for r in record['requests']]}


class SharedBackend:
    def __init__(self, shared, cfg, output, *, sender=None, resume=False):
        self.actor_protocol=validate_actor_protocol(shared,cfg)
        self.shared, self.cfg, self.output = shared, cfg, Path(output)
        self.iteration, self.rollout_counts = 0, defaultdict(int)
        self.sender, self.resume = sender or self.send, resume
        self.patch_context, self.momentum = None, None
        self.queries = {}

    def execute_batch(self, execution):
        requests = execution.requests
        ids = [r.case.case_id for r in requests]
        require(execution.context == context_for(self.shared, self.cfg), 'Backend context changed')
        require(len(ids) == len(set(ids)) and set(ids) <= set(self.cfg['native']['optimization_case_ids']),
                'Unexpected or duplicate rollout cases')
        skill = requests[0].skill
        require(skill and all(r.skill == skill for r in requests), 'Missing or mixed batch skills')
        key = (self.iteration, execution.stage)
        index = self.rollout_counts[key]
        self.rollout_counts[key] += 1
        directory = self.output / 'shared_actor' / f'iter_{self.iteration:03d}' / f'{execution.stage}_{index}'
        signature = {'case_ids': ids, 'skill': skill, 'shared_config_sha256': digest(self.shared)}
        if protocol.execution_history(self.shared['actor_profile']):signature.update(self.actor_protocol)
        marker = directory / 'batch.json'
        if marker.exists():
            require(read(marker) == signature, 'Saved batch inputs changed')
        else:
            write(marker, signature)

        def one(key):
            folder = directory / key.replace(':', '_')
            path = actor.run(self.shared['task_items'][key], skill, folder, self.shared)
            record = SharedAdapter().check_record(read(path), key, skill, self.shared)
            self.queries[key] = record['initial_messages'][-1]['content']
            print(json.dumps({'event': 'actor_complete', 'iteration': self.iteration,
                              'stage': execution.stage, 'case': key, 'hard': record['score']['hard']}), flush=True)
            return RawRollout(key, convert_record(record))

        # Match V25 bounded scheduling: do not replenish the queue after failure.
        rows, pending, todo = {}, {}, iter(ids)
        with ThreadPoolExecutor(max_workers=self.shared['actor_max_workers']) as pool:
            for key in list(ids)[:self.shared['actor_max_workers']]:
                next(todo)
                pending[pool.submit(one, key)] = key
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    key = pending.pop(future)
                    rows[key] = future.result()
                for _ in done:
                    key = next(todo, None)
                    if key is not None:
                        pending[pool.submit(one, key)] = key
        return tuple(rows[key] for key in ids)

    def send(self, body, directory):
        import requests
        from urllib.parse import urlsplit
        cfg = self.shared['call_config']
        timeout = self.cfg['optimizer_transport']['timeout_seconds']
        write(directory / 'request.json', {'endpoint': cfg['endpoint'], 'body': body,
                                          'timeout_seconds': timeout, 'attempts': 1})
        with requests.Session() as session:
            if '.intra.' in (urlsplit(cfg['endpoint']).hostname or ''):
                session.trust_env = False
            raw = session.post(cfg['endpoint'], headers={'Authorization': f"Bearer {os.environ['OPENAI_API_KEY']}"},
                               json=body, timeout=(10, timeout), allow_redirects=False)
        (directory / 'http_response.txt').write_bytes(raw.content)
        write(directory / 'http_status.json', {'status_code': raw.status_code})
        require(200 <= raw.status_code < 300, f'Model API returned HTTP {raw.status_code}')
        return raw.json()

    def validate_output(self, request, result):
        if request.stage == 'iteration_patch':
            parsed = IterationGeneration.from_raw_text(result.text)
            report = apply_patch_with_fallback(self.patch_context.current_skill, parsed.patch)
            require(not (parsed.patch.strip() and report.hunks_total == 0) and not report.all_failed,
                    '; '.join(report.fail_diagnostics) or 'patch contained no applicable hunks')
        elif request.stage == 'momentum_update':
            _validate_momentum_tool_calls(result.tool_calls, request.metadata['tools'])
            tracker = deepcopy(self.momentum)
            for call in result.tool_calls:
                response = tracker.execute_tool_call(call.name, dict(call.arguments))
                require(not response.startswith('Unknown tool:') and ' call failed:' not in response, response)
        elif request.stage == 'trajectory_compression':
            require(result.text.strip(), 'trajectory compression returned empty text')
        else:
            raise RuntimeError(f'Unexpected generation stage: {request.stage}')

    def generate(self, request):
        cfg = self.cfg['optimizer_transport']
        body = _generation_payload(request, OpenAICompatibleConfig(
            max_completion_tokens=cfg['max_tokens'], token_limit_field='max_tokens',
            temperature=cfg['temperature'], reasoning_mode='top_level'))
        body.update(thinking=self.shared['call_config']['thinking'], stream=False)
        signature = {'iteration': self.iteration, 'stage': request.stage, 'body': body}
        directory = self.output / 'model_calls' / f'{request.stage}_{digest(signature)}'
        cached = directory / 'success.json'
        if cached.exists():
            saved = read(cached)
            require(saved['signature'] == signature, 'Cached request changed')
            result = _generation_result(saved['response'])
            self.validate_output(request, result)
            return replace(result, usage=tuple(normalize_usage(u) for u in saved['usage']))
        existing = sorted(directory.glob('attempt_*'))
        require(not existing or self.resume, 'Prior attempts require explicit resume')
        write(directory / 'request.json', signature)
        context = {'policy': feedback.POLICY, 'feedback_from': None}
        usage = []
        for path in existing:
            if (path / 'usage.json').exists():
                usage.append(normalize_usage(read(path / 'usage.json')))
            else:
                usage.append(normalize_usage(None, requests=1))
            require((path / 'error.json').exists(), 'Interrupted request requires explicit archive recovery')
            error = read(path / 'error.json')
            require(error['retryable'], 'Preserved non-retryable failure')
            if error['kind'] == 'output_validation':
                context['feedback_from'] = str(path)
        for number in range(len(existing) + 1, self.shared['max_attempts'] + 1):
            path = directory / f'attempt_{number:03d}'
            messages = feedback.request_messages(body['messages'], context)
            if context['feedback_from'] is not None:
                # Preserve the native text/tool output contract; V25's own
                # modules all return JSON, whereas Momentum uses tool calls.
                messages[-1]['content'] = messages[-1]['content'].replace(
                    'complete JSON object', 'complete output (native tool calls when required)')
            protocol.check_capacity(messages, self.shared)
            current = {**body, 'messages': messages}
            write(path / 'messages.json', messages)
            raw = None
            print(json.dumps({'event': 'model_request', 'stage': request.stage, 'attempt': number}), flush=True)
            try:
                try:
                    raw = self.sender(current, path)
                except Exception as exc:
                    failure = request_failure(exc, path)
                    if failure is None:
                        raise
                    raise failure from exc
                write(path / 'raw_response.json', raw)
                try:
                    choice = raw['choices'][0]
                    finish = choice['finish_reason']
                    message = choice['message']
                    require(isinstance(message, dict), 'Malformed message')
                except (KeyError, IndexError, TypeError, ValueError) as exc:
                    raise RequestFailure('Malformed API response envelope') from exc
                # Tool-call completion is SkillAdam Momentum's native output form.
                if finish != 'stop' and not (finish == 'tool_calls' and request.stage == 'momentum_update'):
                    raise RequestFailure('Model response did not finish normally', truncated=finish == 'length')
                previous = message.get('content') or ''
                if message.get('tool_calls'):
                    previous = json.dumps(message, ensure_ascii=False)
                write(path / 'response.json', {'content': previous, 'finish_reason': 'stop',
                                              'provider_finish_reason': finish})
                try:
                    result = _generation_result(raw)
                    self.validate_output(request, result)
                except (ValueError, BackendProtocolError) as exc:
                    raise feedback.OutputValidationError(request.stage, str(exc)) from exc
                usage.append(normalize_usage(raw.get('usage'), requests=1))
                write(path / 'usage.json', asdict(usage[-1]))
                write(cached, {'signature': signature, 'response': raw, 'usage': [asdict(u) for u in usage]})
                return replace(result, usage=tuple(usage))
            except Exception as exc:
                usage.append(normalize_usage(raw.get('usage') if isinstance(raw, dict) else None, requests=1))
                write(path / 'usage.json', asdict(usage[-1]))
                validation = isinstance(exc, feedback.OutputValidationError)
                retryable = validation or isinstance(exc, RequestFailure) and exc.retryable
                error = {'kind': 'output_validation' if validation else 'technical', 'retryable': retryable,
                         'error_type': type(exc).__name__, 'error': str(exc)[:600] if isinstance(exc, ValueError) else type(exc).__name__}
                if validation:
                    error['diagnostic'] = exc.diagnostic
                    context['feedback_from'] = str(path)
                write(path / 'error.json', error)
                if not retryable:
                    raise
                if number < self.shared['max_attempts']:
                    time.sleep(self.shared['retry_delay_seconds'] * number)
        raise RuntimeError('Frozen optimizer request budget exhausted; resume does not reset it')

    def public_metadata(self):
        metadata={'backend': 'v25-shared-spreadsheet-environment', 'optimizer': self.cfg['optimizer_transport']}
        if protocol.execution_history(self.shared['actor_profile']):metadata.update(self.actor_protocol)
        return metadata


class AlignedRunner(SkillAdamRunner):
    def _propose_patch(self, context):
        self.backend.iteration, self.backend.patch_context = context.iteration, context
        return super()._propose_patch(context)

    def _generate_momentum(self, context):
        self.backend.iteration, self.backend.momentum = context.record.iteration, self.momentum
        return super()._generate_momentum(context)

    def _condense(self, case, evaluated, *, allow_llm=False):
        boundary = ('Execution protocol: the Actor receives only execution/format-error feedback, never gold answers, '
                    'cell mismatches, or scores. Harness execution records and actual_feedback_to_actor are distinct. '
                    'Outcome metrics are computed only after submission and were not visible to the Actor. '
                    'Assistant content below is the visible response, not hidden reasoning.\n\n')
        if protocol.execution_history(self.backend.shared['actor_profile']):
            boundary+=('Evidence view: execution_only_v1. Only actual program executions are shown. '
                       'Generation failures and temporary format-repair exchanges are excluded. '
                       'A repaired response may have been influenced by temporary validation feedback; '
                       'this trace is formal execution history, not every actual API request. '
                       'Evidence ID gaps are not program failures or execution counts.\n\n')
        case = replace(case, payload={'task': boundary + self.backend.queries[case.case_id]})
        return super()._condense(case, evaluated, allow_llm=allow_llm)


def check(experiment=None):
    experiment=Path(experiment) if experiment is not None else EXPERIMENT
    manifest = read(experiment / 'manifest.json')
    require(sys.version == manifest['python_version'], 'Host Python version changed')
    require(Path(sys.executable) == Path(manifest['python_executable']), 'Host Python environment changed')
    for path, expected in manifest['files'].items():
        require(sha(ROOT / path) == expected, f'Frozen input changed: {path}')
    for name, version in manifest['packages'].items():
        require(importlib.metadata.version(name) == version, f'Runtime package changed: {name}')
    shared, cfg = read(experiment / 'shared_config.json'), read(experiment / 'skilladam.json')
    actor_protocol=validate_actor_protocol(shared,cfg)
    if protocol.execution_history(shared['actor_profile']):
        for name in ('shared_config.json','skilladam.json'):
            relative=os.path.relpath(experiment/name,ROOT)
            require(manifest['files'].get(relative)==sha(experiment/name), f'Actor protocol config is not frozen: {name}')
    prepared='reference_preparation' in cfg
    reference = ROOT / cfg['reference_preparation' if prepared else 'reference_campaign']
    require(shared == read(reference / ('campaign.json' if prepared else 'config.json')), 'Shared environment differs from V25')
    require((experiment / 'initial_skill.md').read_text() == shared['initial_skill']['text'], 'Initial Skill differs')
    require(not cfg['stage0_enabled'] and not cfg['automatic_test'], 'Unexpected Stage0 or Test')
    frozen = read(reference / 'contract.json')
    for relative, content in frozen.items():
        require((ROOT / relative).read_text() == content, f'V25 source differs from its campaign: {relative}')
    require(executor.runtime_snapshot(shared) == read(reference / 'runtime.json'), 'Docker runtime differs')
    image_id = subprocess.check_output(['docker', 'image', 'inspect', shared['executor']['image'], '--format', '{{.Id}}'], text=True).strip()
    require(image_id == manifest['docker_image_id'], 'Docker image changed')
    if 'comparison_profile' in manifest:
        from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.prepared.actor_runtime.baseline import COMPARISON_PROFILE, validate_latest_configuration
        from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.prepared.actor_runtime.benchmark import using_benchmark
        require(manifest['comparison_profile']==cfg.get('comparison_profile')==COMPARISON_PROFILE,'Frozen comparison profile differs')
        validate_latest_configuration(shared)
        with using_benchmark(SharedAdapter()):require(frozen==ev.frozen_contract(),'Incomplete or changed V25 source freeze')
    runner = AlignedRunner(config=native_config(cfg), adapter=AlignedAdapter(experiment), backend=None,
                           context=context_for(shared, cfg), output_dir=experiment / 'campaign')
    cases = runner._validate_cases(cases_for(shared, cfg))
    batches = list(runner._build_sampler(cases))
    require([list(b.training_case_ids) for b in batches] == shared['batches'], 'Batch sequence differs')
    require(all(b.training_case_ids == b.validation_case_ids for b in batches), 'Expected same-batch Gate')
    require(not set(cfg['native']['optimization_case_ids']) & set(shared['test_tasks']), 'Test leakage')
    return {'status': 'passed', **actor_protocol, 'model_requests': 0, 'optimization_tasks': len(cases),
            'batch_sizes': [len(b.training_case_ids) for b in batches], 'test_tasks_excluded': len(shared['test_tasks']),
            'actor_workers': shared['actor_max_workers'], 'actor_max_tokens': shared['actor_profile']['actor_max_output_tokens'],
            'actor_task_timeout_seconds': shared['actor_profile']['actor_task_timeout_seconds'],
            'actor_attempt_budget_policy': shared['actor_profile'].get('attempt_budget_policy', 'responses_v1'),
            'optimizer_max_tokens': cfg['optimizer_transport']['max_tokens'], 'max_request_attempts': shared['max_attempts'],
            'initial_skill_sha256': sha(experiment / 'initial_skill.md'), 'stage0_enabled': False,
            'docker_image_id': image_id, 'checked_at': datetime.now(timezone.utc).isoformat()}


def main(argv=None):
    global EXPERIMENT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true')
    group.add_argument('--start', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    EXPERIMENT = args.experiment.resolve()
    report = check()
    if not args.start:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    import fcntl
    with (EXPERIMENT / 'campaign.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        shared, cfg = read(EXPERIMENT / 'shared_config.json'), read(EXPERIMENT / 'skilladam.json')
        require(datetime.now(timezone.utc) >= datetime.fromisoformat(cfg['not_before']), 'Scheduled start time has not arrived')
        output = EXPERIMENT / 'campaign'
        if args.resume:
            require((output / 'checkpoint.json').exists(), 'No native checkpoint; explicit recovery required')
        else:
            require(not output.exists(), 'Campaign exists; refusing duplicate training')
        ev.check_live_environment(shared)
        backend = SharedBackend(shared, cfg, output, resume=args.resume)
        runner = AlignedRunner(config=native_config(cfg), adapter=AlignedAdapter(EXPERIMENT), backend=backend,
                               context=context_for(shared, cfg), output_dir=output)
        result = runner.run(cases=cases_for(shared, cfg), initial_skill=(EXPERIMENT / 'initial_skill.md').read_text(),
                            resume=args.resume)
        write(output / 'completion.json', {'status': 'complete', 'automatic_test': False,
                                          'iterations': [r.to_dict() for r in result.feedback_loop.iterations],
                                          'finished_at': datetime.now(timezone.utc).isoformat()})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
