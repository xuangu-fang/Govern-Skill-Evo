import json

import pytest

from scripts.runs.v18 import run_v18_diagnosis_pilot as pilot
from src.skill_evolution.v18.diagnosis_prompt_v18 import build_diagnosis_request
from src.skill_evolution.v17.diagnosis_prompt_v17 import build_diagnosis_request as old_request


def test_fixed_evolution_replay_preserves_original_input():
    requests = pilot.replay_sources()
    assert [key for key, _ in requests] == ['round-02-g5', 'round-02-g3', 'round-03-g6']
    for _, request in requests:
        assert build_diagnosis_request(request)['user_prompt'] == old_request(request)['user_prompt']


def test_replay_rejects_changed_source_digest(tmp_path, monkeypatch):
    manifest = pilot.load(pilot.MANIFEST)
    manifest[0]['files_sha256']['request.json'] = '0' * 64
    path = tmp_path / 'sources.json'
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(pilot, 'MANIFEST', path)
    with pytest.raises(ValueError, match='Historical source changed'):
        pilot.replay_sources()
