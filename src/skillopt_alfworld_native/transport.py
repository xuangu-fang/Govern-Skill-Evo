"""Provider parameters and audit only; all retry loops remain upstream-owned."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import json
from pathlib import Path
from uuid import uuid4

from .project import read, write, require


@contextmanager
def provider(root, *, api_key, http_transport=None):
    import httpx
    from openai import OpenAI, DefaultHttpxClient
    from skillopt.model import openai_compatible_backend as backend
    root = Path(root)
    settings = read(root / 'optimizer.json')
    backend.configure_openai_compatible(base_url=settings['base_url'], api_key=api_key,
        model=settings['model'], temperature=settings['temperature'],
        timeout_seconds=settings['timeout_seconds'], max_tokens=settings['max_tokens'])
    native_client, native_call = backend.OpenAI, backend._chat_messages_impl
    context = ContextVar('skillopt_optimizer_audit')
    clients = []

    def factory(**options):
        # No max_retries argument: preserve the installed SDK default.
        require('max_retries' not in options, 'Unexpected SDK retry override')

        def sent(request):
            call = context.get()
            call['http_attempts'] += 1
            write(call['directory'] / f'http_{call["http_attempts"]:03d}_request.json',
                  {'url': str(request.url), 'body': json.loads(request.content)})

        def received(response):
            call = context.get()
            response.read()
            directory = call['directory']
            stem = f'http_{call["http_attempts"]:03d}'
            (directory / f'{stem}_response_body.bin').write_bytes(response.content)
            try:
                usage = response.json().get('usage')
            except (ValueError, AttributeError):
                usage = None
            write(directory / f'{stem}_response.json', {'status': response.status_code, 'usage': usage})

        options['http_client'] = DefaultHttpxClient(transport=http_transport,
            event_hooks={'request': [sent], 'response': [received]})
        client = OpenAI(**options)
        original = client.chat.completions.create

        def create(**payload):
            payload['extra_body'] = {**payload.get('extra_body', {}),
                'thinking': settings['thinking'], 'reasoning_effort': settings['reasoning_effort']}
            payload['stream'] = settings['stream']
            return original(**payload)

        client.chat.completions.create = create
        clients.append(client)
        return client

    def audited(messages, max_completion_tokens, retries, stage, **kwargs):
        directory = root / 'campaign/model_calls' / uuid4().hex
        write(directory / 'input.json', {'messages': messages, 'max_completion_tokens': max_completion_tokens,
              'retries': retries, 'stage': stage, 'role': kwargs.get('role'),
              'timeout': kwargs.get('timeout')})
        state = {'directory': directory, 'http_attempts': 0}
        token = context.set(state)
        status, error = 'complete', None
        try:
            return native_call(messages, max_completion_tokens, retries, stage, **kwargs)
        except BaseException as exc:
            status, error = 'failed', type(exc).__name__
            raise
        finally:
            write(directory / 'status.json', {'status': status, 'error_type': error,
                  'http_attempts': state['http_attempts']})
            context.reset(token)

    backend.OpenAI, backend._chat_messages_impl = factory, audited
    backend._reset_clients()
    try:
        yield
    finally:
        backend.OpenAI, backend._chat_messages_impl = native_client, native_call
        backend._reset_clients()
        for client in clients:
            client.close()


def usage_summary(root):
    root = Path(root)
    result = {'optimizer': {'logical_calls': 0, 'http_requests': 0, 'unknown_usage_requests': 0,
                           'prompt_tokens': 0, 'completion_tokens': 0},
              'actor': {'episodes': 0, 'http_requests': 0, 'unknown_usage_requests': 0,
                        'prompt_tokens': 0, 'completion_tokens': 0}}
    for folder in (root / 'campaign/model_calls').glob('*'):
        if not folder.is_dir():
            continue
        total = result['optimizer']
        total['logical_calls'] += 1
        for request in folder.glob('http_*_request.json'):
            total['http_requests'] += 1
            response = request.with_name(request.name.replace('_request.json', '_response.json'))
            usage = read(response).get('usage') if response.exists() else None
            if not usage:
                total['unknown_usage_requests'] += 1
            else:
                for key in ('prompt_tokens', 'completion_tokens'):
                    total[key] += usage.get(key, 0)
    for path in (root / 'campaign').glob('**/episodes/*/*/trajectory.json'):
        total = result['actor']
        total['episodes'] += 1
        for step in read(path)['steps']:
            for attempt in step.get('transport_attempts', []):
                total['http_requests'] += 1
                usage = attempt.get('usage')
                if not usage:
                    total['unknown_usage_requests'] += 1
                else:
                    for key in ('prompt_tokens', 'completion_tokens'):
                        total[key] += usage.get(key, 0)
    return result
