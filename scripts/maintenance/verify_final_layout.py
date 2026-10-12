"""Verify the final migration snapshot, current files and unchanged raw evidence."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    receipt = json.loads((ROOT / 'docs/repository/final-migration.json').read_text())
    errors = []
    snapshot = ROOT / receipt['snapshot']
    if sha(snapshot) != receipt['snapshot_sha256']:
        raise ValueError('Final migration snapshot changed')
    excluded = receipt['snapshot_excluded_raw_files']
    expected_excluded = {row['old']: receipt['raw_files'][row['old']]
                         for row in receipt['files'] if row['old'] in receipt['raw_files']}
    if excluded != expected_excluded:
        errors.append('Snapshot raw exclusion list differs from migration records')
    with zipfile.ZipFile(snapshot) as archive:
        expected_names = ({row['old'] for row in receipt['files']} - set(excluded)
                          | set(receipt['deleted_files']))
        names = archive.namelist()
        if set(names) != expected_names or len(names) != len(expected_names):
            errors.append('Snapshot contains missing, extra or duplicate entries')
        for row in receipt['files']:
            if row['old'] in excluded:
                # Unchanged local evidence is checked below, without packaging it in Git.
                if not (row['before_sha256'] == row['after_sha256'] == excluded[row['old']]):
                    errors.append('Excluded raw evidence checksum differs: ' + row['old'])
            elif row['old'] not in names or hashlib.sha256(archive.read(row['old'])).hexdigest() != row['before_sha256']:
                errors.append('Snapshot changed: ' + row['old'])
            p = ROOT / row['new']
            if not p.is_file() or sha(p) != row['after_sha256']:
                errors.append('Current file changed: ' + row['new'])
        for name, expected in receipt['deleted_files'].items():
            if name not in names or hashlib.sha256(archive.read(name)).hexdigest() != expected or (ROOT / name).exists():
                errors.append('Deleted marker differs: ' + name)
    for name, expected in {**receipt['created_files'], **receipt['preserved_logs']}.items():
        p = ROOT / name
        if not p.is_file() or sha(p) != expected:
            errors.append('Recorded file changed: ' + name)
    moves = {r['old']: r['new'] for r in receipt['relocations']}
    for old, new in moves.items():
        if (ROOT / old).exists() or (ROOT / old).is_symlink():
            errors.append('Old entry remains: ' + old)
        if not (ROOT / new).is_file():
            errors.append('Destination missing: ' + new)
    for old, expected in receipt['raw_files'].items():
        p = ROOT / moves[old]
        if not p.is_file() or sha(p) != expected:
            errors.append('Raw evidence changed: ' + old)
    for name, originals in receipt['merged_documents'].items():
        text = (ROOT / name).read_text()
        for old in originals:
            anchor = Path(old).stem.lower().replace('_', '-')
            if f'<a id="{anchor}"></a>' not in text:
                errors.append('Merged section missing: ' + old)
    errors.extend('Python remains in benchmark data: ' + str(p.relative_to(ROOT))
                  for p in (ROOT / 'benchmarks').rglob('*.py'))
    return dict(relocations=len(moves), raw_files_checked=len(receipt['raw_files']),
                snapshot_raw_files_excluded=len(excluded),
                merged_documents=len(receipt['merged_documents']), errors=errors)


if __name__ == '__main__':
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result['errors']))
