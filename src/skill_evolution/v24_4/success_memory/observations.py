"""Supplemental behavioral observations, excluded from the flip Replay and Gate."""
from src.skill_evolution.v24_2 import method
from src.skill_evolution.v27.contracts.diagnosis import fields
from src.skill_evolution.v27.facts import require


def success_input(adapter, audit, parents, children, diff):
    verified = audit['input']['pairs']
    require(len(verified) == len(parents) == len(children), 'Incomplete paired batch')
    ranked = []
    for index, (pair, p, q) in enumerate(zip(verified, parents, children)):
        for side, raw in [('parent', p), ('candidate', q)]:
            require(pair[side]['run_id'] == raw['run_id'] and pair['task_id'] == raw['task']['id'],
                    'Success observation run differs from verified pair')
        if pair['parent']['success'] and pair['candidate']['success']:
            gap = abs(len(q['steps']) - len(p['steps']))
            if gap:
                ranked.append((-gap, index))
    chosen = [i for _, i in sorted(ranked)[:2]]
    payload = dict(pairs=[], runs=[], command_sets={}, diff=diff)
    if not chosen:
        return payload
    for records, prefix in [(parents, 'P'), (children, 'Q')]:
        facts = adapter.build_facts([records[i] for i in chosen])['facts']
        for i, run in zip(chosen, facts['runs']):
            ref = f'{prefix}{i+1}'
            run['ref'] = ref
            for n, step in enumerate(run['steps'], 1):
                step['step'] = f'{ref}:{n}'
            for state in [run['initial'], *(s[k] for s in run['steps'] for k in ('before', 'after'))]:
                key = state['commands_ref']
                if key in facts['command_sets']:
                    state['commands_ref'] = f'{prefix}_{key}'
            payload['runs'].append(run)
        payload['command_sets'].update({f'{prefix}_{k}': v for k, v in facts['command_sets'].items()})
    for i in chosen:
        payload['pairs'].append(dict(task_id=verified[i]['task_id'], parent=f'P{i+1}', candidate=f'Q{i+1}',
                                     parent_steps=len(parents[i]['steps']), candidate_steps=len(children[i]['steps'])))
    return payload


def validate_observations(result, payload):
    fields(result, ('observations',), 'Success-pair Replay')
    items = result['observations']
    require(isinstance(items, list), 'Expected observations array')
    pairs = {p['task_id']: p for p in payload['pairs']}
    runs = {r['ref']: r for r in payload['runs']}
    ids = []
    observations = []
    for item in items:
        fields(item, ('task_id', 'text', 'evidence'), 'Observation')
        task = item['task_id']
        require(isinstance(task, str) and task in pairs, 'Unknown observed task')
        ids.append(task)
        pair = pairs[task]
        sides = [{s['step'] for s in runs[pair[k]]['steps']} for k in ('parent', 'candidate')]
        ev = item['evidence']
        require(isinstance(ev, list) and all(isinstance(e, str) for e in ev), 'Expected step references')
        refs = set(ev)
        require(len(ev) == len(refs) and refs <= (sides[0] | sides[1]) and all(refs & s for s in sides),
                'Cite distinct steps from both runs of this task')
        method.cited(item['text'], sides[0] | sides[1])
        observations.append(dict(kind='both_success', parent_steps=pair['parent_steps'],
                                 candidate_steps=pair['candidate_steps'], **item))
    require(ids == [t for t in pairs if t in ids], 'Duplicate or out-of-order observation')
    return observations


def next_memory_id(memory):
    return 1 + max((int(entry['id'][1:]) for r in memory['rounds']
                    for key in ('entries', 'observations') for entry in r.get(key, [])), default=0)


def attach_observations(memory, observations):
    if not observations:
        return memory
    first = next_memory_id(memory)
    rounds = memory['rounds']
    require('observations' not in rounds[-1], 'Success observations already attached')
    extra = [dict(id=f'M{i}', **item) for i, item in enumerate(observations, first)]
    return dict(rounds=[*rounds[:-1], dict(rounds[-1], observations=extra)])


def effective_plan(result, payload):
    # The frozen validator reads only entry IDs. Include the additional citable
    # IDs in its local view; the actual model input keeps the two lists separate.
    rounds = [dict(r, entries=r['entries'] + r.get('observations', [])) for r in payload['memory']['rounds']]
    return method.effective_plan(result, dict(payload, memory=dict(rounds=rounds)))
