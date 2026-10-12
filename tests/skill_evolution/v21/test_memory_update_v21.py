from copy import deepcopy

import pytest

from tests.skill_evolution.v21.test_modification_evidence_v21 import completed, setup, case
from src.skill_evolution.v19.edit_tracking_v19 import encode, parse
from src.skill_evolution.v21.evidence_wire_v21 import expand
from src.skill_evolution.v20.issue_memory_v20 import merge_update
from src.skill_evolution.v21.modification_evidence_v21 import ModificationEvidence, build_modification_evidence, open_memory_evidence, load_modification_evidence
from src.skill_evolution.v21.memory_update_v21 import build_memory_update_input, build_memory_update_request, validate_memory_update, run_memory_update


@pytest.fixture
def update_input(completed):
    return build_memory_update_input(build_modification_evidence(**completed))


def fresh_event(update_input, role='CANDIDATE'):
    p = update_input.payload
    return next(ref for ref, item in p['events'].items()
                if p['trajectories'][item['trajectory_ref']]['role'] == role
                and p['trajectories'][item['trajectory_ref']].get('pair_id') in p['current_pair_refs'])


def response(update_input):
    p = update_input.payload
    issue = p['memory_issues'][0]
    return {'issues': [{'issue_id': issue['issue_id'], 'problem': issue['problem'],
        'current_understanding': 'The revised choice completed this run compliantly. The old failed '
            'alternative and its scope limitation remain; the new joint attempt does not establish '
            'individual edit effects or generalization. Recheck applicable conditions before reuse.',
        'source_refs': [fresh_event(update_input, 'PARENT'), fresh_event(update_input)],
        'attempts': [{'attempt_id': 'NEW/revised-approach', 'approach': 'Bounded revised choice.',
            'assessment': 'The Candidate completed this task and was compliant in this run; '
                          'the individual edit effect and generalization remain unresolved.',
            'edit_refs': [e['edit_id'] for e in p['current_edits']],
            'source_refs': [fresh_event(update_input, 'PARENT'), fresh_event(update_input)]}]}]}


def completion(value):
    return {'finish_reason': 'stop', 'refusal': None, 'raw_response': encode(value)}


def test_new_attempt_uses_replay_sources_and_preserves_history_without_changing_schema(update_input):
    original = update_input.evidence.payload
    raw = encode(response(update_input))
    result = validate_memory_update(raw, request=update_input)
    p = result.payload
    assert original == update_input.evidence.payload
    assert p['memory']['schema_version'] == 'issue_memory_v20.1'
    before = original['memory']['issues'][0]
    after = p['memory']['issues'][0]
    assert after['attempts'][:-1] == before['attempts']
    new = after['attempts'][-1]
    assert set(new) == {'attempt_id', 'approach', 'assessment', 'edit_refs', 'source_refs'}
    assert new['attempt_id'].startswith('ATTEMPT/')
    assert new['source_refs'][0].startswith('ASSESSMENT_V21/')
    record = p['updated_evidence']['archive']['records'][new['source_refs'][0]]
    assert record['evidence_refs'] == response(update_input)['issues'][0]['attempts'][0]['source_refs']
    assert 'OLD/1/E1' in record['counterevidence_refs']
    assert 'ATTR/old' in record['source_refs']
    view = open_memory_evidence(result.updated_evidence, issue_refs=[after['issue_id']])
    assert 'OLD/1/E1' in view['events']
    assert set(record['evidence_refs']) <= view['events'].keys()
    assert merge_update(p['memory'], p['memory_update']) == p['memory']  # idempotent delta


def test_current_evidence_revises_old_attempt_and_unmentioned_attempt_is_unchanged(update_input):
    value = response(update_input)
    old = update_input.payload['memory_issues'][0]['attempts']
    value['issues'][0]['attempts'].append({
        'attempt_id': old[0]['attempt_id'], 'approach': old[0]['approach'],
        'assessment': 'New observed behavior limits the earlier task hypothesis; '
                      'the prior compliance caveat remains and causality is unresolved.',
        'edit_refs': [], 'source_refs': [fresh_event(update_input, 'PARENT')]})
    result = validate_memory_update(encode(value), request=update_input).payload
    attempts = result['memory']['issues'][0]['attempts']
    assert len(attempts) == len(old) + 1
    assert attempts[0]['assessment'] == value['issues'][0]['attempts'][1]['assessment']
    assert set(old[0]['source_refs']) < set(attempts[0]['source_refs'])
    assert attempts[0]['edit_refs'] == old[0]['edit_refs']
    assert attempts[1] == old[1]


