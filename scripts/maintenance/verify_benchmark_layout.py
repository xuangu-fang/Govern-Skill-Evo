"""Read-only audit of the benchmark layout and explicitly identified snapshots.

This never relaxes a runner's frozen-source checks or rewrites experiment data.
Archived matches prove historical bytes are available, not current-code identity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from layout_history import current as canonical_path, expected_digest


ROOT = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(manifests=()):
    receipt = json.loads((ROOT / 'benchmarks/path-map.json').read_text())
    previous = json.loads((ROOT / receipt['previous_snapshot']).read_text())
    old_docs = {row['old']: row['new'] for row in previous['files']}
    errors = []
    snapshots = {}
    later_path = ROOT / 'experiments/methods/migration.json'
    later = json.loads(later_path.read_text()) if later_path.is_file() else None
    later_rows = {r['old']: r for r in later['files']} if later else {}
    later_map = (json.loads((ROOT / 'experiments/methods/path-map.json').read_text())
                 if later else {'relocations': []})
    runtime = json.loads((ROOT / 'experiments/methods/runtime-migration.json').read_text())
    runtime_map = json.loads((ROOT / 'experiments/methods/runtime-path-map.json').read_text())
    runtime_rows = {row['old']: row for row in runtime['files']}
    for record in (previous, receipt, *([later] if later else []), runtime):
        path = ROOT / record['snapshot']
        if digest(path.read_bytes()) != record['snapshot_sha256']:
            raise ValueError('Snapshot checksum mismatch: ' + str(path))
        with zipfile.ZipFile(path) as archive:
            for row in record['files']:
                if not row.get('archived', True):
                    continue
                data = archive.read(row['old'])
                actual = digest(data)
                if actual != row['before_sha256']:
                    errors.append('Archived bytes changed: ' + row['old'])
                snapshots.setdefault(row['old'], set()).add(actual)

    def current_path(name):
        name = old_docs.get(name, name)
        for mapping in (receipt, later_map, runtime_map):
            for row in sorted(mapping['relocations'], key=lambda r: len(r['old']), reverse=True):
                old, new = row['old'], row['new']
                if name == old or name.startswith(old + '/'):
                    name = new + name[len(old):]
                    break
        return ROOT / canonical_path(name)

    for row in receipt['files']:
        path = current_path(row['new'])
        expected = row['after_sha256']
        next_row = later_rows.get(row['new'])
        if next_row and next_row['before_sha256'] == expected:
            # The verified later archive holds this stage's exact after-bytes.
            expected = next_row['after_sha256']
        runtime_row = runtime_rows.get(next_row['new'] if next_row else row['new'])
        if runtime_row and runtime_row['before_sha256'] == expected:
            expected = runtime_row['after_sha256']
        expected = expected_digest(str(path.relative_to(ROOT)), expected)
        if not path.is_file() or digest(path.read_bytes()) != expected:
            errors.append('Destination missing or changed: ' + row['new'])
        if row['old'] != row['new'] and (ROOT / row['old']).exists():
            errors.append('Old path still exists: ' + row['old'])
    for name, expected in receipt['preserved_logs'].items():
        if digest((ROOT / name).read_bytes()) != expected:
            errors.append('Preserved log changed: ' + name)

    reports = []
    for supplied in manifests:
        path = Path(supplied)
        if not path.is_absolute():
            path = current_path(supplied)
        manifest = json.loads(path.read_text())
        entries = manifest.get('source_sha256', manifest.get('sources', manifest))
        if not isinstance(entries, dict):
            raise ValueError('Expected a source hash mapping: ' + str(path))
        current, archived, mismatches = [], [], []
        for name, expected in entries.items():
            if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
                continue
            destination = current_path(name)
            if destination.is_file() and digest(destination.read_bytes()) == expected:
                current.append(name)
            elif expected in snapshots.get(name, set()) or expected in snapshots.get(old_docs.get(name), set()):
                archived.append(name)
            else:
                mismatches.append(name)
        if not current and not archived and not mismatches:
            raise ValueError('No SHA-256 entries found: ' + str(path))
        reports.append(dict(manifest=str(supplied), current_matches=len(current),
                            archived_snapshot_matches=archived, mismatches=mismatches))
        errors.extend(str(supplied) + ': ' + name for name in mismatches)
    return dict(files_checked=len(receipt['files']), manifests=reports, errors=errors,
                note='Archived matches verify historical bytes, not current-source identity or experiment replay.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', action='append', default=[],
                        help='Frozen source manifest; may be repeated. No model execution.')
    args = parser.parse_args()
    result = verify(args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
