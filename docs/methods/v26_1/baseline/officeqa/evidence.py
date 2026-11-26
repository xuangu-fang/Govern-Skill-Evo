"""OfficeQA evidence dispatch with exact references and module-specific views."""
from copy import deepcopy
import json
import re

from ...facts import require, text
from ...benchmark import current
from ...contracts.diagnosis import fields, links, validate_diagnosis
from ...contracts.grouping import references
from ...contracts import memory as mem
from ...contracts.editor import apply_patch
from ...memory_view import knowledge_only, historical_references
from . import protocol as p
from .facts import build_facts, validate_envelope, assistant_message
from src.adapters.officeqa.retry import parse_turn


def run_references(run):
    return {run['ref'], run['initial']['ref'], run['outcome']['ref'],
            *[a['ref'] for a in run['attempts']],
            *[t['ref'] for a in run['attempts'] for t in a['tools']]}


def validate_run(run):
    fields(run, ('ref', 'task_id', 'run_id', 'initial', 'attempts', 'outcome'), 'Run')
    require(re.fullmatch(r'[PQ][1-9]\d*', run['ref']) is not None, 'Invalid run reference')
    text(run['run_id'], 'run ID'); initial = run['initial']; ref = run['ref']
    fields(initial, ('ref', 'task', 'declared_source_pages', 'messages'), 'Initial evidence')
    require(initial['ref'] == ref + ':0' and p.validate_task(initial['task'])['id'] == run['task_id'], 'Initial identity differs')
    require(initial['task']['split'] != 'test', 'Test evidence cannot enter optimization')
    require(p.equal(initial['declared_source_pages'], p.source_pages(initial['task'])), 'Declared page mapping differs')
    messages = deepcopy(initial['messages'])
    require(isinstance(messages, list) and len(messages) >= 2 and isinstance(messages[0], dict)
            and messages[0].get('role') == 'system', 'Initial messages missing')
    require(all(isinstance(m, dict) and set(m) == {'role', 'content'} and
                m['role'] in ('system', 'user') and isinstance(m['content'], str) for m in messages), 'Invalid initial messages')
    require(isinstance(run['attempts'], list) and 1 <= len(run['attempts']) <= 24, 'Invalid accepted rounds')
    calls = 0; final = None
    for n, a in enumerate(run['attempts'], 1):
        fields(a, ('ref', 'request_context', 'request_messages', 'assistant', 'tools'), 'Round evidence')
        require(final is None and a['ref'] == f'{ref}:{n}' and a['request_context'] == p.FORMAL_CONTEXT,
                'Invalid round identity/context')
        require(p.equal(a['request_messages'], messages), 'Formal request context differs')
        assistant = a['assistant']
        turn = parse_turn({'choices': [{'finish_reason': 'tool_calls' if assistant.get('tool_calls') else 'stop',
                                       'message': assistant}]})
        require(p.equal(assistant, assistant_message(turn)), 'Assistant message differs')
        require(isinstance(a['tools'], list) and len(a['tools']) == len(turn.tool_calls), 'Tool coverage differs')
        messages.append(deepcopy(assistant))
        for j, (tool, call) in enumerate(zip(a['tools'], assistant.get('tool_calls', [])), 1):
            fields(tool, ('ref', 'call', 'observation'), 'Tool evidence')
            require(tool['ref'] == f'{ref}:{n}_t{j}' and p.equal(tool['call'], call), 'Tool identity/call differs')
            obs = tool['observation']; fields(obs, ('role', 'tool_call_id', 'name', 'content'), 'Tool observation')
            require(obs['role'] == 'tool' and obs['tool_call_id'] == call['id']
                    and obs['name'] == call['function']['name'] and isinstance(obs['content'], str), 'Tool observation differs')
            messages.append(deepcopy(obs)); calls += 1
        if not turn.tool_calls:
            final = turn.text
    o = run['outcome']
    fields(o, ('ref', 'status', 'termination', 'answer', 'model_rounds', 'tool_calls', 'api_requests', 'score'), 'Outcome')
    require(o['ref'] == ref + ':outcome' and o['status'] == 'completed', 'Incomplete outcome')
    require(type(o['model_rounds']) is int and o['model_rounds'] == len(run['attempts'])
            and type(o['tool_calls']) is int and o['tool_calls'] == calls, 'Outcome counters differ')
    require(type(o['api_requests']) is int and o['model_rounds'] <= o['api_requests'] <= 6 * o['model_rounds'], 'Invalid request count')
    p.score_view(o['score'])
    from skilladam.benchmarks.officeqa.rollout import extract_answer
    require(o['answer'] == extract_answer({'response': final or ''})[0], 'Outcome answer differs')
    if final is None:
        require(o['termination'] == 'max_tool_turns' and o['model_rounds'] == 24
                and o['score']['em'] == o['score']['f1'] == 0, 'Invalid exhausted outcome')
    else:
        require(o['termination'] == 'answer', 'Invalid answer termination')
    return run


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
    from ...update_patch import normalize_update_patches
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
    for key in ('source_assets', 'task_context_sha256'):
        require(p.equal(parent['provenance'][key], candidate['provenance'][key]), f'Pair {key} differs')
    require(p.equal(parent['execution']['initial_messages'][1:], candidate['execution']['initial_messages'][1:]), 'Paired task messages differ')


