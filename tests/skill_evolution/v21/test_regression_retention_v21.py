"""Cross-round citation auditing; fixtures are not semantic model validation."""
from copy import deepcopy

import pytest

from tests.skill_evolution.v21.test_memory_update_v21 import update_input, completed, setup, case, response, completion
from tests.skill_evolution.v21.test_memory_consumption_v21 import following
from tests.skill_evolution.v20.test_local_generation_v20 import proposal
from src.skill_evolution.v19.edit_tracking_v19 import encode, parse
from src.skill_evolution.v21.modification_evidence_v21 import ModificationEvidence
from src.skill_evolution.v21.memory_update_v21 import MemoryUpdateResult, build_memory_update_input, regression_retention_report, validate_memory_update, run_memory_update
from src.skill_evolution.v21.memory_consumption_v21 import build_issue_fusion_input, build_generation_input
from src.skill_evolution.v20.issue_fusion_v20 import validate_issue_fusion


def add_observation(request, roles=('parent', 'candidate')):
    payload = request.payload
    pid = payload['regression_pair_refs'][0]
    refs = [next(r for r, e in payload['events'].items()
                 if e['trajectory_ref'] == payload['pairs'][pid][role]) for role in roles]
    value = response(request)
    value['issues'].append({'issue_id': 'NEW/observed-decline',
        'problem': 'Observed outcome decline in a separate task; the behavioral cause is unknown.',
        'current_understanding': 'This paired task outcome declined without an established local cause. '
            'The observation does not justify a repair rule or an edit attribution.',
        'source_refs': refs, 'attempts': []})
    return value, pid


def test_missing_decline_is_reported_without_inventing_issue_ownership(update_input):
    result = validate_memory_update(encode(response(update_input)), request=update_input)
    before = result.payload_json
    report = regression_retention_report(update_input, result)
    assert report['uncited_pair_refs'] == update_input.payload['regression_pair_refs']
    assert not report['one_sided_pair_refs'] and not report['unreadable_pair_refs']
    assert all(not row['issues'] for row in report['pairs'])
    assert result.payload_json == before
    assert len(result.payload['memory']['issues']) == len(update_input.evidence.payload['memory']['issues'])
    assert 'NOT_SEMANTIC_TRUTH' in report['scope']


@pytest.mark.parametrize('roles', [('candidate',), ('parent',), ('parent', 'candidate')])
def test_direct_citations_are_distinct_from_complete_issue_local_readability(update_input, roles):
    value, pid = add_observation(update_input, roles)
    result = validate_memory_update(encode(value), request=update_input)
    report = regression_retention_report(update_input, result)
    assert report['uncited_pair_refs'] == []
    assert report['one_sided_pair_refs'] == ([] if len(roles) == 2 else [pid])
    assert report['unreadable_pair_refs'] == []
    row = next(r for r in report['pairs'] if r['pair_ref'] == pid)
    assert len(row['issues']) == 1
    new = result.payload['memory']['issues'][-1]
    assert row['issues'][0]['issue_id'] == new['issue_id']
    assert row['issues'][0]['review_has_complete_pair']
    assert new['attempts'] == []  # no invented edit or causal ownership
    original = result.payload['memory']['issues'][0]
    assert original['problem'] == update_input.payload['memory_issues'][0]['problem']
    for role in ('parent', 'candidate'):
        assert bool(row['issues'][0][role + '_event_refs']) == (role in roles)


def test_opposite_sides_in_different_issues_do_not_become_one_paired_understanding(update_input):
    value, pid = add_observation(update_input, ('parent',))
    second, _ = add_observation(update_input, ('candidate',))
    item = second['issues'][-1]
    item['issue_id'] = 'NEW/another-question'
    item['problem'] = 'A separate question about the candidate behavior, still unresolved.'
    value['issues'].append(item)
    result = validate_memory_update(encode(value), request=update_input)
    report = regression_retention_report(update_input, result)
    assert report['one_sided_pair_refs'] == [pid]
    assert len(report['pairs'][0]['issues']) == 2


def test_alias_of_the_same_parent_is_counted_as_parent_not_another_observation(update_input):
    data = update_input.evidence.payload
    pid = update_input.payload['regression_pair_refs'][0]
    archive = data['archive']
    tid = archive['pairs'][pid]['parent']
    alias = 'TRAJECTORY/parent-alias'
    archive['trajectories'][alias] = {**archive['trajectories'][tid], 'trajectory_ref': alias}
    archive['parent_pairs'][alias] = pid
    event = next(e for e in archive['events'].values() if e['trajectory_ref'] == tid)
    archive['events']['ALIAS/E1'] = {**event, 'trajectory_ref': alias}
    # Explicitly open the known alias observation as well as the complete pair.
    # Alias loading is induced through a real source link, not forged input data.
    source = archive['records'][pid]
    source['evidence_refs'].append('ALIAS/E1')
    request = build_memory_update_input(ModificationEvidence(encode(data)))
    value, _ = add_observation(request, ('candidate',))
    value['issues'][-1]['source_refs'].append('ALIAS/E1')
    result = validate_memory_update(encode(value), request=request)
    report = regression_retention_report(request, result)
    assert not report['uncited_pair_refs'] and not report['one_sided_pair_refs']
    assert report['pairs'][0]['issues'][0]['parent_event_refs'] == ['ALIAS/E1']


