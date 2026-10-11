import hashlib

from scripts import run_v18_diagnosis_v31_pilot as pilot
from src.skill_evolution.diagnosis_prompt_v18 import build_diagnosis_request


def test_v31_replays_six_inputs_and_adds_five_generic_boundaries():
    requests = pilot.frozen_requests()
    assert len(requests) == 11
    assert [role for _, _, _, role in requests].count('REGRESSION') == 6
    assert [role for _, _, _, role in requests].count('BOUNDARY') == 5
    prepared = [build_diagnosis_request(request) for _, request, _, _ in requests]
    assert all(item['prompt_version'] == 'v18-group-diagnosis-3.2.1' for item in prepared)
    assert len({item['input_sha256'] for item in prepared}) == 11


def test_boundary_rubric_is_pre_prompt_and_hash_bound():
    manifest = pilot.load(pilot.BOUNDARY_FREEZE / 'manifest.json')
    rubric_path = pilot.BOUNDARY_FREEZE / 'semantic_rubric.json'
    rubric = pilot.load(rubric_path)
    assert rubric['written_before_prompt_v31'] is True
    assert rubric['monitor_data_used'] is False
    assert len(rubric['cases']) == 5
    assert hashlib.sha256(rubric_path.read_bytes()).hexdigest() == manifest['semantic_rubric_sha256']


def test_generic_boundaries_cover_declared_learnability_cases():
    cases = pilot.load(pilot.BOUNDARY_FREEZE / 'cases.json')
    assert {case['boundary'] for case in cases} == {
        'UNKNOWN_MECHANISM_STABLE_RELATION', 'FINITE_ACTIONS_NO_SELECTION_BASIS',
        'ANSWERABLE_CLARIFICATION', 'NEGATIVE_OUTCOME_ONLY',
        'EXPLICIT_PROHIBITION_BASIS',
    }
    forbidden = ('cedar', 'baggage', 'insurance', 'coverage', 'G02', 'G03', 'G06')
    serialized = str(cases).lower()
    assert all(word.lower() not in serialized for word in forbidden)
