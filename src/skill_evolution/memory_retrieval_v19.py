"""Deterministic, learner-safe v19 Memory retrieval; never a Skill editor.

Full round evidence units, closed over explicit/structural cross-round links.
No embedding model, hidden evaluation data, semantic identity merge or auto-resolution.
"""
from dataclasses import dataclass
import re

from .edit_tracking_v19 import encode, parse, skill_ref, trace_edit_history, _rules
from .memory_store_v19 import MemoryRejected, load_memory, require, _round_ref


class MemoryBudgetExceeded(MemoryRejected):
    pass


@dataclass(frozen=True)
class MemoryContext:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)


def _terms(text):
    lowered = text.casefold()
    tokens = set(re.findall(r'[a-z0-9_]+', lowered))
    for sequence in re.findall(r'[\u3400-\u9fff]+', lowered):
        tokens.update(sequence[i:i+2] for i in range(max(1, len(sequence)-1)))
    return tokens


def retrieve_memory(*, store_dir, current_parent, query='', edit_ids=(), max_rounds=None, max_chars=None):
    """Read committed history and return complete evidence, including counterevidence.

    query must be learner-visible text supplied by the caller. Matching is lexical,
    not semantic proof. Review queues work with no query/current failures at all.
    Character budget counts the entire canonical JSON; nothing is silently clipped.
    """
    require(type(current_parent) is str and type(query) is str, 'exact Parent and visible query text required')
    require(type(edit_ids) is tuple and all(type(e) is str for e in edit_ids)
            and len(edit_ids) == len(set(edit_ids)), 'unique explicit edit IDs tuple required')
    for value in (max_rounds, max_chars):
        require(value is None or type(value) is int and value > 0, 'positive retrieval budget required')
    snapshot = load_memory(store_dir)
    head, rounds = snapshot.head, snapshot.rounds
    require(current_parent == head['retained_skill'], 'retrieval Parent differs from committed retained Skill')
    view = trace_edit_history(snapshot.history) if snapshot.history else {
        'current_rules': [{'current_rule_ref': ref, **block, 'writer_edit_ids': [],
                           'ancestor_edit_ids': [], 'contains_initial_or_separator_text': True}
                          for ref, block in _rules(current_parent).items()], 'edits': []}
    bindings = {b['edit_id']: b for b in view['edits']}
    owner = {e['edit_id']: i for i, r in enumerate(rounds) for e in r['edits']}
    require(set(edit_ids) <= set(owner), 'requested edit not in committed memory')
    # Round units already keep joint attributions and every scope/反证 intact.
    # Join related rounds so followups/basis refs never become dangling excerpts.
    parents = list(range(len(rounds)))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    def union(a, b):
        parents[find(a)] = find(b)

    for i, row in enumerate(rounds):
        for edit in row['edits']:
            for link in edit['related_history']:
                union(i, owner[link['prior_edit_id']])
            for change in bindings[edit['edit_id']]['structural_changes']:
                union(i, owner[change['edit_id']])
    groups = {}
    for i in range(len(rounds)):
        groups.setdefault(find(i), []).append(i)
    query_terms = _terms(query)
    reasons, scores = {}, {}
    for i, row in enumerate(rounds):
        why = set()
        ids = {e['edit_id'] for e in row['edits']}
        if ids.intersection(edit_ids):
            why.add('EXPLICIT_EDIT')
        for attribution in row['attribution']['records']:
            effect = attribution.get('effect')
            if effect is None:
                why.add('HISTORICAL_REVIEW_NEEDED')
            if effect in ('HARMFUL', 'MIXED') and any(
                    bindings[e]['binding_status'] in ('EXACT', 'PARTIAL', 'UNRESOLVED')
                    for e in attribution['edit_ids']):
                why.add('NEGATIVE_EVIDENCE_WITH_CURRENT_BINDING')
            if (effect in ('UNKNOWN', 'NOT_EXERCISED', 'HARMFUL', 'MIXED')
                    or attribution.get('suggested_followup') in ('REVISE', 'CONSIDER_REMOVE', 'RETRY', 'DEFER')):
                why.add('HISTORICAL_REVIEW_NEEDED')
            if row['record']['gate_decision'] == 'RETAIN' and effect in ('BENEFICIAL', 'MIXED'):
                why.add('UNPROMOTED_POTENTIAL_BENEFIT')
        # Search observable text and hypotheses, never real task IDs or private DB.
        visible = encode({'edits': row['edits'], 'attribution': row['attribution'], 'pairs': row['replay']['pairs']})
        scores[i] = len(query_terms & _terms(visible))
        if scores[i]:
            why.add('LEXICAL_QUERY_MATCH')
        if not why:
            why.add('HISTORY_REVIEW')
        reasons[i] = sorted(why)

    def rank(group):
        why = {reason for i in group for reason in reasons[i]}
        priority = next((n for n, reason in enumerate((
            'EXPLICIT_EDIT', 'NEGATIVE_EVIDENCE_WITH_CURRENT_BINDING', 'UNPROMOTED_POTENTIAL_BENEFIT',
            'HISTORICAL_REVIEW_NEEDED', 'LEXICAL_QUERY_MATCH')) if reason in why), 5)
        return priority, -sum(scores[i] for i in group), -max(group)

    ordered = sorted(groups.values(), key=rank)
    selected = set()
    excluded_reasons = {tuple(group): 'CHARACTER_BUDGET' for group in ordered}

    def context(indices):
        evidence = []
        for i in sorted(indices):
            row = rounds[i]
            evidence.append({'source': 'COMMITTED_HISTORICAL_EVIDENCE',
                'memory_record': row['record'], 'parent_skill': row['parent_skill'],
                'candidate_skill': row['candidate_skill'], 'edits': row['edits'],
                'source_evidence': row['source_evidence'],
                'current_bindings': [bindings[e['edit_id']] for e in row['edits']],
                'replay': row['replay'], 'attribution': row['attribution']})
            if 'generation_reviews' in row:
                evidence[-1]['generation_reviews'] = row['generation_reviews']
        return {'schema_version': 'memory_context_v19.1', 'run_id': head['run_id'],
            'committed_memory_ref': head['memory_ref'], 'current_parent_ref': skill_ref(current_parent),
            'current_parent': current_parent, 'current_rules': view['current_rules'],
            'interpretation_boundary': 'HISTORICAL_HYPOTHESES_NOT_POLICY_OR_EDIT_AUTHORIZATION',
            'resolution_status': 'NOT_AUTOMATICALLY_INFERRED_FROM_GATE_OR_FOLLOWUP',
            'query': query, 'requested_edit_ids': list(edit_ids), 'rounds': evidence,
            'selection': {'method': 'ROUND_AND_LINEAGE_CLOSURE_WITH_LEXICAL_AND_REVIEW_PRIORITY',
                'max_rounds': max_rounds, 'max_chars': max_chars, 'size_unit': 'CANONICAL_JSON_CHARACTERS',
                'total_committed_rounds': len(rounds), 'selected_rounds': len(indices),
                'complete_history': len(indices) == len(rounds),
                'units': [{'round_refs': [_round_ref(rounds[i]['record']) for i in group],
                           'selected': all(i in indices for i in group),
                           'retrieval_reasons': sorted({r for i in group for r in reasons[i]}),
                           'lexical_overlap': sum(scores[i] for i in group),
                           'exclusion_reason': None if all(i in indices for i in group) else
                               excluded_reasons.get(tuple(group), 'NOT_SELECTED')}
                          for group in ordered]}}

    for group in ordered:
        proposed = selected | set(group)
        if max_rounds is not None and len(proposed) > max_rounds:
            excluded_reasons[tuple(group)] = 'ROUND_BUDGET'
            continue
        # Use final-size exclusion labels for all remaining units when checking
        # budget so a later metadata update cannot push the result over budget.
        excluded_reasons[tuple(group)] = 'CHARACTER_BUDGET'
        if max_chars is not None and len(encode(context(proposed))) > max_chars:
            continue
        selected = proposed
    payload = context(selected)
    if max_chars is not None and len(encode(payload)) > max_chars:
        raise MemoryBudgetExceeded('budget cannot fit context and complete selection manifest')
    if rounds and not selected:
        raise MemoryBudgetExceeded('no complete round/lineage evidence unit fits; increase budget')
    # An explicit edit request cannot silently return an unrelated unit instead.
    require(all(owner[e] in selected for e in edit_ids), 'budget excluded explicitly requested edit evidence')
    return MemoryContext(encode(payload))
