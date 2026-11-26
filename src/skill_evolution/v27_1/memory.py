"""Append-only v27.1 Memory with verified sources and one publication pointer.

Prepare is read-only. Commit publishes Memory and Selected Skill together;
loading checks committed records without reopening historical Actor sources.
No model calls, historical revision, experiment execution or campaign wiring.
The store uses a POSIX advisory writer lock and atomic same-directory renames.
"""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts.diagnosis import fields
from src.skill_evolution.v27.facts import require, text
from . import editor, gate, preconditioner, memory_operation

FORMAT = 'v27_1_memory_commit_v1'
PREPARED_FORMAT = 'v27_1_memory_prepared_v1'
HEAD_FORMAT = 'v27_1_memory_head_v1'
_HEAD = re.compile(r'([0-9]{6,})')
_STATE_FIELDS = ('head', 'memory', 'selection', 'selected_execution_source')
_DERIVED = ('round', 'selection', 'selected_execution_source')


def _bytes(value):
    """Canonical JSON; disallow Python-only containers and non-string keys."""
    def check(item):
        require(type(item) in (dict, list, str, int, float, bool, type(None)), 'Expected JSON value')
        if isinstance(item, dict):
            require(all(type(key) is str for key in item), 'Expected string JSON keys')
            for child in item.values(): check(child)
        elif isinstance(item, list):
            for child in item: check(child)
    check(value)
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    except (ValueError, UnicodeError) as exc:
        raise ValueError('Invalid JSON text or number') from exc


def _same(left, right):
    return _bytes(left) == _bytes(right)


def _head_parts(head):
    require(isinstance(head, str), 'Invalid Memory head')
    match = _HEAD.fullmatch(head)
    require(match is not None, 'Invalid Memory head')
    sequence = int(match[1])
    require(sequence > 0 and match[1] == f'{sequence:06d}', 'Invalid Memory sequence')
    return sequence, None


def _empty():
    return {'head': None, 'memory': {'rounds': []}, 'selection': None, 'selected_execution_source': None}


def _validate_state(state):
    fields(state, _STATE_FIELDS, 'Memory state')
    _bytes(state)
    preconditioner.validate_memory_view(state['memory'])
    if state['head'] is None:
        require(_same(state, _empty()), 'Initial Memory state must be empty')
        return
    sequence, _ = _head_parts(state['head'])
    require(sequence == len(state['memory']['rounds']), 'Memory sequence differs from history')
    entries = [entry for record in state['memory']['rounds'] for entry in record['entries']]
    require([entry['id'] for entry in entries] == [f'M{i}' for i in range(1, len(entries) + 1)],
            'Memory IDs must follow committed event order')
    selection = state['selection']
    fields(selection, ('selected_update_ids', 'selected_text', 'actual_diff'), 'Memory selection')
    require(isinstance(selection['selected_update_ids'], list) and
            all(isinstance(uid, str) for uid in selection['selected_update_ids']), 'Invalid selected IDs')
    require(selection['selected_text'] is None or isinstance(selection['selected_text'], str),
            'Invalid selected text')
    require(isinstance(selection['actual_diff'], str), 'Invalid selected diff')
    require(state['selected_execution_source'] in ('parent', 'candidate', None), 'Invalid execution source')


