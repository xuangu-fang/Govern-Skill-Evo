"""Replay-only display: shared complete initial messages and no duplicate request.

Initial-message sharing is locally ported from v25.2's frozen v25 implementation.
Facts, archives and evidence IDs remain unchanged; no timeline or task encoding.
"""
from copy import deepcopy
import json

from .protocol import require, fields, FORMAL_CONTEXT

FORMAT = 'replay_shared_initial_v1'
INPUT_VIEW = 'v29_docvqa_pairs_shared_initial_v2'


def exact(message):
    # Preserve field order as well as text. Even semantically equivalent objects
    # with different serialization may remain inline rather than lose information.
    return json.dumps(message, ensure_ascii=False, separators=(',', ':'))


def share_initial(view):
    require('shared_initial' not in view, 'Replay initial messages already shared')
    result = deepcopy(view)
    runs = {run['ref']: run for run in result['runs']}
    systems = {}
    for run in result['runs']:
        for message in run['initial']['messages']:
            if message.get('role') == 'system':
                systems.setdefault(exact(message), set()).add(run['ref'])
    table, system_keys = {}, {}
    for run in result['runs']:
        messages = run['initial']['messages']
        for index, message in enumerate(messages):
            if message.get('role') != 'system' or len(systems[exact(message)]) < 2:
                continue
            value = exact(message)
            if value not in system_keys:
                key = f'system_{len(system_keys) + 1}'
                system_keys[value] = key
                table[key] = message
            messages[index] = {'shared_message': system_keys[value]}
    for pair_index, pair in enumerate(result['pairs'], 1):
        p, q = (runs[pair[side]]['initial']['messages'] for side in ('parent', 'candidate'))
        users = [[(i, m) for i, m in enumerate(messages) if m.get('role') == 'user'] for messages in (p, q)]
        if not users[0] or exact([m for _, m in users[0]]) != exact([m for _, m in users[1]]):
            continue
        for user_index, ((pi, message), (qi, _)) in enumerate(zip(*users), 1):
            key = f'pair_{pair_index}_user_{user_index}'
            table[key] = message
            p[pi] = {'shared_message': key}
            q[qi] = {'shared_message': key}
    return {**{key: result[key] for key in ('parent', 'diff', 'plan')},
            'shared_initial': {'format': FORMAT, 'messages': table},
            **{key: result[key] for key in ('pairs', 'runs', 'memory')}}


def restore_initial(view):
    result = deepcopy(view)
    shared = result.pop('shared_initial', None)
    require(isinstance(shared, dict) and set(shared) == {'format', 'messages'}
            and shared['format'] == FORMAT and isinstance(shared['messages'], dict),
            'Invalid Replay shared initial table')
    for run in result['runs']:
        messages = run['initial']['messages']
        for index, message in enumerate(messages):
            if 'shared_message' not in message:
                continue
            key = message['shared_message']
            require(set(message) == {'shared_message'} and isinstance(key, str)
                    and key in shared['messages'], 'Invalid Replay shared message reference')
            restored = shared['messages'][key]
            require(isinstance(restored, dict) and restored.get('role') in ('system', 'user'),
                    'Invalid Replay shared message role')
            messages[index] = deepcopy(restored)
    # Also reject unused entries, cross-pair user sharing and noncanonical pointers.
    require(share_initial(result) == view, 'Noncanonical Replay shared initial view')
    return result


def model_input(view):
    """Project an already verified Replay view; never modify the audit payload."""
    fields(view, ('parent', 'diff', 'plan', 'pairs', 'runs', 'memory'), 'Replay view')
    result = deepcopy(view)
    for run in result['runs']:
        attempts = run['attempts']
        require(isinstance(attempts, list) and len(attempts) == 1,
                'Replay request sharing requires exactly one completed round')
        attempt = attempts[0]
        require(attempt.get('request_context') == FORMAL_CONTEXT,
                'Replay request sharing requires the DocVQA single-turn context')
        require('request_messages' in attempt and
                exact(attempt['request_messages']) == exact(run['initial']['messages']),
                'Replay formal request differs from initial messages')
        del attempt['request_messages']
        answer = run['outcome']['answer']
        require('raw_content' in answer and answer['raw_content'] == attempt['assistant']['content'],
                'Replay answer raw_content differs from ordinary assistant content')
        del answer['raw_content']
    return share_initial(result)


def restore_model_input(view):
    """Offline lossless check; production sends the compact view directly."""
    result = restore_initial(view)
    for run in result['runs']:
        require(len(run['attempts']) == 1, 'Expected one completed round')
        attempt = run['attempts'][0]
        answer = run['outcome']['answer']
        require('request_messages' not in attempt and 'raw_content' not in answer,
                'Expected the compact Replay view')
        attempt['request_messages'] = deepcopy(run['initial']['messages'])
        answer['raw_content'] = attempt['assistant']['content']
    require(model_input(result) == view, 'Replay view cannot be restored exactly')
    return result
