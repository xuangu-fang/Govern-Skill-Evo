"""Audit the 2026-10-12 document move and explicitly inspect frozen snapshots.

This does not relax experiment runners' source checks or claim that archived
source is the current implementation. No files or experiment results are written.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from layout_history import current as canonical_path


ROOT = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def current_path(name):
    # A later benchmark move relocated some README destinations in this receipt.
    for relative in ('benchmarks/path-map.json', 'experiments/methods/path-map.json',
                     'experiments/methods/runtime-path-map.json'):
        path = ROOT / relative
        if path.is_file():
            for row in sorted(json.loads(path.read_text())['relocations'],
                              key=lambda r: len(r['old']), reverse=True):
                old, new = row['old'], row['new']
                if name == old or name.startswith(old + '/'):
                    name = new + name[len(old):]
                    break
    return canonical_path(name)


def verify(manifests=()):
    receipt = json.loads((ROOT / 'docs/path-map.json').read_text())
    archive_path = ROOT / receipt['snapshot']
    errors = []
    if digest(archive_path.read_bytes()) != receipt['snapshot_sha256']:
        raise ValueError('Migration snapshot checksum mismatch')
    mapping = {row['old']: row for row in receipt['files']}
    reports = []
    with zipfile.ZipFile(archive_path) as archive:
        for row in mapping.values():
            if digest(archive.read(row['old'])) != row['before_sha256']:
                errors.append('Snapshot changed: ' + row['old'])
            if not (ROOT / current_path(row['new'])).is_file():
                errors.append('Missing destination: ' + row['new'])
            if row['old'] != row['new'] and (ROOT / row['old']).exists():
                errors.append('Old document still exists: ' + row['old'])
        for supplied in manifests:
            path = Path(supplied)
            if not path.is_absolute():
                path = ROOT / path
            manifest = json.loads(path.read_text())
            entries = manifest.get('source_sha256', manifest.get('sources', manifest))
            if not isinstance(entries, dict):
                raise ValueError('Expected a source hash mapping: ' + str(path))
            current, frozen, mismatches = 0, [], []
            for name, expected in entries.items():
                if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
                    continue
                row = mapping.get(name)
                destination = ROOT / current_path(row['new'] if row else name)
                if destination.is_file() and digest(destination.read_bytes()) == expected:
                    current += 1
                elif row and digest(archive.read(name)) == expected:
                    frozen.append(name)
                else:
                    mismatches.append(name)
            if not current and not frozen and not mismatches:
                raise ValueError('No SHA-256 entries found: ' + str(path))
            reports.append(dict(manifest=str(supplied), current_matches=current,
                                archived_snapshot_matches=frozen, mismatches=mismatches))
            errors.extend(str(supplied) + ': ' + name for name in mismatches)
    return dict(moved_documents=receipt['moved_documents'],
                original_files_in_snapshot=len(mapping), manifests=reports, errors=errors,
                note='Snapshot matches verify historical bytes, not current-source identity or experiment replay.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', action='append', default=[],
                        help='Frozen source manifest; may be repeated. Audits without executing models.')
    args = parser.parse_args()
    result = verify(args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
