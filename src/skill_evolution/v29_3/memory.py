"""Read committed Knowledge without re-executing its historical model evidence.

The v29.2 canonical commit format, content-addressed chain, writer lock and
atomic HEAD publication are unchanged. Current proposals still validate Gate.
"""
from copy import deepcopy
from pathlib import Path

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v29_2 import memory as base

prepare_append = base.prepare_append
prepare_no_change = base.prepare_no_change


def _states(chain):
    states = [base._empty()]
    for head, commit in chain:
        state = {'head': head,
                 'memory': {'rounds': states[-1]['memory']['rounds'] + [commit['round']]},
                 'selection': commit['selection'],
                 'selected_execution_source': commit['selected_execution_source']}
        base._validate_state(state)
        states.append(state)
    return states


def load_memory(directory, head=None):
    """Validate small committed records; do not open historical sources/images."""
    root = Path(directory)
    chain = base._chain(root, base._read_head(root))
    if head is not None:
        base._head_parts(head)
        positions = [i for i, (cid, _) in enumerate(chain) if cid == head]
        require(bool(positions), 'Requested Memory head is not published history')
        chain = chain[:positions[0] + 1]
    return deepcopy(_states(chain)[-1])


def commit_memory(directory, prepared, *, expected_head):
    """Validate this proposal and publish once; never rebuild old Actor runs."""
    prepared = deepcopy(prepared)
    with current().memory_operation():
        base._validate_prepared(prepared)
    require(base._same(expected_head, prepared['previous']['head']),
            'Expected head differs from prepared history')
    root = Path(directory)
    with base._writer(root):
        current_head = base._read_head(root)
        chain = base._chain(root, current_head)
        states = _states(chain)
        previous = prepared['previous']
        index = 0 if previous['head'] is None else base._head_parts(previous['head'])[0]
        require(index < len(states) and base._same(previous, states[index]),
                'Prepared prefix is not committed history')
        source_data = base._bytes(prepared['source'])
        commit = {'format': base.FORMAT, 'sequence': index + 1, 'previous_head': expected_head,
                  'source_digest': base._digest(source_data),
                  **{key: prepared[key] for key in base._DERIVED}}
        data = base._bytes(commit)
        new_head = f'{index + 1:06d}-{base._digest(data)}'
        for position, (cid, existing) in enumerate(chain, 1):
            if existing['round']['round_id'] == prepared['round']['round_id']:
                require(cid == new_head, 'Round already committed with different content')
                return deepcopy(states[position])
        require(current_head == expected_head, 'Stale Memory head; cannot append a new round')
        if not (root / 'HEAD.json').exists():
            base._publish_head(root, None)
        base._freeze(root / 'sources' / f'{commit["source_digest"]}.json', source_data)
        base._freeze(root / 'commits' / f'{new_head}.json', data)
        # Check exactly the newly staged objects before publishing the pointer.
        staged_source, staged_bytes = base._read(root / 'sources' / f'{commit["source_digest"]}.json')
        require(base._digest(staged_bytes) == commit['source_digest'] and
                base._same(staged_source, prepared['source']), 'Staged Memory source differs')
        state = _states(base._chain(root, new_head))[-1]
        base._publish_head(root, new_head)
        return deepcopy(state)
