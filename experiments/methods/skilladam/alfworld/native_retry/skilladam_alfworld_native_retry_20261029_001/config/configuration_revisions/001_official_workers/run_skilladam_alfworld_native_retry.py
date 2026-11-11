#!/usr/bin/env python3
"""ALFWorld: unchanged shared Actor/native method, upstream optimizer retries.

Prepare/check are offline. Training requires --start; Test is never automatic.
"""
import argparse
from copy import deepcopy
from dataclasses import asdict, replace
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'experiments/baselines/skilladam_current_actor_20261025'
POLICY = 'upstream_sdk2_native_patch3_v1'
sys.path[:0] = [str(ROOT / 'scripts/runs'), str(ROOT / 'external/SkillAdam'), str(ROOT)]
from alfworld_aligned_common import read, write, sha, require


def bridge_module():
    path = ROOT / 'scripts/runs/run_skilladam_aligned.py'
    spec = importlib.util.spec_from_file_location('alfworld_original_bridge', path)
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    return bridge


def desired_config(source, experiment):
    cfg = deepcopy(source)
    cfg['optimizer_retry_policy'] = POLICY
    cfg['optimizer_transport'].pop('request_attempts')
    cfg['optimizer_transport']['sdk_max_retries'] = 2
    cfg['output_root'] = os.path.relpath(Path(experiment).resolve() / 'campaign', ROOT)
    return cfg


def context_for(bridge, actor, cfg):
    return bridge.BackendContext('alfworld', 'skilladam', actor['model'],
        cfg['optimizer_transport']['reasoning_effort'], actor['workers'], cfg['native']['seed'])


def transport_settings(cfg):
    from skilladam.backends.openai_compatible import OpenAICompatibleConfig
    t = cfg['optimizer_transport']
    require(t['sdk_max_retries'] == 2 and 'request_attempts' not in t, 'Native SDK retry policy changed')
    return OpenAICompatibleConfig(max_retries=2, timeout_seconds=t['timeout_seconds'],
        max_completion_tokens=t['max_tokens'], token_limit_field='max_tokens',
        temperature=t['temperature'], reasoning_mode='top_level')


def native_transport(bridge, actor, cfg, output, active_directory, *, api_key, http_transport=None):
    """Wrap only provider parameters/auditing; upstream SDK and parser own errors."""
    import httpx
    from openai import OpenAI, DefaultHttpxClient
    from skilladam.backends.openai_compatible import create_generation_transport
    from skilladam.execution.contracts import BackendInit
    settings = transport_settings(cfg)
    t = cfg['optimizer_transport']

    def factory(**options):
        def sent(request):
            directory = active_directory()
            number = len(list(directory.glob('http_request_*.json'))) + 1
            write(directory / f'http_request_{number:02d}.json',
                  {'url': str(request.url), 'body': json.loads(request.content)})

        def received(response):
            directory = active_directory()
            number = len(list(directory.glob('http_request_*.json')))
            write(directory / f'http_response_{number:02d}.json', {'status_code': response.status_code})

        options['timeout'] = httpx.Timeout(t['timeout_seconds'], connect=t['connect_timeout_seconds'])
        options['http_client'] = DefaultHttpxClient(event_hooks={'request': [sent], 'response': [received]},
                                                   transport=http_transport)
        client = OpenAI(**options)
        original = client.chat.completions.create

        def create(**payload):
            payload['extra_body'] = {**payload.get('extra_body', {}), 'thinking': t['thinking']}
            payload['stream'] = False
            response = original(**payload)
            write(active_directory() / 'response.json', response.model_dump(mode='json'))
            return response

        client.chat.completions.create = create
        return client

    return create_generation_transport(
        BackendInit(Path(output), Path(output), {}, context_for(bridge, actor, cfg)),
        config=settings, environ={settings.api_key_env: api_key, settings.base_url_env: actor['base_url']},
        client_factory=factory)


def backend_type(bridge):
    class NativeBackend(bridge.SharedBackend):
        def __init__(self, actor, cfg, output, *, api_key=None, http_transport=None):
            super().__init__(actor, cfg, output)
            self.optimizer = None
            self.api_key, self.http_transport, self.active_directory = api_key, http_transport, None

        def generate(self, request):
            from skilladam.backends.openai_compatible import _generation_payload, _generation_result
            payload = _generation_payload(request, transport_settings(self.cfg))
            payload.update(extra_body={'thinking': self.cfg['optimizer_transport']['thinking']}, stream=False)
            signature = {'iteration': self.iteration, 'stage': request.stage, 'payload': payload}
            directory = self.output / 'model_calls' / f'{request.stage}_{bridge.digest(signature)}'
            cached = directory / 'success.json'
            if cached.exists():
                saved = read(cached)
                require(saved['signature'] == signature, 'Cached generation signature differs')
                result = _generation_result(saved['response'])
                return replace(result, usage=tuple(bridge.normalize_usage(u) for u in saved['usage']))
            # Retain the old no-silent-reset recovery boundary and successful cache.
            require(not (directory / 'request_started.json').exists(),
                    'Incomplete optimizer call requires explicit recovery; no silent retry reset')
            write(directory / 'request.json', signature)
            self.active_directory = directory
            if self.optimizer is None:
                self.optimizer = native_transport(bridge, self.actor, self.cfg, self.output,
                    lambda: self.active_directory, api_key=self.api_key or os.environ['OPENAI_API_KEY'],
                    http_transport=self.http_transport)
            write(directory / 'request_started.json', {'policy': POLICY})
            self.new_generations += 1
            try:
                result = self.optimizer.generate(request)
                write(cached, {'signature': signature, 'response': read(directory / 'response.json'),
                               'usage': [asdict(u) for u in result.usage]})
                return result
            except Exception as exc:
                write(directory / 'error.json', {'error_type': type(exc).__name__})
                raise

        def public_metadata(self):
            return {**super().public_metadata(), 'optimizer_retry_policy': POLICY,
                    'http_attempt_audit': 'model_calls/*/http_request_*.json'}

    return NativeBackend


