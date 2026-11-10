"""The four model boundaries and deterministic selection on native ALFWorld success."""
from copy import deepcopy
import re

from src.skill_evolution.v24_1.benchmarks.alfworld.evidence_contracts_memory import run_menus, run_references
from src.skill_evolution.v27.contracts.diagnosis import fields, links
from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v28_5.editor import construct_candidate, construct_selected
from src.skill_evolution.v29_2.execution_references import references


def evidence_ids(runs):
    return {ref for run in runs for ref in run_references(run)}


def cited(value, allowed, memory_ids=()):
    result = references(text(value, 'explanation or instruction'))
    require(result <= allowed, f'Unavailable execution references: {sorted(result - allowed)}')
    require(set(re.findall(r'\bM[1-9]\d*\b', value)) <= set(memory_ids), 'Unavailable Memory reference')
    return result


def diagnosis(result, payload):
    fields(result, ('decision', 'reason', 'plan'), 'Diagnosis')
    allowed = evidence_ids(payload['runs'])
    cited(result['reason'], allowed)
    plan = result['plan']
    if result['decision'] == 'no_change':
        require(plan is None, 'no_change requires null plan')
        return None
    require(result['decision'] == 'revise', 'Unknown Diagnosis decision')
    fields(plan, ('goal', 'updates'), 'Original Plan')
    cited(plan['goal'], allowed)
    require(isinstance(plan['updates'], list) and plan['updates'], 'Expected nonempty Updates')
    seen = set()
    for update in plan['updates']:
        fields(update, ('id', 'text', 'basis'), 'Original Update')
        uid = text(update['id'], 'Update ID')
        require(uid not in seen | allowed, 'Duplicate or evidence-colliding Update ID')
        seen.add(uid)
        cited(update['text'], allowed)
        links(update['basis'], allowed, 'basis')
    return plan


def menus_for(runs, menus):
    result = {}
    for run in runs:
        result.update(run_menus(run, menus))
    return result


def preconditioner_input(payload, plan, memory):
    source_ids = references(plan['goal'])
    for update in plan['updates']:
        source_ids.update(update['basis'])
        source_ids.update(references(update['text']))
    runs = [r for r in payload['runs'] if source_ids & run_references(r)]
    return dict(parent=payload['parent'], plan=plan, runs=runs, memory=memory,
                command_sets=menus_for(runs, payload['command_sets']))


def effective_plan(result, payload):
    fields(result, ('adjustments',), 'Preconditioner')
    items = result['adjustments']
    plan = payload['plan']
    require(isinstance(items, list) and len(items) == len(plan['updates']), 'Expected one action per Original')
    allowed = evidence_ids(payload['runs'])
    kept = []
    memory_ids = {entry['id'] for r in payload['memory']['rounds'] for entry in r['entries']}
    for item, update in zip(items, plan['updates']):
        fields(item, ('target', 'action', 'text', 'reason'), 'Adjustment')
        require(item['target'] == update['id'], 'Invalid target or Original order')
        cited(item['reason'], allowed, memory_ids)
        action = item['action']
        if action == 'REPLACE':
            cited(item['text'], allowed)
            require(item['text'] != update['text'], 'REPLACE must change the text')
            kept.append({**update, 'text': item['text']})
        else:
            require(action in ('KEEP', 'WITHDRAW') and item['text'] is None, 'Invalid adjustment')
            if action == 'KEEP':
                kept.append(update)
    return dict(goal=plan['goal'], updates=kept) if kept else None


def editor_input(parent, plan):
    return dict(parent=parent, plan=dict(goal=plan['goal'], updates=[
        dict(id=u['id'], text=u['text']) for u in plan['updates']]))


def edit(result, payload):
    candidate = construct_candidate(result, payload)
    require([e['update_id'] for e in result['edits']] == [u['id'] for u in payload['plan']['updates']],
            'Return edits in Effective Plan order')
    return candidate


