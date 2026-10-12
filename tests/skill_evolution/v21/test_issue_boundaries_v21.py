"""Issue ownership survives joint decisions without hiding shared evidence."""
from copy import deepcopy
from dataclasses import replace

import pytest

from tests.skill_evolution.v21.test_memory_update_v21 import update_input, completed, setup, case, response, fresh_event
from tests.skill_evolution.v21.test_memory_consumption_v21 import following
from tests.skill_evolution.v20.test_local_generation_v20 import proposal
from src.skill_evolution.v19.edit_tracking_v19 import encode, parse
from src.skill_evolution.v20.issue_memory_v20 import merge_update
from src.skill_evolution.v21.modification_evidence_v21 import ModificationEvidence, open_memory_evidence
from src.skill_evolution.v21.memory_update_v21 import build_memory_update_input, build_memory_update_request, validate_memory_update
from src.skill_evolution.v21.memory_consumption_v21 import build_issue_fusion_input, build_issue_fusion_request, build_generation_input
from src.skill_evolution.v20.issue_fusion_v20 import validate_issue_fusion
from src.skill_evolution.v21.evidence_wire_v21 import expand


@pytest.fixture
def joint(update_input):
    data = update_input.evidence.payload
    # Two independent issues have one old joint edit. The sibling's sources and
    # counterexample must stay available without becoming A's inherited claims.
    record = data['archive']['records']['ATTR/unrelated']
    record['edit_refs'] = ['EDIT/joint']
    record['statement'] = 'A separate problem about payment; not the original choice problem.'
    record['counterevidence_refs'] = ['OLD/2/E1']
    data['memory'] = merge_update(data['memory'], {
        'schema_version': 'issue_memory_update_v20.1', 'run_id': data['run_id'], 'round_id': 'old',
        'issues': [{'new_issue_key': 'payment', 'problem': 'Payment result was not checked.',
            'source_refs': ['ATTR/unrelated'], 'attempts': [{
                'new_attempt_key': 'payment-attempt', 'approach': 'Check the payment result.',
                'assessment': 'Payment failed in the old example; choice behavior was not assessed.',
                'edit_refs': ['EDIT/joint'], 'source_refs': ['ATTR/unrelated']}]}]})
    a, b = data['memory']['issues']
    # Reproduce a broad joint decision. Its text must not become either problem.
    data['proposals'][0]['memory_issue_refs'] = [a['issue_id'], b['issue_id']]
    data['proposals'][0]['issue_statement'] = 'Revise choice behavior AND payment verification.'
    return build_memory_update_input(ModificationEvidence(encode(data))), a, b


def a_response(request, a):
    value = response(request)
    value['issues'][0].update(issue_id=a['issue_id'], problem=a['problem'])
    return value


def next_source(following, evidence, issue_ids):
    kwargs = {**following[0], 'memory_evidence': evidence}
    fusion = build_issue_fusion_input(**kwargs)
    finding_ids = [f['finding_id'] for f in fusion.payload['current_findings']]
    chosen = proposal(finding_ids, issue_ids)
    result = validate_issue_fusion(encode({'schema_version': 'issue_fusion_response_v20.1',
        'issues': [chosen], 'unassociated_findings': []}), request=fusion)
    return build_generation_input(**kwargs, fusion_input=fusion, fusion_result=result)


def test_shared_edit_keeps_sibling_evidence_without_assigning_its_sources(joint):
    request, a, b = joint
    view = request.payload
    assert 'ATTR/unrelated' in view['source_records']
    assert 'OLD/2/E1' in view['events']
    assert {'ATTR/old', 'ATTR/failed'} <= set(view['issue_source_refs'][a['issue_id']])
    assert 'ATTR/unrelated' not in view['issue_source_refs'][a['issue_id']]
    assert view['issue_source_refs'][b['issue_id']] == ['ATTR/unrelated']
    assert 'ATTR/old' not in view['issue_source_refs'][b['issue_id']]


def test_writeback_does_not_launder_sibling_counterevidence_into_own_record(joint):
    request, a, b = joint
    result = validate_memory_update(encode(a_response(request, a)), request=request)
    updated = {i['issue_id']: i for i in result.payload['memory']['issues']}
    assert updated[b['issue_id']] == b
    assert updated[a['issue_id']]['problem'] == a['problem']
    new = updated[a['issue_id']]['attempts'][-1]
    record = result.updated_evidence.payload['archive']['records'][new['source_refs'][0]]
    assert 'OLD/1/E1' in record['counterevidence_refs']
    assert 'OLD/2/E1' not in record['counterevidence_refs']
    assert 'ATTR/unrelated' not in record['source_refs']
    view = open_memory_evidence(result.updated_evidence, issue_refs=[a['issue_id']])
    assert 'ATTR/unrelated' in view['source_records'] and 'OLD/2/E1' in view['events']
    assert 'ATTR/unrelated' not in view['issue_source_refs'][a['issue_id']]


def test_joint_edit_can_have_separate_issue_specific_assessments(joint):
    request, a, b = joint
    value = a_response(request, a)
    other = deepcopy(value['issues'][0])
    other.update(issue_id=b['issue_id'], problem=b['problem'])
    other['attempts'][0].update(approach='Check the payment result in this joint attempt.',
        assessment='The observed payment behavior concerns this issue; individual edit effects remain unknown.')
    value['issues'].append(other)
    result = validate_memory_update(encode(value), request=request)
    rows = {i['issue_id']: i for i in result.payload['memory']['issues']}
    aa, bb = (rows[i['issue_id']]['attempts'][-1] for i in (a, b))
    assert aa['edit_refs'] == bb['edit_refs']  # shared identity, not isolated replay
    assert aa['attempt_id'] != bb['attempt_id']
    assert aa['assessment'] != bb['assessment']
    assert result == validate_memory_update(encode(value), request=request)


