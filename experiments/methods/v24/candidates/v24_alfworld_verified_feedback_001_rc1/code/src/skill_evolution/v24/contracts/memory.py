from src.skill_evolution.v24.benchmark import current as benchmark_current
"""Immutable Memory commits, atomic Active index and lossless referenced sources."""
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import re

from src.skill_evolution.v24.storage import write_record
from .diagnosis import fields, links
from ..facts import require, text

LEGACY_CONTRACT = 'entries_sources'
MULTI_KNOWLEDGE_CONTRACT = 'entries_sources_multi_knowledge_v1'


def _check_contract(memory_contract):
    require(memory_contract in (LEGACY_CONTRACT, MULTI_KNOWLEDGE_CONTRACT), 'Unsupported Memory contract')


def _entry_fields(memory_contract):
    return ('knowledge', 'evidence') if memory_contract == LEGACY_CONTRACT else ('knowledge',)


def entry_evidence(entry, *, memory_contract=LEGACY_CONTRACT):
    """Ordered union for validated entries; retain each Knowledge's own evidence."""
    _check_contract(memory_contract)
    groups = [entry['evidence']] if memory_contract == LEGACY_CONTRACT else [k['evidence'] for k in entry['knowledge']]
    return list(dict.fromkeys(ref for group in groups for ref in group))


def _validate_knowledge(entry, allowed, memory_contract):
    if memory_contract == LEGACY_CONTRACT:
        text(entry['knowledge'], 'knowledge')
        links(entry['evidence'], allowed, 'evidence')
    else:
        require(isinstance(entry['knowledge'], list) and bool(entry['knowledge']), 'knowledge must be a nonempty array')
        for knowledge in entry['knowledge']:
            fields(knowledge, ('text', 'evidence'), 'Knowledge')
            text(knowledge['text'], 'Knowledge text')
            links(knowledge['evidence'], allowed, 'Knowledge evidence')
    refs = entry_evidence(entry, memory_contract=memory_contract)
    require(any(r == 'diff' or r.endswith('/diff') for r in refs) and
            any(r != 'diff' and not r.endswith('/diff') for r in refs),
            'Entry requires actual edit and execution evidence')


def _normalize_entry(entry, source_contract):
    result = deepcopy(entry)
    if source_contract == LEGACY_CONTRACT:
        result['knowledge'] = [{'text': result['knowledge'], 'evidence': result.pop('evidence')}]
    return result


def normalize_memory(memory, *, source_contract):
    """Validate first, then return a detached multi-Knowledge view; never migrate files."""
    validate_memory(memory, memory_contract=source_contract)
    result = deepcopy(memory)
    result['entries'] = [_normalize_entry(e, source_contract) for e in memory['entries']]
    return result


def empty_memory():
    return {"entries": [], "sources": {}}


def run_references(*args, **kwargs):
    return benchmark_current().evidence("contracts.memory.run_references", *args, **kwargs)


def run_menus(*args, **kwargs):
    return benchmark_current().evidence("contracts.memory.run_menus", *args, **kwargs)


def validate_run(*args, **kwargs):
    return benchmark_current().evidence("contracts.memory.validate_run", *args, **kwargs)


def validate_memory(memory, *, memory_contract=LEGACY_CONTRACT):
    """Return resolvable historical fact refs; never infer support from prose."""
    _check_contract(memory_contract)
    fields(memory, ('entries', 'sources'), 'Memory')
    require(isinstance(memory['entries'], list) and isinstance(memory['sources'], dict), 'Invalid Memory collections')
    allowed, ids = set(), set()
    for key, source in memory['sources'].items():
        require(isinstance(key, str) and '/' in key, 'History needs context-qualified references')
        context, local = key.rsplit('/', 1)
        text(context, 'historical context')
        if local == 'diff':
            fields(source, ('parent', 'diff', 'execution_context'), 'Edit source')
            require(source['parent'] is None or isinstance(source['parent'], str), 'Invalid historical Parent')
            text(source['diff'], 'historical diff')
            require(isinstance(source['execution_context'], dict) and bool(source['execution_context']), 'Missing historical execution context')
            allowed.add(key)
        else:
            run = benchmark_current().validate_execution_source(source)
            require(run['ref'] == local, 'Source identity differs')
            require(f'{context}/diff' in memory['sources'], 'Execution source lacks historical edit/context')
            allowed.update(f'{context}/{r}' for r in run_references(run))
    for entry in memory['entries']:
        fields(entry, ('id', *_entry_fields(memory_contract)), 'Active MemoryEntry')
        mid = text(entry['id'], 'Memory ID')
        require(re.fullmatch(r'M[1-9]\d*', mid) and mid not in ids, 'Duplicate or invalid Memory ID')
        ids.add(mid)
        _validate_knowledge(entry, allowed, memory_contract)
    return allowed