def check(experiment):
    experiment = Path(experiment).resolve()
    manifest = read(experiment / 'manifest.json')
    require(sys.executable == manifest['python_executable'] and sys.version == manifest['python_version'],
            'Optimizer Python runtime changed')
    for p, expected in manifest['files'].items():
        require(sha(p) == expected, f'Frozen file changed: {p}')
    for name, version in manifest['packages'].items():
        require(importlib.metadata.version(name) == version, f'Optimizer package changed: {name}')
    bridge = bridge_module()
    original_report = bridge.check()  # Original source/environment/commit/split checks, no model/env run.
    cfg, actor = read(experiment / 'skilladam.json'), read(experiment / 'actor.json')
    require(cfg == desired_config(read(SOURCE / 'skilladam.json'), experiment), 'Unexpected configuration change')
    transport_settings(cfg)
    for name in ('actor.json', 'initial_skill.md', 'optimization_items.json',
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
        backend=None, context=context, output_dir=ROOT / cfg['output_root'])
    cases = runner._validate_cases(bridge.cases_for(cfg))
    batches = list(runner._build_sampler(cases))
    require([list(b.training_case_ids) for b in batches] == read(ROOT / actor['reference_campaign'])['batches'],
            'Batch order changed')
    require(all(b.training_case_ids == b.validation_case_ids for b in batches), 'Gate batch changed')
    return {**original_report, 'optimizer_retry_policy': POLICY, 'sdk_max_retries': 2, 'patch_attempts': 3,
            'native_method_settings_unchanged': True, 'actor_config_byte_identical': True,
            'campaign_present': (ROOT / cfg['output_root']).exists(), 'dataset_tasks_executed': 0}


def prepare(experiment):
    experiment = Path(experiment).resolve()
    require(not experiment.exists(), 'Preparation requires a new directory')
    original = read(SOURCE / 'skilladam.json')
    require(sys.executable == original['python'], 'Use the original SkillAdam Python environment')
    bridge = bridge_module()
    bridge.check()
    # Save a verifiable record of all historical results before making the new config.
    old_output = ROOT / original['output_root']
    preserved = {str(p): sha(p) for p in old_output.rglob('*') if p.is_file()}
    for name in ('actor.json', 'initial_skill.md', 'optimization_items.json',
                 'splits/train/items.json', 'splits/val/items.json', 'splits/test/items.json'):
        dest = experiment / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / name, dest)
    cfg = desired_config(original, experiment)
    require(not (ROOT / cfg['output_root']).exists(), 'New output already exists')
    write(experiment / 'skilladam.json', cfg)
    write(experiment / 'source_config.json', original)
    write(experiment / 'preserved_results.json', preserved)
    actor = read(experiment / 'actor.json')
    runtime = json.loads(subprocess.check_output([actor['python'], '-c',
        'import sys,json,importlib.metadata as m;print(json.dumps({"python":sys.version,"packages":'
        '{d.metadata["Name"]:d.version for d in m.distributions()}}))'], text=True))
    write(experiment / 'actor_runtime.json', runtime)
    packages = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}
    (experiment / 'requirements.lock').write_text(''.join(f'{k}=={v}\n' for k, v in sorted(packages.items())))
    write(experiment / 'alignment.json', {'source_experiment': str(SOURCE), 'source_results': str(old_output),
        'optimizer_retry_policy': POLICY, 'native_method_settings_unchanged': cfg['native'] == original['native'],
        'sdk_max_retries': {'before': 0, 'after': 2}, 'custom_request_attempts': {'before': 3, 'after': None},
        'patch_attempts': {'before': 3, 'after': 3}, 'historical_manual_recovery_not_inherited': True,
        'model_requests': 0, 'dataset_tasks_executed': 0})
    files = {str(ROOT / p): h for p, h in read(SOURCE / 'manifest.json')['files'].items()}
    files[str(SOURCE / 'manifest.json')] = sha(SOURCE / 'manifest.json')
    files[str(Path(__file__).resolve())] = sha(__file__)
    files.update({str(p): sha(p) for p in experiment.rglob('*') if p.is_file()})
    write(experiment / 'manifest.json', {'files': files, 'packages': packages,
        'python_executable': sys.executable, 'python_version': sys.version})
    report = check(experiment)
    write(experiment / 'preflight.json', report)
    return report


def start(experiment, *, resume=False):
    import fcntl
    experiment = Path(experiment).resolve()
    bridge = bridge_module()
    bridge.EXPERIMENT = experiment
    actor, cfg = read(experiment / 'actor.json'), read(experiment / 'skilladam.json')
    output = ROOT / cfg['output_root']
    with output.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt = output.with_suffix('.launch.json')
        signature = {'manifest_sha256': sha(experiment / 'manifest.json'), 'config': cfg}
        if resume:
            require(read(receipt) == signature and (output / 'checkpoint.json').is_file(), 'Resume configuration/checkpoint differs')
        else:
            require(not output.exists() and not receipt.exists(), 'Output exists; use explicit resume')
            write(receipt, signature)
        bridge.configure_runtime(actor)
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
