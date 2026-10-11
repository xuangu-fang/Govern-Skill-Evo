"""Current synthesis and selective consumption, without extra model calls."""
from copy import deepcopy

import pytest

from tests.skill_evolution.test_memory_update_v21 import (
    update_input, completed, setup, case, response, fresh_event, completion,
)
from tests.skill_evolution.test_memory_consumption_v21 import following
from tests.skill_evolution.test_local_generation_v20 import proposal
from src.skill_evolution.edit_tracking_v19 import encode, parse
from src.skill_evolution.issue_memory_v20 import merge_update
from src.skill_evolution.modification_evidence_v21 import ModificationEvidence, open_memory_evidence
from src.skill_evolution.current_understanding_v21 import (
    current_understanding, open_current_memory_evidence, PREFIX, MAX_CHARACTERS,
)
from src.skill_evolution.memory_update_v21 import (
    build_memory_update_input, validate_memory_update, run_memory_update,
)
from src.skill_evolution.memory_consumption_v21 import (
    build_issue_fusion_input, build_issue_fusion_request, build_generation_input,
)
from src.skill_evolution.issue_fusion_v20 import validate_issue_fusion
from src.skill_evolution.evidence_review_v20 import validate_evidence_review
from src.skill_evolution.evidence_wire_v21 import pack, expand


def updated(request):
    return validate_memory_update(encode(response(request)), request=request).updated_evidence


def review_for(following, evidence, attempts=()):
    kwargs = {**following[0], 'memory_evidence': evidence}
    fusion = build_issue_fusion_input(**kwargs)
    issue = fusion.payload['memory_issues'][0]
    selected = proposal([f['finding_id'] for f in fusion.payload['current_findings']],
                        [issue['issue_id']], attempts)
    result = validate_issue_fusion(encode({'schema_version': 'issue_fusion_response_v20.1',
        'issues': [selected], 'unassociated_findings': []}), request=fusion)
    return build_generation_input(**kwargs, fusion_input=fusion, fusion_result=result).build_review_inputs()[0]


def test_single_update_saves_synthesis_and_complete_attempts_without_new_memory_fields(update_input, tmp_path):
    calls = []
    def model(prompt):
        calls.append(prompt)
        return completion(response(update_input))
    result = run_memory_update(update_input, output=tmp_path/'update', transport=model)
    assert len(calls) == 1
    evidence = result.updated_evidence
    issue = evidence.payload['memory']['issues'][0]
    summary = current_understanding(issue, evidence.payload['archive'])
    assert summary['statement'] == response(update_input)['issues'][0]['current_understanding']
    assert summary['ref'] in issue['source_refs']
    assert set(issue) == {'issue_id', 'problem', 'source_refs', 'attempts'}
    assert issue['attempts'][:-1] == update_input.payload['memory_issues'][0]['attempts']
    assert 'OLD/1/E1' in summary['counterevidence_refs']
    assert all(r.startswith('PAIR/') for r in summary['source_refs'])
    assert summary['edit_refs'] == []  # not a fabricated aggregate attempt
    assert run_memory_update(update_input, output=tmp_path/'update', resume=True,
                             transport=lambda _: pytest.fail('extra summarizer')) == result


def test_revision_replaces_current_synthesis_and_keeps_previous_sources(update_input):
    first = updated(update_input)
    before = first.payload['memory']['issues'][0]
    old = current_understanding(before, first.payload['archive'])
    request = build_memory_update_input(first)
    assert request.payload['memory_issues'][0]['current_understanding'] == old['statement']
    value = response(request)
    value['issues'][0]['attempts'] = []  # test revision of synthesis alongside actual edit bookkeeping below
    # Reuse the recorded attempt rather than inventing another attempt for these same observations.
    attempt = deepcopy(before['attempts'][-1])
    attempt['source_refs'] = [fresh_event(request)]
    value['issues'][0]['attempts'] = [attempt]
    value['issues'][0]['current_understanding'] = (
        'Revised interpretation: the observed compliant result remains limited to this condition; '
        'the older counterexample still restricts reuse. No independent edit effect is established.')
    second = validate_memory_update(encode(value), request=request).updated_evidence
    issue = second.payload['memory']['issues'][0]
    latest = current_understanding(issue, second.payload['archive'])
    assert latest['statement'] == value['issues'][0]['current_understanding']
    assert old['ref'] != latest['ref'] and old['ref'] in issue['source_refs']
    assert second.payload['archive']['records'][old['ref']] == old
    assert old['ref'] not in latest['source_refs']
    assert len(issue['attempts']) == len(before['attempts'])


