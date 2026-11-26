#!/usr/bin/env python3
"""Verify compact DocVQA archives or restore their original bytes to a new directory."""
import argparse
import base64
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import re
import shutil
import sys
import tempfile

STORE = Path(__file__).resolve().parent
ROOT = STORE.parent
PREFIX = b'docvqa-image:sha256:'
REFERENCE = re.compile(rb'(?<=")docvqa-image:sha256:([0-9a-f]{64})(?=")')


@lru_cache(maxsize=374)
def original_image_uri(digest):
    raw = (STORE / 'images' / (digest + '.png')).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f'Image hash mismatch: {digest}')
    return b'data:image/png;base64,' + base64.b64encode(raw)


def expand(data):
    start = 0
    for match in REFERENCE.finditer(data):
        yield data[start:match.start()]
        yield original_image_uri(match[1].decode('ascii'))
        start = match.end()
    yield data[start:]


def process_file(source, entry, destination=None):
    data = source.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual == entry['original_sha256']:
        chunks = (data,)
    elif actual == entry.get('compact_sha256'):
        chunks = expand(data)
    else:
        raise ValueError(f'Unexpected archive contents: {source}')

    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
    output = destination.open('xb') if destination is not None else None
    digest = hashlib.sha256()
    try:
        for chunk in chunks:
            digest.update(chunk)
            if output is not None:
                output.write(chunk)
    finally:
        if output is not None:
            output.close()
    if digest.hexdigest() != entry['original_sha256']:
        raise ValueError(f'Reconstructed file hash mismatch: {source}')
    if destination is not None:
        shutil.copystat(source, destination)


def verify_on_disk(manifest, temporary_file):
    for folder, files in manifest['archives'].items():
        for name, entry in files.items():
            process_file(ROOT / folder / name, entry, temporary_file)
            digest = hashlib.sha256()
            with temporary_file.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != entry['original_sha256']:
                raise ValueError(f'On-disk verification failed: {folder}/{name}')
            temporary_file.unlink()
        print(f'{folder}: restored and read back {len(files)} files', flush=True)
    print('All on-disk original hashes verified.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    flags = parser.add_mutually_exclusive_group(required=True)
    flags.add_argument('--verify', action='store_true', help='verify all original SHA-256 hashes without writing')
    flags.add_argument('--output', type=Path, help='restore all three archives into a new directory')
    flags.add_argument('--verify-on-disk', action='store_true',
                       help='restore one file at a time and verify the bytes read back from disk')
    args = parser.parse_args()
    manifest = json.loads((STORE / 'manifest.json').read_bytes())
    dest = args.output.resolve() if args.output else None
    if dest:
        for protected in [STORE, *(ROOT / name for name in manifest['archives'])]:
            if dest == protected or protected in dest.parents:
                parser.error('output must be outside the shared store and compact archives')
        if dest.exists():
            parser.error('output directory already exists; choose a new path')
        dest.mkdir(parents=True)
    if args.verify_on_disk:
        with tempfile.TemporaryDirectory(prefix='docvqa-restore-check-') as temporary:
            verify_on_disk(manifest, Path(temporary) / 'restored-file')
        return
    for folder, files in manifest['archives'].items():
        for name, entry in files.items():
            path = ROOT / folder / name
            process_file(path, entry, dest / folder / name if dest else None)
        print(f'{folder}: verified {len(files)} original file hashes', flush=True)
    if dest:
        print(f'Restored and verified in {dest}')
    else:
        print('All original file hashes verified.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))