def test_new_observation_reaches_fusion_and_only_its_selected_review(update_input, following):
    value, pid = add_observation(update_input)
    result = validate_memory_update(encode(value), request=update_input)
    evidence = result.updated_evidence
    new = evidence.payload['memory']['issues'][-1]
    kwargs = {**following[0], 'memory_evidence': evidence}
    fusion = build_issue_fusion_input(**kwargs)
    selected = next(i for i in fusion.payload['memory_issues'] if i['issue_id'] == new['issue_id'])
    assert selected['current_understanding'] == value['issues'][-1]['current_understanding']
    assert not selected['attempts']
    decision = proposal([f['finding_id'] for f in fusion.payload['current_findings']], [new['issue_id']])
    choice = validate_issue_fusion(encode({'schema_version': 'issue_fusion_response_v20.1',
        'issues': [decision], 'unassociated_findings': []}), request=fusion)
    reviews = build_generation_input(**kwargs, fusion_input=fusion, fusion_result=choice).build_review_inputs()
    assert len(reviews) == 1  # no new review layer
    view = reviews[0].payload
    assert [i['issue_id'] for i in view['memory_issues']] == [new['issue_id']]
    assert pid in view['pairs']
    for role in ('parent', 'candidate'):
        tid = update_input.payload['pairs'][pid][role]
        expected = {r: e for r, e in update_input.payload['events'].items() if e['trajectory_ref'] == tid}
        assert expected and all(view['events'][r] == e for r, e in expected.items())


def test_report_is_checkpointed_and_resume_does_not_call_or_silently_replace_it(update_input, tmp_path):
    root = tmp_path/'update'
    result = run_memory_update(update_input, output=root, transport=lambda _: completion(response(update_input)))
    report = parse((root/'regression-retention.json').read_text())
    assert report == regression_retention_report(update_input, result)
    assert 'regression-retention.json' in parse((root/'complete.json').read_text())['files']
    no_call = lambda _: pytest.fail('must reuse completed response')
    assert run_memory_update(update_input, output=root, resume=True, transport=no_call) == result
    (root/'regression-retention.json').write_text('{}')
    with pytest.raises(ValueError, match='saved Memory update artifact changed'):
        run_memory_update(update_input, output=root, resume=True, transport=no_call)


def test_audit_rejects_a_result_that_disagrees_with_its_original_response(update_input):
    result = validate_memory_update(encode(response(update_input)), request=update_input)
    corrupted = deepcopy(result.payload)
    corrupted['memory']['issues'][0]['problem'] = 'Wrong ownership'
    with pytest.raises(ValueError, match='differs from validated response'):
        regression_retention_report(update_input, MemoryUpdateResult(encode(corrupted)))


def test_no_decline_has_no_artificial_retention_obligation(update_input):
    data = update_input.evidence.payload
    for pair in data['archive']['pairs'].values():
        for role in ('parent', 'candidate'):
            data['archive']['trajectories'][pair[role]]['supervision'].update(success=True, compliant=True)
    request = build_memory_update_input(ModificationEvidence(encode(data)))
    result = validate_memory_update(encode(response(request)), request=request)
    report = regression_retention_report(request, result)
    assert report['pairs'] == report['uncited_pair_refs'] == report['one_sided_pair_refs'] == []


def test_incidental_shared_edit_context_does_not_count_as_issue_understanding(update_input):
    data = update_input.evidence.payload
    pid = update_input.payload['regression_pair_refs'][0]
    candidate = data['archive']['pairs'][pid]['candidate']
    ref = next(r for r, e in data['archive']['events'].items() if e['trajectory_ref'] == candidate)
    data['archive']['records']['SHARED/context'] = {
        'ref': 'SHARED/context', 'kind': 'ATTRIBUTION', 'statement': 'Shared context, not issue ownership.',
        'evidence_refs': [ref], 'counterevidence_refs': [], 'source_refs': [],
        'edit_refs': [data['edits'][0]['edit_id']]}
    request = build_memory_update_input(ModificationEvidence(encode(data)))
    value = response(update_input)  # original citations exclude the unrelated pair
    result = validate_memory_update(encode(value), request=request)
    report = regression_retention_report(request, result)
    assert report['uncited_pair_refs'] == [pid]
