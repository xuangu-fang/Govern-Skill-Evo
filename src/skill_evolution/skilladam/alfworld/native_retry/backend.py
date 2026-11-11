"""Native SkillAdam retry transport and ALFWorld backend used by the three profiles."""
from dataclasses import asdict, replace
import json
import os
from pathlib import Path

from scripts.runs.alfworld.alfworld_aligned_common import read, write, require

POLICY = 'upstream_sdk2_native_patch3_v1'


def context_for(bridge, actor, cfg):
    transport = cfg['optimizer_transport']
    model = transport['model'] if 'base_url' in transport else actor['model']
    return bridge.BackendContext('alfworld', 'skilladam', model,
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
        config=settings, environ={settings.api_key_env: api_key, settings.base_url_env: t.get('base_url', actor['base_url'])},
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
                    lambda: self.active_directory, api_key=self.api_key or os.environ[self.cfg['optimizer_transport'].get('api_key_env', 'OPENAI_API_KEY')],
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
