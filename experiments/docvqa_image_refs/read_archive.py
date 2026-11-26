"""Read ordinary or archived DocVQA records without modifying the source files."""
import base64
from contextlib import ExitStack
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sqlite3

from experiments.docvqa_image_refs import restore
from experiments.evaluations.docvqa_checkpoints_shared_images_20261117 import restore as checkpoints

ROOT = restore.ROOT


class DocVQAArchive:
    def __init__(self):
        self._resources = ExitStack()
        self._db = None
        self._legacy = None
        self._image = lru_cache(maxsize=32)(self._read_image)

    def __enter__(self):
        manifest = restore.ARCHIVE / 'manifest.sqlite3'
        if manifest.is_file():
            self._db = sqlite3.connect(manifest.as_uri() + '?mode=ro', uri=True)
            self._resources.callback(self._db.close)
        return self

    def __exit__(self, *exc):
        self._image.cache_clear()
        checkpoints.original_image_uri.cache_clear()
        return self._resources.__exit__(*exc)

    def _read_image(self, digest):
        key = digest.decode('ascii')
        row = self._db.execute('SELECT path FROM images WHERE digest=?', (key,)).fetchone()
        if row is None:
            raise ValueError(f'Image missing from DocVQA archive: {key}')
        image = (ROOT / row[0]).read_bytes()
        if hashlib.sha256(image).hexdigest() != key:
            raise ValueError(f'DocVQA image SHA-256 differs: {row[0]}')
        return restore.URI + base64.b64encode(image)

    def _new_record(self, key):
        if self._db is None:
            return None
        return self._db.execute(
            'SELECT original_sha256, compact_sha256, offsets, original_size FROM records WHERE path=?',
            (key,),
        ).fetchone()

    def _legacy_record(self, key):
        root, _, relative = key.partition('/')
        if self._legacy is None:
            manifest = checkpoints.STORE / 'manifest.json'
            self._legacy = json.loads(manifest.read_bytes())['archives'] if manifest.is_file() else {}
        return self._legacy.get(root, {}).get(relative)

    def __getitem__(self, digest):
        return self._image(digest)

    def read_bytes(self, path):
        path = Path(path).resolve()
        data = path.read_bytes()
        if not path.is_relative_to(ROOT):
            return data

        record = self._new_record(path.relative_to(ROOT).as_posix())
        legacy = None
        if record is None and path.is_relative_to(checkpoints.ROOT):
            legacy = self._legacy_record(path.relative_to(checkpoints.ROOT).as_posix())
        if record is None and legacy is None:
            if restore.REFERENCE in data:
                raise ValueError(f'Compact DocVQA file has no archive entry: {path}')
            return data

        if record is not None:
            original, compact, offsets, size = record
        else:
            original, compact, size = legacy['original_sha256'], legacy.get('compact_sha256'), None
        current = hashlib.sha256(data).hexdigest()
        if current == original:
            return data
        if current != compact:
            raise ValueError(f'Compact DocVQA file SHA-256 differs: {path}')
        chunks = (restore.expand(data, json.loads(offsets), self) if record is not None
                  else checkpoints.expand(data))
        restored = b''.join(chunks)
        if ((size is not None and len(restored) != size)
                or hashlib.sha256(restored).hexdigest() != original):
            raise ValueError(f'Restored DocVQA file SHA-256 or size differs: {path}')
        return restored

    def read_json(self, path):
        return json.loads(self.read_bytes(path))
