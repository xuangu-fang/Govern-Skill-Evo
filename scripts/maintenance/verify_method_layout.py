"""Audit method experiment relocation and explicit historical source snapshots.

No experiment is run, no frozen manifest is rewritten, and current source
matches are reported separately from archived historical matches.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from layout_history import current as canonical_path, expected_digest, retired


ROOT = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(manifests=()):
    receipt = json.loads((ROOT / 'experiments/methods/migration.json').read_text())
    method_map = json.loads((ROOT / 'experiments/methods/path-map.json').read_text())
    benchmark = json.loads((ROOT / 'benchmarks/path-map.json').read_text())
    docs = json.loads((ROOT / 'docs/path-map.json').read_text())
    runtime = json.loads((ROOT / 'experiments/methods/runtime-migration.json').read_text())
    runtime_map = json.loads((ROOT / 'experiments/methods/runtime-path-map.json').read_text())
    runtime_rows = {row['old']: row for row in runtime['files']}
    doc_moves = {r['old']: r['new'] for r in docs['files']}
    snapshots = {}
    errors = []
    for record in (docs, benchmark, receipt, runtime):
        archive_path = ROOT / record['snapshot']
        if digest(archive_path.read_bytes()) != record['snapshot_sha256']:
            raise ValueError('Snapshot checksum mismatch: ' + str(archive_path))
        with zipfile.ZipFile(archive_path) as archive:
            for row in record['files']:
                if row.get('archived', True):
                    actual = digest(archive.read(row['old']))
                    if actual != row['before_sha256']:
                        errors.append('Snapshot bytes changed: ' + row['old'])
                    snapshots.setdefault(row['old'], set()).add(actual)

    def current(name):
        name = doc_moves.get(name, name)
        for mapping in (benchmark, method_map, runtime_map):
            for row in sorted(mapping['relocations'], key=lambda r: len(r['old']), reverse=True):
                if name == row['old'] or name.startswith(row['old'] + '/'):
                    name = row['new'] + name[len(row['old']):]
                    break
        return ROOT / canonical_path(name)

    for row in receipt['files']:
        path = current(row['new'])
        expected = row['after_sha256']
        later = runtime_rows.get(row['new'])
        if later and later['before_sha256'] == expected:
            expected = later['after_sha256']
        expected = expected_digest(str(path.relative_to(ROOT)), expected)
        if not path.is_file() or digest(path.read_bytes()) != expected:
            errors.append('Destination missing or changed: ' + row['new'])
        old = ROOT / row['old']
        if row['old'] != row['new'] and old.exists() and old.resolve() != path.resolve():
            errors.append('Old path is a separate copy: ' + row['old'])
    for alias in method_map['compatibility_aliases']:
        path = ROOT / alias['entry']
        if retired(alias['entry']):
            if path.exists() or path.is_symlink():
                errors.append('Retired alias recreated: ' + alias['entry'])
            continue
        if not path.is_symlink() or path.resolve() != (ROOT / alias['target']).resolve():
            errors.append('Compatibility alias changed: ' + alias['entry'])
    for name, expected in receipt['preserved_logs'].items():
        if digest((ROOT / name).read_bytes()) != expected:
            errors.append('Preserved log changed: ' + name)
    reports = []
    for supplied in manifests:
        path = Path(supplied)
        if not path.is_absolute():
            path = current(supplied)
        manifest = json.loads(path.read_text())
        entries = manifest.get('files', manifest.get('source_sha256', manifest.get('sources', manifest)))
        if not isinstance(entries, dict):
            raise ValueError('Expected a source hash mapping: ' + str(path))
        matches, archived, missing = [], [], []
        for name, expected in entries.items():
            if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
                continue
            destination = current(name)
            if destination.is_file() and digest(destination.read_bytes()) == expected:
                matches.append(name)
            elif any(expected in snapshots.get(p, set()) for p in (name, doc_moves.get(name))):
                archived.append(name)
            else:
                missing.append(name)
        if not matches and not archived and not missing:
            raise ValueError('No SHA-256 entries found: ' + str(path))
        reports.append(dict(manifest=str(supplied), current_matches=len(matches),
                            archived_snapshot_matches=archived, mismatches=missing))
        errors.extend(str(supplied) + ': ' + name for name in missing)
    return dict(files_checked=len(receipt['files']), manifests=reports, errors=errors,
                note='Archived matches prove historical bytes, not current-code equivalence or experiment replay.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', action='append', default=[])
    args = parser.parse_args()
    result = verify(args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
