from copy import deepcopy
from src.skill_evolution.v24.facts import require
from src.skill_evolution.v24.contracts.memory import MULTI_KNOWLEDGE_CONTRACT as CONTRACT
from src.skill_evolution.v24.contracts.replay import validate_payload
from src.skill_evolution.v24.contracts.replay_view import _current_pairs
from src.skill_evolution.v24.replay import validate_result
from src.skill_evolution.v24 import knowledge_verifier as v, knowledge_repair as repair
from src.skill_evolution.v24.knowledge_evidence import menu_key, select_targets, verify_equivalence

def extract(ref, bundle, historical):
    """Fixed reference-granularity extraction; never expand neighbors or claims."""
    if '/' in ref:
        context_id, local = ref.rsplit('/', 1)
        source = historical[context_id]
    else:
        context_id, local, source = None, ref, bundle
    payload = source['payload']
    if local == 'diff':
        return {'parent': deepcopy(payload['parent']), 'diff': payload['diff'],
                'execution_context': deepcopy(source['execution_context'])}
    rid, _, suffix = local.partition(':')
    run = next(r for r in payload['runs'] if r['ref'] == rid)
    _current_pairs(source)  # Includes task IDs and recorded pair audit checks.
    audit = next(a for a in source['pair_audit'] if rid in a['pair'].values())
    role = next(side for side, value in audit['pair'].items() if value == rid)
    result = {'task_id': audit['task']['id'], 'task': run['task'], 'role': role}
    if not suffix:
        record = run
        states = [run['initial'], *[s[side] for s in run['steps'] for side in ('before', 'after')]]
    elif suffix == '0':
        record, states = run['initial'], [run['initial']]
    elif suffix == 'outcome':
        record, states = run['outcome'], []
        result['executed_action_count'] = len(run['steps'])
    else:
        record = next(s for s in run['steps'] if s['step'] == local)
        states = [record['before'], record['after']]
    menus = list(dict.fromkeys(s['commands_ref'] for s in states if s['commands_ref'] is not None))
    result.update(record=deepcopy(record),
                  command_sets={key: deepcopy(payload['command_sets'][key]) for key in menus})
    if context_id:
        # Historical Actor conditions must not be inferred from the current round.
        result['execution_context'] = deepcopy(source['execution_context'])
    return result


def build_input(bundle, candidate, historical=None):
    historical = historical or {}
    payload = validate_payload(bundle['payload'], memory_contract=CONTRACT)
    validate_result(candidate, payload, memory_contract=CONTRACT)
    pairs, _ = _current_pairs(bundle)
    targets, inventory = select_targets(candidate, payload['memory'])
    refs = list(dict.fromkeys(ref for target in targets for ref in target['knowledge']['evidence']))
    for cid in {ref.rsplit('/', 1)[0] for ref in refs if '/' in ref}:
        prior = historical[cid]
        validate_payload(prior['payload'], memory_contract=CONTRACT)
        _current_pairs(prior)
        # Check retrieved originals against the actual frozen Memory sources.
        for key, original in payload['memory']['sources'].items():
            if key.rsplit('/', 1)[0] != cid:
                continue
            local = key.rsplit('/', 1)[1]
            if local == 'diff':
                require(original == {k: prior['payload'][k] for k in ('parent', 'diff')} |
                        {'execution_context': prior['execution_context']}, 'Historical edit differs')
            else:
                run = next(r for r in prior['payload']['runs'] if r['ref'] == local)
                require(original['run'] == run, 'Historical run differs')
                require(all(prior['payload']['command_sets'].get(k) == v
                            for k, v in original['command_sets'].items()), 'Historical menus differ')
    cited_runs = {ref.split(':')[0] for ref in refs if '/' not in ref and ref != 'diff'}
    # Only identities of cited current pairs; no all-task catalog or extra outcomes.
    related_pairs = [{k: pair[k] for k in ('task_id', 'parent', 'candidate')}
                     for pair in pairs if pair['parent'] in cited_runs or pair['candidate'] in cited_runs]
    value = {'context': {'parent': payload['parent'], 'diff': payload['diff'],
                         'execution_context': deepcopy(bundle['execution_context']), 'pairs': related_pairs},
             'targets': targets, 'source_records': {ref: extract(ref, bundle, historical) for ref in refs}}
    return value, inventory


def menu_references(value):
    """Inspect only the raw record, including full-run initial/before/after states."""
    result = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'commands_ref':
                require(item is None or isinstance(item, str) and bool(item), 'Invalid commands_ref')
                if item is not None:
                    result.add(item)
            else:
                result.update(menu_references(item))
    elif isinstance(value, list):
        for item in value:
            result.update(menu_references(item))
    return result