@pytest.mark.parametrize('damage', ['missing', 'blank', 'long', 'summary_as_event', 'no_current'])
def test_invalid_synthesis_is_rejected_not_truncated_or_published(update_input, damage):
    value = response(update_input)
    issue = value['issues'][0]
    if damage == 'missing':
        del issue['current_understanding']
    elif damage == 'blank':
        issue['current_understanding'] = '   '
    elif damage == 'long':
        issue['current_understanding'] = 'x' * (MAX_CHARACTERS + 1)
    elif damage == 'summary_as_event':
        issue['source_refs'] = [next(iter(update_input.payload['source_records']))]
    else:
        issue['source_refs'] = ['OLD/0/E0']
    with pytest.raises(ValueError):
        validate_memory_update(encode(value), request=update_input)


def test_fusion_gets_one_synthesis_and_attempt_directory_not_all_assessments(update_input, following):
    evidence = updated(update_input)
    request = build_issue_fusion_input(**{**following[0], 'memory_evidence': evidence})
    issue = request.payload['memory_issues'][0]
    stored = evidence.payload['memory']['issues'][0]
    assert issue['problem'] == stored['problem']
    assert issue['current_understanding'] == current_understanding(stored, evidence.payload['archive'])['statement']
    assert {a['attempt_id'] for a in issue['attempts']} == {a['attempt_id'] for a in stored['attempts']}
    assert all(set(a) == {'attempt_id', 'approach', 'current_binding'} for a in issue['attempts'])
    prompt = build_issue_fusion_request(request)
    assert 'ARCHIVED_NOT_LOADED' not in prompt['user_prompt']  # validator-only compatibility placeholder
    assert all(a['assessment'] not in prompt['user_prompt'] for a in stored['attempts'])


def test_default_review_does_not_expand_old_positive_diary_but_keeps_counterexample(update_input, following):
    evidence = updated(update_input)
    issue = evidence.payload['memory']['issues'][0]
    full = open_memory_evidence(evidence, issue_refs=[issue['issue_id']])
    request = review_for(following, evidence)
    p = request.payload
    assert not p['memory_issues'][0]['attempts']
    assert p['memory_issues'][0]['current_understanding']
    assert 'ATTR/old' not in p['source_records']
    assert 'OLD/0/E0' not in p['events']
    assert 'OLD/0/E0' in full['events']  # full archive still readable on demand
    assert 'OLD/1/E1' in p['known_counterevidence_refs'] and 'OLD/1/E1' in p['events']
    for pair in p['pairs'].values():
        for role in ('parent', 'candidate'):
            refs = {r for r, e in evidence.payload['archive']['events'].items() if e['trajectory_ref'] == pair[role]}
            assert refs <= p['events'].keys()
    wire, refs = pack(p)
    assert expand(wire, refs) == p
    # A review still may not drop preserved counterexamples.
    with pytest.raises(ValueError, match='reference errors'):
        validate_evidence_review(encode({'proposal_id': p['proposal_id'], 'verdict': 'NO_EDIT',
            'evidence_refs': [], 'counterevidence_refs': [], 'reason': 'No justified edit.', 'gap': None}), request=request)


def test_explicit_attempt_selection_reopens_its_original_and_joint_restrictions(update_input, following):
    evidence = updated(update_input)
    old = evidence.payload['memory']['issues'][0]['attempts'][0]
    request = review_for(following, evidence, [old['attempt_id']])
    p = request.payload
    assert p['memory_issues'][0]['attempts'] == [old]
    assert 'ATTR/old' in p['source_records'] and 'OLD/0/E0' in p['events']
    assert 'OLD/1/E1' in p['known_counterevidence_refs']
    assert p['memory_issues'][0]['current_understanding']


def test_legacy_issue_falls_back_to_complete_history_without_fake_synthesis(update_input, following):
    evidence = update_input.evidence
    issue = evidence.payload['memory']['issues'][0]
    full = open_memory_evidence(evidence, issue_refs=[issue['issue_id']])
    view = open_current_memory_evidence(evidence, issue_refs=[issue['issue_id']])
    assert view['memory_issues'] == full['memory_issues']
    for key in ('events', 'source_records', 'pairs', 'issue_source_refs'):
        assert view[key] == full[key]
    fusion = build_issue_fusion_input(**{**following[0], 'memory_evidence': evidence})
    assert 'current_understanding' not in fusion.payload['memory_issues'][0]
    assert all('assessment' in a for a in fusion.payload['memory_issues'][0]['attempts'])