def _prepare(previous, source):
    _validate_state(previous)
    require(isinstance(source, dict), 'Invalid Memory source')
    if source.get('kind') == 'gate':
        fields(source, ('kind', 'replayed', 'gate_result'), 'Gate Memory source')
        replayed, result = source['replayed'], source['gate_result']
        gate.validate_gate(result, replayed=replayed)
        saved = replayed['audit']['editor']
        parent = replayed['payload']['parent']
        decisions = {item['update_id']: item['gate_decision'] for item in result['decisions']}
        knowledge = replayed['knowledge']
        selection, execution_source = result['selection'], result['selected_execution_source']
    else:
        fields(source, ('kind', 'edited'), 'No-change Memory source')
        require(source['kind'] == 'no_change', 'Unknown Memory source kind')
        saved = source['edited']
        view = editor.editor_input(saved)
        require(all(key in saved for key in ('editor', 'editor_status', 'candidate_text', 'actual_diff')),
                'Memory requires completed Editor output')
        constructed = editor.validate_editor(saved['editor'], view, saved=saved)
        require(constructed['editor_status'] == 'no_change' and
                all(key in saved and _same(saved[key], value) for key, value in constructed.items()),
                'Memory no-change requires verified all-empty Editor patches')
        parent = view['parent']
        selection = editor.select_skill(saved, [])
        execution_source = 'parent'
        decisions = {update['id']: None for update in saved['effective_plan']['updates']}
        knowledge = []
    rid = text(saved.get('round_id'), 'Memory round_id')
    require(all(record['round_id'] != rid for record in previous['memory']['rounds']), 'Duplicate Memory round_id')
    require(_same(saved['memory'], previous['memory']), 'Preconditioner Memory differs from frozen history')
    if previous['head'] is not None:
        require(_same(parent, previous['selection']['selected_text']), 'Parent differs from previous Selected Skill')
    count = sum(len(record['entries']) for record in previous['memory']['rounds'])
    record = {'round_id': rid, 'source_updates': [
        {'id': update['id'], 'text': update['text'], 'gate_decision': decisions[update['id']]}
        for update in saved['effective_plan']['updates']],
        'entries': [{'id': f'M{count + index}', 'knowledge': deepcopy(item)}
                    for index, item in enumerate(knowledge, 1)]}
    preconditioner.validate_memory_view({'rounds': previous['memory']['rounds'] + [record]})
    result = {'format': PREPARED_FORMAT, 'previous': previous, 'source': source,
              'round': record, 'selection': selection, 'selected_execution_source': execution_source}
    _bytes(result)
    return deepcopy(result)


def prepare_append(previous, *, replayed, gate_result):
    """Build a round without writes; committed-prefix authenticity is checked at commit."""
    with current().memory_operation():
        return _prepare(deepcopy(previous), {'kind': 'gate', 'replayed': deepcopy(replayed),
                                            'gate_result': deepcopy(gate_result)})


def prepare_no_change(previous, *, edited):
    """Archive all-empty Editor proposals without fabricating Replay or Gate."""
    with current().memory_operation():
        return _prepare(deepcopy(previous), {'kind': 'no_change', 'edited': deepcopy(edited)})


def _validate_prepared(prepared):
    fields(prepared, ('format', 'previous', 'source', *_DERIVED), 'Prepared Memory')
    require(prepared['format'] == PREPARED_FORMAT, 'Unknown prepared Memory format')
    require(_same(prepared, _prepare(prepared['previous'], prepared['source'])),
            'Prepared Memory differs from verified sources')


def _read(path):
    # Immutable objects remain dependencies until the enclosing operation ends.
    # HEAD itself is mutable during our own atomic publication.
    active = memory_operation.current(current())
    if active is not None and path.parent.name in ('commits', 'sources'):
        active.watch_file(path)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    try:
        data = path.read_bytes()
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs)
        require(data == _bytes(value), f'Noncanonical Memory record: {path}')
        return value, data
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f'Missing or invalid Memory record: {path}') from exc


def _read_head(root):
    path = root / 'HEAD.json'
    if not path.exists():
        # Initialize HEAD before writing any immutable objects. Its later loss
        # must not silently turn a populated store into empty history.
        require(not any(p for folder in ('commits', 'sources') for p in (root / folder).glob('*.json')),
                'Missing HEAD in populated Memory store')
        return None
    value, _ = _read(path)
    fields(value, ('format', 'head'), 'Memory HEAD')
    require(value['format'] == HEAD_FORMAT, 'Unknown Memory HEAD format')
    if value['head'] is not None: _head_parts(value['head'])
    return value['head']


def _chain(root, head):
    chain, cursor = [], head
    while cursor is not None:
        sequence, _ = _head_parts(cursor)
        record, _ = _read(root / 'commits' / f'{cursor}.json')
        fields(record, ('format', 'sequence', 'previous_head', 'source', *_DERIVED), 'Memory commit')
        require(record['format'] == FORMAT and type(record['sequence']) is int and
                record['sequence'] == sequence, 'Invalid Memory commit format/sequence')
        previous = record['previous_head']
        require((previous is None and sequence == 1) or
                (previous is not None and _head_parts(previous)[0] == sequence - 1), 'Broken Memory commit chain')
        chain.append((cursor, record))
        cursor = previous
    return list(reversed(chain))


