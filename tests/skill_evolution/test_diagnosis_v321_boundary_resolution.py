import hashlib

from scripts import run_v18_diagnosis_v321_boundary_resolution as pilot
from src.skill_evolution.diagnosis_prompt_v18 import build_diagnosis_request


def test_boundary_resolution_is_frozen_and_orthogonal():
    manifest = pilot.load(pilot.FREEZE / 'manifest.json')
    cases_path = pilot.FREEZE / 'cases.json'
    rubric_path = pilot.FREEZE / 'semantic_rubric.json'
    assert hashlib.sha256(cases_path.read_bytes()).hexdigest() == manifest['cases_sha256']
    assert hashlib.sha256(rubric_path.read_bytes()).hexdigest() == manifest['semantic_rubric_sha256']
    cases = pilot.load(cases_path)
    assert len(cases) == 2
    assert cases[0]['experiences'] == cases[1]['experiences']
    assert cases[0]['tools'] == cases[1]['tools']
    assert cases[0]['visible_policy'] != cases[1]['visible_policy']


def test_boundary_resolution_uses_current_prompt_without_specialization():
    requests = pilot.frozen_requests()
    assert len(requests) == 2
    prepared = [build_diagnosis_request(request) for _, request in requests]
    assert all(item['prompt_version'] == 'v18-group-diagnosis-3.2.1' for item in prepared)
    from src.skill_evolution.diagnosis_prompt_v18 import SYSTEM_PROMPT
    assert 'resolved-pure-negative-only' not in SYSTEM_PROMPT
    assert 'resolved-explicit-prerequisite' not in SYSTEM_PROMPT
