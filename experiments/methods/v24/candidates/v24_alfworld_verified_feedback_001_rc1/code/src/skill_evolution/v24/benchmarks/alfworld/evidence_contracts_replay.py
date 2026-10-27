from copy import deepcopy
from pathlib import Path
from src.skill_evolution.v24.storage import validate_skill
from src.skill_evolution.v24.contracts.editor import apply_patch
from src.skill_evolution.v24.facts import build_facts, parent_text, require, text
from src.skill_evolution.v24.contracts.diagnosis import fields, links
from src.skill_evolution.v24.contracts.memory import empty_memory, validate_memory, validate_run, LEGACY_CONTRACT

def verify_pair(parent, candidate, *, implementation_review=None):
    """Shared deterministic task/config/reset checks; no outcome decision."""
    for key in ('task', 'split', 'model', 'backend_id', 'protocol', 'versions'):
        require(parent[key] == candidate[key], f'Pair: {key} differs')
    require(parent.get('gamefile') == candidate.get('gamefile'), 'Pair: environment differs')
    require(parent['initial_observation'] == candidate['initial_observation'] and
            parent['initial_admissible_commands'] == candidate['initial_admissible_commands'],
            f'Pair: reset state differs')
    # Git metadata need not be identical; the execution implementation must be.
    if parent['implementation']['files'] != candidate['implementation']['files']:
        require(isinstance(implementation_review, dict), 'Actor implementation differs; explicit source review required')
        require(implementation_review.get('parent_files') == parent['implementation']['files'] and
                implementation_review.get('candidate_files') == candidate['implementation']['files'],
                'Implementation review does not cover these source versions')
        text(implementation_review.get('reason'), 'implementation review reason')
        text(implementation_review.get('diff'), 'implementation source diff')


def build_replay_from_editor(saved, editor_directory, parent_records, candidate_records, *,
                             memory=None, implementation_review=None, memory_contract=LEGACY_CONTRACT):
    """Shared pairing/fact assembly after the caller's versioned Editor loader."""
    require(saved['editor_status'] == 'candidate', 'Replay requires a real Candidate')
    require(apply_patch(saved['facts']['parent'], saved['actual_diff']) == saved['candidate_text'],
            'Actual diff does not reproduce Candidate')
    p, q = build_facts(parent_records), build_facts(candidate_records)
    require(p['facts'] == saved['facts'], 'Parent facts differ from frozen Editor lineage')
    require(p['background'] == saved['background'] == q['background'], 'Actor background differs')
    require(q['facts']['parent'] == saved['candidate_text'], 'Executed Candidate differs from Editor')
    require(len(parent_records) == len(candidate_records), 'Incomplete paired batch')
    by_task = {r['task']['id']: (r, run, source) for r, run, source in
               zip(candidate_records, q['facts']['runs'], q['sources'])}
    menus = deepcopy(p['facts']['command_sets'])
    menu_ids = {tuple(v): k for k, v in menus.items()}
    candidate_menu_ids = {}
    for key, value in q['facts']['command_sets'].items():
        if tuple(value) not in menu_ids:
            menu_ids[tuple(value)] = f'C{len(menus) + 1}'
            menus[menu_ids[tuple(value)]] = deepcopy(value)
        candidate_menu_ids[key] = menu_ids[tuple(value)]
    runs, pairs, audits = deepcopy(p['facts']['runs']), [], []
    identities = set()
    for index, (parent, prun, psource) in enumerate(zip(parent_records, p['facts']['runs'], p['sources']), 1):
        require(parent['task']['id'] in by_task, 'Candidate task not paired')
        candidate, qrun, qsource = by_task[parent['task']['id']]
        for r in (parent, candidate):
            validate_skill(r['skill'])
            require(r['run_id'] not in identities, 'Execution identity reused')
            identities.add(r['run_id'])
        verify_pair(parent, candidate, implementation_review=implementation_review)
        qrun = deepcopy(qrun)
        qref = f'Q{index}'
        qrun['ref'] = qref
        for i, step in enumerate(qrun['steps'], 1):
            step['step'] = f'{qref}:{i}'
        for state in [qrun['initial'], *[s[side] for s in qrun['steps'] for side in ('before', 'after')]]:
            if state['commands_ref'] is not None:
                state['commands_ref'] = candidate_menu_ids[state['commands_ref']]
        runs.append(qrun)
        pairs.append({'parent': prun['ref'], 'candidate': qref})
        qsource = deepcopy(qsource)
        old_ref = qsource['ref']
        qsource['ref'] = qref
        for event in qsource['events']:
            event['step'] = event['step'].replace(old_ref + ':', qref + ':', 1)
            if event['after_menu_source']:
                event['after_menu_source'] = event['after_menu_source'].replace(old_ref + ':', qref + ':', 1)
        if qsource['pending_step']:
            qsource['pending_step']['step'] = qsource['pending_step']['step'].replace(old_ref + ':', qref + ':', 1)
        audits.append({'pair': pairs[-1], 'task': deepcopy(parent['task']), 'verified': True,
                       'parent': psource, 'candidate': {**deepcopy(qsource), 'ref': qref},
                       'parent_skill': deepcopy(parent['skill']), 'candidate_skill': deepcopy(candidate['skill']),
                       'actor_model': parent['model'], 'backend_id': parent['backend_id'],
                       'protocol': deepcopy(parent['protocol']), 'versions': parent['versions'],
                       'environment': parent['environment'], 'implementation': parent['implementation'],
                       'candidate_implementation': candidate['implementation'],
                       'implementation_review': deepcopy(implementation_review)})
    plan = saved['effective_plan']
    payload = {'parent': parent_text(parent_records[0]), 'diff': saved['actual_diff'],
               'plan': {'goal': plan['goal'], 'updates': [{k: u[k] for k in ('id', 'text')} for u in plan['updates']],
                        'checks': deepcopy(plan['checks'])},
               'command_sets': menus, 'runs': runs, 'pairs': pairs,
               'memory': deepcopy(empty_memory() if memory is None else memory)}
    validate_payload(payload, memory_contract=memory_contract)
    return {'payload': payload, 'background': p['background'], 'pair_audit': audits,
            'editor_directory': str(Path(editor_directory).resolve()), 'candidate': saved['candidate_text'],
            'execution_context': {'background': p['background'], 'actor_model': parent_records[0]['model'],
                'protocol': deepcopy(parent_records[0]['protocol']), 'versions': parent_records[0]['versions']}}


