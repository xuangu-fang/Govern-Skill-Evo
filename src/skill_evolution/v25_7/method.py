"""Contracts, permitted evidence projections and deterministic Update selection."""
from src.skill_evolution.v27.contracts.diagnosis import fields, links
from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v28_5.editor import construct_candidate, construct_selected
from src.skill_evolution.v29_2.explicit_references import parse as citations
from .baseline.benchmarks.spreadsheetbench import evidence


def refs(runs):
    return {ref for run in runs for ref in evidence.run_references(run)}


def diagnosis(result, payload):
    fields(result, ('decision', 'reason', 'plan'), 'Diagnosis')
    allowed = refs(payload['runs'])
    citations(result['reason'], {'Evidence': allowed}, location='reason')
    plan = result['plan']
    if result['decision'] == 'no_change':
        require(plan is None, 'no_change requires null plan')
        return None
    require(result['decision'] == 'revise', 'Unknown Diagnosis decision')
    fields(plan, ('goal', 'updates'), 'Original Plan')
    citations(plan['goal'], {'Evidence': allowed}, location='goal')
    require(isinstance(plan['updates'], list) and plan['updates'], 'Expected Updates')
    seen = set()
    for u in plan['updates']:
        fields(u, ('id', 'text', 'basis'), 'Original Update')
        uid = text(u['id'], 'id')
        require(uid not in seen | allowed, 'Duplicate or evidence-colliding Update ID')
        seen.add(uid)
        citations(u['text'], {'Evidence': allowed}, location='text')
        links(u['basis'], allowed, 'basis')
    return plan


def preconditioner_input(parent_input, plan, memory):
    # Spreadsheet coordinates such as P1 are ordinary prose unless explicitly cited.
    allowed = refs(parent_input['runs'])
    cited = {ref for u in plan['updates'] for ref in u['basis']}
    for value in [plan['goal'], *(u['text'] for u in plan['updates'])]:
        cited.update(ref for _, ref in citations(value, {'Evidence': allowed}, location='Plan'))
    return dict(parent=parent_input['parent'], plan=plan, memory=memory,
                runs=[run for run in parent_input['runs'] if cited & evidence.run_references(run)])


def effective_plan(result, payload):
    fields(result, ('adjustments',), 'Preconditioner')
    plan = payload['plan']
    updates = {u['id']: u for u in plan['updates']}
    allowed = {'Update': set(updates), 'Evidence': refs(payload['runs']),
               'Memory': {e['id'] for r in payload['memory']['rounds'] for e in r['entries']}}
    require(isinstance(result['adjustments'], list), 'Expected adjustments array')
    effective = {}
    for item in result['adjustments']:
        fields(item, ('target', 'action', 'text', 'reason'), 'Adjustment')
        uid = text(item['target'], 'target')
        require(uid in updates and uid not in effective, 'Unknown or duplicate target')
        citations(item['reason'], allowed, location='reason')
        action = item['action']
        if action == 'REPLACE':
            citations(item['text'], allowed, location='replacement')
            require(item['text'] != updates[uid]['text'], 'REPLACE must change text')
            effective[uid] = {**updates[uid], 'text': item['text']}
        else:
            require(action in ('KEEP', 'WITHDRAW') and item['text'] is None, 'Invalid action or text')
            effective[uid] = updates[uid] if action == 'KEEP' else None
    require(set(effective) == set(updates), 'Missing Original decision')
    kept = [effective[uid] for uid in updates if effective[uid] is not None]
    return {'goal': plan['goal'], 'updates': kept} if kept else None


def editor_input(parent, plan):
    return {'parent': parent, 'plan': {'goal': plan['goal'], 'updates': [
        {'id': u['id'], 'text': u['text']} for u in plan['updates']]}}


