"""DocVQA evidence dispatch with exact references and module-specific views."""
from copy import deepcopy
import json
import re

from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts.diagnosis import fields, links, validate_diagnosis as inherited_diagnosis
from src.skill_evolution.v27.contracts.grouping import references as parent_references
from src.skill_evolution.v27.contracts import memory as mem
from src.skill_evolution.v27.contracts.editor import apply_patch
from src.skill_evolution.v27.memory_view import knowledge_only
from . import protocol as p
from .facts import validate_envelope, validate_saved, validate_run, run_references


def references(value):
    # v27's Parent-only scanner does not recognize Q or qualified historical
    # citations. Neither is authorized in Grouping/Diagnosis for DocVQA.
    return (parent_references(value) |
            set(re.findall(r'\bQ\d+(?::[A-Za-z0-9_]+)?\b', value)) |
            set(re.findall(r'\b[A-Za-z0-9_-]+/(?:diff|[PQ]\d+(?::[A-Za-z0-9_]+)?)\b', value)))


def validate_diagnosis(result, payload):
    inherited_diagnosis(result, payload)
    allowed = {ref for run in payload['runs'] for ref in run_references(run)}
    prose = [result['reason']]
    if result['plan'] is not None:
        plan = result['plan']
        prose += [plan['goal'], *[u['text'] for u in plan['updates']], *[c['question'] for c in plan['checks']]]
    require(all(references(value) <= allowed for value in prose), 'Unavailable execution reference in Diagnosis')
    return result


def validate_grouping(result, facts):
    fields(result, ('groups',), 'Grouping')
    require(isinstance(result['groups'], list) and result['groups'], 'Missing groups')
    runs = {r['ref']: validate_run(r) for r in facts['runs']}
    require(runs and len(runs) == len(facts['runs']), 'Duplicate/missing runs')
    allowed = set().union(*(run_references(r) for r in runs.values())); assigned = []; ids = set()
    for group in result['groups']:
        fields(group, ('group_id', 'members', 'decision_problem', 'shared_basis', 'important_differences'), 'Group')
        gid = text(group['group_id'], 'Group ID'); require(gid not in ids, 'Duplicate Group ID'); ids.add(gid)
        links(group['members'], set(runs), 'Members'); assigned += group['members']
        require(isinstance(group['important_differences'], list), 'Invalid differences')
        for item in [group['decision_problem'], group['shared_basis'], *group['important_differences']]:
            require(references(text(item, 'group text')) <= allowed, 'Unknown execution reference')
        for member in group['members']:
            r = runs[member]; decisions = run_references(r) - {r['ref'], r['initial']['ref'], r['outcome']['ref']}
            require(bool((decisions or {r['initial']['ref']}) & references(group['shared_basis'])), 'Group lacks decision evidence')
    require(len(assigned) == len(set(assigned)) and set(assigned) == set(runs), 'Grouping must cover each run exactly once')
    return result


def diagnosis_input(saved):
    validate_saved(saved)
    fields(saved['facts'], ('parent', 'runs'), 'Facts'); validate_grouping(saved['grouping'], saved['facts'])
    return deepcopy({**saved['facts'], 'grouping': saved['grouping']})


