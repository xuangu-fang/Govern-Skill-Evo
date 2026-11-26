"""Verify or restore the DocVQA records listed in manifest.sqlite3."""
import argparse
import base64
import hashlib
import json
import os
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ARCHIVE = Path(__file__).resolve().parent
ROOT = ARCHIVE.parents[1]
REFERENCE = b'docvqa-image:sha256:'
URI = b'data:image/png;base64,'


def load_images(db):
    images = {}
    for digest, path in db.execute('SELECT digest, path FROM images'):
        raw = (ROOT / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f'Original image hash mismatch: {path}')
        images[digest.encode()] = URI + base64.b64encode(raw)
    return images


def expand(data, offsets, images):
    """Expand only the references introduced by this conversion."""
    start = 0
    for offset in offsets:
        digest_at = offset + len(REFERENCE)
        end = digest_at + 64
        if offset < start or data[offset:digest_at] != REFERENCE:
            raise ValueError(f'Invalid image reference at byte {offset}')
        yield data[start:offset]
        yield images[data[digest_at:end]]
        start = end
    yield data[start:]


def restore_record(row, images, destination):
    path, original, compact, offsets, size = row
    source = ROOT / path
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != compact:
        raise ValueError(f'Compact file hash mismatch: {path}')
    digest = hashlib.sha256()
    length = 0
    output = None
    if destination is not None:
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        output = target.open('xb')
    try:
        for chunk in expand(data, json.loads(offsets), images):
            length += len(chunk)
            digest.update(chunk)
            if output is not None:
                output.write(chunk)
    finally:
        if output is not None:
            output.close()
    if length != size or digest.hexdigest() != original:
        raise ValueError(f'Restored file hash or length mismatch: {path}')
    if destination is not None:
        shutil.copystat(source, target)
    return source.stat().st_blocks * 512


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--verify', action='store_true', help='expand in memory and verify every original byte')
    modes.add_argument('--output', type=Path, help='write verified records in a new directory')
    parser.add_argument('--file', help='limit to one repository-relative record path')
    args = parser.parse_args()
    db = sqlite3.connect((ARCHIVE / 'manifest.sqlite3').as_uri() + '?mode=ro', uri=True)
    images = load_images(db)
    query = 'SELECT path, original_sha256, compact_sha256, offsets, original_size FROM records'
    params = ()
    if args.file:
        query += ' WHERE path=?'
        params = (args.file,)
    rows = db.execute(query, params).fetchall()
    if not rows:
        parser.error('No matching records')
    if args.output:
        args.output = args.output.resolve()
        args.output.mkdir(parents=True, exist_ok=False)
    total_blocks = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for count, value in enumerate(pool.map(lambda row: restore_record(row, images, args.output), rows), 1):
            total_blocks += value
            if count % 10000 == 0:
                print(f'Verified {count} / {len(rows)}', flush=True)
    print(json.dumps(dict(verified_files=len(rows), verified_original_images=len(images),
                          restored_bytes=sum(r[4] for r in rows), compact_allocated_bytes=total_blocks)))


if __name__ == '__main__':
    main()
