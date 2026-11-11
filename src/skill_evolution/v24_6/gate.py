"""Select independent ALFWorld updates from verified, same-task evidence."""
from collections import Counter

from src.skill_evolution.v24_1.benchmarks.alfworld.evidence_contracts_memory import run_menus
from src.skill_evolution.v24_2 import method
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v29_2.execution_references import references
from src.skill_evolution.v28_5.editor import construct_selected


STEP_THRESHOLD = 10


def event_direction(parent_success, candidate_success, steps_saved):
    if parent_success != candidate_success:
        return 'gain' if candidate_success else 'loss'
    if parent_success:
        if steps_saved >= STEP_THRESHOLD:
            return 'efficiency_gain'
        if steps_saved <= -STEP_THRESHOLD:
            return 'efficiency_loss'
    return None


def replay_input(adapter, tasks, editor_view, edits, candidate, parents, children):
    audit = adapter.build_gate(parents, children, tasks, parent_skill=editor_view['parent'],
                               candidate_skill=candidate['candidate_text'])
    rows = {row['task_id']: row for row in audit['audit']}
    pairs = []
    for index, task in enumerate(tasks, 1):
        parent, child = rows[task]['parent'], rows[task]['candidate']
        saved = parent['steps'] - child['steps']
        direction = event_direction(parent['success'], child['success'], saved)
        if direction:
            pairs.append(dict(task_id=task, parent=f'P{index}', candidate=f'Q{index}',
                              parent_success=parent['success'], candidate_success=child['success'],
                              parent_steps=parent['steps'], candidate_steps=child['steps'],
                              steps_saved=saved, direction=direction))

    # Preserve the task's batch index even when only one pair qualified.
    runs, menus = [], {}
    for side, records in [('parent', parents), ('candidate', children)]:
        if not pairs:
            break
        by_task = {r['task']['id']: r for r in records}
        facts = adapter.build_facts([by_task[p['task_id']] for p in pairs])['facts']
        for pair, run in zip(pairs, facts['runs']):
            run['ref'] = pair[side]
            for number, step in enumerate(run['steps'], 1):
                step['step'] = f"{run['ref']}:{number}"
            referenced = run_menus(run, facts['command_sets'])
            if side == 'candidate':
                states = [run['initial'], *(s[k] for s in run['steps'] for k in ('before', 'after'))]
                for state in states:
                    if state['commands_ref'] is not None:
                        state['commands_ref'] = 'Q_' + state['commands_ref']
                referenced = {'Q_' + key: value for key, value in referenced.items()}
            menus.update(referenced)
            runs.append(run)

    return dict(**editor_view, pairs=pairs, runs=runs, command_sets=menus, diff=candidate['actual_diff'],
                edits=[dict(update_id=e['update_id'], patch=e['patch']) for e in edits['edits']]), audit


def knowledge(result, payload):
    events = method.knowledge(result, payload)
    for pair, event in zip(payload['pairs'], events):
        sources = {ref.split(':')[0] for ref in references(event['text'])}
        require({pair['parent'], pair['candidate']} <= sources,
                'Cite evidence from both executions of this task')
    return events


def decision(votes):
    if votes['gain']:
        return 'Defer' if votes['loss'] else 'Retain'
    if votes['loss']:
        return 'Reject'
    if votes['efficiency_gain'] and not votes['efficiency_loss']:
        return 'Retain'
    return 'Defer'


def select(editor_view, edits, pairs, events):
    patches = {e['update_id']: e['patch'] for e in edits['edits']}
    counts = {u['id']: Counter() for u in editor_view['plan']['updates']}
    require(len(pairs) == len(events), 'Expected one event per verified eligible pair')
    for pair, event in zip(pairs, events):
        saved = pair['parent_steps'] - pair['candidate_steps']
        direction = event_direction(pair['parent_success'], pair['candidate_success'], saved)
        require(event['task_id'] == pair['task_id'] and direction is not None
                and pair['direction'] == direction and pair['steps_saved'] == saved,
                'Event differs from verified pair')
        uid = event['update_id']
        if uid is not None:
            require(uid in counts and patches[uid], 'Vote needs a nonempty applied patch')
            counts[uid][direction] += 1

    retained, decisions = [], []
    for uid, votes in counts.items():
        choice = decision(votes) if patches[uid] else None
        decisions.append(dict(update_id=uid, G=votes['gain'], L=votes['loss'],
                              efficiency_gain=votes['efficiency_gain'], efficiency_loss=votes['efficiency_loss'],
                              gate_decision=choice))
        if choice == 'Retain':
            retained.append(uid)
    return decisions, construct_selected(edits, editor_view, retained)
