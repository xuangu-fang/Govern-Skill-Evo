import pytest

from src.skill_evolution.v24_4.success_memory import observations as obs


def test_observations_are_separate_and_citable():
    before = {'rounds': [{'entries': [{'id': 'M1'}]}]}
    pair = dict(task_id='train:example', parent='P2', candidate='Q2', parent_steps=1, candidate_steps=2)
    payload = dict(pairs=[pair], runs=[dict(ref=ref, steps=[dict(step=ref + ':1')]) for ref in ('P2', 'Q2')])
    note = dict(task_id=pair['task_id'], text='The two executions chose different destinations.',
                evidence=['P2:1', 'Q2:1'])
    notes = obs.validate_observations({'observations': [note]}, payload)
    after = obs.attach_observations(before, notes)
    assert before == {'rounds': [{'entries': [{'id': 'M1'}]}]}
    assert after['rounds'][0]['entries'] == before['rounds'][0]['entries']
    assert after['rounds'][0]['observations'][0]['id'] == 'M2'
    assert obs.next_memory_id(after) == 3
    assert obs.attach_observations(before, []) == before
    original = dict(id='u1', text='test', basis=[])
    args = dict(plan=dict(goal='test', updates=[original]), runs=[], memory=after)
    adj = dict(target='u1', action='KEEP', text=None, reason='M2 bears on this case.')
    assert obs.effective_plan({'adjustments': [adj]}, args)['updates'] == [original]
    for bad in (['P2:1'], ['P2:1', 'Q1:1']):
        with pytest.raises(ValueError):
            obs.validate_observations(dict(observations=[dict(note, evidence=bad)]), payload)
    with pytest.raises(ValueError):
        obs.validate_observations(dict(observations=[note, note]), payload)


def test_success_selection_uses_absolute_difference_and_batch_order():
    class Adapter:
        def build_facts(self, rows):
            runs = [dict(initial={'commands_ref': 'C1'}, steps=[]) for _ in rows]
            return {'facts': dict(command_sets={'C1': ['look']}, runs=runs)}

    pairs, parents, children = [], [], []
    for i, (p, q, both_won) in enumerate([(9, 3, True), (3, 9, True), (2, 8, True), (2, 50, False), (5, 5, True)]):
        task = f'train:{i}'
        pairs.append(dict(task_id=task, parent=dict(run_id='p'+task, success=True),
                          candidate=dict(run_id='q'+task, success=both_won)))
        for side, steps, dest in [('p', p, parents), ('q', q, children)]:
            dest.append(dict(run_id=side+task, task={'id': task}, steps=[None]*steps))
    payload = obs.success_input(Adapter(), {'input': {'pairs': pairs}}, parents, children, '')
    assert [(p['task_id'], p['parent_steps'], p['candidate_steps']) for p in payload['pairs']] == [
        ('train:0', 9, 3), ('train:1', 3, 9)]
    assert set(payload['command_sets']) == {'P_C1', 'Q_C1'}
