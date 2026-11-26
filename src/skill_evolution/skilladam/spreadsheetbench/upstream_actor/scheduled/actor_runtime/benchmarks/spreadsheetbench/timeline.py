"""Lossless deduplication within the selected evidence view, not raw API archives."""
from copy import deepcopy
import json

from ...facts import require
from .protocol import EXECUTION_HISTORY


INSTRUCTION = """## Execution timeline representation
For each complete run, initial.messages is shown once and attempts are ordered.
Attempt n's Actor request is exactly initial.messages followed by every earlier
attempt's response as an assistant message (unless response_in_history=false)
and its non-null feedback_to_actor message, in order. Missing response_in_history
means true for legacy runs. Truncated outputs marked false are archived evidence,
not additions to Actor history. Repeated request_messages are omitted from these complete runs.
Responses and executed_code remain separate and complete. execution contains
runtime evidence; only feedback_to_actor was returned to the Actor. outcome.score
is post-execution evidence and was not Actor feedback. An isolated cited attempt
retains request_messages because its initial context and earlier attempts may not
be supplied. Evidence IDs and the scope of available evidence are unchanged."""


EXECUTION_INSTRUCTION = """## Execution timeline representation
For each complete run, initial.messages is shown once and attempts are ordered.
Each attempt's request_messages is initial.messages followed by every earlier
attempt's response as an assistant message (unless response_in_history=false)
and its non-null feedback_to_actor message, in order. Missing response_in_history
means true for legacy runs. Truncated outputs marked false are archived evidence,
not additions to Actor history in legacy views. Attempts marked
request_context=execution_only_v1 contain formal execution history only:
generation failures and temporary format corrections are excluded. This formal
history does not reconstruct the complete real API request, which may have
included temporary format feedback. Full requests remain in the raw audit archive.
Evidence numbers may have gaps; gaps are not execution failures or execution counts.
Repeated request_messages are omitted from these complete runs.
Responses and executed_code remain separate and complete. execution contains
runtime evidence; feedback_to_actor records the execution feedback actually
returned to the Actor, rather than every stored log. outcome.score
is post-execution evidence and was not Actor feedback. An isolated cited attempt
retains request_messages with the same view semantics because its initial context and earlier attempts may not
be supplied. Evidence IDs and the scope of available evidence are unchanged."""


def exact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def requests_for(run):
    """Reconstruct the chosen view's context, never excluded temporary corrections."""
    messages = deepcopy(run['initial']['messages'])
    for attempt in run['attempts']:
        yield deepcopy(messages)
        if attempt.get('response_in_history',True):
            messages.append({'role': 'assistant', 'content': attempt['response']})
        if attempt['feedback_to_actor'] is not None:
            messages.append(deepcopy(attempt['feedback_to_actor']))


def full_runs(payload):
    """Only traverse complete runs already authorized by the module's view."""
    yield from payload.get('runs', [])
    for source in payload.get('source_records', {}).values():
        record = source.get('record', {})
        if all(key in record for key in ('initial', 'attempts', 'outcome')):
            yield record


def copy_payload(payload):
    result = deepcopy(payload)
    if 'source_records' in payload:
        # A full-run citation and an isolated-attempt citation are independent
        # evidence views, even if the caller reused a Python object for both.
        result['source_records'] = {ref: deepcopy(source)
                                    for ref, source in payload['source_records'].items()}
    return result


def project(payload):
    result = copy_payload(payload)
    for run in full_runs(result):
        for attempt, messages in zip(run['attempts'], requests_for(run)):
            require('request_messages' in attempt and
                    exact(attempt['request_messages']) == exact(messages),
                    f"Actor request cannot be reconstructed: {attempt['ref']}")
            del attempt['request_messages']
    return result


def restore(payload):
    result = copy_payload(payload)
    for run in full_runs(result):
        for attempt, messages in zip(run['attempts'], requests_for(run)):
            require('request_messages' not in attempt, 'Expected a timeline view')
            attempt['request_messages'] = messages
    return result


def model_messages(messages):
    """Project only the evidence message, before stage retry feedback is added."""
    payload = json.loads(messages[1]['content'])
    runs=list(full_runs(payload))
    filtered=any(a.get('request_context')==EXECUTION_HISTORY for run in runs for a in run['attempts'])
    filtered=filtered or any(source.get('record',{}).get('request_context')==EXECUTION_HISTORY
                            for source in payload.get('source_records',{}).values())
    if not runs and not filtered:
        return deepcopy(messages)
    result = deepcopy(messages)
    result[0]['content'] = result[0]['content'].rstrip() + '\n\n' + (EXECUTION_INSTRUCTION if filtered else INSTRUCTION)
    result[1]['content'] = json.dumps(project(payload), ensure_ascii=False, separators=(',', ':'))
    return result
