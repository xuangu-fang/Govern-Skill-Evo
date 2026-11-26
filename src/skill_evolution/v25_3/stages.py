"""Bounded model stages. Completed slots can be replayed without a new request."""
import hashlib
import json
import time
from pathlib import Path

from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.storage import write_record
from src.skill_evolution.v27.transport import RequestFailure, http_failure, response_value
from . import PACKAGE
from .baseline.benchmarks.spreadsheetbench import protocol
from . import execution_input_view
from .output_feedback import OutputValidationError, checked_output


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def freeze(path, value):
    if path.exists():
        require(digest(read(path)) == digest(value), f'Checkpoint mismatch: {path}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_record(path, value)


def archived_http_response(slot):
    status = read(slot / 'http_status.json')['status_code']
    raw = (slot / 'http_response.txt').read_text()
    if not 200 <= status < 300:
        raise http_failure(status, raw)
    try:
        return response_value(json.loads(raw))
    except RequestFailure as exc:
        raise ValueError('Invalid archived HTTP response envelope') from exc


def messages_for(name, payload, profile):
    prompt = (PACKAGE / 'prompts' / (name + '.md')).read_text()
    prompt += ('\nFor structured basis use exact run/step IDs. In prose use one backtick pair '
               'around each explicit Evidence, Update or Memory citation, for example '
               '`Evidence:P1:outcome`. Spreadsheet coordinates are not evidence identifiers. '
               'Only cite material supplied to this stage.')
    if name != 'editor':
        context = (PACKAGE / 'prompts/execution_context.md').read_text()
        prompt += '\n\n' + protocol.render(context, protocol.time_fields(protocol.background(profile)))
    messages = [{'role': 'system', 'content': prompt},
                {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]
    return execution_input_view.model_messages(messages)


def stage(rd, name, payload, validate, config, generate):
    base = messages_for(name, payload, config['actor_profile'])
    require(sum(len(m['content']) for m in base) <= config['max_input_chars'], 'Input exceeds character limit')
    call = {k: v for k, v in config['call_config'].items() if k != 'stream'}
    call['max_tokens'] = config['module_max_tokens'].get(name, call['max_tokens'])
    root = rd / name
    freeze(root / 'input.json', payload)
    freeze(root / 'call.json', call)
    selected = None
    if (root / 'result.json').exists():
        selected = read(root / 'result.json')['attempt']
        require(type(selected) is int and 1 <= selected <= config['max_attempts'],
                'Invalid selected attempt in stage archive')
    messages = base
    for number in range(1, config['max_attempts'] + 1):
        slot = root / 'attempts' / f'{number:03}'
        require(len(json.dumps(messages, ensure_ascii=False).encode()) <= config['max_message_utf8_bytes'],
                'Request exceeds byte budget')
        # Allocate before requesting; a crash with an unknown response consumes this slot.
        fresh = not (slot / 'messages.json').exists()
        if selected is not None:
            require(not fresh and number <= selected and
                    (number != selected or (slot / 'response.json').exists()),
                    'Incomplete selected stage archive')
        if (slot / 'validation.json').exists():
            require((slot / 'response.json').is_file(), 'Validation failure lacks its saved response')
        freeze(slot / 'messages.json', messages)
        try:
            if (slot / 'response.json').exists():
                response = read(slot / 'response.json')
                if (slot / 'http_status.json').exists():
                    try:
                        archived = archived_http_response(slot)
                    except RequestFailure as exc:
                        raise ValueError('Saved response conflicts with HTTP archive') from exc
                    require(response == archived, 'Saved response differs from HTTP archive')
            elif (slot / 'error.json').exists():
                error = read(slot / 'error.json')
                require(type(error.get('retryable')) is bool and isinstance(error.get('reason'), str),
                        'Invalid archived request failure')
                if not error['retryable']:
                    raise RuntimeError(error['reason'])
                continue
            elif (slot / 'http_status.json').exists():
                response = archived_http_response(slot)
            elif fresh:
                response = generate(name, messages, slot, call)
            else:
                raise RequestFailure('Interrupted request without saved response')
            freeze(slot / 'response.json', response)
            if response.get('finish_reason') != 'stop' or not isinstance(response.get('content'), str):
                raise RequestFailure('Incomplete model response')
        except RequestFailure as exc:
            require(number != selected, 'Selected response failed transport verification')
            freeze(slot / 'error.json', {'reason': str(exc), 'retryable': exc.retryable})
            if not exc.retryable:
                raise
            if fresh and number < config['max_attempts']:
                time.sleep(config.get('retry_delay_seconds', 0) * number)
            continue
        try:
            require(not (slot / 'error.json').exists(), 'Complete response conflicts with saved request failure')
            parsed, result = checked_output(name, validate, response['content'], payload)
        except OutputValidationError as exc:
            require(number != selected, 'Selected response failed output verification')
            # Preserve the diagnostic format used to verify earlier attempts on resume.
            detail = str(exc.__cause__) if exc.__cause__ is not None else exc.diagnostic['error']
            freeze(slot / 'validation.json', {'error': detail})
            messages = base + [{'role': 'assistant', 'content': response['content']},
                               {'role': 'user', 'content': f'Correct this output error and return full JSON: {detail}'}]
            continue
        require(not (slot / 'validation.json').exists(), 'Valid response conflicts with saved validation failure')
        freeze(root / 'result.json', {'attempt': number, 'parsed': parsed, 'result': result})
        return parsed, result
    raise RuntimeError(f'{name}: request budget exhausted')
