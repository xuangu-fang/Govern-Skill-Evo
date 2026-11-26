"""Expose original archive bytes to offline validators, including frozen Python readers."""
from contextlib import contextmanager, ExitStack
from contextvars import ContextVar
import io
import os
from pathlib import Path
from threading import RLock

from experiments.benchmark_record_refs.restore import ARCHIVE, ROOT, SELECT, Archive


_active = ContextVar('offline_record_archive', default=None)
_bindings = RLock()


class EvidencePath(type(Path())):
    """A pathlib path whose read-only opens see verified, expanded records."""

    def open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        archive = _active.get()
        if archive is not None and mode in ('r', 'rt', 'rb'):
            absolute = Path(os.path.abspath(self))
            if absolute.is_relative_to(ROOT):
                relative = absolute.relative_to(ROOT)
                if relative.parts[:1] in (('artifacts',), ('experiments',), ('output',), ('outputs',)):
                    key = archive.archive_key(relative)
                    source = archive.source_path(key)
                    row = archive.db.execute(SELECT + ' WHERE r.path=?', (key,)).fetchone()
                    if row is not None:
                        with source.open('rb') as stream:
                            data = stream.read()
                        original = io.BytesIO()
                        archive.verify_bytes(row, data, original)
                        original.seek(0)
                        if mode == 'rb':
                            return original
                        return io.TextIOWrapper(original, encoding=encoding, errors=errors, newline=newline)
                    if source != absolute:
                        return source.open(mode, buffering, encoding, errors, newline)
        return super().open(mode, buffering, encoding, errors, newline)


@contextmanager
def offline_records(benchmark, *readers):
    """Bind the named legacy modules' Path constructors and repository roots for offline reads.

    Those modules are hashed into historical training contracts. Their validation
    code still sees the original paths, prompts, HTTP bodies and publication hashes.
    Other threads use ordinary file reads through the context-local default.
    """
    if not (ARCHIVE / benchmark / 'manifest.sqlite3').is_file():
        yield Path
        return
    with _bindings, ExitStack() as stack:
        archive = Archive(benchmark)
        stack.callback(archive.close)
        token = _active.set(archive)
        stack.callback(_active.reset, token)
        for module in readers:
            stack.callback(setattr, module, 'Path', module.Path)
            module.Path = EvidencePath
            if isinstance(getattr(module, 'ROOT', None), Path):
                stack.callback(setattr, module, 'ROOT', module.ROOT)
                module.ROOT = EvidencePath(module.ROOT)
        yield EvidencePath
