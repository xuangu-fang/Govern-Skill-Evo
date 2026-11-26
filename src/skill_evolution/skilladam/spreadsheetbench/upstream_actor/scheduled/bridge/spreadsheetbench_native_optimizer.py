"""Frozen native optimizer functions, with independent provider routing. No CLI."""
from collections import defaultdict
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid
POLICY = 'upstream_sdk2_patch3_v1'

def read(path):
    return json.loads(Path(path).read_text())

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def require(condition, message):
    if not condition:
        raise ValueError(message)

def load_bridge(experiment):
    from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.scheduled.bridge import run_skilladam_spreadsheetbench_aligned as bridge
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
            trust_env='.intra.' not in transport.get('base_url', shared['actor_base_url']),
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
        config=settings, environ={settings.api_key_env: api_key, settings.base_url_env: transport.get('base_url', shared['actor_base_url'])},
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
