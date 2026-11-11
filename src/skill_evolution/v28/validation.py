"""Operation-local evidence validation; never a persistent trust cache.

Only completed archives may be watched. Content and directory membership
are rechecked before the caller receives a successful result. v28 also checks
file metadata; v28.1 compares bytes without treating metadata as evidence changes.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
from pathlib import Path

_ACTIVE = ContextVar('v28_validation_operation', default=None)


def current(adapter=None):
    state = _ACTIVE.get()
    return state if state is not None and (adapter is None or state.adapter is adapter) else None


class ValidationOperation:
    def __init__(self, adapter):
        self.adapter = adapter
        self.files, self.trees = {}, {}
        self.identities, self.templates, self.batches, self.records = {}, {}, {}, {}

    def _file(self, path):
        if not getattr(self.adapter, 'verify_hashes', True):
            content = path.read_bytes()
            if path.read_bytes() != content:
                raise ValueError(f'Validation dependency changed while reading: {path}')
            # Preserve the fingerprint shape used by Memory, without a metadata gate.
            return (None, content), content
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
        def identity(s):
            return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after):
            raise ValueError(f'Validation dependency changed while reading: {path}')
        value = hashlib.sha256(content).hexdigest()
        return (identity(after), value), content

    def watch_file(self, path):
        path = Path(path).absolute()
        if path not in self.files:
            self.files[path] = self._file(path)[0]

    @staticmethod
    def _members(root, source):
        if not root.exists():
            return None
        paths = root.rglob('*')
        if source == 'memory':
            paths = root.glob('*.json')  # Pending .tmp files are not committed dependencies.
        return tuple(sorted(paths))

    def watch_tree(self, root, *, source=False):
        root = Path(root).absolute()
        key = (root, source)
        if key not in self.trees:
            members = self._members(root, source)
            self.trees[key] = members
            for path in members or ():
                if path.is_file():
                    self.watch_file(path)

    def template(self, path):
        path = Path(path).absolute()
        if path not in self.templates:
            # A local render snapshot, not a source/Prompt integrity lock.
            self.templates[path] = path.read_text()
        return self.templates[path]

    def verify(self):
        for (root, source), members in self.trees.items():
            if self._members(root, source) != members:
                raise ValueError(f'Validation dependency membership changed: {root}')
        for path, fingerprint in self.files.items():
            if self._file(path)[0] != fingerprint:
                raise ValueError(f'Validation dependency changed: {path}')


@contextmanager
def operation(adapter):
    """Nest only for the same adapter; discard every cache on exit or failure."""
    active = current(adapter)
    if active is not None:
        yield active
        return
    state = ValidationOperation(adapter)
    dataset_root = getattr(adapter.dataset, 'root', None)
    if dataset_root is not None and getattr(adapter, 'verify_hashes', True):
        state.watch_tree(dataset_root)
    token = _ACTIVE.set(state)
    try:
        adapter._preflight()
        yield state
        # Also recheck mutable bound data/config, independently of file hashes.
        adapter._preflight()
        state.verify()
    finally:
        _ACTIVE.reset(token)
