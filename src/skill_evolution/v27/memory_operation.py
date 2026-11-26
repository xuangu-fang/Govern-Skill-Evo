"""Validated Memory history reused only within one controlled publication.

Locally adapted from v28/v29. File bytes and Active state are rechecked, not
trusted across calls. LMB evidence is self-contained; no Actor cache is needed.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import json
from pathlib import Path

from .benchmark import current as benchmark_current
from .contracts import memory
from .facts import require

_ACTIVE = ContextVar('v27_memory_operation', default=None)


def current(memory_contract):
    session = _ACTIVE.get()
    return session if (session is not None and session.adapter is benchmark_current()
                       and session.contract == memory_contract) else None


class MemoryOperation:
    def __init__(self, memory_contract):
        self.adapter, self.contract = benchmark_current(), memory_contract
        self.snapshots, self.files, self.trees = {}, {}, {}

    @staticmethod
    def members(root):
        # Atomic-write .tmp files are not published commits.
        return tuple(sorted(root.glob('*.json')))

    def watch_file(self, path):
        path = Path(path).resolve()
        if path not in self.files:
            self.files[path] = path.read_bytes()

    def read_commit(self, path):
        self.watch_file(path)
        return json.loads(self.files[Path(path).resolve()])

    def watch_archive(self, root):
        if root not in self.trees:
            self.trees[root] = self.members(root)
            for path in self.trees[root]:
                self.watch_file(path)

    def load(self, directory):
        root = Path(directory).resolve()
        if root not in self.snapshots:
            self.watch_archive(root / 'archive')
            state = memory._state(root)
            entries, contexts = memory._archive(root, state, memory_contract=self.contract,
                                                read_commit=self.read_commit)
            view = memory._view(entries, contexts, state['active_ids'], self.contract)
            self.snapshots[root] = (deepcopy(state), entries, contexts, view)
        state, _, _, view = self.snapshots[root]
        require(memory._state(root) == state, 'Active snapshot changed during Memory operation')
        return deepcopy(view)

    def adopt(self, source, dest):
        """Reuse an exact copied prefix; an already advanced target loads cold."""
        source, dest = Path(source).resolve(), Path(dest).resolve()
        snapshot = self.snapshots[source]
        if memory._state(dest) != snapshot[0]:
            return self.load(dest)
        self.watch_archive(dest / 'archive')
        for cid in snapshot[0]['commits']:
            old, new = source / 'archive' / f'{cid}.json', dest / 'archive' / f'{cid}.json'
            require(new.resolve() in self.files and self.files[new.resolve()] == self.files[old.resolve()],
                    'Prepared Memory archive differs')
        self.snapshots[dest] = deepcopy(snapshot)
        return deepcopy(snapshot[3])

    def written(self, path, value):
        """Accept only the exact receipt just written by this operation."""
        path = Path(path).resolve()
        data = path.read_bytes()
        require(json.loads(data) == value, 'Written Memory receipt differs')
        self.files[path] = data

    def committed(self, root, state, entries, contexts, view, path, commit):
        self.written(path, commit)
        archive = root / 'archive'
        self.trees[archive] = tuple(sorted(set(self.trees[archive]) | {path}))
        self.written(root / 'active.json', state)
        self.snapshots[root] = (deepcopy(state), entries, contexts, deepcopy(view))

    def verify(self):
        require(benchmark_current() is self.adapter, 'Memory benchmark binding changed')
        for root, members in self.trees.items():
            require(self.members(root) == members, 'Memory archive membership changed')
        for path, data in self.files.items():
            require(path.read_bytes() == data, f'Memory dependency changed: {path}')
        for root, (state, _, _, _) in self.snapshots.items():
            require(memory._state(root) == state, 'Active snapshot changed during Memory operation')


@contextmanager
def operation(memory_contract):
    memory._check_contract(memory_contract)
    existing = current(memory_contract)
    if existing is not None:
        yield existing
        return
    session = MemoryOperation(memory_contract)
    token = _ACTIVE.set(session)
    try:
        yield session
        session.verify()
    finally:
        _ACTIVE.reset(token)
