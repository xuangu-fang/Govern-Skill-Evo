"""Independent v29.1-based Preconditioner: full-text decisions, no transport.

Requires a registered SearchQA method via method.using(), just like Diagnosis.
Memory validation covers the supplied view, not historical archive authenticity.
No Memory writes, Editor calls, campaign wiring or model calls occur here.
"""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Callable

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts.diagnosis import fields
from src.skill_evolution.v27.contracts.editor import actual_diff
from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v27.json_response import parse_json_response
from src.skill_evolution.v28.benchmarks.searchqa import protocol
from src.skill_evolution.v28.benchmarks.searchqa.facts import run_references
from . import diagnosis, execution_input_view as view
from src.skill_evolution.v28_5.explicit_references import parse as parse_references
from src.skill_evolution.v28_5.execution_references import references

PROMPT_VERSION = 'v28_5_searchqa_preconditioner_v2'
INPUT_VIEW = view.INPUT_VIEW
CONTRACT_VERSION = 'v28_5_preconditioner_direct_evidence_v1'
PROMPT_PATH = protocol.ROOT / 'docs/methods/v28_5/prompts' / 'preconditioner.md'


def validate_memory_view(memory):
    """Check append-only round view structure and identities; never revise it."""
    fields(memory, ('rounds',), 'Memory')
    require(isinstance(memory['rounds'], list), 'Memory rounds must be an array')
    rounds, entries = set(), set()
    for record in memory['rounds']:
        fields(record, ('round_id', 'source_updates', 'entries'), 'Memory round')
        rid = text(record['round_id'], 'round_id')
        require(rid not in rounds, 'Duplicate Memory round_id')
        rounds.add(rid)
        require(isinstance(record['source_updates'], list), 'source_updates must be an array')
        updates = {}
        for update in record['source_updates']:
            fields(update, ('id', 'text', 'gate_decision'), 'Historical Update')
            uid = text(update['id'], 'Historical Update ID')
            require(uid not in updates, 'Duplicate historical Update ID within round')
            text(update['text'], 'Historical Update text')
            require(update['gate_decision'] in ('Retain', 'Reject', 'Defer', None),
                    'Unknown historical Gate decision')
            updates[uid] = update
        require(isinstance(record['entries'], list), 'Memory entries must be an array')
        tasks = set()
        for entry in record['entries']:
            fields(entry, ('id', 'knowledge'), 'Memory entry')
            mid = text(entry['id'], 'Memory ID')
            require(mid not in entries, 'Duplicate Memory ID')
            entries.add(mid)
            knowledge = entry['knowledge']
            fields(knowledge, ('task_id', 'update_id', 'text'), 'Knowledge')
            tid = text(knowledge['task_id'], 'Knowledge task_id')
            require(tid not in tasks, 'Duplicate task event within Memory round')
            tasks.add(tid)
            text(knowledge['text'], 'Knowledge text')
            uid = knowledge['update_id']
            if uid is not None:
                text(uid, 'Knowledge update_id')
                require(uid in updates, 'Knowledge refers to an unavailable historical Update')
                require(updates[uid]['gate_decision'] is not None,
                        'Knowledge cannot attribute a transition to a no-modification Update')
    return memory


def preconditioner_input(saved, memory):
    """Verify Diagnosis and archives, then project exactly four model fields."""
    with current().memory_operation():
        facts = diagnosis.diagnosis_input(saved)
        runs = diagnosis.referenced_runs(saved['diagnosis'], facts)
        require(saved['diagnosis']['decision'] == 'revise', 'Preconditioner needs revise')
        validate_memory_view(memory)
        require(all(r['round_id'] != saved.get('round_id') for r in memory['rounds']),
                'Current round cannot appear in historical Memory')
        return deepcopy({'parent': facts['parent'], 'plan': saved['diagnosis']['plan'],
                         'runs': runs, 'memory': memory})


def validate_input(payload, *, saved):
    """Require the exact projection of the frozen Diagnosis and current archives.

    saved supplies the full batch for source verification only;
    unrelated batch members are not sent to the model.
    """
    fields(payload, ('parent', 'plan', 'runs', 'memory'), 'Preconditioner input')
    expected = preconditioner_input(saved, payload['memory'])
    require(json.dumps(payload, sort_keys=True, allow_nan=False) ==
            json.dumps(expected, sort_keys=True, allow_nan=False),
            'Preconditioner input differs from frozen Diagnosis projection')
    return payload


