"""v17 Grouping contracts only: no card extraction, model call, or Diagnosis.

The trusted runtime supplies the current-round Evolution manifest. Validation
checks structure and provenance bindings, not the truth/safety of arbitrary prose.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any


class GroupingContractError(ValueError):
    """A Grouping input, partition, or scope violates the v17 contract."""


@dataclass(frozen=True)
class EvolutionExperienceRef:
    """Runtime-owned binding; identifiers must be opaque learner-local aliases."""

    task_ref: str
    context_ref: str
    trajectory_ref: str


@dataclass(frozen=True)
class GroupingScope:
    """Never populated from model output; contains only this round's Evolution set."""

    round_id: str
    parent_skill_digest: str
    experiences: tuple[EvolutionExperienceRef, ...]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GroupingContractError(message)


def _text(value: Any, path: str) -> None:
    _require(isinstance(value, str) and bool(value.strip()), f'{path}: nonempty string required')


def _object(value: Any, fields: set[str], path: str) -> None:
    _require(isinstance(value, dict) and set(value) == fields,
             f'{path}: exact fields required: {sorted(fields)}')


def _list(value: Any, path: str, *, nonempty: bool = True) -> None:
    _require(isinstance(value, list) and (bool(value) or not nonempty),
             f'{path}: {"nonempty " if nonempty else ""}list required')


def _scope(scope: GroupingScope) -> dict[str, EvolutionExperienceRef]:
    _require(isinstance(scope, GroupingScope), 'trusted GroupingScope required')
    _text(scope.round_id, 'scope.round_id')
    _text(scope.parent_skill_digest, 'scope.parent_skill_digest')
    _require(isinstance(scope.experiences, tuple) and bool(scope.experiences),
             'scope.experiences: nonempty tuple required')
    tasks, trajectories = {}, set()
    for ref in scope.experiences:
        _require(isinstance(ref, EvolutionExperienceRef), 'invalid experience reference')
        for field in ('task_ref', 'context_ref', 'trajectory_ref'):
            _text(getattr(ref, field), f'scope.{field}')
        _require(ref.task_ref not in tasks, 'duplicate scope task_ref')
        _require(ref.trajectory_ref not in trajectories, 'duplicate scope trajectory_ref')
        tasks[ref.task_ref] = ref
        trajectories.add(ref.trajectory_ref)
    return tasks


