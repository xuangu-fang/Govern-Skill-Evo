"""Deterministic material checks; semantic conclusions are reviewed in OFFLINE_REVIEW.md."""
from copy import deepcopy

import pytest

from src.skill_evolution.v23.diagnosis import validate_diagnosis
from src.skill_evolution.v23.editor import apply_patch
from src.skill_evolution.v23.memory import commit_memory, load_memory, validate_entries, validate_memory
from src.skill_evolution.v23.replay import validate_payload
from src.skill_evolution.v23_3.memory_view import project_payload
from src.skill_evolution.v23_4.update_patch import normalize_update_patches
from .offline_cases import cases, run


@pytest.mark.parametrize('case', cases(), ids=lambda c: c['id'])
def test_complete_case_material_and_patch_correspondence(case, tmp_path):
    payload, raw = case['payload'], case['output']
    before = deepcopy(case)
    assert set(payload) == {'parent', 'plan', 'command_sets', 'runs', 'grouping', 'memory'}
    validate_diagnosis({'decision': 'revise', 'reason': 'Synthetic reviewed proposal.', 'plan': payload['plan']}, payload)
    validate_payload(case['replay_payload'])
    validate_entries(case['replay_output'], case['replay_payload'])
    validate_memory(payload['memory'])
    legacy, effective = normalize_update_patches(raw, payload)
    assert legacy['decision'] == ('no_change' if case['id'] == 'A8' else 'ready')
    if effective is not None:
        assert effective['goal'] == payload['plan']['goal']
        for a, original, compiled in zip(raw['adjustments'], payload['plan']['updates'], effective['updates']):
            assert compiled['basis'] == original['basis']
            if a['change'] == 'KEEP': assert compiled == original
            else:
                assert apply_patch(original['text'], a['to']['patch']) == compiled['text']
                # For these human-authored witnesses only, change contains the full
                # intended replacement. This is NOT a general semantic validator.
                assert compiled['text'].strip() == a['change']
    context = {'payload': case['replay_payload'], 'execution_context': {'synthetic': True}}
    commit_memory(tmp_path, context_id=f'H_{case["id"]}', context=context, result=case['replay_output'])
    loaded = load_memory(tmp_path)
    assert loaded['entries'][0]['evidence'] == payload['memory']['entries'][0]['evidence']
    if case['id'] != 'A7': assert loaded['entries'] == payload['memory']['entries']
    else:
        # Deliberately stale knowledge is structurally legal but contradicted by Diff.
        assert loaded['entries'][0]['knowledge'] != payload['memory']['entries'][0]['knowledge']
        assert 'repair' not in apply_patch(case['replay_payload']['parent'], case['replay_payload']['diff'])
    assert project_payload(payload)['memory']['entries'] == payload['memory']['entries']
    assert case == before


@pytest.mark.parametrize('cid', ['A1', 'A3'])
def test_changed_evidence_requires_reconsidering_reason_not_forced_edit(cid):
    case = next(c for c in cases() if c['id'] == cid)
    changed = deepcopy(case['payload'])
    sources = changed['memory']['sources']
    if cid == 'A1':
        q = sources['H_A1/Q1']['run']
        q['initial']['observation'] = 'The drawer is visibly unlocked but opening failed.'
        for step in q['steps']:
            step['before']['observation'] = 'The drawer is visibly unlocked but opening failed.'
            step['after']['observation'] = 'The drawer is visibly unlocked but opening failed.'
        changed['memory']['entries'][0]['knowledge'] = 'The repeated failures occurred despite an unlocked drawer. The reason for the failed opening is unresolved; unchanged locking cannot explain them.'
        reason = 'In `M1` and `H_A1/Q1:2`, opening fails despite visible unlocking, so this response does not support the earlier lock-based explanation. Current `P1:1` still motivates a conditional proposal; this change remains unverified.'
    else:
        for rid in ('P1', 'Q1'):
            r = sources[f'H_A3/{rid}']['run']
            initial = 'A is unavailable; this historical task requires only a coarse estimate, which B supplies.'
            r['initial']['observation'] = initial
            r['steps'][0]['before']['observation'] = initial
            r['steps'][0]['after']['observation'] = 'A remains unavailable.' if rid == 'P1' else 'A coarse estimate is obtained; no exact reading was measured.'
        changed['memory']['entries'][0]['knowledge'] = 'Using B met a coarse-estimate requirement. This observation does not establish suitability for the current exact-reading requirement.'
        reason = '`M1` and `H_A3/Q1:1` now concern coarse rather than exact information. Current `P2:1` still motivates allowing a visibly suitable alternative, but historical transfer to the exact-reading requirement is unverified.'
    raw = deepcopy(case['output'])
    raw['adjustments'][0]['reason'] = reason
    assert changed['plan'] == case['payload']['plan']
    validate_memory(changed['memory'])
    _, revised = normalize_update_patches(raw, changed)
    _, original = normalize_update_patches(case['output'], case['payload'])
    assert revised == original  # The same action can have a different evidential basis.
    # An obsolete explanation still passes structure: the manual review must catch it.
    normalize_update_patches(case['output'], changed)
    assert raw['adjustments'][0]['reason'] != case['output']['adjustments'][0]['reason']


