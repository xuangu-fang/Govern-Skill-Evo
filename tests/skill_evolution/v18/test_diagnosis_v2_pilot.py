import json

from scripts.runs.v18 import run_v18_diagnosis_v2_pilot as pilot
from src.skill_evolution.v18.diagnosis_prompt_v18 import build_diagnosis_request


def test_five_fixed_inputs_remain_distinct_under_current_prompt():
    requests = pilot.fixed_requests()
    assert [key for key, _ in requests] == [
        'round-02-g5', 'round-02-g3', 'round-03-g6',
        'constructed-needs-revision', 'constructed-should-remove']
    prepared = [build_diagnosis_request(request) for _, request in requests]
    assert all(item['prompt_version'] == 'v18-group-diagnosis-3.2.1' for item in prepared)
    assert len({item['input_sha256'] for item in prepared}) == 5


def test_constructed_inputs_have_current_rule_and_expected_supervision():
    cases = pilot.load(pilot.CONSTRUCTED)
    for case in cases:
        request = pilot.constructed_request(case)
        payload = request.learner_payload
        assert len(payload['available_rule_refs']) == 1
        assert list(payload['available_rule_refs'].values())[0]['text'].strip() in case['parent_skill']
        expected = [False, True, True] if case['id'].endswith('should-remove') else [True, False, True]
        assert [e['supervision']['success'] for e in payload['experiences']] == expected
        build_diagnosis_request(request)


def test_constructed_spec_change_changes_input_digest():
    case = pilot.load(pilot.CONSTRUCTED)[0]
    original = build_diagnosis_request(pilot.constructed_request(case))['input_sha256']
    changed = json.loads(json.dumps(case))
    changed['experiences'][0]['events'][0]['content'] += ' changed'
    assert build_diagnosis_request(pilot.constructed_request(changed))['input_sha256'] != original
