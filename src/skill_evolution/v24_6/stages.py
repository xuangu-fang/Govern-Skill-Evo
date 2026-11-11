"""Bounded, replayable requests using the frozen V24.6 system prompts."""
import json
import time

from src.skill_evolution.v24_2.storage import freeze, read
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.json_response import parse_json_response
from src.skill_evolution.v27.transport import RequestFailure, http_failure, response_value
from src.skill_evolution.v24_2.stages import trajectory_view
from . import system_prompt


def stage(directory, name, payload, validate, config, generate):
    root = directory / name
    freeze(root / 'input.json', payload)
    base = [{'role': 'system', 'content': system_prompt(name)},
            {'role': 'user', 'content': json.dumps(trajectory_view(payload), ensure_ascii=False, separators=(',', ':'))}]
    call = dict(config['call_config'])
    require(call.pop('stream', False) is False, 'Expected nonstreaming module call')
    call['max_tokens'] = config['module_max_tokens'].get(name, call['max_tokens'])
    freeze(root / 'call.json', call)
    messages = base
    marker = root / 'result.json'
    chosen = read(marker)['attempt'] if marker.exists() else None
    for n in range(1, config['max_attempts'] + 1):
        require(sum(len(m['content']) for m in messages) <= config['max_input_chars'], 'Input exceeds character limit')
        require(len(json.dumps(messages, ensure_ascii=False).encode()) <= config['max_message_utf8_bytes'],
                'Input exceeds byte limit')
        slot = root / 'attempts' / f'{n:03}'
        fresh = not (slot / 'messages.json').exists()
        require(chosen is None or not fresh and n <= chosen, 'Incomplete selected request archive')
        freeze(slot / 'messages.json', messages)
        failure = slot / 'failure.json'
        if failure.exists():
            require(chosen != n, 'Selected request has a failure receipt')
            error = read(failure)
            if not error['retryable']:
                raise RuntimeError(error['message'])
            continue
        try:
            if (slot / 'http_status.json').exists():
                status = read(slot / 'http_status.json')['status_code']
                raw = (slot / 'http_response.txt').read_text()
                if not 200 <= status < 300:
                    raise http_failure(status, raw)
                try:
                    response = response_value(json.loads(raw))
                except json.JSONDecodeError as exc:
                    raise RequestFailure('Malformed API JSON') from exc
            elif (slot / 'response.json').exists():
                response = read(slot / 'response.json')
            elif fresh:
                response = generate(name, messages, slot, call)
            else:
                raise RequestFailure('Previous request was interrupted before saving a response')
            freeze(slot / 'response.json', response)
            if response.get('finish_reason') != 'stop' or not isinstance(response.get('content'), str):
                raise RequestFailure('Incomplete model response')
        except RequestFailure as exc:
            require(chosen is None, 'Selected archive contains an incomplete response')
            freeze(failure, {'message': str(exc), 'retryable': exc.retryable})
            if not exc.retryable:
                raise
            if fresh and n < config['max_attempts']:
                time.sleep(config['retry_delay_seconds'])
            continue
        try:
            parsed = parse_json_response(response.get('content'))
            result = validate(parsed, payload)
        except ValueError as exc:
            require(chosen != n, 'Selected response no longer validates')
            freeze(slot / 'validation.json', {'error': str(exc)})
            messages = base + [{'role': 'assistant', 'content': str(response.get('content', ''))},
                               {'role': 'user', 'content': f'Correct this error and return full JSON: {exc}'}]
            continue
        require(not (slot / 'validation.json').exists(), 'Previously invalid output now validates')
        freeze(marker, dict(attempt=n, parsed=parsed, result=result))
        return parsed, result
    raise RuntimeError(f'{name} exhausted its {config["max_attempts"]} attempts')