@pytest.mark.parametrize('kind,initial,action,after,knowledge', [
    ('unencountered', 'No relevant container is visible.', 'wait', 'No relevant container is visible.',
     'No relevant visible container was encountered, so these executions do not test the inspection trigger.'),
    ('not_followed', 'A relevant closed container is visible.', 'wait', 'The relevant container remains closed.',
     'A relevant closed container was visible but no inspection was attempted; guidance adherence was not observed.'),
    ('followed_without_task_gain', 'A relevant closed container is visible.', 'inspect container', 'Container inspected; the target is absent.',
     'The relevant container was inspected but did not contain the target. Local inspection occurred without task completion; this does not establish that inspection is useless.'),
])
def test_equal_outcomes_do_not_collapse_different_response_evidence(kind, initial, action, after, knowledge):
    case = next(c for c in cases() if c['id'] == 'A3')
    replay = deepcopy(case['replay_payload'])
    from src.skill_evolution.v23.editor import actual_diff
    replay['parent'] = 'Preserve the task goal.\n'
    replay['diff'] = actual_diff(replay['parent'], 'Inspect a currently visible relevant closed container.\n')
    replay['runs'] = [run('P1', initial, [('wait', initial)]), run('Q1', initial, [(action, after)])]
    replay['pairs'] = [{'parent': 'P1', 'candidate': 'Q1'}]
    replay['plan']['updates'][0]['text'] = 'Inspect a currently visible relevant closed container.\n'
    output = {'entries': [{'revises': [], 'knowledge': knowledge, 'evidence': ['diff', 'P1:1', 'Q1:1']}]}
    validate_payload(replay)
    validate_entries(output, replay)
    assert {r['outcome']['status'] for r in replay['runs']} == {'step_limit'}
    assert replay['runs'][1]['steps'][0]['action'] == action


def test_condition_and_response_citations_select_needed_details():
    case = next(c for c in cases() if c['id'] == 'A3')
    payload = case['payload']
    source = payload['memory']['sources']['H_A3/Q1']
    source['run'] = run('Q1', 'Waiting for a source.', [('wait', 'Waiting for a source.')] * 7 +
                        [('read B', 'Exact required reading obtained.')], True)
    last = source['run']['steps'][-1]
    last['before']['observation'] = 'B visibly supplies the required exact reading.'
    source['run']['steps'][-2]['after'] = deepcopy(last['before'])
    payload['memory']['entries'][0]['evidence'] = ['H_A3/diff', 'H_A3/P1:1', 'H_A3/Q1:1']
    before = project_payload(payload)['memory']['sources']['H_A3/Q1']
    assert 'H_A3/Q1:8' not in {s['step'] for s in before['detailed_steps']}
    payload['memory']['entries'][0]['evidence'].append('H_A3/Q1:8')
    after = project_payload(payload)['memory']['sources']['H_A3/Q1']
    detail = next(s for s in after['detailed_steps'] if s['step'] == 'H_A3/Q1:8')
    assert detail['before'] == last['before'] and detail['after'] == last['after']
    assert before['run']['trace'] == after['run']['trace']  # No view algorithm change.


def test_withdrawal_and_inconsistent_goal_need_semantic_review():
    case = next(c for c in cases() if c['id'] == 'A8')
    # Remove the Parent coverage on which the human withdrawal reason depended.
    uncovered = deepcopy(case['payload'])
    uncovered['parent'] = 'Make task progress.\n'
    assert normalize_update_patches(case['output'], uncovered)[1] is None
    # A contradictory immutable Goal is expressible but cannot become a valid
    # behavioral Plan merely because syntax/patch checks succeed.
    conflict = deepcopy(case['payload'])
    conflict['plan']['goal'] = 'Always identify the exact target and never identify any target.'
    assert normalize_update_patches(case['output'], conflict)[1] is None
    # Both are marked unacceptable in the human review, not falsely auto-detected.