def pair_result(run):
    o = run['outcome']
    return {k: o[k] for k in ('status', 'model_rounds', 'tool_calls', 'api_requests')} | deepcopy(o['score'])


def relabel(run, ref):
    run = deepcopy(run); old = run['ref']; run['ref'] = ref
    run['initial']['ref'] = ref + ':0'; run['outcome']['ref'] = ref + ':outcome'
    for a in run['attempts']:
        a['ref'] = ref + a['ref'][len(old):]
        for t in a['tools']:
            t['ref'] = ref + t['ref'][len(old):]
    return validate_run(run)


def build_replay_from_editor(saved, editor_directory, parent_records, candidate_records, *, memory=None,
                             implementation_review=None, memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    """Consume a caller-supplied Editor handoff; no Editor/model is run here."""
    require(saved['editor_status'] == 'candidate', 'Replay needs real Candidate')
    require(apply_patch(saved['facts']['parent'], saved['actual_diff']) == saved['candidate_text'], 'Actual Diff differs')
    # Pure offline readers retain the strict native policy without a binding.
    # A pilot exception is available only through an explicitly bound adapter.
    try:
        adapter = current()
    except RuntimeError:
        facts_builder, pair_verifier = build_facts, verify_pair
    else:
        facts_builder = adapter.build_facts
        pair_verifier = lambda *a, **kw: adapter.evidence('contracts.replay.verify_pair', *a, **kw)
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


def extract(ref, bundle, historical=None):
    validate_bundle(bundle); historical = historical or {}; local = ref; source = bundle; history = None
    if '/' in ref:
        require(ref in historical_references(knowledge_only(bundle['payload']['memory'])), 'Unprovided historical evidence')
        history, local = ref.rsplit('/', 1); require(history in historical, 'Missing historical archive')
        source = validate_bundle(historical[history])
    payload = source['payload']
    if local == 'diff':
        return {'parent': payload['parent'], 'diff': payload['diff'], 'execution_context': deepcopy(source['execution_context'])}
    rid = local.split(':')[0]; by_ref = {r['ref']: r for r in payload['runs']}
    require(rid in by_ref and local in run_references(by_ref[rid]), 'Unknown evidence reference')
    run = by_ref[rid]
    if local == rid: record = run
    elif local == run['initial']['ref']: record = run['initial']
    elif local == run['outcome']['ref']: record = run['outcome']
    else:
        record = None
        for a in run['attempts']:
            if local == a['ref']: record = a; break
            for tool in a['tools']:
                if local == tool['ref']:
                    record = {**tool, 'request_context': a['request_context'], 'request_messages': a['request_messages']}
                    break
            if record is not None: break
        require(record is not None, 'Evidence record missing')
    value = {'task_id': run['task_id'], 'run_id': run['run_id'],
             'role': 'parent' if rid.startswith('P') else 'candidate', 'record': deepcopy(record)}
    if history: value['execution_context'] = deepcopy(source['execution_context'])
    return value


def build_input(bundle, candidate, historical=None):
    from ...knowledge_evidence import select_targets
    from ...replay import validate_result
    historical = historical or {}; validate_bundle(bundle); payload = bundle['payload']; validate_result(candidate, payload)
    targets, inventory = select_targets(candidate, payload['memory'])
    refs = list(dict.fromkeys(ref for t in targets for ref in t['knowledge']['evidence']))
    for cid in {ref.rsplit('/', 1)[0] for ref in refs if '/' in ref}:
        require(cid in historical, 'Missing historical archive'); prior = validate_bundle(historical[cid])
        for key, original in payload['memory']['sources'].items():
            context, local = key.rsplit('/', 1)
            if context != cid: continue
            pp = prior['payload']
            if local == 'diff':
                expected = {'parent': pp['parent'], 'diff': pp['diff'], 'execution_context': prior['execution_context']}
            else:
                found = [r for r in pp['runs'] if r['ref'] == local]; require(len(found) == 1, 'Historical run missing')
                expected = {'run': found[0]}
            require(p.equal(original, expected), 'Historical source differs')
    cited = {x.split(':')[0] for x in refs if '/' not in x and x != 'diff'}
    pairs = [{k: pair[k] for k in ('parent', 'candidate', 'task_id')} for pair in payload['pairs']
             if pair['parent'] in cited or pair['candidate'] in cited]
    return {'context': {'parent': payload['parent'], 'diff': payload['diff'],
                        'execution_context': deepcopy(bundle['execution_context']), 'pairs': pairs},
            'targets': targets, 'source_records': {ref: extract(ref, bundle, historical) for ref in refs}}, inventory


def compact(value):
    fields(value, ('context', 'targets', 'source_records'), 'Knowledge input')
    return deepcopy(value)  # No lossy summaries or cross-run code deduplication.


def build_repair_input(value, verdicts, candidate):
    from ... import knowledge_verifier as v
    v.validate_result(verdicts, value)
    original = {v.position(t['target'], 'target'): t for t in value['targets']}; targets = []; refs = set()
    for row in verdicts['results']:
        if row['verdict'] != 'CONFLICT': continue
        ei, ki = key = v.position(row['target'], 'target'); target = deepcopy(original[key])
        require(p.equal(target['knowledge'], candidate['entries'][ei]['knowledge'][ki]), 'Target differs')
        target['issues'] = deepcopy(row['issues']); targets.append(target); refs.update(target['knowledge']['evidence'])
        for issue in row['issues']: refs.update(issue['evidence'])
    context = deepcopy(value['context']); rids = {r.split(':')[0] for r in refs if '/' not in r and r != 'diff'}
    context['pairs'] = [pair for pair in context['pairs'] if pair['parent'] in rids or pair['candidate'] in rids]
    return {'context': context, 'targets': targets, 'source_records': {r: deepcopy(value['source_records'][r]) for r in sorted(refs)}}


OPERATIONS = {
    'contracts.grouping.validate_grouping': validate_grouping,
    'contracts.diagnosis.diagnosis_input': diagnosis_input,
    'contracts.preconditioner.preconditioner_input': preconditioner_input,
    'contracts.memory.run_references': run_references, 'contracts.memory.validate_run': validate_run,
    'contracts.memory._view': memory_view, 'contracts.replay.verify_pair': verify_pair,
    'contracts.replay.build_replay_from_editor': build_replay_from_editor,
    'contracts.replay.validate_payload': validate_payload,
    'contracts.replay_view._current_pairs': current_pairs, 'replay_view.model_input': model_input,
    'replay.validate_bundle': validate_bundle, 'knowledge_evidence.extract': extract,
    'knowledge_evidence.build_input': build_input, 'knowledge_evidence.compact': compact,
    'knowledge_evidence.restore': compact, 'knowledge_evidence.build_repair_input': build_repair_input,
}
