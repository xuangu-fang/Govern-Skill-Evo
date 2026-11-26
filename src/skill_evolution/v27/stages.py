"""Persistent bounded method calls, with V25 retry and semantic-stop boundaries.

An allocated request slot is never recycled. Response recovery completes the same
slot and makes no new request. Only identified output errors add temporary context.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import time
from pathlib import Path

import requests

from .facts import require
from .capacity import account
from .benchmark import current
from .storage import write_record
from .json_response import parse_json_response
from . import output_feedback as feedback, knowledge_verifier, modules
from .benchmarks.lmb import prompting, protocol
from .transport import RequestFailure, response_value, validate_call, http_failure


class Stopped(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    protocol.exact(value)  # Reject non-finite or non-JSON state before writing.
    write_record(path, value)


def freeze(path, value, *, read_only=False):
    path = Path(path)
    if path.exists():
        require(protocol.equal(read(path), value), f'Frozen value changed: {path}')
    else:
        require(not read_only, f'Missing frozen value: {path}')
        save(path, value)


def freeze_text(path, value, *, read_only=False):
    path = Path(path)
    if path.exists():
        require(path.read_bytes() == value.encode('utf-8'), f'Frozen text changed: {path}')
    else:
        require(not read_only, f'Missing frozen text: {path}')
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_bytes(value.encode('utf-8')); temporary.replace(path)


def _parse(call, response, *, fresh):
    require(isinstance(response, dict), 'Saved response must be an object')
    require(response.get('finish_reason') == 'stop' and isinstance(response.get('content'), str),
            'Saved response was not completed')
    parser = knowledge_verifier.parse_output if call.name in ('verifier', 'repair') else parse_json_response
    if fresh:
        parsed = feedback.output_call(f'{call.name} response', parser, response['content'])
        result = feedback.output_call(f'{call.name} output', call.complete, parsed)
    else:
        parsed = parser(response['content']); result = call.complete(parsed)
    return parsed, result


def run_stage(directory, call, *, call_config, max_attempts, max_input_chars, max_message_utf8_bytes,
              generate=None, resume=False, read_only=False, check_contract=lambda: None, retry_delay_seconds=0):
    validate_call(call_config)
    require(type(retry_delay_seconds) in (int, float) and math.isfinite(retry_delay_seconds)
            and retry_delay_seconds >= 0, "Invalid retry delay")
    require(type(max_attempts) is int and 1 <= max_attempts <= 6, 'Method total attempts must be 1..6')
    require(type(max_input_chars) is int and max_input_chars > 0 and
            type(max_message_utf8_bytes) is int and max_message_utf8_bytes > 0, 'Invalid input capacity')
    directory = Path(directory)
    check_contract()
    identity = {'module': call.name, 'prompt': prompting.prompt_identity(call.name), 'call_config': call_config,
                'source_sha256': protocol.digest(current().frozen_files()),
                'retry_policy': feedback.POLICY, 'execution_view': feedback.TIMELINE,
                'retry_delay_seconds': retry_delay_seconds,
                'max_attempts': max_attempts, 'max_input_chars': max_input_chars,
                'max_message_utf8_bytes': max_message_utf8_bytes}
    for name, value in [('identity', identity), ('input', call.input), ('base_messages', call.messages)]:
        freeze(directory / f'{name}.json', value, read_only=read_only)
    attempts = directory / 'attempts'
    if not read_only: attempts.mkdir(exist_ok=True)
    existing = sorted(path for path in attempts.iterdir() if path.is_dir())
    require([p.name for p in existing] == [f'{n:03}' for n in range(1, len(existing)+1)], 'Invalid request slot sequence')
    require(len(existing) <= max_attempts, 'Saved attempts exceed frozen budget')

    def expected_context(index):
        source = None
        for prior in existing[:index]:
            if (prior / 'error.json').exists() and read(prior / 'error.json')['kind'] == 'output_validation':
                source = str(prior.resolve())
        return {'policy': feedback.POLICY, 'execution_view': feedback.TIMELINE, 'feedback_from': source}

    def checked_messages(path, index):
        context = expected_context(index)
        require(read(path / 'request_context.json') == context, 'Saved request context changed')
        messages = feedback.request_messages(call.messages, context)
        require(read(path / 'messages.json') == messages, 'Saved request messages changed')
        freeze_text(path / 'prompt.md', messages[0]['content'], read_only=True)
        require(read(path / 'request_started.json')['call_config'] == call_config, 'Request configuration changed')
        freeze(path / 'capacity.json', account(messages, call_config, max_input_chars=max_input_chars,
               max_message_utf8_bytes=max_message_utf8_bytes), read_only=True)
        return messages

    def finish(path, response, *, fresh, verify_only=False):
        check_contract()
        parsed, result = _parse(call, response, fresh=fresh)
        freeze_text(path / 'raw_output.txt', response['content'], read_only=verify_only)
        for name, value in [('parsed', parsed), ('result', result)]:
            freeze(path / f'{name}.json', value, read_only=verify_only)
        expected_files = modules.output_files(call, result, parsed)
        for name in ('candidate.md', 'actual.diff', 'patch.diff'):
            if name in expected_files:
                freeze_text(path / name, expected_files[name], read_only=verify_only)
            else:
                require(not (path / name).exists(), 'Unexpected Candidate/patch artifact')
        freeze(path / 'validation.json', {'valid': True, 'semantic_truth_verified': False}, read_only=verify_only)
        freeze(path / 'completed.json', {'status': 'valid', 'module': call.name}, read_only=verify_only)
        if not verify_only:
            freeze(directory / 'result.json', {'path': f'attempts/{path.name}'})
        return path, result

    pending_preparation = None
    marker = directory / 'result.json'
    if marker.exists():
        selected = read(marker)
        require(set(selected) == {'path'}, 'Invalid stage selection')
        choices = {f'attempts/{path.name}': (i, path) for i, path in enumerate(existing)}
        require(selected['path'] in choices, 'Invalid selected attempt path')
        i, path = choices[selected['path']]
        require(i == len(existing)-1, 'Selected attempt is not the last slot')
        checked_messages(path, i)
        return finish(path, read(path / 'response.json'), fresh=False, verify_only=True)
    require(not read_only, 'Missing selected stage result')
    if existing:
        require(resume, 'Prior attempts require explicit resume')
        path = existing[-1]
        if not (path / 'request_started.json').exists():
            # No send is possible before the durable start marker. Reuse this
            # reserved slot; do not delete it or increase the frozen budget.
            allowed = {'request_context.json', 'messages.json', 'prompt.md',
                       'request_context.tmp', 'messages.tmp', 'prompt.md.tmp', 'request_started.tmp', 'capacity.json', 'capacity.tmp'}
            require(all(p.name in allowed and p.is_file() for p in path.iterdir()),
                    'Unstarted slot contains execution artifacts; cannot infer request state')
            context = expected_context(len(existing)-1)
            messages = feedback.request_messages(call.messages, context)
            freeze(path / 'request_context.json', context)
            freeze(path / 'messages.json', messages)
            freeze_text(path / 'prompt.md', messages[0]['content'])
            pending_preparation = path
        else:
            checked_messages(path, len(existing)-1)
        error = read(path / 'error.json') if (path / 'error.json').exists() else None
        if (path / 'completed.json').exists():
            value = finish(path, read(path / 'response.json'), fresh=False, verify_only=True)
            freeze(marker, {'path': f'attempts/{path.name}'})
            return value
        if error and not error['retryable']:
            raise Stopped(f'{call.name}: preserved non-retryable failure')
        if error is None and pending_preparation is None:
            try:
                if not (path / 'response.json').exists() and (path / 'http_status.json').exists():
                    status = read(path / 'http_status.json')['status_code']
                    body = (path / 'http_response.txt').read_text()
                    if not 200 <= status < 300:
                        raise http_failure(status, body)
                    try: raw = json.loads(body)
                    except json.JSONDecodeError:
                        raise RequestFailure('Malformed API JSON') from None
                    save(path / 'response.json', response_value(raw))
                if (path / 'response.json').exists():
                    response = read(path / 'response.json')
                    _check_response(response)
                    value = finish(path, response, fresh=True)
                    freeze(path / 'recovery.json', {'additional_requests': 0})
                    return value
                save(path / 'error.json', {'kind': 'technical', 'retryable': True,
                                          'error': 'Interrupted request; response unavailable'})
            except Exception as exc:
                error = _record_error(path, exc)
                if not error['retryable']:
                    raise Stopped(f'{call.name}: response recovery failed') from exc

    start = len(existing) if pending_preparation is not None else len(existing)+1
    for number in range(start, max_attempts+1):
        check_contract()
        context = expected_context(number-1)
        messages = feedback.request_messages(call.messages, context)
        capacity = account(messages, call_config, max_input_chars=max_input_chars,
                           max_message_utf8_bytes=max_message_utf8_bytes)
        require(callable(generate), 'Explicit method generator required for a new request')
        path = attempts / f'{number:03}'
        if path != pending_preparation: path.mkdir()
        freeze(path / 'request_context.json', context); freeze(path / 'messages.json', messages)
        freeze(path / 'capacity.json', capacity)
        freeze_text(path / 'prompt.md', messages[0]['content'])
        save(path / 'request_started.json', {'at': now(), 'call_config': call_config})
        try:
            try:
                response = generate(call.name, deepcopy(messages), path, deepcopy(call_config))
            except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError) as exc:
                raise RequestFailure(type(exc).__name__) from exc
            save(path / 'response.json', response)
            _check_response(response)
            return finish(path, response, fresh=True)
        except Exception as exc:
            error = _record_error(path, exc)
            if not error['retryable']:
                raise Stopped(f'{call.name}: preserved non-retryable failure') from exc
            if path not in existing: existing.append(path)
            if number < max_attempts:
                time.sleep(retry_delay_seconds * number)
    raise Stopped(f'{call.name}: frozen request budget exhausted; resume does not reset it')


def _check_response(response):
    if not isinstance(response, dict) or not isinstance(response.get('content'), str):
        raise RequestFailure('Malformed API response envelope')
    if response.get('finish_reason') != 'stop':
        raise RequestFailure('Model response did not finish normally')


def _record_error(path, exc):
    output_error = isinstance(exc, feedback.OutputValidationError)
    value = {'kind': 'output_validation' if output_error else 'technical',
             'retryable': output_error or (isinstance(exc, RequestFailure) and exc.retryable),
             'error_type': type(exc).__name__, 'error': str(exc)[:600] if isinstance(exc, (ValueError, RequestFailure)) else type(exc).__name__}
    if output_error: value['diagnostic'] = exc.diagnostic
    save(path / 'error.json', value)
    return value
