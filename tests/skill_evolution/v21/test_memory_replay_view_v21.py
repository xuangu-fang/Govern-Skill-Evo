"""A presentation change must not select outcomes, conflate versions, or invent calls."""
from copy import deepcopy

import pytest

from src.skill_evolution.v21.evidence_wire_v21 import pack, pack_memory, expand
from tests.skill_evolution.v21.test_memory_update_v21 import update_input, completed, setup, case


def test_all_pairs_keep_both_axes_original_order_and_non_execution(update_input):
    payload = update_input.payload
    original = deepcopy(payload)
    # Remove all candidate tool calls in one pair: absence must stay explicit,
    # not be filled in from the Parent or another task with a favorable label.
    pid, pair = next(iter(payload['pairs'].items()))
    payload['events'] = {r: e for r, e in payload['events'].items()
        if not (e['trajectory_ref'] == pair['candidate'] and e['event']['event_type'] == 'tool_call')}
    payload['trajectories'][pair['parent']]['supervision'].update(success=True, compliant=False)
    payload['trajectories'][pair['candidate']]['supervision'].update(success=False, compliant=True)
    wire, mapping = pack_memory(payload)
    assert mapping == pack(payload)[1]
    assert expand(wire, mapping) == payload
    assert set(wire['events']) == set(pack(payload)[0]['events'])
    assert {mapping[r['pair_ref']] for r in wire['replay_comparison']} == set(payload['pairs'])
    row = next(r for r in wire['replay_comparison'] if mapping[r['pair_ref']] == pid)
    assert (row['parent']['success'], row['parent']['compliant']) == (True, False)
    assert (row['candidate']['success'], row['candidate']['compliant']) == (False, True)
    assert row['candidate']['tool_calls'] == []
    for row in wire['replay_comparison']:
        pair = payload['pairs'][mapping[row['pair_ref']]]
        for role in ('parent', 'candidate'):
            side = row[role]
            assert mapping[side['trajectory_ref']] == pair[role]
            originals = {r: e['event'] for r, e in payload['events'].items() if e['trajectory_ref'] == pair[role]}
            assert set(side['event_refs']) == {a for a, ref in mapping.items() if ref in originals}
            assert {mapping[c['evidence_ref']] for c in side['tool_calls']} == {
                r for r, event in originals.items() if event['event_type'] == 'tool_call'}
            assert [c['step'] for c in side['tool_calls']] == sorted(c['step'] for c in side['tool_calls'])
    assert update_input.payload == original


@pytest.mark.parametrize('damage', ['drop_pair', 'label', 'wrong_role', 'invent_call', 'drop_event'])
def test_comparison_cannot_change_labels_roles_or_coverage(update_input, damage):
    wire, mapping = pack_memory(update_input.payload)
    row = wire['replay_comparison'][0]
    if damage == 'drop_pair': wire['replay_comparison'].pop()
    elif damage == 'label': row['candidate']['success'] = not row['candidate']['success']
    elif damage == 'wrong_role': row['candidate']['trajectory_ref'] = row['parent']['trajectory_ref']
    elif damage == 'invent_call': row['candidate']['tool_calls'].append({'tool_name': 'imagined_success'})
    else: row['candidate']['event_refs'].pop()
    with pytest.raises(ValueError, match='replay comparison differs'):
        expand(wire, mapping)


@pytest.mark.parametrize('damage', [None, 'replace_with_parent', 'drop_user_turn'])
def test_user_conditions_belong_to_their_own_run(update_input, damage):
    payload = update_input.payload
    pid, pair = next(iter(payload['pairs'].items()))
    # A repeated task can have different user-provided facts. A comparison must
    # neither substitute Parent facts nor silently omit Candidate conditions.
    for role, value in [('parent', '1992-02-01'), ('candidate', '1992-02-02')]:
        payload['events']['USER/' + role] = {
            'trajectory_ref': pair[role],
            'event': {'actor': 'user', 'event_type': 'message', 'step': 0,
                      'content': {'date_of_birth': value}}}
    wire, mapping = pack_memory(payload)
    row = next(r for r in wire['replay_comparison'] if mapping[r['pair_ref']] == pid)
    assert expand(wire, mapping) == payload
    for role in ('parent', 'candidate'):
        ref = 'USER/' + role
        actual = next(m for m in row[role]['user_messages'] if mapping[m['evidence_ref']] == ref)
        assert actual['event'] == payload['events'][ref]['event']
    if damage == 'replace_with_parent':
        row['candidate']['user_messages'] = deepcopy(row['parent']['user_messages'])
    elif damage == 'drop_user_turn':
        row['candidate']['user_messages'].pop()
    else:
        return
    with pytest.raises(ValueError, match='replay comparison differs'):
        expand(wire, mapping)


def test_previous_paired_action_encoding_remains_readable(update_input):
    payload = update_input.payload
    wire, mapping = pack_memory(payload)
    for row in wire['replay_comparison']:
        for role in ('parent', 'candidate'):
            row[role].pop('user_messages')
    wire['reference_encoding'] = 'paired_replay_v21.1'
    assert expand(wire, mapping) == payload
