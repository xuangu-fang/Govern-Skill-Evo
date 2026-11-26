"""Exact initial-context sharing without changing executed evidence or old views."""
from copy import deepcopy
import json

import pytest

from src.skill_evolution.v25 import replay, replay_view, output_feedback as feedback
from src.skill_evolution.v25.replay_shared_initial import share_initial, restore_initial, exact, INSTRUCTION
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench import timeline
from .test_replay_input_views import saved


def paired(saved):
    _, adapter, _, bundle = saved
    with using_benchmark(adapter):
        return replay_view.model_input(bundle, input_view=replay_view.PAIRED_FORMAT)


def test_full_and_timeline_round_trip_preserve_every_byte_of_each_message(saved):
    view = paired(saved)
    before = exact(view)
    shared = share_initial(view)
    assert exact(view) == before
    assert exact(restore_initial(shared)) == before
    assert len(exact(shared)) < len(before)
    compact = timeline.project(shared)
    expanded = restore_initial(compact)
    assert exact(expanded) == exact(timeline.project(view))
    # Existing timeline.restore appends the request_messages key; object values
    # and every message string are identical, JSON object key order may differ.
    assert restore_initial(timeline.restore(compact)) == view
    for original, restored in zip(view['runs'], expanded['runs']):
        assert list(timeline.requests_for(original)) == list(timeline.requests_for(restored))
        for a, b in zip(original['attempts'], restored['attempts']):
            assert {k:v for k,v in a.items() if k != 'request_messages'} == b
    assert len({m['shared_message'] for r in shared['runs']
                for m in r['initial']['messages'] if m.get('shared_message', '').startswith('system_')}) == 2


def test_same_task_text_is_shared_only_within_each_pair(saved):
    view = paired(saved)
    user = {'role':'user', 'content':' Identical task\r\nWith  spaces ', 'name':'original'}
    for r in view['runs']:
        r['initial']['messages'][1] = deepcopy(user)
    shared = share_initial(view)
    refs = [r['initial']['messages'][1]['shared_message'] for r in shared['runs']]
    assert refs[0] == refs[1] and refs[2] == refs[3] and refs[0] != refs[2]
    assert exact(restore_initial(shared)) == exact(view)


@pytest.mark.parametrize('change', ['whitespace','case','metadata','extra_user'])
def test_different_complete_user_sequences_are_not_partially_shared(saved, change):
    view = paired(saved)
    p, q = view['runs'][:2]
    common = {'role':'user','content':'common second message'}
    p['initial']['messages'].append(deepcopy(common))
    q['initial']['messages'].append(deepcopy(common))
    if change == 'whitespace':
        q['initial']['messages'][1]['content'] += ' '
    elif change == 'case':
        q['initial']['messages'][1]['content'] = q['initial']['messages'][1]['content'].swapcase()
    elif change == 'metadata':
        q['initial']['messages'][1]['name'] = 'different'
    else:
        q['initial']['messages'].append({'role':'user','content':'additional task condition'})
    shared = share_initial(view)
    for original, compressed in zip(view['runs'][:2], shared['runs'][:2]):
        assert compressed['initial']['messages'][1:] == original['initial']['messages'][1:]
    assert exact(restore_initial(shared)) == exact(view)


def test_multiple_identical_user_messages_keep_order_and_metadata(saved):
    view = paired(saved)
    p, q = view['runs'][:2]
    extra = {'role':'user','content':'second\nmessage', 'name':'original'}
    p['initial']['messages'].append(deepcopy(extra))
    q['initial']['messages'].append(deepcopy(extra))
    shared = share_initial(view)
    assert all('shared_message' in m for r in shared['runs'][:2] for m in r['initial']['messages'][1:])
    assert exact(restore_initial(shared)) == exact(view)


def test_unique_system_with_even_one_byte_difference_stays_inline(saved):
    view = paired(saved)
    view['runs'][0]['initial']['messages'][0]['content'] += ' '
    shared = share_initial(view)
    assert shared['runs'][0]['initial']['messages'][0] == view['runs'][0]['initial']['messages'][0]
    assert exact(restore_initial(shared)) == exact(view)


@pytest.mark.parametrize('damage', ['missing','extra_field','unused','role','format','cross_pair'])
def test_invalid_or_noncanonical_sharing_rejected(saved, damage):
    view = paired(saved)
    # Ensure tasks in both pairs have identical text; even then cross-pair user sharing is forbidden.
    for r in view['runs']:
        r['initial']['messages'][1] = {'role':'user','content':'same task'}
    shared = share_initial(view)
    pointer = shared['runs'][0]['initial']['messages'][0]
    table = shared['shared_initial']['messages']
    if damage == 'missing':
        del table[pointer['shared_message']]
    elif damage == 'extra_field':
        pointer['role'] = 'system'
    elif damage == 'unused':
        table['unused'] = {'role':'system','content':'unreferenced'}
    elif damage == 'role':
        table[pointer['shared_message']]['role'] = 'assistant'
    elif damage == 'format':
        shared['shared_initial']['format'] = 'unknown'
    else:
        shared['runs'][2]['initial']['messages'][1] = deepcopy(shared['runs'][0]['initial']['messages'][1])
    with pytest.raises(ValueError):
        restore_initial(shared)


def test_v3_messages_restore_to_v2_and_encoding_keys_are_not_evidence(saved):
    _, adapter, path, bundle = saved
    with using_benchmark(adapter):
        old = replay.messages_for(bundle, input_view=replay_view.PAIRED_FORMAT)
        new = replay.messages_for(bundle, input_view=replay_view.SHARED_INITIAL_FORMAT)
        assert new[0]['content'] == old[0]['content'] + '\n\n' + INSTRUCTION
        assert exact(restore_initial(json.loads(new[1]['content']))) == exact(json.loads(old[1]['content']))
        context = feedback.saved_context(path)
        old, new = (feedback.request_messages(m, context) for m in (old,new))
        assert exact(restore_initial(json.loads(new[1]['content']))) == exact(json.loads(old[1]['content']))
        result = {'entries':[{'revises':[], 'knowledge':[{'text':'Invalid encoding citation',
                  'evidence':['diff','system_1']}]}]}
        with pytest.raises(ValueError):
            replay.validate_result(result, bundle['payload'])
