"""Path migration must preserve evidence and never recreate old directories."""
import hashlib
import json
from pathlib import Path

import pytest

from src.skill_evolution.shared import experiment_paths as paths
from src.skill_evolution.v19.evolution_replay_v19 import _file_digest, _load, _save


def test_read_historical_evidence_without_a_filesystem_alias():
    old = paths.ROOT / 'artifacts/v20_pilot_001/binding.json'
    current = paths.ROOT / 'artifacts/methods/v20/v20_pilot_001/binding.json'
    original = current.read_bytes()
    assert not old.exists() and not old.is_symlink()
    assert _load(old) == json.loads(original)
    assert _file_digest(old) == hashlib.sha256(original).hexdigest()
    assert current.read_bytes() == original
    assert not old.exists()


def test_legacy_write_targets_canonical_directory_only(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'ROOT', tmp_path)
    monkeypatch.setattr(paths, '_relocations', lambda: [
        {'old': 'artifacts/old_run', 'new': 'artifacts/methods/v19/new_run'},
    ])
    _save('artifacts/old_run/state.json', {'state': 'test'})
    assert json.loads((tmp_path / 'artifacts/methods/v19/new_run/state.json').read_text()) == {'state': 'test'}
    assert not (tmp_path / 'artifacts/old_run').exists()


def test_caller_relative_read_is_not_rebased_to_repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('state.json').write_text('{"state": "local"}')
    assert _load('state.json') == {'state': 'local'}


@pytest.mark.parametrize('run_id,version', [
    ('autonomous_gse_v03', 'v03'),
    ('autonomous_gse_v04_seed_150', 'v04'),
    ('autonomous_gse_v14_tge_v1', 'v14'),
])
def test_dynamic_run_directory_uses_campaign_version(tmp_path, run_id, version):
    assert paths.method_artifact_root(run_id, root=tmp_path) == (
        tmp_path / 'artifacts/methods' / version / run_id)