def test_unselected_old_issue_can_be_loaded_without_an_extra_review(update_input):
    e = update_input.evidence.payload
    # Remove proposal association while retaining the issue and evidence archive.
    for p in e['proposals']:
        p['memory_issue_refs'] = []; p['memory_attempt_refs'] = []
    evidence = ModificationEvidence(encode(e))
    iid = e['memory']['issues'][0]['issue_id']
    unloaded = build_memory_update_input(evidence)
    assert not unloaded.payload['memory_issues']
    assert unloaded.payload['memory_catalog'][0]['issue_id'] == iid
    loaded = build_memory_update_input(evidence, issue_refs=[iid])
    assert validate_memory_update(encode(response(loaded)), request=loaded)
    with pytest.raises(ValueError, match='unloaded issue'):
        validate_memory_update(encode(response(loaded)), request=unloaded)


def test_two_axis_disagreement_is_carried_as_observations_not_inferred_effect_states(update_input):
    e = update_input.evidence.payload
    pair = e['archive']['pairs'][e['current_pair_refs'][0]]
    e['archive']['trajectories'][pair['parent']]['supervision'].update(success=True, compliant=False)
    e['archive']['trajectories'][pair['candidate']]['supervision'].update(success=False, compliant=True)
    req = build_memory_update_input(ModificationEvidence(encode(e)), pair_refs=[pair['pair_id']])
    def fake_model(prompt):
        wire = expand(parse(prompt['user_prompt']), prompt['reference_map'])
        assert wire['trajectories'][pair['parent']]['supervision']['success'] is True
        assert wire['trajectories'][pair['candidate']]['supervision']['success'] is False
        value = response(req)
        value['issues'][0]['attempts'][0]['assessment'] = (
            'This Candidate run is compliant but unsuccessful. The old run succeeded with a violation. '
            'These are separate observations, not joint success, and the cause of failure is unresolved.')
        return completion(value)
    prompt = build_memory_update_request(req)
    result = validate_memory_update(fake_model(prompt)['raw_response'], request=req)
    text = result.payload['memory']['issues'][0]['attempts'][-1]['assessment']
    assert 'compliant but unsuccessful' in text and 'unresolved' in text
    assert not {'effect', 'score', 'status'} & result.payload['memory']['issues'][0]['attempts'][-1].keys()


@pytest.mark.parametrize('mutation', [
    lambda x, r: x['issues'][0]['attempts'][0].update(source_refs=['PAIR/invented']),
    lambda x, r: x['issues'][0]['attempts'][0].update(source_refs=['OLD/0/E0']),
    lambda x, r: x['issues'][0]['attempts'][0].update(source_refs=[fresh_event(r, 'PARENT')]),
    lambda x, r: x['issues'][0]['attempts'][0].update(edit_refs=['EDIT/old']),
    lambda x, r: x['issues'][0]['attempts'][0].update(attempt_id='ATTEMPT/missing'),
    lambda x, r: x['issues'][0]['attempts'][0].update(effect='BENEFICIAL'),
    lambda x, r: x['issues'].append(deepcopy(x['issues'][0])),
    lambda x, r: x['issues'][0]['attempts'].append(deepcopy(x['issues'][0]['attempts'][0])),
    lambda x, r: x['issues'].clear(),
    lambda x, r: x['issues'][0].update(problem='Changed without evidence'),
])
def test_unsupported_sources_identity_and_edit_coverage_fail_closed(update_input, mutation):
    value = response(update_input); mutation(value, update_input)
    with pytest.raises(ValueError):
        validate_memory_update(encode(value), request=update_input)


def test_new_issue_and_joint_attempt_get_program_owned_stable_ids(update_input):
    value = response(update_input)
    item = value['issues'][0]
    item.update(issue_id='NEW/new-problem', problem='Newly observed bounded issue.',
                source_refs=[fresh_event(update_input)])
    first = validate_memory_update(encode(value), request=update_input)
    assert first == validate_memory_update(encode(value), request=update_input)
    p = first.payload
    assert p['memory']['issues'][0] == update_input.evidence.payload['memory']['issues'][0]
    assert p['memory']['issues'][-1]['issue_id'].startswith('ISSUE/')


def test_prompt_is_lossless_and_budget_failure_happens_before_transport(update_input, tmp_path):
    prompt = build_memory_update_request(update_input)
    restored = expand(parse(prompt['user_prompt']), prompt['reference_map'])
    for ref, item in update_input.payload['events'].items():
        assert restored['events'][ref]['event'] == item['event']
    assert restored['parent_pairs'] == update_input.payload['parent_pairs']
    assert 'Gate decisions' in prompt['system_prompt']
    output = tmp_path / 'over-budget'
    with pytest.raises(ValueError, match='exceeds budget'):
        run_memory_update(update_input, output=output, max_input_tokens=1,
                          transport=lambda _: pytest.fail('must not call'))
    assert not output.exists()


