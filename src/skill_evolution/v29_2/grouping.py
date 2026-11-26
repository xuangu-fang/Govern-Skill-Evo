"""v29.2 Grouping with scoped execution references and a lossless request view."""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v27.contracts.diagnosis import fields, links
from src.skill_evolution.v27.json_response import parse_json_response
from src.skill_evolution.v29.benchmarks.docvqa import evidence, protocol
from . import execution_input_view as view
from .execution_references import references

PROMPT_VERSION = 'v29_2_docvqa_grouping_v2'
CONTRACT_VERSION = 'v29_2_docvqa_grouping_v2'
INPUT_VIEW = view.INPUT_VIEW
PROMPT_PATH = Path(__file__).with_name('prompts') / 'grouping.md'


def validate_grouping(result, facts):
    """Preserve Grouping permissions; distinguish local lists from history."""
    fields(result, ('groups',), 'Grouping')
    require(isinstance(result['groups'], list) and result['groups'], 'Missing groups')
    runs = {r['ref']: evidence.validate_run(r) for r in facts['runs']}
    require(runs and len(runs) == len(facts['runs']), 'Duplicate/missing runs')
    allowed = set().union(*(evidence.run_references(r) for r in runs.values()))
    assigned, ids = [], set()
    for group in result['groups']:
        fields(group, ('group_id', 'members', 'decision_problem', 'shared_basis', 'important_differences'), 'Group')
        gid = text(group['group_id'], 'Group ID')
        require(gid not in ids, 'Duplicate Group ID'); ids.add(gid)
        links(group['members'], set(runs), 'Members'); assigned += group['members']
        require(isinstance(group['important_differences'], list), 'Invalid differences')
        for item in [group['decision_problem'], group['shared_basis'], *group['important_differences']]:
            require(references(text(item, 'group text')) <= allowed, 'Unknown execution reference')
        for member in group['members']:
            run = runs[member]
            decisions = evidence.run_references(run) - {run['ref'], run['initial']['ref'], run['outcome']['ref']}
            require(bool((decisions or {run['initial']['ref']}) & references(group['shared_basis'])),
                    'Group lacks decision evidence')
    require(len(assigned) == len(set(assigned)) and set(assigned) == set(runs),
            'Grouping must cover each run exactly once')
    return result


def diagnosis_input(saved):
    evidence.validate_saved(saved)
    fields(saved['facts'], ('parent', 'runs'), 'Facts')
    validate_grouping(saved['grouping'], saved['facts'])
    return deepcopy({**saved['facts'], 'grouping': saved['grouping']})


def grouping_input(saved):
    with current().memory_operation():
        evidence.validate_saved(saved)
    return deepcopy(saved['facts'])


def model_input(saved):
    return view.model_input(grouping_input(saved), module='grouping')


def validate_model_input(payload, *, saved):
    return view.validate_model_input(payload, original=grouping_input(saved), module='grouping')


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    require(prompt_version == PROMPT_VERSION, 'Unknown Grouping prompt version')
    prompt = PROMPT_PATH.read_text(encoding='utf-8')
    marker, end = '<actor_base_protocol>\n', '\n</actor_base_protocol>'
    require(prompt.count(marker) == prompt.count(end) == 1, 'Invalid Actor protocol quotation')
    require(prompt.split(marker)[1].split(end)[0] == protocol.actor_base_protocol(),
            'Grouping/Actor base protocol differs')
    require(protocol.execution_context(background) in prompt, 'Grouping/Actor runtime differs')
    return prompt


@dataclass(frozen=True)
class GroupingCall:
    name: str
    prompt_version: str
    contract_version: str
    input: dict
    messages: list
    complete: Callable

    def complete_text(self, content):
        return self.complete(parse_json_response(content))


def call_from_saved(payload):
    protocol.fields(payload, ('bundle', 'round_id'), 'Grouping call')
    frozen = deepcopy(payload['bundle'])
    rid = text(payload['round_id'], 'round ID')
    projected = model_input(frozen)
    messages = [
        {'role': 'system', 'content': render_prompt(frozen['background'])},
        {'role': 'user', 'content': json.dumps(projected, ensure_ascii=False,
                                             separators=(',', ':'), allow_nan=False)},
    ]

    def complete(parsed):
        with current().memory_operation():
            facts = grouping_input(frozen)
            validate_grouping(parsed, facts)
        return {**deepcopy(frozen), 'round_id': rid, 'grouping': deepcopy(parsed)}

    return GroupingCall('grouping', PROMPT_VERSION, CONTRACT_VERSION,
                        deepcopy(payload), messages, complete)


def grouping_call(records, round_id):
    text(round_id, 'round ID')
    with current().memory_operation():
        saved = current().build_facts(records, role='parent')
    return call_from_saved({'bundle': saved, 'round_id': round_id})
