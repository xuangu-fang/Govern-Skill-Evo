"""Deterministic single-owner routing of learner-safe historical edit units.

Routing is a scheduling hint, not causal evidence. No task aliases, outcomes,
Gate decisions, or hypothesis prose participate in similarity scoring.
"""
from copy import deepcopy
from fractions import Fraction

from .edit_tracking_v19 import digest, encode
from .memory_store_v19 import require
from ..v17.group_diagnosis_input_v17 import GroupDiagnosisInput
from ..v15.information_boundary_v15 import _seal


def _tools(events):
    return {e['tool_name'] for e in events
            if e.get('event_type') == 'tool_call' and e.get('tool_name')}


def _context(context):
    return digest(encode({k: context[k] for k in ('visible_policy', 'public_tools')}))


def _features(payload):
    contexts = {c['context_ref']: _context(c) for c in payload['contexts']}
    return {(contexts[e['context_ref']], tool) for e in payload['experiences']
            for tool in _tools(e['events'])}


def allocate_memory(memory, requests):
    """Return (request, allocated Memory) pairs with an auditable batch manifest.

    Joint attributions and explicit/structural lineage are indivisible. A unique
    positive tool/context overlap selects a current group; ties and no matches
    go to a historical-only review. Every selected edit has exactly one owner.
    """
    rows = memory['rounds']
    edits = {e['edit_id']: e for row in rows for e in row['edits']}
    parents = {key: key for key in edits}

    def root(key):
        while parents[key] != key:
            key = parents[key]
        return key

    def join(keys):
        roots = sorted({root(k) for k in keys if k in parents})
        for key in roots[1:]:
            parents[key] = roots[0]

    for row in rows:
        for record in row['attribution']['records']:
            join(record['edit_ids'])
        for edit, binding in zip(row['edits'], row['current_bindings']):
            join([edit['edit_id']] + [r['prior_edit_id'] for r in edit['related_history']])
            for change in binding['structural_changes']:
                join([edit['edit_id'], change['edit_id']] + change['affected_prior_edit_ids'])
    units = {}
    for key in sorted(edits):
        units.setdefault(root(key), []).append(key)
    group_features = {r.provenance['group_id']: _features(r.learner_payload) for r in requests}
    require(len(group_features) == len(requests), 'duplicate current group ID')
    history_group = 'HISTORY/' + digest(encode(sorted(edits)))
    require(history_group not in group_features, 'historical review group collision')
    allocations = []
    for ids in sorted(units.values()):
        features = set()
        for row in rows:
            contexts = {c['context_ref']: _context(c) for c in row['replay']['contexts']}
            pairs = {p['pair_id']: p for p in row['replay']['pairs']}
            for record in row['attribution']['records']:
                if not set(ids).intersection(record['edit_ids']):
                    continue
                for observation in record['observations']:
                    pair = pairs[observation['pair_id']]
                    for role in ('parent', 'candidate'):
                        refs = set(observation[role + '_evidence_refs'])
                        events = [e for e in pair[role]['events'] if e['evidence_ref'] in refs]
                        features.update((contexts[pair[role]['context_ref']], t) for t in _tools(events))
        # Inverse group frequency reduces generic tools' routing influence.
        scores = {group: sum((Fraction(1, sum(f in fs for fs in group_features.values()))
                            for f in features & fs), Fraction())
                  for group, fs in group_features.items()}
        maximum = max(scores.values(), default=Fraction())
        winners = sorted(g for g, score in scores.items() if score == maximum and score > 0)
        owner = winners[0] if len(winners) == 1 else history_group
        allocations.append({'edit_ids': ids, 'owner': owner,
            'reason': 'UNIQUE_VISIBLE_TOOL_CONTEXT_OVERLAP' if len(winners) == 1 else
                      'AMBIGUOUS_MATCH' if winners else 'NO_VISIBLE_TOOL_CONTEXT_MATCH',
            'scores': {g: str(s) for g, s in sorted(scores.items())}})
    manifest = {'schema_version': 'memory_allocation_v19.1',
                'retrieved_memory_sha256': digest(encode(memory)), 'units': allocations,
                'review_group_ids': sorted(set(group_features) | {a['owner'] for a in allocations})}
    work = list(requests)
    if any(a['owner'] == history_group for a in allocations):
        require(bool(requests), 'current Diagnosis groups required')
        payload = requests[0].learner_payload
        payload.update(grouping_hint={'group_id': history_group, 'members': [],
            'decision_problem': 'Reassess historical edits without a unique current-group match',
            'shared_basis': 'Historical evidence only; current applicability remains unproven',
            'important_differences': [], 'origin': 'HISTORICAL_MEMORY_REVIEW'},
            experiences=[], contexts=[], available_evidence_refs={}, available_supervision_refs={})
        provenance = {**requests[0].provenance, 'group_id': history_group, 'experience_bindings': []}
        work.append(GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT', payload), encode(provenance)))
    result = []
    for request in work:
        owner = request.provenance['group_id']
        owned = {e for a in allocations if a['owner'] == owner for e in a['edit_ids']}
        view = {k: deepcopy(v) for k, v in memory.items() if k != 'rounds'}
        view['rounds'] = []
        for row in rows:
            selected = [e for e in row['edits'] if e['edit_id'] in owned]
            if not selected:
                continue
            sliced = deepcopy(row)
            sliced['edits'] = selected
            sliced['current_bindings'] = [b for b in sliced['current_bindings'] if b['edit_id'] in owned]
            sliced['attribution']['records'] = [r for r in sliced['attribution']['records']
                                              if owned.intersection(r['edit_ids'])]
            evidence_ids = {ref for e in selected for ref in e['source_evidence_refs']}
            evidence_ids.update(ref for e in selected for link in e['related_history'] for ref in link['basis_refs'])
            sliced['source_evidence'] = [e for e in sliced['source_evidence'] if e['evidence_id'] in evidence_ids]
            pair_ids = {o['pair_id'] for r in sliced['attribution']['records'] for o in r['observations']}
            # Unresolved edits without observations need the full original replay
            # to remain reviewable. Otherwise include all cited sides and counterevidence.
            full = len(selected) == len(row['edits']) or any(
                not r['observations'] for r in sliced['attribution']['records'])
            if not full:
                sliced['replay']['pairs'] = [p for p in sliced['replay']['pairs'] if p['pair_id'] in pair_ids]
                context_ids = {p[role]['context_ref'] for p in sliced['replay']['pairs']
                               for role in ('parent', 'candidate')}
                sliced['replay']['contexts'] = [c for c in sliced['replay']['contexts']
                                                if c['context_ref'] in context_ids]
            sliced['allocation_scope'] = {'owned_edit_ids': sorted(e['edit_id'] for e in selected),
                'replay_scope': 'FULL_ROUND_BACKGROUND' if full else 'ALL_ASSIGNED_ATTRIBUTION_PAIRS',
                'summary_scope': 'ORIGINAL_FULL_ROUND_NOT_ALLOCATED_SUBSET',
                'source_row_sha256': digest(encode(row))}
            view['rounds'].append(sliced)
        view['allocation'] = {'schema_version': 'memory_allocation_view_v19.1',
            'owner': owner, 'owned_edit_ids': sorted(owned),
            'batch_manifest_sha256': digest(encode(manifest)),
            'review_scope': 'OWNED_EDITS_ONLY', 'selection_scope': 'RETRIEVAL_BEFORE_ALLOCATION'}
        provenance = {**request.provenance, 'memory_allocation': manifest}
        result.append((GroupDiagnosisInput(request.learner_view, encode(provenance)), view))
    return tuple(result)


def validate_allocation(requests):
    """Check complete, unique ownership before any generation calls."""
    require(bool(requests), 'Diagnosis requests required')
    manifest = requests[0].provenance['memory_allocation']
    expected = [(e, a['owner']) for a in manifest['units'] for e in a['edit_ids']]
    require(len({e for e, _ in expected}) == len(expected), 'duplicate allocated edit')
    require(sorted(r.provenance['group_id'] for r in requests) == manifest['review_group_ids'],
            'incomplete or repeated review group ownership')
    actual = []
    for request in requests:
        require(request.provenance['memory_allocation'] == manifest, 'allocation manifest mismatch')
        memory = request.learner_payload['memory_context']
        allocation = memory['allocation']
        owner = request.provenance['group_id']
        require(allocation['owner'] == owner and allocation['batch_manifest_sha256'] == digest(encode(manifest)),
                'allocation binding mismatch')
        ids = [e['edit_id'] for row in memory['rounds'] for e in row['edits']]
        require(sorted(ids) == allocation['owned_edit_ids'], 'allocated edit view mismatch')
        actual.extend((e, owner) for e in ids)
    require(sorted(actual) == sorted(expected), 'incomplete or repeated historical review ownership')
