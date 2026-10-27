"""Resolve curated V23.4 evidence and separately stored local runtime data."""
from pathlib import Path

from experiments.methods.v23_3.archive_io import (
    archive_glob as legacy_glob,
    resolve as legacy_resolve,
)

EXPERIMENTS = Path(__file__).resolve().parent
ARCHIVE = EXPERIMENTS.parents[2] / 'artifacts/methods/v23_4'


def source_path(path):
    path = Path(path).absolute()
    return EXPERIMENTS / path.relative_to(ARCHIVE) if path.is_relative_to(ARCHIVE) else path


def raw_path(path):
    path = source_path(path)
    return ARCHIVE / path.relative_to(EXPERIMENTS) if path.is_relative_to(EXPERIMENTS) else path


def resolve(path):
    """Read either namespace, preferring retained evidence at its source location."""
    path = Path(path)
    source = source_path(path)
    if not source.is_relative_to(EXPERIMENTS):
        return legacy_resolve(path)
    if source.exists():
        return source
    archived = raw_path(source)
    return archived if archived.exists() else path


def archive_glob(path, pattern, *, recursive=False):
    """Enumerate split folders once; retained source files take precedence."""
    source = source_path(path)
    if not source.is_relative_to(EXPERIMENTS):
        return legacy_glob(path, pattern, recursive=recursive)
    files = {}
    for root in (raw_path(source), source):
        matches = root.rglob(pattern) if recursive else root.glob(pattern)
        for file in matches:
            files[file.relative_to(root)] = file
    return iter(files[key] for key in sorted(files))


def runtime_root(directory):
    """Continue migrated studies in artifacts; leave unmigrated studies in place."""
    archived = raw_path(directory)
    return archived if archived.is_dir() else Path(directory)
