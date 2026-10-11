"""Input coverage tests; label declines are observations, not causal findings."""
from copy import deepcopy
from dataclasses import replace

import pytest

from tests.skill_evolution.test_memory_update_v21 import update_input, completed, setup, case, response
from tests.skill_evolution.test_memory_consumption_v21 import following
from tests.skill_evolution.test_local_generation_v20 import proposal
from src.skill_evolution.edit_tracking_v19 import encode
from src.skill_evolution.modification_evidence_v21 import ModificationEvidence, open_memory_evidence
from src.skill_evolution.memory_update_v21 import (
    regression_pair_refs, build_memory_update_input, build_memory_update_request,
    validate_memory_update, run_memory_update,
)
from src.skill_evolution.memory_consumption_v21 import build_issue_fusion_input, build_generation_input
from src.skill_evolution.issue_fusion_v20 import validate_issue_fusion
from src.skill_evolution.evidence_wire_v21 import expand
from src.skill_evolution.edit_tracking_v19 import parse


def baseline(evidence):
    return open_memory_evidence(evidence,
        proposal_refs=[p['proposal_issue_id'] for p in evidence.payload['proposals']])


def neutral(update_input):
    data = update_input.evidence.payload
    for pid in data['current_pair_refs']:
        pair = data['archive']['pairs'][pid]
        for role in ('parent', 'candidate'):
            data['archive']['trajectories'][pair[role]]['supervision'].update(success=True, compliant=True)
    return data


def set_labels(data, pid, parent, candidate):
    pair = data['archive']['pairs'][pid]
    for role, labels in (('parent', parent), ('candidate', candidate)):
        data['archive']['trajectories'][pair[role]]['supervision'].update(
            success=labels[0], compliant=labels[1])


def assert_original_pair_loaded(request, pid):
    original = request.evidence.payload['archive']
    p = request.payload
    assert p['pairs'][pid] == original['pairs'][pid]
    for role in ('parent', 'candidate'):
        tid = p['pairs'][pid][role]
        assert p['trajectories'][tid] == original['trajectories'][tid]
        expected = {r: e for r, e in original['events'].items() if e['trajectory_ref'] == tid}
        assert expected and all(p['events'][r] == e for r, e in expected.items())
        context = original['trajectories'][tid]['context_ref']
        assert p['contexts'][context] == original['contexts'][context]


def test_default_detects_previously_unselected_failure_without_full_round_loading(update_input):
    old = baseline(update_input.evidence)
    assert len(old['pairs']) == 1
    p = update_input.payload
    assert len(p['regression_pair_refs']) == 1
    ref = p['regression_pair_refs'][0]
    assert ref not in old['pairs'] and p['pairs'][ref]['task_ref'] == 'T002'
    assert set(p['pairs']) == set(old['pairs']) | {ref}
    assert len(p['pairs']) < len(update_input.evidence.payload['current_pair_refs'])
    assert set(old['events']) <= p['events'].keys()  # prior support/counterevidence not replaced
    assert p['memory_issues'] == old['memory_issues']
    assert_original_pair_loaded(update_input, ref)
    prompt = build_memory_update_request(update_input)
    assert expand(parse(prompt['user_prompt']), prompt['reference_map']) == p


@pytest.mark.parametrize('parent,candidate,declines', [
    ((True, True), (False, True), True),
    ((True, True), (True, False), True),
    ((True, True), (False, False), True),
    ((True, False), (False, True), True),  # improved compliance cannot cancel success decline
    ((False, True), (True, False), True),  # improved success cannot cancel compliance decline
    ((False, False), (False, False), False),
    ((False, False), (True, True), False),
    ((True, True), (True, True), False),
])
def test_both_dimensions_independently_select_new_adverse_pairs(update_input, parent, candidate, declines):
    data = neutral(update_input)
    pid = data['current_pair_refs'][-1]  # outside the pre-edit proposal's cited case
    set_labels(data, pid, parent, candidate)
    request = build_memory_update_input(ModificationEvidence(encode(data)))
    assert request.payload['regression_pair_refs'] == ([pid] if declines else [])
    assert (pid in request.payload['pairs']) == declines
    if declines:
        assert_original_pair_loaded(request, pid)


def test_explicit_selection_cannot_disable_regression_coverage_or_duplicate_pairs(update_input):
    refs = regression_pair_refs(update_input.evidence)
    empty = build_memory_update_input(update_input.evidence, proposal_refs=[], pair_refs=[])
    explicit = build_memory_update_input(update_input.evidence, proposal_refs=[], pair_refs=list(refs) * 2)
    assert empty == explicit
    assert set(empty.payload['pairs']) == set(refs)
    assert not empty.payload['memory_issues']  # loading a decline does not invent issue ownership
    assert empty.payload['memory_catalog']


def test_no_decline_preserves_previous_selected_evidence_scope(update_input):
    data = neutral(update_input)
    evidence = ModificationEvidence(encode(data))
    old = baseline(evidence)
    request = build_memory_update_input(evidence)
    assert not request.payload['regression_pair_refs']
    for key in ('events', 'trajectories', 'contexts', 'pairs', 'source_records', 'memory_issues'):
        assert request.payload[key] == old[key]