def validate_entries(result, payload, *, memory_contract=LEGACY_CONTRACT):
    _check_contract(memory_contract)
    fields(result, ('entries',), 'Replay')
    require(isinstance(result['entries'], list), 'entries must be an array')
    history = validate_memory(payload['memory'], memory_contract=memory_contract)
    allowed = {'diff'} | history
    for run in payload['runs']:
        allowed.update(run_references(run))
    active = {e['id'] for e in payload['memory']['entries']}
    revised = set()
    for entry in result['entries']:
        fields(entry, ('revises', *_entry_fields(memory_contract)), 'Memory proposal')
        require(isinstance(entry['revises'], list), 'revises must be an array')
        if entry['revises']:
            links(entry['revises'], active, 'revises')
        require(not revised.intersection(entry['revises']), 'Repeated revision target')
        revised.update(entry['revises'])
        _validate_knowledge(entry, allowed, memory_contract)
    return result


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _state(root):
    path = root / 'active.json'
    state = _read(path) if path.exists() else {'active_ids': [], 'commits': []}
    fields(state, ('active_ids', 'commits'), 'Active index')
    require(all(isinstance(state[k], list) and len(state[k]) == len(set(state[k])) for k in state), 'Invalid Active index')
    return state


def _stored_entry(proposal, history, cid, mid, memory_contract):
    stored = {**deepcopy(proposal), 'id': mid, 'context_id': cid}
    groups = [stored] if memory_contract == LEGACY_CONTRACT else stored['knowledge']
    for group in groups:
        group['evidence'] = [r if r in history else f'{cid}/{r}' for r in group['evidence']]
    return stored


def _archive(root, state, *, memory_contract=LEGACY_CONTRACT):
    _check_contract(memory_contract)
    entries, contexts, active = {}, {}, []
    for cid in state['commits']:
        require(re.fullmatch(r'[A-Za-z0-9_-]+', cid), 'Invalid context ID')
        commit = _read(root / 'archive' / f'{cid}.json')
        version = commit.get('memory_contract', LEGACY_CONTRACT)
        _check_contract(version)
        require(memory_contract == MULTI_KNOWLEDGE_CONTRACT or version == LEGACY_CONTRACT,
                'Legacy Memory reader cannot read multi-Knowledge commits')
        require(commit['context_id'] == cid and commit['before_active_ids'] == active, 'Broken commit lineage')
        validate_entries(commit['result'], commit['context']['payload'], memory_contract=version)
        history = validate_memory(commit['context']['payload']['memory'], memory_contract=version)
        if memory_contract == MULTI_KNOWLEDGE_CONTRACT:
            from .replay import validate_payload
            validate_payload(commit['context']['payload'], memory_contract=version)
            require(isinstance(commit['context'].get('execution_context'), dict) and
                    bool(commit['context']['execution_context']), 'Missing context')
            snapshot = normalize_memory(commit['context']['payload']['memory'], source_contract=version)
            require(snapshot == _view(entries, contexts, active, memory_contract), 'Archived Active snapshot differs')
        require(len(commit['entries']) == len(commit['result']['entries']), 'Archived proposal count differs')
        for stored, proposal in zip(commit['entries'], commit['result']['entries']):
            fields(stored, ('id', 'context_id', 'revises', *_entry_fields(version)), 'Archived entry')
            expected = _stored_entry(proposal, history, cid, stored['id'], version)
            require(isinstance(stored['id'], str) and re.fullmatch(r'M[1-9]\d*', stored['id']), 'Invalid archived Memory ID')
            require(stored == expected, 'Archived entry differs from validated proposal')
        contexts[cid] = commit['context']
        for e in commit['entries']:
            require(e['id'] not in entries and e['context_id'] == cid, 'Duplicate archived identity')
            entries[e['id']] = _normalize_entry(e, version) if memory_contract == MULTI_KNOWLEDGE_CONTRACT else e
        revised = {r for e in commit['entries'] for r in e['revises']}
        require(revised <= set(active), 'Archived revision target is not active')
        active = [mid for mid in active if mid not in revised] + [e['id'] for e in commit['entries']]
        require(active == commit['after_active_ids'], 'Broken Active transition')
    require(active == state['active_ids'], 'Active index differs from immutable commits')
    return entries, contexts


