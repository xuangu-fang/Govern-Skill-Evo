"""Six durable attempts per Actor round, with temporary format correction."""
from copy import deepcopy
from dataclasses import asdict
import json
import time

from skilladam.backends import openai_compatible as native
from skilladam.benchmarks.officeqa.rollout import TOOL_SCHEMAS

from .execution import REQUEST_ATTEMPTS
from .transport import RequestFailure


class GenerationExhausted(RuntimeError):
    pass


class FormatError(ValueError):
    pass


def retry_wait(number):
    time.sleep(2 * number)


def parse_turn(response, *, require_reasoning=False):
    """Validate the whole response before allowing any tool execution.

    Tool *argument values* remain the native tool's responsibility. This only
    validates the call protocol, not read windows, paths or answer correctness.
    """
    if not isinstance(response, dict):
        raise RequestFailure('Malformed API response envelope')
    choices = response.get('choices')
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise RequestFailure('API response must contain one choice')
    choice = choices[0]
    finish = choice.get('finish_reason')
    if finish in (None, 'length'):
        raise RequestFailure('Missing finish reason or truncated response')
    if finish not in ('stop', 'tool_calls'):
        raise RequestFailure('Non-retryable finish reason', retryable=False)
    message = choice.get('message')
    if not isinstance(message, dict) or not isinstance(message.get('content', ''), (str, type(None))):
        raise RequestFailure('Malformed API message')
    if message.get('refusal'):
        raise RequestFailure('Provider refusal', retryable=False)
    if require_reasoning and not isinstance(message.get('reasoning_content'), str):
        raise RequestFailure('Missing or invalid DeepSeek reasoning_content')
    # Invalid usage belongs to the API envelope, not model format feedback.
    try:
        native.normalize_usage(response.get('usage'), requests=1)
    except ValueError:
        raise RequestFailure('Invalid API usage') from None
    calls = message.get('tool_calls')
    if calls is not None and not isinstance(calls, list):
        raise FormatError('tool_calls must be a JSON array (list) or null')
    if not calls and not (message.get('content') or '').strip():
        raise RequestFailure('Empty response')
    try:
        turn = native._officeqa_turn(response)
    except native.BackendProtocolError as exc:
        raise FormatError(str(exc)) from None
    ids = [call.call_id for call in turn.tool_calls]
    if len(ids) != len(set(ids)):
        raise FormatError('Tool call IDs must be unique within the response')
    names = {schema['function']['name'] for schema in TOOL_SCHEMAS}
    if any(call.name not in names for call in turn.tool_calls):
        raise FormatError('Tool names must be glob, read or grep')
    if finish == 'tool_calls' and not turn.tool_calls:
        raise FormatError('tool_calls finish reason requires function calls')
    return turn


def assistant_message(turn, response=None, *, reasoning=False):
    value = {'role': 'assistant', 'content': turn.text}
    if turn.tool_calls:
        value['content'] = turn.text or None
        value['tool_calls'] = [{'id': c.call_id, 'type': 'function',
            'function': {'name': c.name, 'arguments': c.raw_arguments}} for c in turn.tool_calls]
    if reasoning:
        value['reasoning_content'] = response['choices'][0]['message']['reasoning_content']
    return value


def format_repair(response, error, *, reasoning=False):
    message = deepcopy(response['choices'][0]['message'])
    saved = {}
    if reasoning:
        saved['reasoning_content'] = message.pop('reasoning_content')
    return {'output': json.dumps(message, ensure_ascii=False), 'error': str(error), **saved}


def request_messages(messages, repair):
    if repair is None:
        return deepcopy(messages)
    # Serialize invalid calls as text; never send dangling/malformed native
    # tool_calls back to an API that requires matching tool observations.
    assistant = {'role': 'assistant', 'content': repair['output']}
    if 'reasoning_content' in repair:
        assistant['reasoning_content'] = repair['reasoning_content']
    return deepcopy(messages) + [
        assistant,
        {'role': 'user', 'content': '# Previous Tool Call Validation Error\n\n' + repair['error'] +
         '\nNo tools from this response were executed. Correct the call structure and return a complete '
         'response under the original tool/answer contract. This diagnostic is not task evidence.'},
    ]


def generate_round(round_state, messages, transport, save):
    attempts = round_state['attempts']
    reasoning = transport.metadata()['reasoning_mode'] == 'deepseek_thinking'
    while True:
        last = attempts[-1] if attempts else None
        if last and last['status'] == 'accepted':
            return parse_turn(last['response'], require_reasoning=reasoning)
        if last and last['status'] == 'fatal':
            raise RequestFailure(last['error'], retryable=False)
        if last and last['status'] == 'requesting':
            # Process died with no durable response. Count the request anyway.
            last.update(status='interrupted', error='Request outcome unknown; attempt remains consumed')
            save()
        if last and last['status'] == 'received':
            try:
                turn = parse_turn(last['response'], require_reasoning=reasoning)
            except FormatError as exc:
                round_state['repair'] = format_repair(last['response'], exc, reasoning=reasoning)
                last.update(status='format_error', error=str(exc))
            except RequestFailure as exc:
                last.update(status='technical_error' if exc.retryable else 'fatal', error=str(exc))
            else:
                last['status'] = 'accepted'
                round_state['repair'] = None
                save()
                return turn
            save()
            continue
        if len(attempts) >= REQUEST_ATTEMPTS:
            raise GenerationExhausted('Six request attempts exhausted; resume does not reset the budget')
        if attempts:
            retry_wait(len(attempts))
        attempt = {'number': len(attempts) + 1, 'status': 'requesting',
                   'messages': request_messages(messages, round_state['repair']),
                   'usage': asdict(native.normalize_usage(None, requests=1))}
        attempts.append(attempt)
        save()  # Reserve the attempt BEFORE making the request.
        try:
            response = transport(messages=deepcopy(attempt['messages']), tools=deepcopy(TOOL_SCHEMAS))
        except RequestFailure as exc:
            attempt.update(status='technical_error' if exc.retryable else 'fatal', error=str(exc), evidence=exc.evidence)
            save()
        except Exception as exc:
            # Programming/disk/fixture errors must not manufacture another call.
            attempt.update(status='fatal', error=type(exc).__name__)
            save()
            raise
        else:
            attempt.update(status='received', response=response)
            if isinstance(response, dict):
                try:
                    attempt['usage'] = asdict(native.normalize_usage(response.get('usage'), requests=1))
                except ValueError:
                    pass
            save()  # Recovery parses this response without issuing a new call.
