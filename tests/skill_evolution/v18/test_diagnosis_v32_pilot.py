import hashlib

from scripts.runs.v18 import run_v18_diagnosis_v32_pilot as pilot
from src.skill_evolution.v18.diagnosis_prompt_v18 import build_diagnosis_request


def test_v32_replays_all_frozen_inputs_and_adds_aggregation_pair():
    requests = pilot.frozen_requests()
    assert len(requests) == 13
    assert [role for _, _, _, role in requests].count('REGRESSION') == 6
    assert [role for _, _, _, role in requests].count('BOUNDARY') == 5
    assert [role for _, _, _, role in requests].count('AGGREGATION') == 2
    prepared = [build_diagnosis_request(request) for _, request, _, _ in requests]
    assert all(item['prompt_version'] == 'v18-group-diagnosis-3.2.1' for item in prepared)
    assert len({item['input_sha256'] for item in prepared}) == 13


def test_unified_rubric_and_pair_are_hash_bound():
    manifest = pilot.verify_freeze()
    rubric_path = pilot.V32_FREEZE / 'semantic_rubric.json'
    cases_path = pilot.V32_FREEZE / 'cases.json'
    rubric = pilot.load(rubric_path)
    assert rubric['written_before_prompt_v32'] is True
    assert rubric['monitor_data_used'] is False
    assert hashlib.sha256(rubric_path.read_bytes()).hexdigest() == manifest['semantic_rubric_sha256']
    assert hashlib.sha256(cases_path.read_bytes()).hexdigest() == manifest['cases_sha256']


def test_pair_differs_only_by_independent_unresolved_branch():
    alone, mixed = pilot.load(pilot.V32_FREEZE / 'cases.json')
    assert alone['pair_role'] == 'LEARNABLE_ALONE'
    assert mixed['pair_role'] == 'LEARNABLE_WITH_UNRESOLVED'
    assert mixed['experiences'][:len(alone['experiences'])] == alone['experiences']
    assert len(mixed['experiences']) == len(alone['experiences']) + 1
    assert mixed['parent_skill'] == alone['parent_skill']
    assert mixed['visible_policy'] == alone['visible_policy']
    assert mixed['tools'] == alone['tools']


def test_prompt_and_freeze_have_no_special_case_terms():
    from src.skill_evolution.v18.diagnosis_prompt_v18 import SYSTEM_PROMPT
    forbidden = ('cedar', 'baggage', 'insurance', 'coverage', 'G02', 'G03', 'G06')
    assert all(term.lower() not in SYSTEM_PROMPT.lower() for term in forbidden)
    cases = str(pilot.load(pilot.V32_FREEZE / 'cases.json'))
    assert all(term.lower() not in cases.lower() for term in forbidden)
