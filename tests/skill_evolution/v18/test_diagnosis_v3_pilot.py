import hashlib
import json

from scripts.runs.v18 import run_v18_diagnosis_v3_pilot as pilot
from src.skill_evolution.v18.diagnosis_prompt_v18 import build_diagnosis_request


def test_six_frozen_inputs_replay_exactly_under_v3():
    requests = pilot.frozen_requests()
    assert [group_id for group_id, _, _ in requests] == [f'G{i:02d}' for i in range(1, 7)]
    for group_id, request, v2_identity in requests:
        prepared = build_diagnosis_request(request)
        assert prepared['prompt_version'] == 'v18-group-diagnosis-3.2.1'
        assert prepared['input_sha256'] == v2_identity['input_sha256'], group_id


def test_frozen_rubric_predates_v3_and_excludes_monitor_data():
    manifest = pilot.load(pilot.FREEZE / 'manifest.json')
    rubric_bytes = (pilot.FREEZE / 'semantic_rubric.json').read_bytes()
    rubric = json.loads(rubric_bytes)
    assert manifest['monitor_data_used'] is False
    assert rubric['written_before_prompt_v3'] is True
    assert hashlib.sha256(rubric_bytes).hexdigest() == manifest['semantic_rubric_sha256']
    serialized = json.dumps(rubric, ensure_ascii=False)
    assert 'Monitor task-level errors or outcomes' in serialized
    assert set(rubric['cases']) == {f'G{i:02d}' for i in range(1, 7)}