def test_one_call_resume_and_durable_evidence_without_active_head_write(update_input, tmp_path):
    root = tmp_path / 'update'
    calls = []
    def model(prompt):
        calls.append(prompt)
        return completion(response(update_input))
    result = run_memory_update(update_input, output=root, transport=model)
    restored = run_memory_update(update_input, output=root, resume=True,
                                transport=lambda _: pytest.fail('duplicate call'))
    assert restored == result and len(calls) == 1
    assert (root / 'complete.json').exists() and not (root / 'head.json').exists()
    saved = load_modification_evidence(root / 'updated-evidence.json',
                                       expected_ref=result.updated_evidence.evidence_ref)
    assert saved == result.updated_evidence
    assert saved.payload['prior_evidence_ref'] == update_input.evidence.evidence_ref
    with pytest.raises(ValueError, match='request changed'):
        run_memory_update(update_input, output=root, resume=True, model='different-model')


@pytest.mark.parametrize('kind', ['invalid', 'truncated', 'network'])
def test_failure_never_publishes_revision_or_retries_model(update_input, tmp_path, kind):
    root = tmp_path / kind
    def broken(prompt):
        if kind == 'network':
            raise RuntimeError('simulated network failure')
        if kind == 'truncated':
            return {**completion(response(update_input)), 'finish_reason': 'length'}
        return completion({'issues': []})
    with pytest.raises((ValueError, RuntimeError)):
        run_memory_update(update_input, output=root, transport=broken)
    for name in ('memory.json', 'memory-update.json', 'updated-evidence.json', 'complete.json'):
        assert not (root / name).exists()
    with pytest.raises(ValueError):
        run_memory_update(update_input, output=root, resume=True, transport=lambda _: pytest.fail('retry'))


def test_saved_revision_tamper_is_rejected_on_resume(update_input, tmp_path):
    root = tmp_path / 'update'
    run_memory_update(update_input, output=root, transport=lambda _: completion(response(update_input)))
    (root / 'memory.json').write_text('{}')
    with pytest.raises(ValueError, match='artifact changed'):
        run_memory_update(update_input, output=root, resume=True)


def test_same_approach_updates_existing_identity_without_creating_new_attempt(update_input):
    old = update_input.payload['memory_issues'][0]['attempts'][0]
    value = response(update_input)
    attempt = value['issues'][0]['attempts'][0]
    attempt.update(attempt_id=old['attempt_id'], approach=old['approach'])
    result = validate_memory_update(encode(value), request=update_input).payload
    attempts = result['memory']['issues'][0]['attempts']
    assert len(attempts) == len(update_input.payload['memory_issues'][0]['attempts'])
    assert attempts[0]['attempt_id'] == old['attempt_id']
    assert set(attempts[0]['edit_refs']) == set(old['edit_refs'] + attempt['edit_refs'])
    assert attempts[0]['assessment'] == attempt['assessment']


def test_multiple_edits_can_share_one_attempt_with_unresolved_effects(update_input):
    # Construct a two-edit evidence packet to test bookkeeping, not model quality.
    data = update_input.evidence.payload
    second = deepcopy(data['edits'][0])
    second['edit_id'] = 'EDIT_V21/second-fixture-edit'
    data['edits'].append(second)
    archived = deepcopy(data['archive']['edits'][data['edits'][0]['edit_id']])
    archived['edit_id'] = second['edit_id']
    data['archive']['edits'][second['edit_id']] = archived
    req = build_memory_update_input(ModificationEvidence(encode(data)))
    value = response(req)
    value['issues'][0]['attempts'][0]['assessment'] = (
        'The Candidate produced these paired observations; the joint and individual effects remain unresolved.')
    result = validate_memory_update(encode(value), request=req).payload
    assert len(result['memory_update']['issues'][0]['attempts']) == 1
    assert len(result['memory_update']['issues'][0]['attempts'][0]['edit_refs']) == 2


def test_mutated_view_or_stale_evidence_rejected_before_call(update_input):
    from dataclasses import replace
    p = update_input.payload
    ref = fresh_event(update_input)
    p['events'][ref]['event']['content'] = 'Invented original observation'
    bad = replace(update_input, payload_json=encode(p))
    with pytest.raises(ValueError, match='differs from original evidence'):
        build_memory_update_request(bad)
    evidence = update_input.evidence.payload
    evidence['round_id'] = 'another-round'
    with pytest.raises(ValueError, match='binding mismatch'):
        build_memory_update_request(replace(update_input, evidence=ModificationEvidence(encode(evidence))))