def validate_grouping_input(payload: dict, *, scope: GroupingScope) -> None:
    """Validate one card/trajectory per task against a trusted Evolution manifest.

    Contexts contain deployed public policy/tools. Cards carry ordered observed
    events; goals, constraints and authorization remain in original message text.
    Tool arguments and results are opaque observed data, not metadata containers
    to recursively filter (a public tool may legitimately have a 'success' key).
    """
    tasks = _scope(scope)
    _object(payload, {'contexts', 'cards'}, 'input')
    _list(payload['contexts'], 'contexts')
    contexts = {}
    for context in payload['contexts']:
        _object(context, {'context_ref', 'visible_policy', 'public_tools'}, 'context')
        _text(context['context_ref'], 'context_ref')
        _text(context['visible_policy'], 'visible_policy')
        key = context['context_ref']
        _require(key not in contexts, 'duplicate context_ref')
        _list(context['public_tools'], 'public_tools', nonempty=False)
        names = set()
        for tool in context['public_tools']:
            _object(tool, {'type', 'function'}, 'public_tool')
            _require(tool['type'] == 'function', 'public_tool.type must be function')
            function = tool['function']
            _require(isinstance(function, dict), 'function must be an object')
            _require({'name', 'description', 'parameters'} <= set(function)
                     <= {'name', 'description', 'parameters', 'strict'},
                     'invalid public function fields')
            _text(function['name'], 'function.name')
            _require(isinstance(function['description'], str), 'description must be text')
            _require(isinstance(function['parameters'], dict), 'parameters must be an object')
            if 'strict' in function:
                _require(type(function['strict']) is bool, 'strict must be boolean')
            _require(function['name'] not in names, 'duplicate tool name')
            names.add(function['name'])
        contexts[key] = names
    _require(set(contexts) == {ref.context_ref for ref in tasks.values()},
             'contexts must exactly cover Evolution contexts')
    _list(payload['cards'], 'cards')
    seen = set()
    for card in payload['cards']:
        _object(card, {'task_ref', 'context_ref', 'trajectory_ref', 'events'}, 'card')
        for field in ('task_ref', 'context_ref', 'trajectory_ref'):
            _text(card[field], f'card.{field}')
        task = card['task_ref']
        _require(task in tasks and task not in seen, 'unknown or duplicate card task_ref')
        ref = tasks[task]
        _require((card['context_ref'], card['trajectory_ref']) ==
                 (ref.context_ref, ref.trajectory_ref), 'experience provenance mismatch')
        seen.add(task)
        _list(card['events'], 'events')
        previous = 0
        for event in card['events']:
            _require(isinstance(event, dict), 'event must be an object')
            kind = event.get('event_type')
            base = {'step', 'event_type', 'actor'}
            if kind == 'message':
                _object(event, base | {'content'}, 'message')
                _require(event['actor'] in ('user', 'assistant'), 'invalid message actor')
            elif kind in ('tool_call', 'tool_result'):
                field = 'arguments' if kind == 'tool_call' else 'content'
                _object(event, base | {'tool_name', field}, kind)
                _text(event['tool_name'], 'tool_name')
                _require(event['tool_name'] in contexts[ref.context_ref], 'unknown public tool')
                _require(event['actor'] == ('assistant' if kind == 'tool_call' else 'tool'),
                         'invalid tool event actor')
                if kind == 'tool_call':
                    _require(isinstance(event['arguments'], dict), 'arguments must be object')
            else:
                raise GroupingContractError('only observed messages/tool calls/results allowed')
            _require(type(event['step']) is int and event['step'] > previous,
                     'event steps must be positive and strictly increasing')
            previous = event['step']
    _require(seen == set(tasks), 'missing Evolution cards')
    try:
        json.dumps(payload, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise GroupingContractError('input must contain finite JSON data') from exc


def validate_grouping_output(output: dict, *, task_refs: tuple[str, ...]) -> None:
    """Validate a complete exclusive partition; explanations are hypotheses."""
    _require(isinstance(task_refs, tuple) and bool(task_refs), 'task_refs must be nonempty tuple')
    for task in task_refs:
        _text(task, 'task_ref')
    _require(len(set(task_refs)) == len(task_refs), 'duplicate expected task_ref')
    _object(output, {'groups'}, 'output')
    _list(output['groups'], 'groups')
    seen, group_ids = set(), set()
    for group in output['groups']:
        _object(group, {'group_id', 'decision_problem', 'members', 'shared_basis',
                        'important_differences'}, 'group')
        for field in ('group_id', 'decision_problem', 'shared_basis'):
            _text(group[field], field)
        _require(group['group_id'] not in group_ids, 'duplicate group_id')
        group_ids.add(group['group_id'])
        _list(group['members'], 'members')
        for task in group['members']:
            _text(task, 'member')
            _require(task in task_refs, 'unknown group member')
            _require(task not in seen, 'duplicate group member')
            seen.add(task)
        _list(group['important_differences'], 'important_differences', nonempty=False)
        for difference in group['important_differences']:
            _text(difference, 'important_difference')
    _require(seen == set(task_refs), 'missing group members')


def bind_grouping_result(payload: dict, output: dict, *, scope: GroupingScope) -> dict:
    """Attach runtime provenance after validation; never ask the LLM to supply it."""
    validate_grouping_input(payload, scope=scope)
    validate_grouping_output(output, task_refs=tuple(ref.task_ref for ref in scope.experiences))
    return copy.deepcopy({
        'schema_version': 'experience_grouping_v17.1',
        'round_id': scope.round_id,
        'parent_skill_digest': scope.parent_skill_digest,
        'origin': 'LEARNER_INFERRED_GROUPING',
        'experience_refs': [vars(ref) for ref in scope.experiences],
        'groups': output['groups'],
    })