def test_existing_problem_cannot_be_replaced_even_with_valid_current_citations(joint):
    request, a, _ = joint
    value = a_response(request, a)
    value['issues'][0].update(problem=request.payload['proposals'][0]['issue_statement'],
                              source_refs=[fresh_event(request)])
    with pytest.raises(ValueError, match='fixed scope anchor'):
        validate_memory_update(encode(value), request=request)


def test_attempt_identity_cannot_be_moved_to_another_issue(joint):
    request, a, b = joint
    value = a_response(request, a)
    value['issues'][0]['attempts'][0]['attempt_id'] = b['attempts'][0]['attempt_id']
    with pytest.raises(ValueError, match='wrong issue'):
        validate_memory_update(encode(value), request=request)


def test_new_distinct_problem_keeps_existing_problems_unchanged(joint):
    request, a, b = joint
    value = a_response(request, a)
    value['issues'].append({'issue_id': 'NEW/new-regression', 'problem': 'A distinct observed interruption.',
        'current_understanding': 'The interruption is observed, but its cause and relation remain unknown.',
        'source_refs': [fresh_event(request)], 'attempts': []})
    result = validate_memory_update(encode(value), request=request).payload['memory']
    old = {i['issue_id']: i for i in result['issues']}
    assert old[a['issue_id']]['problem'] == a['problem']
    assert old[b['issue_id']] == b
    assert result['issues'][-1]['attempts'] == []


def test_scope_refs_are_lossless_short_ids_and_cannot_be_reassigned(joint):
    request, a, b = joint
    prompt = build_memory_update_request(request)
    wire = parse(prompt['user_prompt'])
    assert expand(wire, prompt['reference_map']) == request.payload
    assert a['issue_id'] not in wire['issue_source_refs']
    reverse = {v: k for k, v in prompt['reference_map'].items()}
    assert reverse['ATTR/unrelated'] in wire['issue_source_refs'][reverse[b['issue_id']]]
    assert reverse['ATTR/unrelated'] not in wire['issue_source_refs'][reverse[a['issue_id']]]
    damaged = request.payload
    damaged['issue_source_refs'][a['issue_id']].append('ATTR/unrelated')
    with pytest.raises(ValueError, match='differs from original evidence'):
        build_memory_update_request(replace(request, payload_json=encode(damaged)))


def test_next_review_keeps_original_focus_and_shared_counterexample(joint, following):
    request, a, b = joint
    result = validate_memory_update(encode(a_response(request, a)), request=request)
    review = next_source(following, result.updated_evidence, [a['issue_id']]).build_review_inputs()[0]
    p = review.payload
    assert [i['issue_id'] for i in p['memory_issues']] == [a['issue_id']]
    assert p['memory_issues'][0]['problem'] == a['problem']
    assert b['issue_id'] not in p['issue_source_refs']
    assert 'ATTR/unrelated' in result.updated_evidence.payload['archive']['records']
    assert 'ATTR/unrelated' not in p['issue_source_refs'][a['issue_id']]
    assert {'OLD/1/E1', 'OLD/2/E1'} <= set(p['known_counterevidence_refs'])
    assert 'OLD/2/E1' in p['events']
    prompt = review.build_request()
    assert expand(parse(prompt['user_prompt']), prompt['reference_map']) == p
    assert 'ISSUE REVIEW BOUNDARY' in prompt['system_prompt']
    assert 'textual coverage only' in prompt['system_prompt']


def test_joint_review_is_one_call_input_with_separate_scope_anchors(joint, following):
    request, a, b = joint
    source = next_source(following, request.evidence, [a['issue_id'], b['issue_id']])
    reviews = source.build_review_inputs()
    assert len(reviews) == 1
    p = reviews[0].payload
    assert {i['problem'] for i in p['memory_issues']} == {a['problem'], b['problem']}
    assert set(p['issue_source_refs']) == {a['issue_id'], b['issue_id']}
    assert 'ATTR/unrelated' not in p['issue_source_refs'][a['issue_id']]
    kwargs = {**following[0], 'memory_evidence': request.evidence}
    prompt = build_issue_fusion_request(build_issue_fusion_input(**kwargs))
    assert 'Sharing a task, rule or edit alone is insufficient' in prompt['system_prompt']


def test_explicit_prior_dependency_remains_visible_not_silently_cleaned(joint):
    request, a, b = joint
    data = request.evidence.payload
    data['archive']['records']['ATTR/old']['source_refs'] = ['ATTR/unrelated']
    req = build_memory_update_input(ModificationEvidence(encode(data)))
    # An explicit older association is history, not something deterministic
    # traversal can declare semantically unrelated or delete automatically.
    assert 'ATTR/unrelated' in req.payload['issue_source_refs'][a['issue_id']]
    result = validate_memory_update(encode(a_response(req, a)), request=req)
    new = next(i for i in result.payload['memory']['issues'] if i['issue_id'] == a['issue_id'])['attempts'][-1]
    record = result.updated_evidence.payload['archive']['records'][new['source_refs'][0]]
    assert 'OLD/2/E1' in record['counterevidence_refs']
