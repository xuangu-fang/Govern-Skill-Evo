"""Configured OpenAI-compatible proxy transport, standard library, no implicit retries."""
import json
import os
from pathlib import Path
import re
import time
import urllib.request
import urllib.error


class TransportError(Exception):
    def __init__(self, kind, status=None):
        super().__init__(kind)
        self.kind, self.status = kind, status


def credentials(root):
    config = {}
    path = Path(root) / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            match = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*)', line)
            if match:
                config[match[1]] = match[2].strip().strip('\"\'')
    config.update({k: os.environ[k] for k in ('OPENAI_API_KEY', 'OPENAI_BASE_URL') if os.environ.get(k)})
    if not config.get('OPENAI_API_KEY') or not config.get('OPENAI_BASE_URL'):
        raise TransportError('missing_connection')
    return config['OPENAI_BASE_URL'].rstrip('/'), config['OPENAI_API_KEY']


def chat(root, payload, timeout=90):
    base, key = credentials(root)
    request = urllib.request.Request(base + '/chat/completions', data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        # Never log response headers/bodies or credentials on failure.
        raise TransportError('http_error', exc.code) from None
    except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise TransportError(type(exc).__name__) from None
    if not isinstance(result, dict) or not result.get('choices'):
        raise TransportError('invalid_provider_response')
    return result, time.monotonic() - started
