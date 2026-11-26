"""Verify or restore archived benchmark records, including their original formatting."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import mmap
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import subprocess

ARCHIVE = Path(__file__).resolve().parent
ROOT = ARCHIVE.parents[1]
FIELD = b'qa-field:sha256:'
BENCHMARKS = ('officeqa', 'searchqa', 'spreadsheetbench', 'alfworld', 'lmb')
SELECT = """SELECT r.path, r.sha, v.original_size, v.compact_sha, v.compact_size,
                   v.offsets, v.pool_pos, r.original_blocks
            FROM records r JOIN versions v ON v.sha=r.sha"""


def file_reference(digest):
    return b'{"$qa_file_ref":"sha256:' + digest.hex().encode('ascii') + b'"}\n'


class Archive:
    def __init__(self, benchmark):
        self.directory = ARCHIVE / benchmark
        self.relocations = {}
        if benchmark == 'lmb':
            mapping = json.loads((ROOT / 'experiments/methods/canonical-paths.json').read_bytes())
            self.relocations = {row['old']: row['new'] for row in mapping['relocations']
                                if row.get('archive') == benchmark}
        self.archive_keys = {new: old for old, new in self.relocations.items()}
        self.db = sqlite3.connect((self.directory / 'manifest.sqlite3').as_uri() + '?mode=ro', uri=True)
        self.file = (self.directory / 'payloads.pack').open('rb')
        self.pool = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        self.fields = {digest: (pos, size) for digest, pos, size in
                       self.db.execute('SELECT sha,pos,size FROM fields')}

    @staticmethod
    def _mapped_name(name, mapping):
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or not path.parts:
            raise ValueError(f'Expected a repository-relative archive path: {name}')
        for parent in (path, *path.parents):
            target = mapping.get(parent.as_posix())
            if target is not None:
                return (Path(target) / path.relative_to(parent)).as_posix()
        return path.as_posix()

    def archive_key(self, name):
        """Translate a canonical path to the historical key in the archive."""
        return self._mapped_name(name, self.archive_keys)

    def source_path(self, name):
        """Locate compact bytes while leaving the SQLite identity unchanged."""
        return ROOT / self._mapped_name(name, self.relocations)

    def read_bytes(self, name):
        key = self.archive_key(name)
        data = self.source_path(key).read_bytes()
        row = self.db.execute(SELECT + ' WHERE r.path=?', (key,)).fetchone()
        if row is None:
            return data
        original = io.BytesIO()
        self.verify_bytes(row, data, original)
        return original.getvalue()

    def validate_pool(self):
        if self.db.execute('PRAGMA integrity_check').fetchone() != ('ok',):
            raise ValueError('Manifest integrity check failed')
        for digest, (pos, size) in self.fields.items():
            raw = memoryview(self.pool)[pos:pos+size]
            if len(raw) != size or hashlib.sha256(raw).digest() != digest:
                raise ValueError('Shared field hash mismatch: ' + digest.hex())

    def chunks(self, record, data):
        path, original, size, compact_hash, compact_size, offsets, pool_pos, original_blocks = record
        # A tracked record can already have been restored in place.
        if len(data) == size and hashlib.sha256(data).digest() == original:
            yield data
            return
        if pool_pos is not None:
            if data != file_reference(original):
                raise ValueError('Whole-file reference mismatch: ' + path)
            template = memoryview(self.pool)[pool_pos:pool_pos+compact_size]
        else:
            template = memoryview(data)
        if len(template) != compact_size or hashlib.sha256(template).digest() != compact_hash:
            raise ValueError('Compact template hash mismatch: ' + path)
        start = 0
        for (at,) in struct.iter_unpack('<I', offsets):
            marker_end = at + len(FIELD)
            end = marker_end + 64
            if at < start or template[at:marker_end] != FIELD or end > len(template):
                raise ValueError('Invalid field reference in ' + path)
            digest = bytes.fromhex(bytes(template[marker_end:end]).decode('ascii'))
            pos, length = self.fields[digest]
            yield template[start:at]
            yield memoryview(self.pool)[pos:pos+length]
            start = end
        yield template[start:]

    def verify_bytes(self, record, data, output=None):
        digest = hashlib.sha256()
        size = 0
        for chunk in self.chunks(record, data):
            digest.update(chunk)
            size += len(chunk)
            if output is not None:
                output.write(chunk)
        if size != record[2] or digest.digest() != record[1]:
            raise ValueError('Original length or SHA-256 mismatch: ' + record[0])

    def read_record(self, record, destination, tracked):
        path = Path(record[0])
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe archive path')
        source = self.source_path(path)
        with source.open('rb') as f:
            data = f.read()
            blocks = os.fstat(f.fileno()).st_blocks * 512
        original = len(data) == record[2] and hashlib.sha256(data).digest() == record[1]
        if record[0] in tracked and (source.is_symlink() or not original):
            raise ValueError('Git-tracked record must retain its original bytes: ' + record[0])
        if destination is None:
            self.verify_bytes(record, data)
        else:
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as output:
                self.verify_bytes(record, data, output)
            shutil.copystat(source, target)
        return blocks, original

    def close(self):
        self.pool.close()
        self.file.close()
        self.db.close()


def restore_assets(archive, selected, destination, tracked):
    index = archive.directory / 'assets.json'
    files = before = after = length = links = 0
    if index.exists():
        for digest, entries in json.loads(index.read_bytes()).items():
            for name, size, blocks, mode, mtime, atime in entries:
                if selected and selected != name:
                    continue
                suffix = Path(name).suffix.lower() if archive.directory.name in ('spreadsheetbench', 'alfworld', 'lmb') else ''
                target = archive.directory / 'assets' / (digest + suffix)
                path = archive.source_path(name)
                if path.is_symlink():
                    if name in tracked or os.readlink(path) != os.path.relpath(target, path.parent):
                        raise ValueError('Asset link mismatch: ' + name)
                    links += 1
                if not path.is_file():
                    raise ValueError('Missing archived asset: ' + name)
                data = path.read_bytes()
                if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError('Asset bytes mismatch: ' + name)
                if destination:
                    result = destination / name
                    result.parent.mkdir(parents=True, exist_ok=True)
                    with result.open('xb') as output:
                        output.write(data)
                    result.chmod(mode)
                    os.utime(result, ns=(atime, mtime))
                files += 1
                before += blocks
                after += path.lstat().st_blocks * 512
                length += size
    return files, before, after, length, links


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('benchmark', choices=BENCHMARKS)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--verify', action='store_true', help='fully expand and hash all selected records')
    modes.add_argument('--output', type=Path, help='restore records under a new output directory')
    parser.add_argument('--file', help='restore or check one repository-relative record')
    args = parser.parse_args()
    archive = Archive(args.benchmark)
    archive.validate_pool()
    if args.file:
        args.file = archive.archive_key(args.file)
    query = SELECT + (' WHERE r.path=?' if args.file else '')
    rows = archive.db.execute(query, (args.file,) if args.file else ())
    tracked = set()
    if (args.benchmark in ('lmb') or (args.verify and args.benchmark in ('alfworld', 'spreadsheetbench'))) and (ROOT / '.git').exists():
        names = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z'])
        tracked = set(os.fsdecode(names).split('\0'))
    if args.output:
        args.output = args.output.resolve()
        args.output.mkdir(parents=True, exist_ok=False)
    files = after = before = original = occurrences = whole_files = plain_records = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        while True:
            batch = rows.fetchmany(1024)
            if not batch:
                break
            checked = pool.map(lambda row: archive.read_record(row, args.output, tracked), batch)
            for row, (blocks, plain) in zip(batch, checked):
                after += blocks
                plain_records += int(plain)
                if not plain:
                    whole_files += int(row[6] is not None)
                    occurrences += len(row[5]) // 4
            files += len(batch)
            before += sum(r[7] for r in batch)
            original += sum(r[2] for r in batch)
            if files % 51200 == 0:
                print(f'{args.benchmark}: verified {files} files', flush=True)
    record_count = files
    assets, asset_before, asset_after, asset_bytes, links = restore_assets(archive, args.file, args.output, tracked)
    files += assets
    before += asset_before
    after += asset_after
    original += asset_bytes
    whole_files += links
    if not files:
        parser.error('No matching archived record')
    print(json.dumps(dict(benchmark=args.benchmark, verified_files=files, original_bytes=original,
                          verified_data_records=record_count, verified_assets=assets,
                          already_original_records=plain_records, regular_assets=assets-links,
                          whole_file_references=whole_files, field_references_when_expanded=occurrences,
                          distinct_shared_fields=len(archive.fields),
                          original_allocated_bytes=before, compact_allocated_bytes=after)))
    archive.close()


if __name__ == '__main__':
    main()
