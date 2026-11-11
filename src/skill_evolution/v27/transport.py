"""Explicit method HTTP transport: one request, no implicit credentials or retries."""
import math
from urllib.parse import urlsplit
import requests

from .facts import require
from .storage import write_record


class RequestFailure(RuntimeError):
    def __init__(self, detail, *, retryable=True):
        super().__init__(detail)
        self.retryable = retryable


def validate_call(config):
    required = {'endpoint', 'model', 'max_tokens', 'timeout_seconds', 'temperature'}
    optional = {'reasoning_effort', 'thinking', 'token_limit_field', 'context_window_tokens'}
    require(isinstance(config, dict) and required <= set(config) <= required | optional, 'Invalid module call fields')
    parsed = urlsplit(config['endpoint'])
    require(parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and
            not parsed.password and not parsed.query and not parsed.fragment, 'Invalid explicit module endpoint')
    require(isinstance(config['model'], str) and bool(config['model'].strip()), 'Explicit model required')
    require(type(config['max_tokens']) is int and config['max_tokens'] > 0, 'Invalid module output budget')
    require(type(config['timeout_seconds']) in (int, float) and math.isfinite(config['timeout_seconds'])
            and config['timeout_seconds'] > 0, 'Invalid module request timeout')
    require(type(config['temperature']) in (int, float) and math.isfinite(config['temperature'])
            and 0 <= config['temperature'] <= 2, 'Invalid temperature')
    require(config.get('token_limit_field', 'max_tokens') in ('max_tokens', 'max_completion_tokens'), 'Invalid token field')
    if 'context_window_tokens' in config:
        require(type(config['context_window_tokens']) is int and config['context_window_tokens'] > config['max_tokens'], 'Invalid explicit context capacity')
    if 'reasoning_effort' in config:
        require(isinstance(config['reasoning_effort'], str) and bool(config['reasoning_effort']), 'Invalid reasoning effort')
    if 'thinking' in config:
        require(isinstance(config['thinking'], dict), 'Invalid thinking configuration')


def response_value(payload):
    try:
        require(isinstance(payload, dict), 'Malformed response object')
        require(isinstance(payload.get('choices'), list) and bool(payload['choices']), 'Malformed choices')
        choice = payload['choices'][0]
        require(isinstance(choice, dict) and isinstance(choice.get('message'), dict), 'Malformed message')
        content = choice['message'].get('content')
        require(isinstance(content, str), 'Missing response content')
        return {'content': content, 'finish_reason': choice.get('finish_reason'),
                'response_model': payload.get('model'), 'usage': payload.get('usage')}
    except (ValueError, TypeError, KeyError, IndexError):
        raise RequestFailure('Malformed API response envelope') from None


def http_failure(status, body):
    retryable = status == 401 or (status in (429, 500, 502, 503, 504)
        and not any(token in body for token in ('insufficient_quota', 'quota_exceeded')))
    return RequestFailure(f'HTTP {status}', retryable=retryable)


class HTTPGenerator:
    """The caller supplies credentials; importing this module makes no requests."""
    def __init__(self, api_key, *, session_factory=requests.Session):
        require(isinstance(api_key, str) and bool(api_key), 'Explicit API key required')
        self.api_key = api_key
        self.session_factory = session_factory

    def __call__(self, name, messages, directory, config):
        validate_call(config)
        body = {'model': config['model'], 'messages': messages, 'temperature': config['temperature'],
                config.get('token_limit_field', 'max_tokens'): config['max_tokens'], 'stream': False}
        body.update({key: config[key] for key in ('reasoning_effort', 'thinking') if key in config})
        write_record(directory / 'request.json', {'endpoint': config['endpoint'], 'body': body,
                                                 'timeout_seconds': config['timeout_seconds'], 'attempts': 1})
        try:
            with self.session_factory() as session:
                for prefix in ('http://', 'https://'):
                    session.mount(prefix, requests.adapters.HTTPAdapter(max_retries=0))
                raw = session.post(config['endpoint'], headers={'Authorization': f'Bearer {self.api_key}'},
                                   json=body, timeout=(10, config['timeout_seconds']), allow_redirects=False)
        except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError) as exc:
            raise RequestFailure(type(exc).__name__) from None
        (directory / 'http_response.txt').write_bytes(raw.content)
        write_record(directory / 'http_status.json', {'status_code': raw.status_code})
        if not 200 <= raw.status_code < 300:
            # Preserve the frozen V25 method transport retry classification.
            raise http_failure(raw.status_code, raw.text)
        try:
            return response_value(raw.json())
        except ValueError:
            raise RequestFailure('Malformed API JSON') from None
