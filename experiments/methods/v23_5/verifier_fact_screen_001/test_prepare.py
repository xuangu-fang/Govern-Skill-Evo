"""Reference integrity and message isolation, not model-quality tests."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from experiments.methods.v23_5.verifier_fact_screen_001 import prepare as p


def fixtures():
    return p.io.read(p.HERE/'reference_review.json'), {
        name: p.io.read(p.shared.DEFAULT_OUTPUT/'cases'/name/'verifier_input.json') for name in p.io.ROUNDS}


def test_real_reference_covers_all_targets_with_predeclared_groups():
    reference, inputs = fixtures()
    assert p.validate_reference(reference, inputs) == {
        'targets': 18, 'expected_verdict_counts': {'SUPPORTED': 14, 'CONFLICT': 4},
        'primary_verdict_counts': {'SUPPORTED': 12, 'CONFLICT': 4}, 'review_only': 2, 'required_findings': 4}
    assert {(i['round'], i['target']['knowledge_index']) for i in reference['items']
            if i['scoring_group'] == 'review_only'} == {('R01', 3), ('R03', 4)}
    hidden = next(i for i in reference['items'] if i['round'] == 'R02' and i['target']['knowledge_index'] == 1)
    assert hidden['expected_verdict'] == 'SUPPORTED'
    assert 'P9:1' not in inputs['R02']['source_records']
    assert 'Q6:2' in inputs['R01']['source_records']  # The boundary note must not conceal a supplied desk observation.


def test_required_findings_use_visible_raw_anchors():
    reference, inputs = fixtures()
    findings = {f['id']: f for i in reference['items'] for f in i['required_findings']}
    assert set(findings) == {'wrong_Q5_49', 'kettle_visibility', 'transform_overgeneralization', 'search_rule_trigger'}
    assert findings['wrong_Q5_49']['anchors'][0]['value'] == 'go to shelf 1'
    assert all('kettle' not in a['value'].lower() for a in findings['kettle_visibility']['anchors'])
    assert 'While the goal object has not been found' in inputs['R03']['source_records']['diff']['diff']


@pytest.mark.parametrize('change', ['missing_target', 'duplicate_target', 'changed_knowledge',
                                    'unprovided_reference', 'wrong_anchor', 'nonverbatim_statement'])
def test_invalid_reference_is_rejected(change):
    reference, inputs = fixtures()
    conflict = next(i for i in reference['items'] if i['required_findings'])
    if change == 'missing_target':
        reference['items'].pop()
    elif change == 'duplicate_target':
        reference['items'].append(deepcopy(reference['items'][0]))
    elif change == 'changed_knowledge':
        reference['items'][0]['knowledge']['text'] += ' edited'
    elif change == 'unprovided_reference':
        conflict['required_findings'][0]['evidence'].append('Q5:9999')
    elif change == 'wrong_anchor':
        conflict['required_findings'][0]['anchors'][0]['value'] = 'go to drawer 1'
    elif change == 'nonverbatim_statement':
        conflict['required_findings'][0]['statement'] = 'invented excerpt'
    with pytest.raises(ValueError):
        p.validate_reference(reference, inputs)


@pytest.mark.parametrize('field,value', [('human_reviewed', True), ('new_policy_model_calls', 1),
                                        ('prior_verifier_outputs_seen', False)])
def test_provenance_cannot_claim_human_blind_or_live_results(field, value):
    reference, inputs = fixtures()
    reference[field] = value
    with pytest.raises(ValueError):
        p.validate_reference(reference, inputs)


def test_frozen_package_has_no_answers_in_messages_and_rejects_tampering(tmp_path):
    root = tmp_path/'frozen'
    assert p.prepare(root)['reference_excluded_from_messages']
    reference, inputs = fixtures()
    for name in p.io.ROUNDS:
        messages = p.io.read(root/'cases'/name/'messages.json')
        assert messages == p.v.messages_for(inputs[name], (p.HERE/'verifier_prompt.md').read_text())
        assert 'detection_criterion' not in messages[1]['content']
        assert 'scoring_group' not in messages[1]['content']
    with pytest.raises(ValueError, match='Output exists'):
        p.prepare(root)
    path = root/'reference_review.json'
    reference['items'][0]['expected_verdict'] = 'CONFLICT'
    p.io.save(path, reference)
    with pytest.raises(ValueError, match='Frozen file changed'):
        p.verify(root)
