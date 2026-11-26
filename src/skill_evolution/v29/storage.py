"""Atomic JSON records for resumable local Actor execution."""
from datetime import datetime, timezone
import json
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def freeze(path, value, *, read_only=False):
    path = Path(path)
    if path.exists():
        if read(path) != value:
            raise ValueError(f'Existing record differs: {path}')
    elif read_only:
        raise ValueError(f'Missing record: {path}')
    else:
        save(path, value)