def _states(root, chain):
    states = [_empty()]
    for head, commit in chain:
        require(commit['source'] == head, 'Memory source identity differs')
        state = {'head': head,
                 'memory': {'rounds': states[-1]['memory']['rounds'] + [commit['round']]},
                 'selection': commit['selection'],
                 'selected_execution_source': commit['selected_execution_source']}
        _validate_state(state)
        retained = [u['id'] for u in commit['round']['source_updates'] if u['gate_decision'] == 'Retain']
        require(state['selection']['selected_update_ids'] == retained,
                'Selected IDs differ from committed Retain decisions')
        states.append(state)
    return states


def load_memory(directory, head=None):
    """Read a verified published prefix. No writes, model calls or automatic repair.

    A supplied head must be an ancestor of current HEAD, never an orphan file.
    Committed records are checked structurally; historical Actor sources are not reopened.
    """
    root = Path(directory)
    with current().memory_operation():
        chain = _chain(root, _read_head(root))
        if head is not None:
            _head_parts(head)
            positions = [index for index, (cid, _) in enumerate(chain) if cid == head]
            require(bool(positions), 'Requested Memory head is not published history')
            chain = chain[:positions[0] + 1]
        return deepcopy(_states(root, chain)[-1])


def _fsync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def _freeze(path, data):
    if path.exists():
        require(path.read_bytes() == data, f'Immutable Memory object differs: {path}')
    else:
        _atomic_write(path, data)


@contextmanager
def _writer(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.writer.lock').open('a+b') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _publish_head(root, head):
    _atomic_write(root / 'HEAD.json', _bytes({'format': HEAD_FORMAT, 'head': head}))


def commit_memory(directory, prepared, *, expected_head):
    """Publish one round, returning its state (also for an older identical retry).

    Retrying an older round never rewinds HEAD; call load_memory for the latest
    state. A stale new proposal is rejected. Unpublished immutable files may be
    reused by an identical retry, but are never auto-promoted by load_memory.
    """
    prepared = deepcopy(prepared)
    with current().memory_operation():
        _validate_prepared(prepared)
    require(_same(expected_head, prepared['previous']['head']), 'Expected head differs from prepared history')
    root = Path(directory)
    with _writer(root), current().memory_operation() as session:
        current_head = _read_head(root)
        chain = _chain(root, current_head)
        states = _states(root, chain)
        previous = prepared['previous']
        index = 0 if previous['head'] is None else _head_parts(previous['head'])[0]
        require(index < len(states) and _same(previous, states[index]), 'Prepared prefix is not committed history')
        with current().memory_operation():
            _validate_prepared(prepared)
        source_data = _bytes(prepared['source'])
        new_head = f'{index + 1:06d}'
        commit = {'format': FORMAT, 'sequence': index + 1, 'previous_head': expected_head,
                  'source': new_head, **{key: prepared[key] for key in _DERIVED}}
        data = _bytes(commit)
        for position, (cid, existing) in enumerate(chain, 1):
            if existing['round']['round_id'] == prepared['round']['round_id']:
                require(cid == new_head and _same(existing, commit) and
                        (root / 'sources' / f'{cid}.json').read_bytes() == source_data,
                        'Round already committed with different content')
                return deepcopy(states[position])
        require(current_head == expected_head, 'Stale Memory head; cannot append a new round')
        if not (root / 'HEAD.json').exists(): _publish_head(root, None)
        _freeze(root / 'sources' / f'{new_head}.json', source_data)
        _freeze(root / 'commits' / f'{new_head}.json', data)
        # Read and revalidate the exact staged files before the only publish step.
        staged_source, staged_bytes = _read(root / 'sources' / f'{new_head}.json')
        require(staged_bytes == source_data and _same(staged_source, prepared['source']),
                'Staged Memory source differs')
        staged_commit, staged_data = _read(root / 'commits' / f'{new_head}.json')
        require(staged_data == data and _same(staged_commit, commit), 'Staged Memory commit differs')
        staged_chain = _chain(root, new_head)
        state = _states(root, staged_chain)[-1]
        session.verify()
        _publish_head(root, new_head)
        return deepcopy(state)