def preconditioner_input(saved, *, memory=None, memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    facts = diagnosis_input(saved); validate_diagnosis(saved['diagnosis'], facts)
    require(saved['diagnosis']['decision'] == 'revise', 'Preconditioner needs revise')
    plan = saved['diagnosis']['plan']; encoded = json.dumps(plan)
    ids = {r.split(':')[0] for r in references(encoded)}; gids = set(re.findall(r'\bG\d+\b', encoded))
    memory = deepcopy(saved.get('memory', mem.empty_memory()) if memory is None else memory)
    mem.validate_memory(memory, memory_contract=memory_contract)
    return dict(parent=facts['parent'], plan=deepcopy(plan), runs=[deepcopy(r) for r in facts['runs'] if r['ref'] in ids],
                grouping={'groups': [deepcopy(g) for g in facts['grouping']['groups']
                                     if g['group_id'] in gids or ids.intersection(g['members'])]}, memory=memory)


def preconditioner_model_input(saved, *, memory=None):
    payload = preconditioner_input(saved, memory=memory)
    payload.pop('grouping'); payload['memory'] = knowledge_only(payload['memory'])
    return payload


def editor_model_input(saved, result):
    """Use the inherited deterministic plan compiler; do not expose raw executions."""
    from src.skill_evolution.v27.update_patch import normalize_update_patches
    _, effective = normalize_update_patches(result, preconditioner_input(saved))
    return None if effective is None else {'parent': saved['facts']['parent'], 'plan': effective}


def memory_view(archive, contexts, active_ids, memory_contract):
    view = mem.empty_memory()
    for mid in active_ids:
        entry = archive[mid]; view['entries'].append({k: deepcopy(entry[k]) for k in ('id', *mem._entry_fields(memory_contract))})
        for ref in mem.entry_evidence(entry, memory_contract=memory_contract):
            cid, local = ref.rsplit('/', 1); context = contexts[cid]; payload = context['payload']
            view['sources'][cid + '/diff'] = {'parent': payload['parent'], 'diff': payload['diff'],
                                             'execution_context': deepcopy(context['execution_context'])}
            if local != 'diff':
                rid = local.split(':')[0]; run = next(r for r in payload['runs'] if r['ref'] == rid)
                require(local in run_references(run), 'Historical source missing')
                view['sources'][cid + '/' + rid] = {'run': deepcopy(run)}
    mem.validate_memory(view, memory_contract=memory_contract)
    return view


def verify_pair(parent, candidate, *, implementation_review=None):
    require(implementation_review is None, 'No runtime implementation amendments')
    validate_envelope(parent); validate_envelope(candidate)
    require(parent['provenance']['role'] == 'parent' and candidate['provenance']['role'] == 'candidate', 'Pair roles differ')
    require(parent['run_id'] != candidate['run_id'], 'Pair reuses execution identity')
    require(p.equal(parent['task'], candidate['task']), 'Pair task differs')
    require(p.equal(parent['execution']['actor'], candidate['execution']['actor']), 'Pair Actor conditions differ')
    require(p.equal(parent['execution']['initial_messages'][1:], candidate['execution']['initial_messages'][1:]), 'Paired task messages differ')


def pair_result(run):
    o = run['outcome']
    return {k: o[k] for k in ('status', 'model_rounds', 'tool_calls', 'api_requests')} | deepcopy(o['score'])


def relabel(run, ref):
    run = deepcopy(run); old = run['ref']; run['ref'] = ref
    run['initial']['ref'] = ref + ':0'; run['outcome']['ref'] = ref + ':outcome'
    for a in run['attempts']:
        a['ref'] = ref + a['ref'][len(old):]
    return validate_run(run)


def build_replay_from_editor(saved, editor_directory, parent_records, candidate_records, *, memory=None,
                             implementation_review=None, memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    """Consume a caller-supplied Editor handoff; no Editor/model is run here."""
    with current().memory_operation():
        return _build_replay_from_editor(saved, editor_directory, parent_records, candidate_records,
            memory=memory, implementation_review=implementation_review, memory_contract=memory_contract)


def _build_replay_from_editor(saved, editor_directory, parent_records, candidate_records, *, memory=None,
                              implementation_review=None, memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    require(saved['editor_status'] == 'candidate', 'Replay needs real Candidate')
    require(apply_patch(saved['facts']['parent'], saved['actual_diff']) == saved['candidate_text'], 'Actual Diff differs')
    adapter = current()
    facts_builder, pair_verifier = adapter.build_facts, verify_pair
    parent = facts_builder(parent_records, role='parent')
    candidate = facts_builder(candidate_records, role='candidate')
    require(p.equal(parent['facts'], saved['facts']) and p.equal(parent['background'], saved['background'])
            and p.equal(parent['background'], candidate['background']), 'Frozen Parent lineage differs')
    require(candidate['facts']['parent'] == saved['candidate_text'], 'Executed Candidate differs')
    require(len(parent_records) == len(candidate_records), 'Incomplete pairs')
    by_task = {r['task_id']: (r, run) for r, run in zip(candidate_records, candidate['facts']['runs'])}
    runs = []; pairs = []; audits = []
    for i, (record, prun) in enumerate(zip(parent_records, parent['facts']['runs']), 1):
        require(record['task_id'] in by_task, 'Missing Candidate task')
        qr, qrun = by_task[record['task_id']]
        pair_verifier(record, qr, implementation_review=implementation_review)
        qrun = relabel(qrun, f'Q{i}'); runs.extend([deepcopy(prun), qrun])
        pair = dict(parent=prun['ref'], candidate=qrun['ref'], task_id=prun['task_id'],
                    parent_result=pair_result(prun), candidate_result=pair_result(qrun)); pairs.append(pair)
        audits.append({'pair': {k: pair[k] for k in ('parent', 'candidate')}, 'task_id': prun['task_id'],
                       'parent_run_id': record['run_id'], 'candidate_run_id': qr['run_id'], 'verified': True})
    plan = saved['effective_plan']
    plan = {'goal': plan['goal'], 'updates': [{k: u[k] for k in ('id', 'text')} for u in plan['updates']], 'checks': deepcopy(plan['checks'])}
    payload = dict(parent=parent['facts']['parent'], diff=saved['actual_diff'], plan=plan, pairs=pairs, runs=runs,
                   memory=deepcopy(mem.empty_memory() if memory is None else memory))
    validate_payload(payload, memory_contract=memory_contract)
    editor = {k: deepcopy(saved[k]) for k in ('editor_status', 'facts', 'background', 'candidate_text', 'actual_diff', 'effective_plan')}
    return {'payload': payload, 'background': parent['background'], 'pair_audit': audits,
            'editor_directory': str(editor_directory), 'candidate': saved['candidate_text'],
            'execution_context': {'background': parent['background'], 'description': p.execution_context(parent['background'])},
            'audit': {'editor': editor, 'parent_records': deepcopy(parent_records), 'candidate_records': deepcopy(candidate_records)}}


def validate_payload(payload, *, memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    fields(payload, ('parent', 'diff', 'plan', 'runs', 'pairs', 'memory'), 'Replay input')
    apply_patch(payload['parent'], payload['diff'])
    plan = payload['plan']; fields(plan, ('goal', 'updates', 'checks'), 'Plan'); text(plan['goal'], 'goal')
    require(isinstance(plan['updates'], list) and plan['updates'], 'Missing Updates'); ids = set()
    for u in plan['updates']:
        fields(u, ('id', 'text'), 'Update'); text(u['id'], 'ID'); text(u['text'], 'text')
        require(u['id'] not in ids, 'Duplicate Update'); ids.add(u['id'])
    require(isinstance(plan['checks'], list), 'Invalid Checks'); cids = set()
    for c in plan['checks']:
        fields(c, ('id', 'update_ids', 'question'), 'Check'); text(c['id'], 'Check ID')
        require(c['id'] not in ids | cids, 'Duplicate Check'); cids.add(c['id'])
        text(c['question'], 'Question'); links(c['update_ids'], ids, 'Check updates')
    runs = {r['ref']: validate_run(r) for r in payload['runs']}
    require(runs and len(runs) == len(payload['runs']), 'Duplicate/missing runs')
    require(len({r['run_id'] for r in runs.values()}) == len(runs), 'Duplicate execution identity')
    paired = []; tasks = set()
    for pair in payload['pairs']:
        fields(pair, ('parent', 'candidate', 'task_id', 'parent_result', 'candidate_result'), 'Pair')
        require(pair['task_id'] not in tasks, 'Duplicate paired task'); tasks.add(pair['task_id'])
        for side, prefix in [('parent', 'P'), ('candidate', 'Q')]:
            ref = pair[side]; require(ref in runs and ref.startswith(prefix), 'Invalid pair role')
            require(runs[ref]['task_id'] == pair['task_id'] and p.equal(pair[side + '_result'], pair_result(runs[ref])), 'Pair task/result differs')
            paired.append(ref)
    require(len(paired) == len(set(paired)) and set(paired) == set(runs), 'Pair coverage differs')
    mem.validate_memory(payload['memory'], memory_contract=memory_contract)
    return payload


def validate_bundle(bundle, *, memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    fields(bundle, ('payload', 'background', 'pair_audit', 'editor_directory', 'candidate', 'execution_context', 'audit'), 'Replay bundle')
    fields(bundle['audit'], ('editor', 'parent_records', 'candidate_records'), 'Replay audit')
    a = bundle['audit']
    rebuilt = build_replay_from_editor(a['editor'], bundle['editor_directory'], a['parent_records'], a['candidate_records'],
                                      memory=bundle['payload']['memory'], memory_contract=memory_contract)
    require(p.equal(rebuilt, bundle), 'Replay bundle differs from audited executions/Editor handoff')
    return bundle


def current_pairs(bundle):
    validate_bundle(bundle)
    return deepcopy(bundle['payload']['pairs']), deepcopy(bundle['payload']['runs'])


def model_input(bundle, *, memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    validate_bundle(bundle, memory_contract=memory_contract)
    return {k: deepcopy(v) for k, v in bundle['payload'].items() if k != 'memory'} | {
        'memory': knowledge_only(bundle['payload']['memory'], memory_contract=memory_contract)}




OPERATIONS = {
    'contracts.grouping.validate_grouping': validate_grouping,
    'contracts.diagnosis.diagnosis_input': diagnosis_input,
    'contracts.preconditioner.preconditioner_input': preconditioner_input,
    'contracts.memory.run_references': run_references,
    'contracts.memory.validate_run': validate_run,
    'contracts.memory._view': memory_view,
    'contracts.replay.verify_pair': verify_pair,
    'contracts.replay.build_replay_from_editor': build_replay_from_editor,
    'contracts.replay.validate_payload': validate_payload,
    'contracts.replay_view._current_pairs': current_pairs,
    'replay_view.model_input': model_input,
    'replay.validate_bundle': validate_bundle,
}