def replay_input(adapter, tasks, editor_view, edits, candidate, parents, children):
    # The old Gate's input builder verifies all raw executions. Its whole-batch decision is never used.
    audit = adapter.build_gate(parents, children, tasks, parent_skill=editor_view['parent'],
                               candidate_skill=candidate['candidate_text'])
    p = adapter.build_facts(parents)['facts']
    q = adapter.build_facts(children)['facts']
    p_by_id = {raw['task']['id']: run for raw, run in zip(parents, p['runs'])}
    q_by_id = {raw['task']['id']: run for raw, run in zip(children, q['runs'])}
    results = {pair['task_id']: pair for pair in audit['input']['pairs']}
    runs, pairs, menus = [], [], {}
    for task in tasks:
        pair = results[task]
        before, after = pair['parent']['success'], pair['candidate']['success']
        if before == after:
            continue
        prun, qrun = p_by_id[task], deepcopy(q_by_id[task])
        qrun['ref'] = 'Q' + prun['ref'][1:]
        for i, step in enumerate(qrun['steps'], 1):
            step['step'] = f"{qrun['ref']}:{i}"
        # Menu IDs are local to each batch. Namespace Candidate menus before sharing the two views.
        qmenus = run_menus(qrun, q['command_sets'])
        states = [qrun['initial'], *(s[side] for s in qrun['steps'] for side in ('before', 'after'))]
        for state in states:
            if state['commands_ref'] is not None:
                state['commands_ref'] = 'Q_' + state['commands_ref']
        menus.update(run_menus(prun, p['command_sets']))
        menus.update({'Q_' + key: value for key, value in qmenus.items()})
        runs.extend((prun, qrun))
        pairs.append(dict(task_id=task, parent=prun['ref'], candidate=qrun['ref'],
                          parent_success=before, candidate_success=after))
    mapped = {e['update_id']: e['patch'] for e in edits['edits']}
    return {**editor_view, 'pairs': pairs, 'runs': runs, 'command_sets': menus,
            'diff': candidate['actual_diff'], 'edits': [
                dict(update_id=u['id'], patch=mapped[u['id']]) for u in editor_view['plan']['updates']]}, audit


def knowledge(result, payload):
    fields(result, ('entries',), 'Replay')
    entries = result['entries']
    require(isinstance(entries, list) and len(entries) == 1, 'Expected one Knowledge container')
    fields(entries[0], ('knowledge',), 'Entry')
    events = entries[0]['knowledge']
    require(isinstance(events, list) and len(events) == len(payload['pairs']), 'Wrong number of events')
    eligible = {e['update_id'] for e in payload['edits'] if e['patch']}
    by_ref = {r['ref']: r for r in payload['runs']}
    for event, pair in zip(events, payload['pairs']):
        fields(event, ('task_id', 'update_id', 'text'), 'Event')
        require(event['task_id'] == pair['task_id'], 'Wrong event task or order')
        uid = event['update_id']
        require(uid is None or isinstance(uid, str) and uid in eligible, 'Ineligible Update association')
        cited(event['text'], evidence_ids([by_ref[pair['parent']], by_ref[pair['candidate']]]))
    return events


def select(editor_view, edits, pairs, events):
    patches = {e['update_id']: e['patch'] for e in edits['edits']}
    counts = {u['id']: [0, 0] for u in editor_view['plan']['updates']}
    require(len(pairs) == len(events), 'Gate requires exactly one event per flip')
    for pair, event in zip(pairs, events):
        require(event['task_id'] == pair['task_id'] and pair['parent_success'] is not pair['candidate_success'],
                'Event does not match its verified flip')
        uid = event['update_id']
        if uid is not None:
            require(uid in counts and patches[uid], 'Vote needs a nonempty patch')
            counts[uid][0 if pair['candidate_success'] else 1] += 1
    decisions, retained = [], []
    for uid, (gains, losses) in counts.items():
        decision = None
        if patches[uid]:
            if gains and not losses:
                decision = 'Retain'
                retained.append(uid)
            elif losses and not gains:
                decision = 'Reject'
            else:
                decision = 'Defer'
        decisions.append(dict(update_id=uid, G=gains, L=losses, gate_decision=decision))
    return decisions, construct_selected(edits, editor_view, retained)