def replay_input(adapter, tasks, editor_payload, edits, built, records, candidates):
    # Audit all tasks, even those excluded from the model view.
    adapter.build_gate(records, candidates, tasks, parent_skill=editor_payload['parent'],
                       candidate_skill=built['candidate_text'])
    p_runs = adapter.build_facts(records)['facts']['runs']
    q_runs = adapter.build_facts(candidates)['facts']['runs']
    require(len({r['run_id'] for r in p_runs + q_runs}) == 2 * len(tasks), 'Reused run identity')
    require([r['task_id'] for r in p_runs] == [r['task_id'] for r in q_runs] == tasks,
            'Actor batch order differs')
    pairs, runs = [], []
    for index, (p, q) in enumerate(zip(p_runs, q_runs), 1):
        q = evidence.relabel(q, f'Q{index}')
        before, after = evidence.pair_result(p), evidence.pair_result(q)
        if before['hard'] != after['hard']:
            pairs.append(dict(task_id=p['task_id'], parent=p['ref'], candidate=q['ref'],
                              parent_result=before, candidate_result=after))
            runs.extend((p, q))
    indexed = {e['update_id']: e['patch'] for e in edits['edits']}
    return {**editor_payload, 'diff': built['actual_diff'], 'pairs': pairs, 'runs': runs,
            'edits': [{'update_id': u['id'], 'patch': indexed[u['id']]} for u in editor_payload['plan']['updates']]}


def knowledge(result, payload):
    fields(result, ('entries',), 'Replay')
    require(isinstance(result['entries'], list) and len(result['entries']) == 1, 'Expected one Replay entry')
    entry = result['entries'][0]
    fields(entry, ('knowledge',), 'Replay entry')
    require(isinstance(entry['knowledge'], list), 'Expected event array')
    eligible = {e['update_id'] for e in payload['edits'] if e['patch']}
    effective_ids = {u['id'] for u in payload['plan']['updates']}
    events = {}
    pairs = {p['task_id']: p for p in payload['pairs']}
    for item in entry['knowledge']:
        fields(item, ('task_id', 'update_id', 'text'), 'Knowledge')
        task = text(item['task_id'], 'task_id')
        require(task in pairs and task not in events, 'Unknown or duplicate event task')
        if item['update_id'] is not None:
            require(text(item['update_id'], 'update_id') in eligible, 'Invalid event Update')
        evidence_ids = refs([r for r in payload['runs'] if r['task_id'] == task])
        citations(item['text'], {'Update': effective_ids, 'Evidence': evidence_ids | {'diff'}}, location='event')
        events[task] = item
    require(set(events) == set(pairs), 'Missing transition event')
    return [events[t] for t in pairs]


def gate(editor_payload, edits, pairs, events):
    counts = {u['id']: [0, 0] for u in editor_payload['plan']['updates']}
    patches = {e['update_id']: e['patch'] for e in edits['edits']}
    directions = {p['task_id']: p['candidate_result']['hard'] for p in pairs}
    require(len(directions) == len(pairs) == len(events)
            and {e['task_id'] for e in events} == set(directions), 'Gate needs one event per flipped task')
    for p in pairs:
        scores = (p['parent_result']['hard'], p['candidate_result']['hard'])
        require(all(type(v) is int for v in scores) and set(scores) == {0, 1}, 'Expected native hard flip')
    for item in events:
        uid = item['update_id']
        if uid is not None:
            require(uid in counts and patches.get(uid), 'Vote requires an implemented Update')
            counts[uid][0 if directions[item['task_id']] else 1] += 1
    decisions = []
    for uid, (gains, losses) in counts.items():
        decision = None
        if patches[uid]:
            decision = 'Retain' if gains and not losses else 'Reject' if losses and not gains else 'Defer'
        decisions.append(dict(update_id=uid, G=gains, L=losses, gate_decision=decision))
    selected = construct_selected(edits, editor_payload,
                                  [d['update_id'] for d in decisions if d['gate_decision'] == 'Retain'])
    return decisions, selected
