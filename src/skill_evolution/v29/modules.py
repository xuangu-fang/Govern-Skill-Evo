"""Prepare the five reviewed calls and validate supplied outputs; no generation."""
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts import diagnosis
from src.skill_evolution.v27.contracts.editor import _utf8, actual_diff
from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v27.json_response import parse_json_response
from src.skill_evolution.v27.unnumbered_patch import apply_patch
from src.skill_evolution.v27.update_patch import normalize_update_patches
from .benchmarks.docvqa import evidence, prompting
from . import replay

REVIEW_POLICY = 'disabled_v1'


@dataclass
class Call:
    name: str
    input: dict
    messages: list
    complete: Callable

    def complete_text(self, content):
        return self.complete(parse_json_response(content))


def grouping_call(records, round_id):
    text(round_id, 'round ID')
    with current().memory_operation():
        saved = current().build_facts(records, role='parent')
        messages = prompting.grouping_messages(saved)

    def complete(parsed):
        with current().memory_operation():
            evidence.validate_saved(saved)
            evidence.validate_grouping(parsed, saved['facts'])
        return {**deepcopy(saved), 'round_id': round_id, 'grouping': deepcopy(parsed)}

    return Call('grouping', {'bundle': deepcopy(saved), 'round_id': round_id},
                messages, complete)


def diagnosis_call(saved):
    saved = deepcopy(saved)
    with current().memory_operation():
        messages = prompting.diagnosis_messages(saved)

    def complete(parsed):
        with current().memory_operation():
            evidence.validate_diagnosis(parsed, evidence.diagnosis_input(saved))
        return {**deepcopy(saved), 'diagnosis': deepcopy(parsed)}

    return Call('diagnosis', deepcopy(saved), messages, complete)


def preconditioner_call(saved, active_memory):
    saved = {**deepcopy(saved), 'memory': deepcopy(active_memory)}
    with current().memory_operation():
        messages = prompting.preconditioner_messages(saved)

    def complete(parsed):
        with current().memory_operation():
            normalized, effective = normalize_update_patches(parsed, evidence.preconditioner_input(saved))
        return {**deepcopy(saved), 'adjustments': deepcopy(parsed),
                'preconditioner': normalized, 'effective_plan': effective}

    return Call('preconditioner', deepcopy(saved), messages, complete)


def validate_editor(parsed, parent):
    diagnosis.fields(parsed, ('patch', 'reason'), 'Editor')
    text(parsed['reason'], 'reason')
    _utf8(parsed['reason'])
    patch = parsed['patch']
    if patch is None:
        return 'needs_revision', None
    require(isinstance(patch, str), 'patch must be a string or null')
    if patch == '':
        return 'no_change', None
    require(bool(patch.strip()), 'Whitespace-only patch is invalid')
    return 'candidate', apply_patch(parent, patch)


def _check_effective(saved):
    normalized, effective = normalize_update_patches(saved['adjustments'], evidence.preconditioner_input(saved))
    require(normalized == saved['preconditioner'] and effective == saved['effective_plan'], 'Effective Plan changed')


def editor_call(saved):
    saved = deepcopy(saved)
    with current().memory_operation():
        _check_effective(saved)
        messages = prompting.editor_messages(saved, saved['adjustments'])
        require(messages is not None, 'Editor requires a nonempty Effective Plan')

    def complete(parsed):
        with current().memory_operation():
            _check_effective(saved)
            status, candidate = validate_editor(parsed, saved['facts']['parent'])
            diff = None if candidate is None else actual_diff(saved['facts']['parent'], candidate)
        return {**deepcopy(saved), 'editor': deepcopy(parsed), 'editor_status': status,
                'candidate_text': candidate, 'actual_diff': diff}

    return Call('editor', deepcopy(saved), messages, complete)


def replay_call(bundle):
    bundle = deepcopy(bundle)
    # Own only this local construction step, never the model request lifetime.
    with current().memory_operation():
        messages = prompting.replay_messages(bundle)

    def complete(parsed):
        with current().memory_operation():
            evidence.validate_bundle(bundle)
            replay.validate_result(parsed, bundle['payload'])
        return {'replay': deepcopy(parsed)}

    return Call('replay', deepcopy(bundle), messages, complete)


def output_files(call, result, parsed):
    if call.name != 'editor':
        return {}
    files = {}
    if isinstance(parsed['patch'], str):
        files['patch.diff'] = parsed['patch']
    if result['candidate_text'] is not None:
        files.update({'candidate.md': result['candidate_text'], 'actual.diff': result['actual_diff']})
    return files
