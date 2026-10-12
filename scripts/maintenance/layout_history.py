"""Follow later path migrations when checking earlier, immutable receipts."""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def latest():
    path = ROOT / 'experiments/methods/canonical-migration.json'
    return json.loads(path.read_text()) if path.exists() else {'files': [], 'removed_links': []}


@lru_cache(maxsize=1)
def relocations():
    return {row['old']: row['new'] for row in json.loads((ROOT / 'experiments/methods/canonical-paths.json').read_text())['relocations']}


def current(name):
    prefix = name
    mapping = relocations()
    while prefix:
        if prefix in mapping:
            return mapping[prefix] + name[len(prefix):]
        prefix = prefix.rpartition('/')[0]
    return name


@lru_cache(maxsize=1)
def digest_changes():
    records = [latest()]
    code_layout = ROOT / 'docs/repository/code-migration.json'
    if code_layout.exists():
        records.append(json.loads(code_layout.read_text()))
    final_layout = ROOT / 'docs/repository/final-migration.json'
    if final_layout.exists():
        records.append(json.loads(final_layout.read_text()))
    return [{(current(row['new']), row['before_sha256']): row['after_sha256']
             for row in record['files']} for record in records]


def expected_digest(name, expected):
    for changes in digest_changes():
        expected = changes.get((current(name), expected), expected)
    return expected


def retired(name):
    return any(name == row['entry'] or name.startswith(row['entry'] + '/')
               for row in latest()['removed_links'])


@lru_cache(maxsize=1)
def deleted_names():
    path = ROOT / 'docs/repository/final-migration.json'
    return set(json.loads(path.read_text()).get('deleted_files', {})) if path.exists() else set()


def deleted(name):
    return name in deleted_names() or current(name) in deleted_names()
