"""Validated Memory snapshots shared only across one publication operation.

The v27 archive format and pure contracts remain unchanged. A cold load still
validates the complete lineage. Commit reuses that lineage under the same lock
and performs only its checked state transition; no persistent cache is trusted.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import re

from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v27.contracts.replay import validate_payload
from src.skill_evolution.v27.storage import write_record
from . import validation
from .benchmarks.searchqa import protocol as p

_ACTIVE = ContextVar('v28_memory_operation', default=None)
CONTRACT = memory.MULTI_KNOWLEDGE_CONTRACT


def current(method):
    session = _ACTIVE.get()
    return session if session is not None and session.method is method else None


class MemoryOperation:
    def __init__(self, method, checks):
        self.method, self.checks = method, checks
        self.snapshots = {}

    def remember(self, root, state, entries, contexts, view):
        self.snapshots[Path(root).resolve()] = (deepcopy(state), entries, contexts, deepcopy(view))

    def watch(self, root):
        self.checks.watch_tree(root / 'archive', source='memory')
        if (root / 'active.json').exists():
            self.checks.watch_file(root / 'active.json')

    def load(self, directory):
        root = Path(directory).resolve()
        if root not in self.snapshots:
            self.watch(root)
            return self.method._load_memory(root)
        state, _, _, view = self.snapshots[root]
        p.require(memory._state(root) == state, 'Cached Active snapshot changed')
        return deepcopy(view)

    def adopt(self, source, dest):
        """Reuse a prepared copy only after exact prefix and index comparison."""
        source, dest = Path(source).resolve(), Path(dest).resolve()
        snapshot = self.snapshots[source]
        if memory._state(dest) != snapshot[0]:
            return self.load(dest)  # A previous commit may already have completed.
        for cid in snapshot[0]['commits']:
            old, new = source / 'archive' / f'{cid}.json', dest / 'archive' / f'{cid}.json'
            self.checks.watch_file(new)
            p.require(self.checks.files[new][1] == self.checks.files[old][1], 'Prepared Memory archive differs')
        self.watch(dest)
        self.remember(dest, *snapshot)
        return deepcopy(snapshot[3])

    def linked(self, source, dest):
        """Verify the linked source and refresh inode metadata for v28 only."""
        source, dest = Path(source).absolute(), Path(dest).absolute()
        expected = self.checks.files[source]
        actual, _ = self.checks._file(source)
        if not getattr(self.method.actor_adapter, 'verify_hashes', True):
            p.require(actual[1] == expected[1] and source.samefile(dest),
                      'Memory source changed while linking')
            return  # Byte-only fingerprints need no ctime refresh after linking.
        p.require(actual[1] == expected[1] and actual[0][:4] == expected[0][:4]
                  and source.samefile(dest), 'Memory source changed while linking')
        # Existing watched aliases of this inode receive the same metadata update.
        for path, old in list(self.checks.files.items()):
            if old[0][:2] == expected[0][:2]:
                p.require(old == expected, 'Watched Memory alias changed')
                self.checks.files[path] = actual

    def verify(self):
        for root, (state, _, _, _) in self.snapshots.items():
            p.require(memory._state(root) == state, 'Active snapshot changed during publication')
        self.method.actor_adapter._preflight()
        self.checks.verify()

    def written(self, path, value):
        """Register a checked receipt, never accept arbitrary disk state."""
        path = Path(path).absolute()
        fingerprint, data = self.checks._file(path)
        p.require(p.equal(json.loads(data), value), 'Written Memory receipt differs')
        self.checks.files[path] = fingerprint

    def commit(self, directory, *, context_id, context, result):
        p.require(isinstance(context_id, str) and re.fullmatch(r'[A-Za-z0-9_-]+', context_id), 'Unsafe context ID')
        validate_payload(context['payload'], memory_contract=CONTRACT)
        p.require(isinstance(context.get('execution_context'), dict) and bool(context['execution_context']), 'Missing context')
        memory.validate_entries(result, context['payload'], memory_contract=CONTRACT)
        root = Path(directory).resolve()
        # Match v27's interrupted immutable-file then atomic-index protocol.
        (root / 'archive').mkdir(parents=True, exist_ok=True)
        with (root / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.load(root)
            state, entries, contexts, view = self.snapshots[root]
            self.verify()
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
            new_archive = {**entries, **{entry['id']: memory._normalize_entry(entry, CONTRACT) for entry in new_entries}}
            new_contexts = {**contexts, context_id: commit['context']}
            new_view = memory._view(new_archive, new_contexts, active, CONTRACT)
            # Finish dependency checks before any durable commit transition.
            self.verify()
            members = self.checks.trees[(root / 'archive', 'memory')]
            if path.exists():
                p.require(memory._read(path) == commit, 'Interrupted commit differs from recovery request')
            else:
                write_record(path, commit)
            self.written(path, commit)
            self.checks.trees[(root / 'archive', 'memory')] = tuple(sorted(set(members or ()) | {path}))
            write_record(root / 'active.json', new_state)
            self.written(root / 'active.json', new_state)
            self.remember(root, new_state, new_archive, new_contexts, new_view)
            return deepcopy(commit)


@contextmanager
def operation(method):
    session = current(method)
    if session is not None:
        yield session
        return
    with validation.operation(method.actor_adapter) as checks:
        session = MemoryOperation(method, checks)
        token = _ACTIVE.set(session)
        try:
            yield session
            session.verify()
        finally:
            _ACTIVE.reset(token)
