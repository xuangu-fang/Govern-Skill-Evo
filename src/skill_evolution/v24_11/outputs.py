"""Match model output to its inputs before applying the shared ALFWorld contracts."""
from src.skill_evolution.v24_2 import method
from src.skill_evolution.v27.contracts.diagnosis import fields
from src.skill_evolution.v27.facts import require


def _in_input_order(items, key, expected_ids):
    require(isinstance(items, list), f'Expected an array of items with {key}')
    indexed = {}
    for item in items:
        require(isinstance(item, dict) and isinstance(item.get(key), str), f'Expected a string {key}')
        identifier = item[key]
        require(identifier not in indexed, f'Duplicate {key}: {identifier}')
        indexed[identifier] = item
    require(indexed.keys() == set(expected_ids), f'Missing or unknown {key}')
    return [indexed[identifier] for identifier in expected_ids]


def effective_plan(result, payload):
    fields(result, ('adjustments',), 'Preconditioner')
    ids = [update['id'] for update in payload['plan']['updates']]
    adjustments = _in_input_order(result['adjustments'], 'target', ids)
    return method.effective_plan({'adjustments': adjustments}, payload)


def knowledge(result, payload):
    fields(result, ('entries',), 'Replay')
    entries = result['entries']
    require(isinstance(entries, list) and len(entries) == 1, 'Expected one Knowledge container')
    fields(entries[0], ('knowledge',), 'Entry')
    ids = [pair['task_id'] for pair in payload['pairs']]
    events = _in_input_order(entries[0]['knowledge'], 'task_id', ids)
    return method.knowledge({'entries': [{'knowledge': events}]}, payload)
