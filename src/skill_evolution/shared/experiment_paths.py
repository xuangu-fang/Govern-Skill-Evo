"""Locate historical evidence at its canonical location without symlinks.

Only explicitly mapped repository paths move. Paths outside this checkout are
unchanged. This never substitutes archived bytes for reads.
"""
from functools import lru_cache
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _relocations():
    mapping = json.loads((ROOT / 'experiments/methods/canonical-paths.json').read_text())
    return {row['old']: row['new'] for row in mapping['relocations']}


def resolve_experiment_path(value):
    """Return the current filesystem location; leave the input identity intact."""
    path = Path(value)
    path = Path(os.path.abspath(path if path.is_absolute() else ROOT / path))
    try:
        name = path.relative_to(ROOT).as_posix()
    except ValueError:
        return path
    mapping = _relocations()
    prefix = name
    while prefix:
        if prefix in mapping:
            return ROOT / (mapping[prefix] + name[len(prefix):])
        prefix = prefix.rpartition('/')[0]
    return path


def resolve_artifact_path(value):
    """Resolve repository evidence paths; preserve ordinary caller-relative paths."""
    path = Path(value)
    if path.is_absolute() or (path.parts and path.parts[0] in
                             ('artifacts', 'experiments', 'benchmarks', 'docs')):
        return resolve_experiment_path(path)
    return path


def method_artifact_root(run_id, *, root=ROOT):
    """Keep seed variants and reused controllers under the run's own version."""
    match = re.fullmatch(r'autonomous_gse_(v\d{2})(?:_[A-Za-z0-9_-]+)?', run_id)
    if not match:
        raise ValueError('Expected an Autonomous GSE campaign ID')
    return Path(root) / 'artifacts/methods' / match[1] / run_id
