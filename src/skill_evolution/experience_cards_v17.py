"""Lossless, outcome-free cards from trusted runtime-captured experience.

This module reuses the existing capture envelopes, not the three-rollout Diagnosis
request. Source identity is supplied by the trusted runtime; no file/task-spec
loader or LLM is involved. Repeated events are meaningful and are never deduplicated.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable

from .experience_grouping_contract_v17 import (
    EvolutionExperienceRef, GroupingContractError, GroupingScope, _scope,
    validate_grouping_input,
)
from .information_boundary_v15 import Envelope, unpack


@dataclass(frozen=True)
class CapturedGroupingExperience:
    """Runtime-owned identity plus signed public context and observed trajectory.

    The caller must bind round/Parent/reference at capture or trusted replay time;
    the underlying v15 envelopes do not themselves authenticate those identities.
    """

    round_id: str
    parent_skill_digest: str
    ref: EvolutionExperienceRef
    visible_view: Envelope
    experience: Envelope


@dataclass(frozen=True)
class ExperienceCardBatch:
    """Only input_json goes to Grouper; statistics are runtime diagnostics."""

    input_json: str
    statistics: dict

    @property
    def payload(self) -> dict:
        return json.loads(self.input_json)


class ExperienceCardBudgetError(GroupingContractError):
    def __init__(self, statistics: dict):
        self.statistics = statistics
        super().__init__('Grouping input exceeds budget; no events were truncated: '
                         + json.dumps(statistics, ensure_ascii=False, sort_keys=True))


def _serialize(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def build_experience_cards(
    sources: tuple[CapturedGroupingExperience, ...], *, scope: GroupingScope,
    max_input_chars: int | None = None,
    token_counter: Callable[[str], int] | None = None,
    max_input_tokens: int | None = None,
) -> ExperienceCardBatch:
    """Build all cards in manifest order, validate, measure, and fail on overflow.

    Token counts require a caller-supplied tokenizer. Limits apply to serialized
    input only; the future Grouper must reserve prompt/schema/output headroom.
    """
    tasks = _scope(scope)
    for limit in (max_input_chars, max_input_tokens):
        if limit is not None and (type(limit) is not int or limit <= 0):
            raise GroupingContractError('input budgets must be positive integers')
    if max_input_tokens is not None and token_counter is None:
        raise GroupingContractError('token budget requires an explicit token_counter')
    if not isinstance(sources, tuple):
        raise GroupingContractError('sources must be a tuple of captured experiences')
    by_task = {}
    for source in sources:
        if not isinstance(source, CapturedGroupingExperience):
            raise GroupingContractError('captured experience required, not raw records')
        if (source.round_id, source.parent_skill_digest) != (scope.round_id, scope.parent_skill_digest):
            raise GroupingContractError('source round/Parent mismatch')
        if not isinstance(source.ref, EvolutionExperienceRef) or source.ref not in scope.experiences:
            raise GroupingContractError('source outside current Evolution manifest')
        if source.ref.task_ref in by_task:
            raise GroupingContractError('duplicate source task')
        by_task[source.ref.task_ref] = source
    if set(by_task) != set(tasks):
        raise GroupingContractError('sources must exactly cover Evolution manifest')

    contexts, cards = {}, []
    for ref in scope.experiences:
        source = by_task[ref.task_ref]
        public = unpack(source.visible_view, 'AGENT_VISIBLE_VIEW')
        observed = unpack(source.experience, 'TRAJECTORY_DERIVED')
        digest = hashlib.sha256(source.visible_view.payload.encode()).hexdigest()
        if observed['view_digest'] != digest or observed['domain'] != public['domain']:
            raise GroupingContractError('trajectory does not match captured visible context')
        context = {'context_ref': ref.context_ref,
                   'visible_policy': public['visible_policy'], 'public_tools': public['public_tools']}
        if ref.context_ref in contexts and contexts[ref.context_ref] != context:
            raise GroupingContractError('context_ref reused for different policy/tools')
        contexts[ref.context_ref] = context
        cards.append({'task_ref': ref.task_ref, 'context_ref': ref.context_ref,
                      'trajectory_ref': ref.trajectory_ref, 'events': observed['trajectory']})

    payload = {'contexts': list(contexts.values()), 'cards': cards}
    validate_grouping_input(payload, scope=scope)
    serialized = _serialize(payload)
    tokens = token_counter(serialized) if token_counter is not None else None
    if token_counter is not None and (type(tokens) is not int or tokens < 0):
        raise GroupingContractError('token_counter must return a nonnegative integer')
    stats = {
        'task_count': len(cards), 'context_count': len(contexts),
        'event_count': sum(len(card['events']) for card in cards),
        'input_chars': len(serialized), 'input_utf8_bytes': len(serialized.encode('utf-8')),
        'input_tokens': tokens,
        'max_input_chars': max_input_chars, 'max_input_tokens': max_input_tokens,
        'cards': [{'task_ref': card['task_ref'], 'event_count': len(card['events']),
                   'serialized_chars': len(_serialize(card))} for card in cards],
    }
    if ((max_input_chars is not None and len(serialized) > max_input_chars)
            or (max_input_tokens is not None and tokens > max_input_tokens)):
        raise ExperienceCardBudgetError(stats)
    return ExperienceCardBatch(serialized, stats)
