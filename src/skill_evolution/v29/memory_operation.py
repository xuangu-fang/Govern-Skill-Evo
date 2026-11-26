"""Reuse current batches and committed Memory views; no historical byte audit.

The v27 durable format, revision semantics and atomic Active switch are unchanged.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import fcntl
from pathlib import Path
import re

from src.skill_evolution.v27.contracts import memory
from .benchmarks.docvqa import protocol as p, evidence
from . import replay

CONTRACT = memory.MULTI_KNOWLEDGE_CONTRACT
_ACTIVE = ContextVar('v29_memory_operation', default=None)


def current(method):
    operation = _ACTIVE.get()
    return operation if operation is not None and operation.method is method else None


class MemoryOperation:
    def __init__(self, method):
        self.method = method
        self.snapshots, self.batches, self.projections = {}, {}, {}

    def batch(self, directory):
        root = Path(directory).resolve()
        if root not in self.batches:
            self.batches[root] = self.method.actor_adapter.read_batch(root)
        return deepcopy(self.batches[root])

    def load(self, directory):
        """Read committed entries and references, without rerunning old evidence."""
        root = Path(directory).resolve()
        if root not in self.snapshots:
            state = memory._state(root)
            entries, contexts, active = {}, {}, []
            for cid in state['commits']:
                p.require(isinstance(cid, str) and re.fullmatch(r'[A-Za-z0-9_-]+', cid), 'Invalid Memory context ID')
                commit = memory._read(root / 'archive' / f'{cid}.json')
                p.require(commit['memory_contract'] == CONTRACT and commit['context_id'] == cid and
                          commit['before_active_ids'] == active, 'Broken Memory commit lineage')
                contexts[cid] = commit['context']
                for entry in commit['entries']:
                    p.fields(entry, ('id', 'context_id', 'revises', 'knowledge'), 'Archived entry')
                    mid = entry['id']
                    p.require(isinstance(mid, str) and re.fullmatch(r'M[1-9]\d*', mid) and
                              mid not in entries and entry['context_id'] == cid, 'Invalid archived Memory identity')
                    p.require(isinstance(entry['revises'], list) and
                              set(entry['revises']) <= set(active), 'Invalid archived revision')
                    entries[mid] = entry
                revised = [ref for entry in commit['entries'] for ref in entry['revises']]
                p.require(len(revised) == len(set(revised)), 'Repeated archived revision')
                active = [mid for mid in active if mid not in revised] + [entry['id'] for entry in commit['entries']]
                p.require(active == commit['after_active_ids'], 'Broken Active transition')
            p.require(active == state['active_ids'], 'Active index differs from committed entries')
            view = memory._view(entries, contexts, active, CONTRACT)
            self.snapshots[root] = (deepcopy(state), entries, contexts, view)
        state, _, _, view = self.snapshots[root]
        p.require(memory._state(root) == state, 'Active index changed during Memory operation')
        return deepcopy(view)

    def commit(self, directory, *, context_id, context, result):
        p.require(isinstance(context_id, str) and re.fullmatch(r'[A-Za-z0-9_-]+', context_id), 'Unsafe context ID')
        root = Path(directory).resolve()
        (root / 'archive').mkdir(parents=True, exist_ok=True)
        with (root / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.load(root)
            evidence.validate_bundle(context)
            replay.validate_result(result, context['payload'])
            state, entries, contexts, view = self.snapshots[root]
            p.require(memory._state(root) == state, 'Active index changed before commit')
            path = root / 'archive' / f'{context_id}.json'
            if context_id in state['commits']:
                old = memory._read(path)
                p.require(old.get('memory_contract', memory.LEGACY_CONTRACT) == CONTRACT and
                          old['context'] == context and old['result'] == result, 'Committed round differs')
                return deepcopy(old)
            pending = {q.stem for q in (root / 'archive').glob('*.json')} - set(state['commits'])
            p.require(pending <= {context_id}, 'Recover the pending Memory commit first')
            p.require(context['payload']['memory'] == view, 'Active snapshot changed before commit')
            next_id = max([int(mid[1:]) for mid in entries] or [0]) + 1
            history = memory.validate_memory(context['payload']['memory'], memory_contract=CONTRACT)
            new_entries = [memory._stored_entry(proposal, history, context_id, f'M{next_id + offset}', CONTRACT)
                           for offset, proposal in enumerate(result['entries'])]
            revised = {ref for entry in new_entries for ref in entry['revises']}
            active = [mid for mid in state['active_ids'] if mid not in revised] + [e['id'] for e in new_entries]
            commit = {'context_id': context_id, 'context': deepcopy(context), 'result': deepcopy(result),
                      'before_active_ids': state['active_ids'], 'after_active_ids': active, 'entries': new_entries,
                      'memory_contract': CONTRACT}
            new_state = {'active_ids': active, 'commits': state['commits'] + [context_id]}
            new_entries_by_id = {**entries, **{e['id']: memory._normalize_entry(e, CONTRACT) for e in new_entries}}
            new_contexts = {**contexts, context_id: commit['context']}
            new_view = memory._view(new_entries_by_id, new_contexts, active, CONTRACT)
            p.require(memory._state(root) == state, 'Active index changed before commit')
            if path.exists():
                p.require(memory._read(path) == commit, 'Interrupted commit differs from recovery request')
            else:
                memory.write_record(path, commit)
            memory.write_record(root / 'active.json', new_state)
            self.snapshots[root] = (new_state, new_entries_by_id, new_contexts, new_view)
            return deepcopy(commit)


@contextmanager
def operation(method):
    existing = current(method)
    if existing is not None:
        yield existing
        return
    session = MemoryOperation(method)
    token = _ACTIVE.set(session)
    try:
        yield session
    finally:
        _ACTIVE.reset(token)
