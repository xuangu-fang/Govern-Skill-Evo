"""Reversible OfficeQA evidence encoding, applied only at the model boundary.

Full runs reconstruct formal requests from initial messages and committed turns.
Partial citations can reference exact prefixes of already supplied contexts.
No normalization, summaries, new evidence, or cross-execution history sharing.
"""
from copy import deepcopy
import json

from ...facts import require

FORMAT = 'v26_officeqa_lossless_input_v2'
PREVIOUS = 'v26_officeqa_lossless_input_v1'
LEGACY = 'v26_officeqa_uncompressed_input_v1'
HEADER = '_officeqa_encoding'
POINTER = 'officeqa_message'
HISTORY = 'officeqa_history'


def exact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def equal(left, right):
    # Preserve JSON types (Python equality alone equates False/0 and 1/1.0).
    dump = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return dump(left) == dump(right)


def _full_runs(payload):
    yield from payload.get('runs', [])
    for source in payload.get('source_records', {}).values():
        record = source.get('record', {})
        if all(key in record for key in ('initial', 'attempts', 'outcome')):
            yield record


def _requests(run):
    messages = deepcopy(run['initial']['messages'])
    for attempt in run['attempts']:
        yield deepcopy(messages)
        messages.append(deepcopy(attempt['assistant']))
        messages.extend(deepcopy(tool['observation']) for tool in attempt['tools'])


def _message_lists(payload):
    """Only initial arrays and formal contexts of explicitly provided citations."""
    for run in payload.get('runs', []):
        yield run['initial']['messages'], (run['run_id'], run['task_id'])
    for source in payload.get('source_records', {}).values():
        record = source.get('record', {})
        owner = (source.get('run_id'), source.get('task_id'))
        if all(key in record for key in ('initial', 'attempts', 'outcome')):
            require(owner == (record['run_id'], record['task_id']), 'Cited run identity differs')
            yield record['initial']['messages'], owner
        elif 'messages' in record:  # An isolated :0 initial citation.
            yield record['messages'], owner
        elif 'request_messages' in record:  # An isolated round or tool citation.
            yield record['request_messages'], owner


def _pair_scopes(payload):
    """Cross-run user sharing requires an explicit, verified current full pair."""
    runs = {r['ref']: r for r in payload.get('runs', [])}
    for key, source in payload.get('source_records', {}).items():
        run = source.get('record', {})
        if '/' not in key and all(field in run for field in ('initial', 'attempts', 'outcome')):
            require(key == run['ref'], 'Cited run reference differs')
            runs[key] = run
    pairs = payload.get('pairs', payload.get('context', {}).get('pairs', []))
    groups = {}
    for pair in pairs:
        if any(pair[side] not in runs for side in ('parent', 'candidate')):
            require('pairs' not in payload, 'Missing full paired run')
            continue  # A review citation does not authorize fetching its counterpart.
        parent, candidate = (runs[pair[side]] for side in ('parent', 'candidate'))
        require(parent['task_id'] == candidate['task_id'] == pair['task_id'], 'Shared pair task differs')
        require(parent['run_id'] != candidate['run_id'], 'Shared pair reuses a run')
        users = [[m for m in run['initial']['messages'] if m['role'] == 'user']
                 for run in (parent, candidate)]
        if exact(users[0]) != exact(users[1]):
            continue
        scope = ('pair', parent['run_id'], candidate['run_id'])
        for run in (parent, candidate):
            owner = (run['run_id'], run['task_id'])
            require(owner not in groups, 'Duplicate shared pair membership')
            groups[owner] = scope
    return groups


def _initial_slots(messages):
    # Never share later assistant/tool observations or later user feedback.
    for index, message in enumerate(messages):
        if message.get('role') not in ('system', 'user'):
            break
        yield index, message


def _partial_contexts(payload):
    from .protocol import FORMAL_CONTEXT
    for ref, source in payload.get('source_records', {}).items():
        record = source.get('record', {})
        if 'request_messages' not in record:
            continue
        require(record.get('request_context') == FORMAL_CONTEXT, 'Invalid partial formal context')
        owner = (ref.rsplit('/', 1)[0] if '/' in ref else None,
                 source.get('run_id'), source.get('task_id'), source.get('role'))
        require(all(isinstance(v, str) and v for v in owner[1:]), 'Missing partial execution identity')
        yield ref, record, owner


def _encode_histories(payload):
    previous = {}
    for ref, record, owner in _partial_contexts(payload):
        messages = record['request_messages']
        require(isinstance(messages, list), 'Expected unencoded partial history')
        chosen = messages; size = len(exact(messages))
        keys = [exact(message) for message in messages]
        for source, (scope, earlier) in previous.items():
            if scope != owner:
                continue
            count = 0
            for left, right in zip(keys, earlier):
                if left != right:
                    break
                count += 1
            if not count:
                continue
            candidate = {HISTORY: source, 'prefix_messages': count, 'suffix': messages[count:]}
            candidate_size = len(exact(candidate))
            if candidate_size < size:
                chosen, size = candidate, candidate_size
        previous[ref] = (owner, keys)
        record['request_messages'] = chosen