def _view(*args, **kwargs):
    return benchmark_current().evidence("contracts.memory._view", *args, **kwargs)


def load_memory(directory, *, memory_contract=LEGACY_CONTRACT):
    """One atomic index snapshot; opt-in new readers normalize validated old commits."""
    root = Path(directory)
    state = _state(root)
    archive, contexts = _archive(root, state, memory_contract=memory_contract)
    return _view(archive, contexts, state['active_ids'], memory_contract)


def commit_memory(directory, *, context_id, context, result, memory_contract=LEGACY_CONTRACT):
    """Immutable commit file then atomic index switch, with crash-safe exact replay.

    Uncommitted files are never exposed as Active. An interrupted commit must be
    recovered with identical input before a different commit can be submitted.
    The context ID includes experiment identity, e.g. v23_replay_memory_001_R1.
    """
    _check_contract(memory_contract)
    require(isinstance(context_id, str) and re.fullmatch(r'[A-Za-z0-9_-]+', context_id), 'Unsafe context ID')
    from .replay import validate_payload
    validate_payload(context['payload'], memory_contract=memory_contract)
    require(isinstance(context.get('execution_context'), dict) and bool(context['execution_context']), 'Missing context')
    validate_entries(result, context['payload'], memory_contract=memory_contract)
    root = Path(directory)
    (root / 'archive').mkdir(parents=True, exist_ok=True)
    with (root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = _state(root)
        entries, _ = _archive(root, state, memory_contract=memory_contract)
        path = root / 'archive' / f'{context_id}.json'
        if context_id in state['commits']:
            old = _read(path)
            require(old.get('memory_contract', LEGACY_CONTRACT) == memory_contract and
                    old['context'] == context and old['result'] == result, 'Committed round differs')
            return deepcopy(old)
        pending = {p.stem for p in (root / 'archive').glob('*.json')} - set(state['commits'])
        require(pending <= {context_id}, 'Recover the pending Memory commit first')
        require(context['payload']['memory'] == load_memory(root, memory_contract=memory_contract),
                'Active snapshot changed before commit')
        next_id = max([int(mid[1:]) for mid in entries] or [0]) + 1
        new_entries = []
        history = validate_memory(context['payload']['memory'], memory_contract=memory_contract)
        for offset, proposal in enumerate(result['entries']):
            new_entries.append(_stored_entry(proposal, history, context_id, f'M{next_id + offset}', memory_contract))
        revised = {r for e in new_entries for r in e['revises']}
        active = [mid for mid in state['active_ids'] if mid not in revised] + [e['id'] for e in new_entries]
        commit = {'context_id': context_id, 'context': deepcopy(context), 'result': deepcopy(result),
                  'before_active_ids': state['active_ids'], 'after_active_ids': active, 'entries': new_entries}
        if memory_contract == MULTI_KNOWLEDGE_CONTRACT:
            commit['memory_contract'] = memory_contract
        if path.exists():
            require(_read(path) == commit, 'Interrupted commit differs from recovery request')
        else:
            write_record(path, commit)
        write_record(root / 'active.json', {'active_ids': active, 'commits': state['commits'] + [context_id]})
        return commit
