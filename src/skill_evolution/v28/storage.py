"""Atomic JSON receipts and read-only freeze checks, following v27 stages."""
from datetime import datetime, timezone
import json
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(data, encoding='utf-8')
    temporary.replace(path)


def freeze(path, value, *, read_only=False):
    from .benchmarks.searchqa.protocol import equal, require
    path = Path(path)
    if path.exists():
        require(equal(read(path), value), f'Frozen value changed: {path}')
    else:
        require(not read_only, f'Missing frozen value: {path}')
        save(path, value)
