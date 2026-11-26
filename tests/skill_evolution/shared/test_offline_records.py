import hashlib
import json
import sqlite3
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.benchmark_record_refs import restore
from src.skill_evolution.shared import offline_records as offline


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    store = tmp_path / 'experiments/benchmark_record_refs'
    package = store / 'alfworld'
    package.mkdir(parents=True)
    for module in (restore, offline):
        monkeypatch.setattr(module, 'ROOT', tmp_path)
        monkeypatch.setattr(module, 'ARCHIVE', store)
    field = b'original value'
    original = b'{"text":"' + field + b'"}\r\n'
    def sha(data):
        return hashlib.sha256(data).digest()
    template = original.replace(field, restore.FIELD + sha(field).hex().encode())
    (package / 'payloads.pack').write_bytes(field + template)
    path = tmp_path / 'artifacts/trajectory.json'
    path.parent.mkdir()
    path.write_bytes(restore.file_reference(sha(original)))
    db = sqlite3.connect(package / 'manifest.sqlite3')
    db.executescript('''
        CREATE TABLE fields(sha BLOB, pos INTEGER, size INTEGER);
        CREATE TABLE records(path TEXT, sha BLOB, original_blocks INTEGER);
        CREATE TABLE versions(sha BLOB, original_size INTEGER, compact_sha BLOB,
                              compact_size INTEGER, offsets BLOB, pool_pos INTEGER);
    ''')
    db.execute('INSERT INTO fields VALUES(?,?,?)', (sha(field), 0, len(field)))
    db.execute('INSERT INTO records VALUES(?,?,0)', (path.relative_to(tmp_path).as_posix(), sha(original)))
    db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?)',
               (sha(original), len(original), sha(template), len(template),
                struct.pack('<I', original.index(field)), len(field)))
    db.commit()
    db.close()
    return path, package, original


def test_frozen_reader_keeps_original_bytes_and_rejects_corruption(evidence):
    path, package, original = evidence
    reader = SimpleNamespace(Path=Path, ROOT=path.parent)
    reference = path.read_bytes()
    with offline.offline_records('alfworld', reader):
        assert reader.Path(path).read_bytes() == original
        assert (reader.ROOT / path.name).read_bytes() == original
        assert path.read_bytes() == reference
        path.write_bytes(b'wrong pointer')
        with pytest.raises(ValueError, match='reference mismatch'):
            reader.Path(path).read_bytes()
        path.write_bytes(reference)
        pool = package / 'payloads.pack'
        pool.write_bytes(b'!' + pool.read_bytes()[1:])
        with pytest.raises(ValueError, match='SHA-256 mismatch'):
            reader.Path(path).read_bytes()
    assert reader.Path is Path
    assert type(reader.ROOT) is type(path)


def test_verifier_requires_plain_original_for_tracked_path(evidence):
    path, _, original = evidence
    archive = restore.Archive('alfworld')
    try:
        row = archive.db.execute(restore.SELECT).fetchone()
        with pytest.raises(ValueError, match='Git-tracked'):
            archive.read_record(row, None, {row[0]})
        path.write_bytes(original)
        _, plain = archive.read_record(row, None, {row[0]})
        assert plain
        path.write_bytes(original.replace(b'value', b'other'))
        with pytest.raises(ValueError, match='Git-tracked'):
            archive.read_record(row, None, {row[0]})
    finally:
        archive.close()


def test_asset_requires_correct_bytes_and_link_target(evidence, tmp_path):
    _, package, _ = evidence
    raw = b'original Skill'
    digest = hashlib.sha256(raw).hexdigest()
    name = 'artifacts/skill.md'
    asset = tmp_path / name
    shared = package / 'assets' / (digest + '.md')
    shared.parent.mkdir()
    shared.write_bytes(raw)
    (package / 'assets.json').write_text(json.dumps({digest: [[name, len(raw), 4096, 420, 0, 0]]}))
    archive = SimpleNamespace(directory=package)
    asset.write_bytes(raw)
    assert restore.restore_assets(archive, name, None, {name})[-1] == 0
    asset.write_bytes(b'other content')
    with pytest.raises(ValueError, match='bytes mismatch'):
        restore.restore_assets(archive, name, None, {name})
    asset.unlink()
    asset.symlink_to(shared)
    with pytest.raises(ValueError, match='link mismatch'):
        restore.restore_assets(archive, name, None, set())