def _compile(result, payload):
    """Validate all decisions before compiling; caller must validate input first."""
    fields(result, ('adjustments',), 'Preconditioner')
    require(isinstance(result['adjustments'], list), 'adjustments must be an array')
    originals = {u['id']: u for u in payload['plan']['updates']}
    executions = {ref for run in payload['runs'] for ref in run_references(run)}
    allowed = {
        'Memory': {e['id'] for r in payload['memory']['rounds'] for e in r['entries']},
        'Group': set(), 'Evidence': executions, 'Update': set(originals), 'Check': set(),
    }

    def prose(value, label):
        parse_references(value, allowed, location=label)
        # Also check inherited unprefixed execution references from Diagnosis.
        require(references(value) <= executions, f'{label}: unavailable execution reference')
        require(not re.search(r'\bG\d+\b', value), f'{label}: unavailable Group reference')

    indexed = {}
    for item in result['adjustments']:
        fields(item, ('target', 'action', 'text', 'reason'), 'Adjustment')
        uid = text(item['target'], 'target')
        require(uid in originals and uid not in indexed, 'Unknown or duplicate Original target')
        require(item['action'] in ('KEEP', 'REPLACE', 'WITHDRAW'), 'Unknown adjustment action')
        prose(item['reason'], f'{uid}.reason')
        if item['action'] == 'REPLACE':
            prose(item['text'], f'{uid}.text')
            require(item['text'] != originals[uid]['text'], 'REPLACE must change Original text')
        else:
            require(item['text'] is None, 'KEEP/WITHDRAW requires text=null')
        indexed[uid] = item
    require(indexed.keys() == originals.keys(), 'Every Original requires exactly one adjustment')
    survivors = []
    for uid, original in originals.items():
        item = indexed[uid]
        if item['action'] != 'WITHDRAW':
            updated = deepcopy(original)
            if item['action'] == 'REPLACE':
                updated['text'] = item['text']
            survivors.append(updated)
    return {'goal': payload['plan']['goal'], 'updates': survivors} if survivors else None


def compile_effective_plan(result, payload, *, saved):
    """Preserve Goal, Original order/IDs/basis; replace only selected texts."""
    validate_input(payload, saved=saved)
    return _compile(result, payload)


def validate_preconditioner(result, payload, *, saved):
    compile_effective_plan(result, payload, saved=saved)
    return result


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    require(prompt_version == PROMPT_VERSION, 'Unknown Preconditioner prompt version')
    prompt = PROMPT_PATH.read_text(encoding='utf-8')
    marker, end = '<actor_base_protocol>\n', '\n</actor_base_protocol>'
    require(prompt.count(marker) == prompt.count(end) == 1, 'Invalid Actor protocol quotation')
    require(prompt.split(marker)[1].split(end)[0] == protocol.actor_base_protocol(),
            'Preconditioner/Actor base protocol differs')
    require(protocol.execution_context(background) in prompt, 'Preconditioner/Actor runtime differs')
    return prompt


@dataclass(frozen=True)
class PreconditionerCall:
    """Versioned local preparation/completion; no transport or campaign binding."""
    name: str
    prompt_version: str
    contract_version: str
    input: dict
    messages: list
    complete: Callable

    def complete_text(self, content):
        return self.complete(parse_json_response(content))


def model_input(saved, memory):
    # Select only directly referenced runs before sharing any execution content.
    return view.model_input(preconditioner_input(saved, memory), module='preconditioner')


def validate_model_input(payload, *, saved, memory):
    return view.validate_model_input(payload, original=preconditioner_input(saved, memory),
                                     module='preconditioner')


def preconditioner_call(saved, memory):
    frozen = {**deepcopy(saved), 'memory': deepcopy(memory)}
    payload = model_input(frozen, frozen['memory'])
    messages = [
        {'role': 'system', 'content': render_prompt(frozen['background'])},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                             separators=(',', ':'), allow_nan=False)},
    ]

    def complete(parsed):
        with current().memory_operation():
            checked = preconditioner_input(frozen, frozen['memory'])
            effective = _compile(parsed, checked)
            originals = {u['id']: u['text'] for u in checked['plan']['updates']}
            # Audit-only standard diffs, not model-generated executable patches.
            diffs = {u['id']: actual_diff(originals[u['id']], u['text'])
                     for u in (effective['updates'] if effective else [])
                     if u['text'] != originals[u['id']]}
        return {**deepcopy(frozen), 'preconditioner': deepcopy(parsed),
                'effective_plan': effective, 'update_diffs': diffs}

    return PreconditionerCall('preconditioner', PROMPT_VERSION, CONTRACT_VERSION,
                             deepcopy(frozen), messages, complete)
