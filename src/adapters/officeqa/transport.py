"""One direct HTTP request per call; retries belong exclusively to the Actor."""
from copy import copy
from dataclasses import replace
from urllib.parse import urlsplit

import requests
from skilladam.backends import openai_compatible as native
from skilladam.execution.contracts import BackendContext, GenerationRequest

from .execution import CONNECT_TIMEOUT_SECONDS, REQUEST_TIMEOUT_SECONDS, REQUEST_ATTEMPTS, RETRY_POLICY


class RequestFailure(RuntimeError):
    def __init__(self, message, *, retryable=True, evidence=None):
        super().__init__(message)
        self.retryable, self.evidence = retryable, evidence


class ChatTransport:
    """Explicit live credentials OR an offline-only response fixture.

    No OpenAI client or credentials are loaded implicitly. offline_create is a
    test seam, not a provider-client adapter. Production calls use requests
    with HTTP retries and redirects disabled.
    """
    def __init__(self, *, model, max_completion_tokens, endpoint=None, api_key=None,
                 offline_create=None, reasoning_effort='none', temperature=1.0,
                 reasoning_mode='omit', token_limit_field='max_completion_tokens'):
        if type(max_completion_tokens) is not int or max_completion_tokens <= 0:
            raise ValueError('Explicit positive per-method max_completion_tokens required')
        if offline_create is not None:
            if not callable(offline_create) or endpoint is not None or api_key is not None:
                raise ValueError('Offline fixture and live credentials are mutually exclusive')
        else:
            parsed = urlsplit(endpoint or '')
            if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
                    or parsed.password or parsed.query or parsed.fragment or not api_key):
                raise ValueError('Explicit HTTP endpoint and API key required')
        self.endpoint, self.api_key, self.offline_create = endpoint, api_key, offline_create
        if reasoning_mode == 'explicit_none' and reasoning_effort != 'none':
            raise ValueError('explicit_none requires reasoning_effort=none')
        if reasoning_mode == 'deepseek_thinking' and reasoning_effort not in ('low', 'medium', 'high', 'max'):
            raise ValueError('deepseek_thinking requires an explicit thinking effort')
        self.reasoning_mode = reasoning_mode
        self.context = BackendContext('officeqa', 'baseline', model, reasoning_effort, 1, 42)
        self.config = native.OpenAICompatibleConfig.from_mapping({
            'max_completion_tokens': max_completion_tokens, 'temperature': temperature,
            'reasoning_mode': ('omit' if reasoning_mode == 'explicit_none' else
                               'top_level' if reasoning_mode == 'deepseek_thinking' else reasoning_mode),
            'token_limit_field': token_limit_field,
            'timeout_seconds': REQUEST_TIMEOUT_SECONDS,
        })

    def __call__(self, *, messages, tools):
        request = GenerationRequest('rollout', tuple(messages), self.context, {'tools': tools})
        body = native._generation_payload(request, self.config)
        # extra_body is an SDK option; direct HTTP needs its fields at top level.
        body.update(body.pop('extra_body', {}))
        if self.reasoning_mode == 'explicit_none':
            body['reasoning_effort'] = 'none'
        if self.reasoning_mode == 'deepseek_thinking':
            body['thinking'] = {'type': 'enabled'}
        try:
            if self.offline_create is not None:
                return self.offline_create(**body, timeout=REQUEST_TIMEOUT_SECONDS)
            with requests.Session() as session:
                for prefix in ('http://', 'https://'):
                    session.mount(prefix, requests.adapters.HTTPAdapter(max_retries=0))
                raw = session.post(self.endpoint, json=body,
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    timeout=(CONNECT_TIMEOUT_SECONDS, REQUEST_TIMEOUT_SECONDS), allow_redirects=False)
        except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError,
                TimeoutError, ConnectionError) as exc:
            raise RequestFailure(type(exc).__name__) from None
        if not 200 <= raw.status_code < 300:
            try:
                error = raw.json().get('error', {})
                quota = isinstance(error, dict) and any(error.get(k) in
                    ('insufficient_quota', 'quota_exceeded', 'billing_hard_limit_reached') for k in ('code', 'type'))
            except (ValueError, AttributeError):
                quota = False
            raise RequestFailure(f'HTTP {raw.status_code}',
                retryable=raw.status_code in (408, 409, 429, 500, 502, 503, 504) and not quota,
                evidence={'http_status': raw.status_code, 'body': raw.text})
        try:
            return raw.json()
        except ValueError:
            raise RequestFailure('Malformed API JSON', evidence={'http_status': raw.status_code, 'body': raw.text}) from None

    def with_output_limit(self, limit):
        if type(limit) is not int or limit <= 0:
            raise ValueError('Task output limit must be a positive integer')
        transport = copy(self)
        transport.config = replace(self.config, max_completion_tokens=limit)
        return transport

    def metadata(self):
        return {'model': self.context.model, 'max_completion_tokens': self.config.max_completion_tokens,
                'temperature': self.config.temperature, 'reasoning_effort': self.context.reasoning_effort,
                'reasoning_mode': self.reasoning_mode, 'token_limit_field': self.config.token_limit_field,
                'request_timeout_seconds': REQUEST_TIMEOUT_SECONDS, 'connect_timeout_seconds': CONNECT_TIMEOUT_SECONDS,
                'retry_policy': RETRY_POLICY, 'request_attempts_total': REQUEST_ATTEMPTS,
                'transport': 'offline_fixture' if self.offline_create is not None else 'direct_http',
                'endpoint': self.endpoint}
