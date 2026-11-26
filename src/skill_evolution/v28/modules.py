"""Five SearchQA module calls using the unchanged v27 contracts.

Call preparation validates inputs before the request boundary. Only parsing and
known output validators are eligible for temporary output-validation feedback.
"""
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable

from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts import diagnosis, memory
from src.skill_evolution.v27.contracts.editor import _utf8, actual_diff
from src.skill_evolution.v27.unnumbered_patch import apply_patch
from src.skill_evolution.v27.update_patch import normalize_update_patches
from . import replay, validation
from .benchmarks.searchqa import evidence, prompting

REVIEW_POLICY = 'disabled_v1'


@dataclass
class Call:
    name: str
    input: dict
    messages: list
    complete: Callable


def grouping_call(records, round_id):
    text(round_id, 'round ID')
    with validation.operation(current().actor_adapter):
        saved = current().build_facts(records, role='parent')
        messages = prompting.grouping_messages(saved)
    def complete(parsed):
        evidence.validate_grouping(parsed, saved['facts'])
        return {**saved, 'round_id': round_id, 'grouping': parsed}
    return Call('grouping', {'bundle': saved, 'round_id': round_id}, messages, complete)


def diagnosis_call(saved):
    with validation.operation(current().actor_adapter):
        payload = evidence.diagnosis_input(saved)
        messages = prompting.diagnosis_messages(saved)
    def complete(parsed):
        evidence.validate_diagnosis(parsed, payload)
        return {**saved, 'diagnosis': parsed}
    return Call('diagnosis', saved, messages, complete)


def preconditioner_call(saved, active_memory):
    saved = {**deepcopy(saved), 'memory': deepcopy(active_memory)}
    with validation.operation(current().actor_adapter):
        payload = evidence.preconditioner_input(saved)
        messages = prompting.preconditioner_messages(saved)
    def complete(parsed):
        normalized, effective = normalize_update_patches(parsed, payload)
        return {**saved, 'adjustments': parsed, 'preconditioner': normalized, 'effective_plan': effective}
    return Call('preconditioner', saved, messages, complete)


def validate_editor(parsed, parent):
    # Same patch/null/empty semantics as the frozen V25 Editor.
    diagnosis.fields(parsed, ('patch', 'reason'), 'Editor')
    text(parsed['reason'], 'reason'); _utf8(parsed['reason'])
    patch = parsed['patch']
    if patch is None:
        return 'needs_revision', None
    require(isinstance(patch, str), 'patch must be a string or null')
    if patch == '':
        return 'no_change', None
    require(bool(patch.strip()), 'Whitespace-only patch is invalid')
    return 'candidate', apply_patch(parent, patch)


def editor_call(saved):
    with validation.operation(current().actor_adapter):
        normalized, effective = normalize_update_patches(saved['adjustments'], evidence.preconditioner_input(saved))
        require(normalized == saved['preconditioner'] and effective == saved['effective_plan'], 'Effective Plan changed')
        messages = prompting.editor_messages(saved, saved['adjustments'])
        require(messages is not None, 'Editor requires a nonempty Effective Plan')
    def complete(parsed):
        status, candidate = validate_editor(parsed, saved['facts']['parent'])
        diff = None if candidate is None else actual_diff(saved['facts']['parent'], candidate)
        return {**saved, 'editor': parsed, 'editor_status': status, 'candidate_text': candidate, 'actual_diff': diff}
    return Call('editor', saved, messages, complete)


def replay_call(bundle):
    with validation.operation(current().actor_adapter):
        messages = prompting.replay_messages(bundle)
    def complete(parsed):
        # Use a fresh scope after the model request; never cache across its wait.
        with validation.operation(current().actor_adapter):
            replay.validate_result(parsed, bundle['payload'])
        return {'replay': parsed}
    return Call('replay', bundle, messages, complete)


def output_files(call, result, parsed):
    if call.name != 'editor':
        return {}
    files = {}
    if isinstance(parsed['patch'], str):
        files['patch.diff'] = parsed['patch']
    if result['candidate_text'] is not None:
        files.update({'candidate.md': result['candidate_text'], 'actual.diff': result['actual_diff']})
    return files
