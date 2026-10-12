"""Verify direct paths, retired links, and the recorded path-only migration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile
from layout_history import current, expected_digest, deleted

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    receipt = json.loads((ROOT / 'experiments/methods/canonical-migration.json').read_text())
    errors = []
    archive_path = ROOT / receipt['snapshot']
    if digest(archive_path) != receipt['snapshot_sha256']:
        raise ValueError('Canonical-path snapshot checksum mismatch')
    with zipfile.ZipFile(archive_path) as archive:
        for row in receipt['files']:
            if hashlib.sha256(archive.read(row['old'])).hexdigest() != row['before_sha256']:
                errors.append('Snapshot changed: ' + row['old'])
            if deleted(row['new']):
                continue
            path = ROOT / current(row['new'])
            if not path.is_file() or digest(path) != expected_digest(row['new'], row['after_sha256']):
                errors.append('Current file changed: ' + row['new'])
    for name, expected in receipt.get('created_files', {}).items():
        if deleted(name):
            continue
        path = ROOT / current(name)
        if not path.is_file() or digest(path) != expected_digest(name, expected):
            errors.append('Created file changed: ' + name)
    for row in receipt['removed_links']:
        path = ROOT / row['entry']
        if path.exists() or path.is_symlink():
            errors.append('Old alias recreated: ' + row['entry'])
        if not (ROOT / current(row['target'])).exists():
            errors.append('Alias target lost: ' + row['target'])
    symlinks = []
    for directory, dirs, files in os.walk(ROOT, followlinks=False):
        dirs[:] = [name for name in dirs if name not in
                   ('.git', 'external', '__pycache__', '.pytest_cache', '.venv')]
        for name in dirs + files:
            path = Path(directory) / name
            if path.is_symlink():
                symlinks.append(path.relative_to(ROOT).as_posix())
    errors.extend('Project symlink remains: ' + name for name in symlinks)
    # Only active code/config is checked here. Immutable evidence and migration
    # receipts retain old identity strings; history-resolution tests exercise them.
    rows = json.loads((ROOT / 'experiments/methods/canonical-paths.json').read_text())['relocations']
    # Factor shared path prefixes so large migration maps remain cheap to scan.
    trie = {}
    for row in rows:
        node = trie
        for char in row['old']:
            node = node.setdefault(char, {})
        node[''] = {}

    def expression(node):
        alternatives = [re.escape(char) + expression(child)
                        for char, child in node.items() if char]
        if '' in node:
            alternatives.append('')
        return '(?:' + '|'.join(alternatives) + ')' if len(alternatives) > 1 else alternatives[0]

    pattern = re.compile(expression(trie) + r'(?=/|[\s\x22\x27]|$)')
    for name in receipt['active_files']:
        if deleted(name):
            continue
        path = ROOT / current(name)
        if path.is_file() and pattern.search(path.read_text()):
            errors.append('Legacy path in active file: ' + name)
    for name, expected in receipt['preserved_logs'].items():
        if digest(ROOT / name) != expected:
            errors.append('Preserved experiment log changed: ' + name)
    return dict(files_checked=len(receipt['files']), removed_links=len(receipt['removed_links']),
                project_symlinks=len(symlinks), active_files_checked=len(receipt['active_files']),
                errors=errors)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