def _restore_histories(payload):
    previous = {}
    for ref, record, owner in _partial_contexts(payload):
        value = record['request_messages']
        if isinstance(value, dict):
            require(set(value) == {HISTORY, 'prefix_messages', 'suffix'}, 'Invalid partial history pointer')
            source, count = value[HISTORY], value['prefix_messages']
            require(isinstance(source, str) and source in previous, 'History must reference an earlier citation')
            scope, messages = previous[source]
            require(scope == owner, 'Partial history execution scope differs')
            require(type(count) is int and 0 < count <= len(messages) and isinstance(value['suffix'], list),
                    'Invalid partial history boundary')
            value = deepcopy(messages[:count]) + deepcopy(value['suffix'])
            record['request_messages'] = value
        require(isinstance(value, list), 'Invalid partial history')
        previous[ref] = (owner, value)


def has_history_pointers(payload):
    return any(isinstance(record['request_messages'], dict)
               for _, record, _ in _partial_contexts(payload))


def project(payload, *, input_view=FORMAT):
    from .evidence import validate_run
    require(isinstance(payload, dict) and HEADER not in payload, 'Expected unencoded OfficeQA input')
    require(input_view in (FORMAT, PREVIOUS), 'Unsupported OfficeQA model input view')
    result = deepcopy(payload)
    full = list(_full_runs(result))
    for run in full:
        validate_run(run)
        for attempt, expected in zip(run['attempts'], _requests(run)):
            require(exact(attempt['request_messages']) == exact(expected),
                    'Formal history cannot be reconstructed exactly')
        for attempt in run['attempts']:
            del attempt['request_messages']
    groups = _pair_scopes(result)
    occurrences = {}
    for messages, owner in _message_lists(result):
        for index, message in _initial_slots(messages):
            require(owner[0] is not None and owner[1] is not None, 'Missing cited execution identity')
            scope = ('system',) if message['role'] == 'system' else groups.get(owner, ('run', *owner))
            occurrences.setdefault((scope, exact(message)), []).append((messages, index))
    table = {}
    for (_, encoded), slots in occurrences.items():
        if len(slots) < 2:
            continue
        key = f'm{len(table)+1}'
        marker = {POINTER: key}
        # Avoid growing a view by interning very short messages.
        if len(encoded) * len(slots) <= len(encoded) + len(exact(marker)) * len(slots) + len(key) + 4:
            continue
        table[key] = deepcopy(slots[0][0][slots[0][1]])
        for messages, index in slots:
            messages[index] = deepcopy(marker)
    if input_view == FORMAT:
        _encode_histories(result)
    if not full and not table and not has_history_pointers(result):
        return result
    return {HEADER: {'format': input_view, 'messages': table}, **result}


def restore(payload):
    """Decode and reject ambiguous, noncanonical or scope-expanding encodings."""
    from .evidence import validate_run
    result = deepcopy(payload)
    if HEADER not in result:
        return result  # Old raw requests remain readable; never rewrite archives.
    header = result.pop(HEADER)
    require(isinstance(header, dict) and set(header) == {'format', 'messages'}
            and header['format'] in (FORMAT, PREVIOUS) and isinstance(header['messages'], dict), 'Invalid OfficeQA encoding')
    if header['format'] == FORMAT:
        _restore_histories(result)
    table = header['messages']
    for messages, _ in _message_lists(result):
        for index, message in enumerate(messages):
            if POINTER not in message:
                continue
            require(set(message) == {POINTER} and isinstance(message[POINTER], str)
                    and message[POINTER] in table, 'Invalid shared message pointer')
            original = table[message[POINTER]]
            require(isinstance(original, dict) and set(original) == {'role', 'content'}
                    and original['role'] in ('system', 'user') and isinstance(original['content'], str),
                    'Invalid shared initial message')
            messages[index] = deepcopy(original)
    for run in _full_runs(result):
        for attempt, messages in zip(run['attempts'], _requests(run)):
            require('request_messages' not in attempt, 'Mixed raw and timeline encoding')
            # Canonical facts place request_messages after request_context.
            restored = {}
            for key, value in attempt.items():
                restored[key] = value
                if key == 'request_context':
                    restored['request_messages'] = messages
            attempt.clear(); attempt.update(restored)
        validate_run(run)
    require(equal(project(result, input_view=header['format']), payload), 'Noncanonical OfficeQA encoding or sharing scope')
    return result


def model_messages(messages, instruction, *, input_view=FORMAT, history_instruction=''):
    require(input_view in (FORMAT, PREVIOUS, LEGACY), 'Unsupported OfficeQA model input view')
    if input_view == LEGACY:
        return deepcopy(messages)
    require(len(messages) == 2 and [m['role'] for m in messages] == ['system', 'user'],
            'Project base messages before adding temporary feedback')
    original = json.loads(messages[1]['content'])
    encoded = project(original, input_view=input_view)
    if HEADER not in encoded:
        return deepcopy(messages)
    require(equal(restore(encoded), original), 'OfficeQA input encoding is not lossless')
    result = deepcopy(messages)
    result[0]['content'] = result[0]['content'].rstrip() + '\n\n' + instruction.rstrip()
    if input_view == FORMAT:
        previous = model_messages(messages, instruction, input_view=PREVIOUS)
        if not has_history_pointers(encoded):
            return previous
        require(bool(history_instruction.strip()), 'Missing partial history decoding instructions')
        result[0]['content'] += '\n\n' + history_instruction.rstrip()
    result[1]['content'] = exact(encoded)
    # Tiny inputs can cost more after decoding instructions. Keep their raw form.
    # These are representation sizes, never a character-to-token estimate.
    fallback = previous if input_view == FORMAT else messages
    if (len(exact(result)) >= len(exact(fallback)) or
            len(exact(result).encode('utf-8')) >= len(exact(fallback).encode('utf-8'))):
        return deepcopy(fallback)
    return result