def test_historical_decline_is_not_automatically_treated_as_current(update_input):
    data = neutral(update_input)
    archive = data['archive']
    old_id = 'PAIR/historical-decline'
    original_pair = archive['pairs'][data['current_pair_refs'][-1]]
    old = {**original_pair, 'pair_id': old_id, 'round_id': 'older-round'}
    refs = []
    for role in ('parent', 'candidate'):
        tid = old_id + '/' + role
        meta = deepcopy(archive['trajectories'][original_pair[role]])
        meta.update(trajectory_ref=tid, pair_id=old_id, source_round_id='older-round')
        meta['supervision'].update(success=(role == 'parent'), compliant=True)
        archive['trajectories'][tid] = meta
        originals = [e for e in archive['events'].values() if e['trajectory_ref'] == original_pair[role]]
        for n, event in enumerate(originals):
            ref = f'{tid}/E{n}'
            archive['events'][ref] = {**event, 'trajectory_ref': tid}
            refs.append(ref)
        old[role] = tid
    archive['pairs'][old_id] = old
    archive['records'][old_id] = {'ref': old_id, 'kind': 'REPLAY', 'statement': 'Historical observations.',
        'evidence_refs': refs, 'counterevidence_refs': [], 'edit_refs': [], 'source_refs': []}
    request = build_memory_update_input(ModificationEvidence(encode(data)))
    assert not request.payload['regression_pair_refs'] and old_id not in request.payload['pairs']
    # Explicit historical loading is still supported.
    chosen = build_memory_update_input(ModificationEvidence(encode(data)), pair_refs=[old_id])
    assert old_id in chosen.payload['pairs'] and old_id not in chosen.payload['regression_pair_refs']


@pytest.mark.parametrize('damage', ['flag', 'pair', 'candidate_events'])
def test_removed_regression_evidence_is_rejected_before_dispatch(update_input, damage):
    p = update_input.payload
    pid = p['regression_pair_refs'][0]
    if damage == 'flag':
        p['regression_pair_refs'] = []
    elif damage == 'pair':
        del p['pairs'][pid]
    else:
        tid = p['pairs'][pid]['candidate']
        p['events'] = {r: e for r, e in p['events'].items() if e['trajectory_ref'] != tid}
    with pytest.raises(ValueError, match='differs from original evidence'):
        build_memory_update_request(replace(update_input, payload_json=encode(p)))


@pytest.mark.parametrize('damage', ['missing_label', 'non_boolean', 'role', 'skill', 'index'])
def test_malformed_current_replay_fails_instead_of_silently_losing_cases(update_input, damage):
    data = update_input.evidence.payload
    pid = data['current_pair_refs'][-1]
    meta = data['archive']['trajectories'][data['archive']['pairs'][pid]['candidate']]
    if damage == 'missing_label':
        del meta['supervision']['compliant']
    elif damage == 'non_boolean':
        meta['supervision']['success'] = 'false'
    elif damage == 'role':
        meta['role'] = 'PARENT'
    elif damage == 'skill':
        meta['skill_ref'] = data['parent_skill_ref']
    else:
        data['current_pair_refs'].remove(pid)
    with pytest.raises(ValueError):
        build_memory_update_input(ModificationEvidence(encode(data)))


def test_budget_failure_does_not_drop_mandatory_pairs_or_call_a_model(update_input, tmp_path):
    prompt = build_memory_update_request(update_input)
    before = update_input.payload_json
    with pytest.raises(ValueError, match='exceeds budget'):
        run_memory_update(update_input, output=tmp_path/'over-budget',
            max_input_tokens=prompt['input_budget']['proxy_input_tokens'] - 1,
            transport=lambda _: pytest.fail('must not call'))
    assert update_input.payload_json == before and not (tmp_path/'over-budget').exists()


def test_cited_new_problem_reaches_review_without_assigning_the_decline_to_an_edit(update_input, following):
    p = update_input.payload
    pid = p['regression_pair_refs'][0]
    refs = [next(r for r, e in p['events'].items() if e['trajectory_ref'] == p['pairs'][pid][role])
            for role in ('parent', 'candidate')]
    raw = response(update_input)
    raw['issues'].append({'issue_id': 'NEW/unexplained-decline',
        'problem': 'Observed task failure after a previously successful run; local cause unresolved.',
        'current_understanding': 'This paired task outcome declined; local cause remains unresolved.',
        'source_refs': refs, 'attempts': []})
    result = validate_memory_update(encode(raw), request=update_input)
    new = result.payload['memory']['issues'][-1]
    assert new['attempts'] == []
    original_issue = result.payload['memory']['issues'][0]
    assert original_issue['problem'] == p['memory_issues'][0]['problem']
    assert len(original_issue['attempts']) == len(p['memory_issues'][0]['attempts']) + 1
    kwargs = {**following[0], 'memory_evidence': result.updated_evidence}
    fusion = build_issue_fusion_input(**kwargs)
    selected = proposal([f['finding_id'] for f in fusion.payload['current_findings']], [new['issue_id']])
    choice = validate_issue_fusion(encode({'schema_version': 'issue_fusion_response_v20.1',
        'issues': [selected], 'unassociated_findings': []}), request=fusion)
    generation = build_generation_input(**kwargs, fusion_input=fusion, fusion_result=choice)
    review = generation.build_review_inputs()[0].payload
    assert review['memory_issues'][0]['issue_id'] == new['issue_id'] and pid in review['pairs']
    assert review['memory_issues'][0]['current_understanding']
    assert set(refs) <= review['events'].keys()
    for role in ('parent', 'candidate'):
        tid = review['pairs'][pid][role]
        assert review['trajectories'][tid] == p['trajectories'][tid]