def check_sources(value, mapping_field):
    evidence = {ref for item in value['targets'] for ref in item['knowledge']['evidence']}
    require(evidence == set(value['source_records']), 'Evidence/source coverage differs')
    for ref, source in value['source_records'].items():
        if ref.rsplit('/', 1)[-1] == 'diff':
            require(mapping_field not in source and 'record' not in source, 'Unexpected diff menu/record')
            continue
        require('record' in source and isinstance(source.get(mapping_field), dict), 'Missing record/menu map')
        require(menu_references(source['record']) == set(source[mapping_field]),
                   f'{ref}: missing or unused local menu reference')


def compact(original):
    require(set(original) == {'context', 'targets', 'source_records'}, 'Not a v1 input')
    check_sources(original, 'command_sets')
    value = deepcopy(original)
    pool, ids = {}, {}
    for source in value['source_records'].values():
        require('command_set_refs' not in source, 'Input already contains shared references')
        if 'command_sets' not in source:
            continue
        local = source.pop('command_sets')
        links = {}
        for old_id, menu in local.items():
            key = menu_key(menu)
            if key not in ids:
                shared_id = f'CS{len(ids) + 1}'
                ids[key] = shared_id
                pool[shared_id] = menu
            links[old_id] = ids[key]
        source['command_set_refs'] = links
    value['command_sets'] = pool
    verify_equivalence(original, value)
    return value


def restore(value):
    require(set(value) == {'context', 'targets', 'source_records', 'command_sets'}, 'Not a v2 input')
    check_sources(value, 'command_set_refs')
    pool = value['command_sets']
    require(isinstance(pool, dict), 'Shared menus must be an object')
    require(all(isinstance(key, str) and key for key in pool), 'Invalid shared ID')
    keys = [menu_key(menu) for menu in pool.values()]
    require(len(set(keys)) == len(keys), 'Duplicate shared menu content')
    restored, used = deepcopy(value), set()
    restored.pop('command_sets')
    for source in restored['source_records'].values():
        require('command_sets' not in source, 'Unexpected inline menus in v2')
        if 'command_set_refs' not in source:
            continue
        links = source.pop('command_set_refs')
        local = {}
        for old_id, shared_id in links.items():
            require(isinstance(shared_id, str) and shared_id in pool, 'Missing shared menu reference')
            local[old_id] = deepcopy(pool[shared_id])
            used.add(shared_id)
        source['command_sets'] = local
    require(used == set(pool), 'Unused shared menu')
    return restored


def build_repair_input(verifier_input, verdicts, candidate):
    v.validate_result(verdicts, verifier_input)
    originals = {v.position(t['target'], 'target'): t for t in verifier_input['targets']}
    targets, refs = [], set()
    for row in verdicts['results']:
        if row['verdict'] != 'CONFLICT':
            continue
        ei, ki = key = v.position(row['target'], 'target')
        target = deepcopy(originals[key])
        require(repair.exact(target['knowledge']) == repair.exact(candidate['entries'][ei]['knowledge'][ki]),
                   'Verifier target differs from candidate')
        target['issues'] = deepcopy(row['issues'])
        targets.append(target)
        refs.update(target['knowledge']['evidence'])
        refs.update(ref for issue in row['issues'] for ref in issue['evidence'])
    sources = {ref: deepcopy(source) for ref, source in verifier_input['source_records'].items() if ref in refs}
    require(set(sources) == refs, 'Missing requested source')
    menu_ids = {cid for s in sources.values() for cid in s.get('command_set_refs', {}).values()}
    menus = {cid: deepcopy(menu) for cid, menu in verifier_input['command_sets'].items() if cid in menu_ids}
    context = deepcopy(verifier_input['context'])
    runs = {ref.split(':')[0] for ref in refs if '/' not in ref and ref != 'diff'}
    context['pairs'] = [p for p in context['pairs'] if p['parent'] in runs or p['candidate'] in runs]
    result = {'context': context, 'targets': targets, 'source_records': sources, 'command_sets': menus}
    # Include issue-only citations in the restoration check, without adding synthetic
    # Knowledge to actual model messages. Preserve source-local IDs and shared IDs.
    view = {**result, 'targets': [{'knowledge': {'evidence': list(sources)}}]}
    restored = restore(view)
    original = restore(verifier_input)
    for ref in sources:
        require(repair.exact(restored['source_records'][ref]) == repair.exact(original['source_records'][ref]),
                   f'Raw record/menu mismatch: {ref}')
    return result
