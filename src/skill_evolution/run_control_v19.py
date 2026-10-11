"""Scoped recovery for the unified CLI. Never retry a completed response."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import uuid

from .evolution_replay_v19 import _load, _save, _file_digest
from .memory_store_v19 import require

_RECOVERY = ContextVar('v19_call_recovery', default=None)
RETRYABLE = {'APITimeoutError', 'APIConnectionError', 'TimeoutError', 'ConnectionError'}


@contextmanager
def recovery_scope(output, enabled):
    token = _RECOVERY.set(Path(output).resolve() if enabled else None)
    try:
        yield
    finally:
        _RECOVERY.reset(token)


def recover_call(directory, request):
    """Called after stage binding checks, immediately before a missing response."""
    root = _RECOVERY.get()
    if root is None:
        return
    directory = Path(directory).resolve()
    require(directory.is_relative_to(root), 'recovery call outside campaign')
    require(_load(directory / 'request.json') == request, 'request changed; cannot recover')
    require(not (directory / 'response.json').exists(),
            'response exists without completion marker; inspect checkpoint instead of resending')
    error = _load(directory / 'failure.json') if (directory / 'failure.json').exists() else None
    require(error is None or error.get('error_type') in RETRYABLE,
            'non-network failure requires inspection, not automatic retry')
    archive = root / 'recovery' / uuid.uuid4().hex
    archive.mkdir(parents=True)
    receipt = {'schema_version': 'call_recovery_v19.1',
        'original_path': str(directory.relative_to(root)),
        'reason': error['error_type'] if error else 'INTERRUPTED_WITHOUT_RESPONSE',
        'files': {str(p.relative_to(directory)): _file_digest(p)
                  for p in directory.rglob('*') if p.is_file()}}
    _save(archive / 'receipt.json', receipt)
    directory.rename(archive / 'call')