def validate_payload(payload, *, memory_contract=LEGACY_CONTRACT):
    fields(payload, ('parent', 'diff', 'plan', 'command_sets', 'runs', 'pairs', 'memory'), 'Replay input')
    require(payload['parent'] is None or isinstance(payload['parent'], str), 'Invalid Parent')
    apply_patch(payload['parent'], payload['diff'])
    require(isinstance(payload['command_sets'], dict), 'Invalid command sets')
    plan = payload['plan']
    fields(plan, ('goal', 'updates', 'checks'), 'Replay Plan')
    text(plan['goal'], 'goal')
    require(isinstance(plan['updates'], list) and bool(plan['updates']), 'Missing effective Updates')
    ids = set()
    for u in plan['updates']:
        fields(u, ('id', 'text'), 'Replay Update')
        uid = text(u['id'], 'Update ID'); text(u['text'], 'Update text')
        require(uid not in ids, 'Duplicate Update ID'); ids.add(uid)
    require(isinstance(plan['checks'], list), 'Invalid Checks')
    check_ids = set()
    for c in plan['checks']:
        fields(c, ('id', 'update_ids', 'question'), 'Check')
        cid = text(c['id'], 'Check ID'); text(c['question'], 'Check question')
        require(cid not in ids | check_ids, 'Duplicate Check ID'); check_ids.add(cid)
        links(c['update_ids'], ids, 'Check references')
    require(isinstance(payload['runs'], list) and bool(payload['runs']), 'Missing executions')
    ids = []
    for run in payload['runs']:
        validate_run(run, payload['command_sets'])
        ids.append(run['ref'])
    require(len(ids) == len(set(ids)), 'Duplicate execution identity')
    require(isinstance(payload['pairs'], list) and bool(payload['pairs']), 'Missing pairs')
    paired = []
    for pair in payload['pairs']:
        fields(pair, ('parent', 'candidate'), 'Pair')
        require(isinstance(pair['parent'], str) and pair['parent'].startswith('P') and
                isinstance(pair['candidate'], str) and pair['candidate'].startswith('Q'), 'Invalid pair roles')
        paired.extend(pair.values())
    require(len(paired) == len(set(paired)) and set(paired) == set(ids), 'Pairs must cover runs once')
    validate_memory(payload['memory'], memory_contract=memory_contract)
    return payload