def test_unknown_attempt_cannot_request_other_history(update_input):
    evidence = updated(update_input)
    iid = evidence.payload['memory']['issues'][0]['issue_id']
    with pytest.raises(ValueError, match='outside selected issues'):
        open_current_memory_evidence(evidence, issue_refs=[iid], attempt_refs=['ATTEMPT/unknown'])


def test_broken_summary_source_fails_instead_of_silently_using_legacy_view(update_input):
    evidence = updated(update_input).payload
    issue = evidence['memory']['issues'][0]
    ref = issue['source_refs'][-1]
    del evidence['archive']['records'][ref]
    with pytest.raises(ValueError, match='missing current understanding'):
        current_understanding(issue, evidence['archive'])


def test_earlier_observed_decline_survives_a_later_synthesis_without_its_citation(update_input):
    p = update_input.payload
    pid = p['regression_pair_refs'][0]
    pair = p['pairs'][pid]
    adverse = next(r for r, e in p['events'].items() if e['trajectory_ref'] == pair['candidate'])
    value = response(update_input)
    value['issues'][0]['source_refs'].append(adverse)
    first = validate_memory_update(encode(value), request=update_input).updated_evidence
    issue = first.payload['memory']['issues'][0]
    previous = current_understanding(issue, first.payload['archive'])
    req = build_memory_update_input(first)
    value = response(req)
    # Use only the non-declining first pair for this controlled revision.
    good_pair = next(v for k, v in req.payload['pairs'].items() if k != pid)
    support = next(r for r, e in req.payload['events'].items() if e['trajectory_ref'] == good_pair['candidate'])
    value['issues'][0]['source_refs'] = [support]
    value['issues'][0]['attempts'][0]['source_refs'] = [support]
    value['issues'][0]['current_understanding'] = 'New support is limited; the earlier paired decline remains unresolved.'
    second = validate_memory_update(encode(value), request=req).updated_evidence
    view = open_current_memory_evidence(second, issue_refs=[issue['issue_id']])
    assert previous['ref'] not in view['source_records']
    assert pid in view['pairs'] and adverse in view['events']
    assert all(pair[role] in view['trajectories'] for role in ('parent', 'candidate'))


def test_many_attempts_remain_local_and_compact_fusion_reduces_prose_input(update_input, following):
    data = update_input.evidence.payload
    issue = data['memory']['issues'][0]
    data['memory'] = merge_update(data['memory'], {'schema_version': 'issue_memory_update_v20.1',
        'run_id': data['run_id'], 'round_id': 'old', 'issues': [{
            'issue_id': issue['issue_id'], 'attempts': [{'new_attempt_key': f'fixture-{n}',
                'approach': f'Historical variant {n}',
                'assessment': ('Fixture-only repeated history, with conditions and uncertainty. ' * 30),
                'edit_refs': ['EDIT/old'], 'source_refs': ['ATTR/old']} for n in range(12)]}]})
    legacy = ModificationEvidence(encode(data))
    request = build_memory_update_input(legacy)
    evidence = updated(request)
    old_prompt = build_issue_fusion_request(build_issue_fusion_input(**{**following[0], 'memory_evidence': legacy}))
    new_prompt = build_issue_fusion_request(build_issue_fusion_input(**{**following[0], 'memory_evidence': evidence}))
    assert len(evidence.payload['memory']['issues'][0]['attempts']) == 15
    assert new_prompt['input_budget']['proxy_input_tokens'] < old_prompt['input_budget']['proxy_input_tokens']
    assert 'Fixture-only repeated history' not in new_prompt['user_prompt']
    p = review_for(following, evidence).payload
    assert not p['memory_issues'][0]['attempts'] and 'OLD/1/E1' in p['events']


def test_unmentioned_issue_keeps_synthesis_and_history(update_input):
    first = updated(update_input)
    data = first.payload
    original = deepcopy(data['memory']['issues'][0])
    # A new distinct issue can carry the actual edit bookkeeping without
    # changing the previous issue merely because the same replay was loaded.
    req = build_memory_update_input(ModificationEvidence(encode(data)))
    value = response(req)
    value['issues'][0].update(issue_id='NEW/another-problem', problem='Another observed problem.')
    result = validate_memory_update(encode(value), request=req)
    assert result.payload['memory']['issues'][0] == original
    prior = current_understanding(original, first.payload['archive'])
    assert result.updated_evidence.payload['archive']['records'][prior['ref']] == prior
