"""Opt-in Actor entry point; keep an episode alive across truncated step responses."""
import argparse
import hashlib
from pathlib import Path
import time

import requests

from .output_budget import POLICY


def chat(session, endpoint, key, model, messages, *, max_attempts=3, strict_response=True):
    if max_attempts != 3 or not strict_response:
        raise ValueError('Budget recovery requires strict three-attempt base policy')
    tokens, streak, other, calls = POLICY['initial_max_tokens'], 0, 0, 0
    while True:
        body = {'model': model, 'messages': messages, 'temperature': 1.0,
                'max_tokens': tokens, 'reasoning_effort': 'medium',
                'thinking': {'type': 'enabled'}, 'stream': False}
        calls += 1
        try:
            response = session.post(endpoint, headers={'Authorization': f'Bearer {key}'},
                                    json=body, timeout=(10, 300))
        except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError):
            other += 1; streak = 0
            if other >= max_attempts:
                raise
            time.sleep(min(2 ** (other-1), 30)); continue
        transient = response.status_code in {429, 500, 502, 503, 504}
        if response.status_code == 429:
            transient = 'insufficient_quota' not in response.text and 'quota_exceeded' not in response.text
        if not response.ok:
            other += 1; streak = 0
            if not transient or other >= max_attempts:
                raise RuntimeError(f'Model API returned HTTP {response.status_code}.')
            time.sleep(min(2 ** (other-1), 30)); continue
        try:
            payload = response.json(); choice = payload['choices'][0]; message = choice['message']
            content = message.get('content') or ''
            if choice.get('finish_reason') == 'length':
                streak += 1
                if streak == POLICY['length_attempts_per_budget']:
                    tokens *= POLICY['multiplier']; streak = 0
                time.sleep(1); continue
            if not isinstance(content, str) or not content.strip() or choice.get('finish_reason') != 'stop':
                raise ValueError('Empty or incomplete Actor response')
        except (ValueError, KeyError, IndexError, TypeError):
            other += 1; streak = 0
            if other >= max_attempts:
                raise
            time.sleep(min(2 ** (other-1), 30)); continue
        return {'content': content, 'finish_reason': choice['finish_reason'], 'response_model': payload.get('model'),
                'usage': payload.get('usage'), 'reasoning_content_chars': len(message.get('reasoning_content') or ''),
                'api_attempts': calls, 'transport_retries': calls-1}


def main():
    from . import evolution as ev
    from . import output_budget
    from src.adapters.alfworld.run_task_skill import main as run
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--budget-campaign', required=True, type=Path)
    args, rest = parser.parse_known_args()
    ev._check_contract(args.budget_campaign)
    if not output_budget.amendment(args.budget_campaign):
        raise ValueError('No authorized output budget recovery')
    extension = {'v23_4/'+name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                 for name in ('budget_actor.py', 'output_budget.py')}
    return run(rest, chat_fn=chat, output_budget_policy=POLICY, implementation_extension=extension)


if __name__ == '__main__':
    raise SystemExit(main())
