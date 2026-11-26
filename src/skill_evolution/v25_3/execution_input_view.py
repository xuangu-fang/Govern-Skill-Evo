"""Request-local, reversible presentation of already authorized complete runs."""
from copy import deepcopy
import json

from src.skill_evolution.v27.facts import require
from .baseline.benchmarks.spreadsheetbench import replay_code_view, timeline


FORMAT = 'v25_3_shared_execution_text_v1'
INSTRUCTION = """## Shared execution evidence
shared_initial.messages stores complete original Actor messages. A run's
initial.messages item {"shared_message":"key"} means that complete table entry
at exactly that position. Read it as part of that run's initial context before
interpreting the execution timeline. Identical system messages are shared across
runs; complete user messages are shared only within the supplied same-task P/Q
pair, and only when both complete user-message sequences match exactly.
All other messages remain inline. Parent and Candidate are independent executions.
Shared keys are display pointers, not evidence IDs. Cite the original run/step IDs.
Message roles and scope are unchanged: Actor messages are evidence for this stage.

Every attempt retains its complete response. An executed_code value
{"from_response":"python_fence_body_exact_v1"} means the complete Python code
inside that same attempt's response fence (including its final newline), verified
identical to the program actually executed. Read that code directly in response;
there are no character-range references. If execution adapted the program, its
executed_code remains a separate complete string. Runtime evidence, returned
feedback, scores, top-level Parent, Plan and Memory retain their original scope.
"""


def exact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def _compact(view):
    require('shared_initial' not in view, 'Execution input is already shared')
    result = replay_code_view.share_code(view)
    runs = {run['ref']: run for run in result['runs']}
    require(len(runs) == len(result['runs']), 'Duplicate run reference')
    occurrences = {}
    for run in runs.values():
        for message in run['initial']['messages']:
            require('shared_message' not in message, 'Expected complete initial message')
            if message.get('role') == 'system':
                occurrences.setdefault(exact(message), set()).add(run['ref'])
    table, keys = {}, {}
    for run in runs.values():
        for index, message in enumerate(run['initial']['messages']):
            value = exact(message)
            if message.get('role') != 'system' or len(occurrences[value]) < 2:
                continue
            if value not in keys:
                key = f'system_{len(keys) + 1}'
                keys[value] = key
                table[key] = message
            run['initial']['messages'][index] = {'shared_message': keys[value]}
    paired = set()
    for number, pair in enumerate(result.get('pairs', []), 1):
        p, q = (runs[pair[side]] for side in ('parent', 'candidate'))
        require(p['ref'] != q['ref'] and not ({p['ref'], q['ref']} & paired),
                'Reused paired execution')
        require(p['task_id'] == q['task_id'] == pair['task_id'], 'Pair task differs')
        paired.update((p['ref'], q['ref']))
        users = [[(i, m) for i, m in enumerate(r['initial']['messages'])
                  if m.get('role') == 'user'] for r in (p, q)]
        if not users[0] or exact([m for _, m in users[0]]) != exact([m for _, m in users[1]]):
            continue
        for index, ((pi, message), (qi, _)) in enumerate(zip(*users), 1):
            key = f'pair_{number}_user_{index}'
            table[key] = message
            p['initial']['messages'][pi] = {'shared_message': key}
            q['initial']['messages'][qi] = {'shared_message': key}
    # Match the other QA views: append for Diagnosis/Preconditioner, precede
    # runs for Replay (identified by its paired-execution input contract).
    shared = {'format': FORMAT, 'messages': table}
    if 'pairs' not in result:
        return {**result, 'shared_initial': shared}
    ordered = {}
    for key, value in result.items():
        if key == 'runs':
            ordered['shared_initial'] = shared
        ordered[key] = value
    return ordered


def project(payload):
    if not payload.get('runs'):
        return deepcopy(payload)
    return _compact(timeline.project(payload))


def restore(payload):
    if not payload.get('runs'):
        require('shared_initial' not in payload, 'Unexpected shared table without runs')
        return deepcopy(payload)
    result = deepcopy(payload)
    shared = result.pop('shared_initial')
    require(set(shared) == {'format', 'messages'} and shared['format'] == FORMAT
            and isinstance(shared['messages'], dict), 'Invalid shared execution table')
    for run in result['runs']:
        for index, message in enumerate(run['initial']['messages']):
            if 'shared_message' not in message:
                continue
            key = message['shared_message']
            require(set(message) == {'shared_message'} and isinstance(key, str)
                    and key in shared['messages'], 'Invalid shared message pointer')
            original = shared['messages'][key]
            require(isinstance(original, dict) and original.get('role') in ('system', 'user'),
                    'Invalid shared message role')
            run['initial']['messages'][index] = deepcopy(original)
    result = timeline.restore(replay_code_view.restore_code(result))
    require(project(result) == payload, 'Noncanonical shared execution view')
    return result


def model_messages(messages):
    result = timeline.model_messages(messages)
    payload = json.loads(messages[1]['content'])
    if not payload.get('runs'):
        return result
    compact = _compact(json.loads(result[1]['content']))
    require(restore(compact) == payload, 'Execution input round trip differs')
    result[0]['content'] = result[0]['content'].replace(
        'Responses and executed_code remain separate and complete.',
        'Responses remain complete; unchanged executed_code may reference its response as explained below.')
    result[0]['content'] += '\n\n' + INSTRUCTION
    result[1]['content'] = exact(compact)
    return result
