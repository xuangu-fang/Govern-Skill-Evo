"""v28.5 batch Diagnosis with direct execution evidence and no Grouping stage."""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Callable

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts.diagnosis import fields, links
from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v27.json_response import parse_json_response
from src.skill_evolution.v28.benchmarks.searchqa import protocol
from src.skill_evolution.v28.benchmarks.searchqa.facts import run_references
from . import execution_input_view as view, facts
from src.skill_evolution.v28_5.execution_references import references

PROMPT_VERSION = 'v28_5_searchqa_diagnosis_v2'
INPUT_VIEW = view.INPUT_VIEW
CONTRACT_VERSION = 'v28_5_diagnosis_direct_evidence_v1'
PROMPT_PATH = protocol.ROOT / 'docs/methods/v28_5/prompts' / 'diagnosis.md'


def validate_input(payload):
    """Validate the complete Parent batch against registered execution archives."""
    fields(payload, ('parent', 'runs'), 'Diagnosis input')
    require(payload['parent'] is None or isinstance(payload['parent'], str), 'Invalid Parent')
    require(isinstance(payload['runs'], list) and payload['runs'], 'Missing Parent runs')
    with current().memory_operation():
        facts.validate_parent_bundle({
            'facts': {key: payload[key] for key in ('parent', 'runs')},
            'background': protocol.actor_config(30),
        })
    return payload


def diagnosis_input(saved):
    """Project Parent and all current runs after full source verification."""
    with current().memory_operation():
        facts.validate_parent_bundle(saved)
        return deepcopy(saved['facts'])


def model_input(saved):
    return view.model_input(diagnosis_input(saved), module='diagnosis')


def validate_model_input(payload, *, saved):
    return view.validate_model_input(payload, original=diagnosis_input(saved), module='diagnosis')


def _validate_output(result, payload):
    """Check structure and reference permissions, not the truth of a diagnosis."""
    fields(result, ('decision', 'reason', 'plan'), 'Diagnosis')
    require(result['decision'] in ('revise', 'no_change'), 'Unknown Diagnosis decision')
    executions = {ref: run['ref'] for run in payload['runs'] for ref in run_references(run)}
    allowed = set(executions)

    def prose(value, label):
        text(value, label)
        require(references(value) <= set(executions),
                f'{label}: unavailable execution reference')
        require(not re.search(r'\bG\d+\b|(?<!\w)Group[ \t]*:(?=\S)', value),
                f'{label}: unavailable Group reference')
        require(not re.search(r'\bMemory:[A-Za-z0-9_-]+', value),
                f'{label}: Memory is not supplied to Diagnosis')

    prose(result['reason'], 'reason')
    if result['decision'] == 'no_change':
        require(result['plan'] is None, 'no_change requires plan=null')
        return result
    plan = result['plan']
    fields(plan, ('goal', 'updates'), 'Plan')
    prose(plan['goal'], 'goal')
    require(isinstance(plan['updates'], list) and plan['updates'], 'revise requires Updates')
    seen = set()
    for update in plan['updates']:
        fields(update, ('id', 'text', 'basis'), 'Update')
        uid = text(update['id'], 'Update ID')
        require(uid not in seen and uid not in allowed, 'Duplicate or source-colliding Update ID')
        seen.add(uid)
        prose(update['text'], f'{uid}.text')
        links(update['basis'], allowed, f'{uid}.basis')
        members = {executions[ref] for ref in update['basis'] if ref in executions}
        require(bool(members), f'{uid}: direct execution evidence is required')
    return result


def validate_diagnosis(result, payload):
    with current().memory_operation():
        validate_input(payload)
        return _validate_output(result, payload)


def referenced_runs(result, payload):
    """Return whole current runs directly referenced by the Plan, in batch order.

    This is the Diagnosis handoff only: no Preconditioner call or Memory view.
    Direct references anywhere in the Plan select runs; reason is not a source.
    """
    validate_diagnosis(result, payload)
    if result['plan'] is None:
        return []
    refs = references(json.dumps(result['plan'], ensure_ascii=False))
    selected = {ref.split(':', 1)[0] for ref in refs}
    return deepcopy([run for run in payload['runs'] if run['ref'] in selected])


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    require(prompt_version == PROMPT_VERSION, 'Unknown Diagnosis prompt version')
    prompt = PROMPT_PATH.read_text(encoding='utf-8')
    marker, end = '<actor_base_protocol>\n', '\n</actor_base_protocol>'
    require(prompt.count(marker) == prompt.count(end) == 1, 'Invalid Actor protocol quotation')
    require(prompt.split(marker)[1].split(end)[0] == protocol.actor_base_protocol(),
            'Diagnosis/Actor base protocol differs')
    require(protocol.execution_context(background) in prompt, 'Diagnosis/Actor runtime differs')
    return prompt


@dataclass(frozen=True)
class DiagnosisCall:
    """Prepared, versioned local call; transport/campaign wiring is intentionally absent."""
    name: str
    prompt_version: str
    contract_version: str
    input: dict
    messages: list
    complete: Callable

    def complete_text(self, content):
        return self.complete(parse_json_response(content))


def diagnosis_call(saved):
    frozen = deepcopy(saved)
    text(frozen.get('round_id'), 'round ID')
    payload = model_input(frozen)
    messages = [
        {'role': 'system', 'content': render_prompt(frozen['background'])},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                             separators=(',', ':'), allow_nan=False)},
    ]

    def complete(parsed):
        # Recheck completed sources at completion; exposed input objects are copies.
        with current().memory_operation():
            checked = diagnosis_input(frozen)
            _validate_output(parsed, checked)
        return {**deepcopy(frozen), 'diagnosis': deepcopy(parsed)}

    return DiagnosisCall('diagnosis', PROMPT_VERSION, CONTRACT_VERSION,
                         deepcopy(frozen), messages, complete)
