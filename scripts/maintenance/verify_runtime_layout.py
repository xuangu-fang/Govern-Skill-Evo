"""Read-only verification of runtime relocation; --full hashes every moved file."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import zipfile
from layout_history import current as canonical_path, expected_digest, retired


ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def verify(full=False):
    receipt = json.loads((ROOT / 'experiments/methods/runtime-migration.json').read_text())
    mapping = json.loads((ROOT / 'experiments/methods/runtime-path-map.json').read_text())
    errors = []
    archive_path = ROOT / receipt['snapshot']
    if digest(archive_path) != receipt['snapshot_sha256']:
        raise ValueError('Runtime relocation snapshot checksum mismatch')
    changed = {row['old']: row for row in receipt['files']}
    with zipfile.ZipFile(archive_path) as archive:
        for row in receipt['files']:
            if hashlib.sha256(archive.read(row['old'])).hexdigest() != row['before_sha256']:
                errors.append('Snapshot changed: ' + row['old'])
            path = ROOT / canonical_path(row['new'])
            if not path.is_file() or digest(path) != expected_digest(row['new'], row['after_sha256']):
                errors.append('Reviewable file changed: ' + row['new'])
    for name, expected in receipt.get('created_files', {}).items():
        path = ROOT / canonical_path(name)
        if not path.is_file() or digest(path) != expected_digest(name, expected):
            errors.append('Created layout file changed: ' + name)
    for alias in mapping['compatibility_aliases'] + receipt['relocated_symlinks']:
        path = ROOT / alias['entry']
        if retired(alias['entry']):
            if path.exists() or path.is_symlink():
                errors.append('Retired alias recreated: ' + alias['entry'])
            continue
        if (not path.is_symlink() or os.path.isabs(os.readlink(path))
                or path.resolve() != (ROOT / alias['target']).resolve()
                or not path.exists()):
            errors.append('Compatibility link missing or changed: ' + alias['entry'])
    for name, expected in receipt['preserved_logs'].items():
        if digest(ROOT / name) != expected:
            errors.append('Preserved log changed: ' + name)
    checked = 0
    if full:
        inventory = ROOT / receipt['local_file_inventory']
        if digest(inventory) != receipt['local_file_inventory_sha256']:
            raise ValueError('Per-file inventory checksum mismatch')
        with gzip.open(inventory, 'rt') as stream:
            for line in stream:
                row = json.loads(line)
                path = ROOT / canonical_path(row['new'])
                expected = changed.get(row['old'], {}).get('after_sha256', row['sha256'])
                expected = expected_digest(str(path.relative_to(ROOT)), expected)
                if not path.is_file() or digest(path) != expected:
                    errors.append('Moved file missing or changed: ' + row['new'])
                elif row['old'] not in changed and path.stat().st_mtime_ns != row['mtime_ns']:
                    errors.append('Original file timestamp changed: ' + row['new'])
                checked += 1
    return dict(runtime_roots=len(receipt['runtime_roots']),
                moved_files=receipt['moved_files'], file_hashes_checked=checked,
                full_integrity_check=full, errors=errors,
                note='Checks relocation integrity, not experiment completion or model reproducibility.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    result = verify(args.full)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
