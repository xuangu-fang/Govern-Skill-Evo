from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from src.skill_evolution.experience_cards_v17 import (
    CapturedGroupingExperience, ExperienceCardBudgetError, build_experience_cards,
)
from src.skill_evolution.experience_grouping_contract_v17 import (
    EvolutionExperienceRef, GroupingContractError, GroupingScope,
)
from src.skill_evolution.information_boundary_v15 import (
    BoundaryError, capture_agent_visible_view, capture_experience,
    project_oracle_supervision, unpack,
)


def captured(ref, *, policy='先报告价格，再请求确认。', success=True):
    agent = SimpleNamespace(domain_policy=policy, tools=[SimpleNamespace(openai_schema={
        'type': 'function', 'function': {'name': 'change', 'description': 'Change.',
                                      'parameters': {'type': 'object'}}})])
    view = capture_agent_visible_view(agent, 'airline')
    message = {'actor': 'user', 'event_type': 'message', 'content': '18:00 后，先告诉我差价。'}
    events = [message, dict(message),
              {'actor': 'assistant', 'event_type': 'tool_call', 'tool_name': 'change',
               'arguments': {'price': 123, 'flight': 'AB123'}},
              {'actor': 'tool', 'event_type': 'tool_result', 'tool_name': 'change',
               'content': {'success': True, 'price': 123}},
              {'actor': 'user', 'event_type': 'message', 'content': '最后一条约束：不要购买保险。'}]
    labels = project_oracle_supervision({'success': success, 'expected_action': 'SECRET'},
                                       {'compliant': not success, 'reason': 'SECRET'})
    experience = capture_experience(view, events, labels, 1)
    return CapturedGroupingExperience('round-1', 'parent', ref, view, experience)


@pytest.fixture
def case():
    refs = tuple(EvolutionExperienceRef(f'T{i}', 'C1', f'R{i}') for i in (1, 2))
    return GroupingScope('round-1', 'parent', refs), tuple(captured(ref) for ref in refs)


def test_lossless_ordered_outcome_free_cards(case):
    scope, sources = case
    batch = build_experience_cards(tuple(reversed(sources)), scope=scope)
    assert [c['task_ref'] for c in batch.payload['cards']] == ['T1', 'T2']
    assert len(batch.payload['contexts']) == 1
    for source, card in zip(sources, batch.payload['cards']):
        assert card['events'] == unpack(source.experience, 'TRAJECTORY_DERIVED')['trajectory']
        assert card['events'][0]['content'] == card['events'][1]['content']
        assert card['events'][-1]['step'] == 5
        assert card['events'][3]['content']['success'] is True  # Real tool data stays.
    assert 'supervision' not in batch.input_json
    assert 'compliant' not in batch.input_json
    assert 'SECRET' not in batch.input_json
    assert batch.statistics['event_count'] == 10
    assert batch.statistics['input_chars'] == len(batch.input_json)
    assert batch.statistics['input_utf8_bytes'] > batch.statistics['input_chars']
    assert batch.statistics['input_tokens'] is None
    payload = batch.payload
    payload['cards'].clear()
    assert len(batch.payload['cards']) == 2


def test_supervision_does_not_affect_cards(case):
    scope, sources = case
    changed = tuple(captured(ref, success=False) for ref in scope.experiences)
    assert build_experience_cards(sources, scope=scope).input_json == build_experience_cards(changed, scope=scope).input_json


def test_budgets_never_truncate(case):
    scope, sources = case
    batch = build_experience_cards(sources, scope=scope)
    size = len(batch.input_json)
    assert build_experience_cards(sources, scope=scope, max_input_chars=size).input_json == batch.input_json
    with pytest.raises(ExperienceCardBudgetError) as error:
        build_experience_cards(sources, scope=scope, max_input_chars=size - 1)
    assert error.value.statistics['event_count'] == 10
    counter = lambda text: len(text.encode('utf-8'))  # Deterministic test counter, not a tokenizer.
    tokens = counter(batch.input_json)
    assert build_experience_cards(sources, scope=scope, token_counter=counter,
                                  max_input_tokens=tokens).statistics['input_tokens'] == tokens
    with pytest.raises(ExperienceCardBudgetError):
        build_experience_cards(sources, scope=scope, token_counter=counter, max_input_tokens=tokens - 1)


@pytest.mark.parametrize('kwargs', [
    {'max_input_chars': 0}, {'max_input_chars': True}, {'max_input_tokens': 3},
    {'token_counter': lambda _: -1}, {'token_counter': lambda _: True},
])
def test_invalid_budget_settings(case, kwargs):
    scope, sources = case
    with pytest.raises(GroupingContractError):
        build_experience_cards(sources, scope=scope, **kwargs)


@pytest.mark.parametrize('change', [
    lambda s: (), lambda s: (s[0],), lambda s: (s[0], s[0]),
    lambda s: ({}, s[1]),
    lambda s: (replace(s[0], round_id='old-round'), s[1]),
    lambda s: (replace(s[0], parent_skill_digest='different-parent'), s[1]),
    lambda s: (replace(s[0], ref=EvolutionExperienceRef('Monitor', 'C1', 'R0')), s[1]),
])
def test_reject_bad_runtime_bindings(case, change):
    scope, sources = case
    with pytest.raises(GroupingContractError):
        build_experience_cards(change(sources), scope=scope)


def test_reject_unsigned_and_tampered_experience(case):
    scope, sources = case
    for bad in (json.loads(sources[0].experience.payload),
                replace(sources[0].experience, payload='{}'), sources[0].visible_view):
        with pytest.raises(BoundaryError):
            build_experience_cards((replace(sources[0], experience=bad), sources[1]), scope=scope)


def test_context_mismatch_and_alias_collision(case):
    scope, sources = case
    other = captured(scope.experiences[1], policy='Different policy')
    with pytest.raises(GroupingContractError, match='visible context'):
        build_experience_cards((replace(sources[0], visible_view=other.visible_view), sources[1]), scope=scope)
    with pytest.raises(GroupingContractError, match='context_ref reused'):
        build_experience_cards((sources[0], other), scope=scope)


def test_separate_contexts_are_preserved(case):
    scope, sources = case
    ref = EvolutionExperienceRef('T2', 'C2', 'R2')
    scope = replace(scope, experiences=(scope.experiences[0], ref))
    batch = build_experience_cards((sources[0], captured(ref, policy='Another policy')), scope=scope)
    assert [c['visible_policy'] for c in batch.payload['contexts']] == ['先报告价格，再请求确认。', 'Another policy']
