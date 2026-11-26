#!/usr/bin/env python3
"""Prepare an isolated historical Actor plus the upstream SkillAdam optimizer.

Default/check/prepare never construct a live client or run dataset tasks.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.skilladam.spreadsheetbench.layout import SHARED_CONFIG, NATIVE_CONFIG, PUBLISHED, UPSTREAM, read_actor_config
SOURCE = ROOT / 'artifacts/methods/skilladam/spreadsheetbench/shared_actor/v25_skilladam_execution_only_actor48k_20261027_001_skilladam'
POLICY = 'upstream_sdk2_patch3_v1'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def desired_config(source, python):
    cfg = deepcopy(source)
    cfg['optimizer_retry_policy'] = POLICY
    cfg['optimizer_transport'].pop('request_attempts_total')
    cfg['optimizer_transport']['sdk_max_retries'] = 2
    cfg['native']['feedback_loop']['patch_attempts'] = 3
    cfg['native']['feedback_loop']['max_iterations'] = 15
    cfg['native']['feedback_loop']['min_iterations'] = 15
    cfg['python'] = python
    return cfg


def load_bridge(experiment):
    from src.skill_evolution.skilladam.spreadsheetbench.native_retry.bridge import run_skilladam_spreadsheetbench_aligned as bridge
    return bridge


def validate(bridge, shared, cfg):
    bridge.SharedAdapter().validate_config(shared)
    require(cfg['optimizer_retry_policy'] == POLICY, 'Unexpected optimizer retry policy')
    require(cfg['optimizer_transport']['sdk_max_retries'] == 2, 'Native SDK retry budget changed')
    require('request_attempts_total' not in cfg['optimizer_transport'], 'Outer optimizer retry budget is forbidden')
    require(cfg['native']['feedback_loop']['patch_attempts'] == 3, 'Native patch budget changed')
    require(cfg['actor_evidence_view'] == shared['actor_profile']['actor_history_policy'] == 'execution_only_v1',
            'Actor evidence protocol changed')
    require(not cfg['automatic_test'] and not cfg['stage0_enabled'] and cfg['momentum'], 'Native method conditions changed')
    return {'actor_history_policy': 'execution_only_v1', 'actor_evidence_view': 'execution_only_v1'}


def native_transport(bridge, shared, cfg, output, *, api_key, http_transport=None):
    """Use upstream generation/parsing and SDK retries; audit without repairing outputs."""
    import httpx
    from openai import OpenAI
    from skilladam.backends.openai_compatible import OpenAICompatibleConfig, create_generation_transport
    from skilladam.execution.contracts import BackendInit
    transport = cfg['optimizer_transport']
    settings = OpenAICompatibleConfig(max_retries=transport['sdk_max_retries'],
        timeout_seconds=transport['timeout_seconds'], max_completion_tokens=transport['max_tokens'],
        token_limit_field='max_tokens', temperature=transport['temperature'], reasoning_mode='top_level')

    def factory(**options):
        active = {}

        def sent(request):
            directory = active['directory']
            number = len(list(directory.glob('http_request_*.json'))) + 1
            # No authentication headers are archived. Count actual SDK attempts.
            write(directory / f'http_request_{number:02d}.json',
                  {'url': str(request.url), 'body': json.loads(request.content)})

        options['http_client'] = httpx.Client(
            trust_env='.intra.' not in shared['actor_base_url'],
            event_hooks={'request': [sent]}, transport=http_transport)
        options['timeout'] = httpx.Timeout(transport['timeout_seconds'], connect=10)
        client = OpenAI(**options)
        original = client.chat.completions.create

        def create(**payload):
            # Preserve the old input ceiling independently of retry/repair policy.
            bridge.protocol.check_capacity(payload['messages'], shared)
            directory = Path(output) / 'model_calls' / uuid.uuid4().hex
            active['directory'] = directory
            payload['extra_body'] = {**payload.get('extra_body', {}), 'thinking': shared['call_config']['thinking']}
            payload['stream'] = False
            write(directory / 'request.json', payload)
            try:
                response = original(**payload)
                write(directory / 'response.json', response.model_dump(mode='json'))
                return response
            except Exception as exc:
                write(directory / 'error.json', {'error_type': type(exc).__name__})
                raise

        client.chat.completions.create = create
        return client

    return create_generation_transport(
        BackendInit(Path(output), Path(output), {}, bridge.context_for(shared, cfg)),
        config=settings, environ={settings.api_key_env: api_key, settings.base_url_env: shared['actor_base_url']},
        client_factory=factory)


def backend_type(bridge):
    class NativeBackend(bridge.SharedBackend):
        def __init__(self, shared, cfg, output, *, optimizer=None):
            # Keep the shared Actor hooks, without the old constructor's patch=1 contract.
            self.actor_protocol = validate(bridge, shared, cfg)
            self.shared, self.cfg, self.output = shared, cfg, Path(output)
            self.iteration, self.rollout_counts = 0, defaultdict(int)
            self.patch_context, self.momentum, self.queries = None, None, {}
            self.optimizer = optimizer

        def generate(self, request):
            if self.optimizer is None:
                self.optimizer = native_transport(bridge, self.shared, self.cfg, self.output,
                                                  api_key=os.environ['OPENAI_API_KEY'])
            # No finish-reason gate, output validation feedback, cache or outer retry.
            return self.optimizer.generate(request)

        def public_metadata(self):
            return {**super().public_metadata(), 'optimizer_retry_policy': POLICY,
                    'http_attempt_audit': 'model_calls/*/http_request_*.json'}

    return NativeBackend


def prepare(experiment, source=SHARED_CONFIG):
    from tempfile import TemporaryDirectory
    experiment = Path(experiment).resolve()
    require(not experiment.exists(), 'Preparation requires a new experiment directory')
    source = Path(source)
    require(read(source / 'shared_config.json') == read(SHARED_CONFIG / 'shared_config.json'),
            'Native retry requires the execution-only Actor configuration')
    native = desired_config(read(source / 'skilladam.json'), sys.executable)
    expected = dict(read(NATIVE_CONFIG / 'skilladam.json'), python=sys.executable)
    require(native == expected, 'Unexpected optimizer configuration')
    experiment.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=experiment.parent) as temp:
        staged = Path(temp) / 'experiment'
        staged.mkdir()
        for name in ('shared_config.json', 'actor_runtime.json', 'initial_skill.md'):
            shutil.copy2(NATIVE_CONFIG / name, staged / name)
        write(staged / 'skilladam.json', native)
        report = check(staged)
        write(staged / 'preflight.json', report)
        staged.rename(experiment)
    return report


def check(experiment):
    experiment = Path(experiment).resolve()
    shared, cfg = read(experiment / 'shared_config.json'), read(experiment / 'skilladam.json')
    expected = read(NATIVE_CONFIG / 'skilladam.json')
    require(cfg == dict(expected, python=cfg['python']), 'Unexpected native optimizer configuration')
    require(shared == read(SHARED_CONFIG / 'shared_config.json') and
            (experiment / 'initial_skill.md').read_text() == shared['initial_skill']['text'], 'Actor inputs differ')
    bridge = load_bridge(experiment)
    validate(bridge, shared, cfg)
    require(bridge.executor.runtime_snapshot(shared) == read(experiment / 'actor_runtime.json') == read(NATIVE_CONFIG / 'actor_runtime.json'), 'Actor Docker runtime changed')
    runner = bridge.AlignedRunner(config=bridge.native_config(cfg), adapter=bridge.AlignedAdapter(experiment),
        backend=None, context=bridge.context_for(shared, cfg), output_dir=experiment / 'campaign')
    cases = runner._validate_cases(bridge.cases_for(shared, cfg))
    batches = list(runner._build_sampler(cases))
    require([list(b.training_case_ids) for b in batches] == shared['batches'], 'Task order changed')
    require(all(b.training_case_ids == b.validation_case_ids for b in batches), 'Gate batch changed')
    require(not set(cfg['native']['optimization_case_ids']) & set(shared['test_tasks']), 'Test leakage')
    return {'status': 'passed', 'optimizer_retry_policy': POLICY, 'sdk_max_retries': 2, 'patch_attempts': 3,
            'batch_sizes': [len(b.training_case_ids) for b in batches], 'model_requests': 0,
            'dataset_tasks_executed': 0, 'campaign_present': (experiment / 'campaign').exists(),
            'shared_config_sha256': sha(experiment / 'shared_config.json'), 'actor_max_tokens': shared['actor_profile']['actor_max_output_tokens']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', type=Path, required=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--prepare', action='store_true')
    actions.add_argument('--check', action='store_true')
    actions.add_argument('--start', action='store_true')
    args = parser.parse_args(argv)
    experiment = args.experiment.resolve()
    if not args.prepare and (experiment / 'config/skilladam.json').is_file():
        experiment = experiment / 'config'
    if args.start and experiment.is_relative_to(PUBLISHED):
        parser.error('Use --prepare with a new working directory before training')
    report = prepare(experiment) if args.prepare else check(experiment)
    if args.start:
        import fcntl
        with (experiment / 'campaign.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            output = experiment / 'campaign'
            require(not output.exists(), 'Campaign exists; explicit recovery review required')
            bridge = load_bridge(experiment)
            shared, cfg = read(experiment / 'shared_config.json'), read(experiment / 'skilladam.json')
            # Actor subprocesses must import the same historical sources.
            os.environ['PYTHONPATH'] = os.pathsep.join((str(ROOT), str(UPSTREAM)))
            os.chdir(ROOT)
            require(cfg['python'] == sys.executable, 'Use the Python environment recorded during preparation')
            shared = read_actor_config(experiment / 'shared_config.json')
            bridge.ev.check_live_environment(shared)
            backend = backend_type(bridge)(shared, cfg, output)
            runner = bridge.AlignedRunner(config=bridge.native_config(cfg), adapter=bridge.AlignedAdapter(experiment),
                backend=backend, context=bridge.context_for(shared, cfg), output_dir=output)
            result = runner.run(cases=bridge.cases_for(shared, cfg), initial_skill=(experiment / 'initial_skill.md').read_text())
            write(output / 'completion.json', {'status': 'complete', 'automatic_test': False,
                                               'iterations': [r.to_dict() for r in result.feedback_loop.iterations]})
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
