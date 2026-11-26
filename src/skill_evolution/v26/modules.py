"""Seven OfficeQA module calls: existing projections and V25-derived contracts.

Call preparation validates inputs before the request boundary. Only parsing and
known output validators are eligible for temporary output-validation feedback.
"""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import json

from .facts import require, text
from .benchmark import current
from .contracts import diagnosis, memory
from .contracts.editor import _utf8, actual_diff
from .unnumbered_patch import apply_patch
from .update_patch import normalize_update_patches
from . import knowledge_verifier as verifier, knowledge_repair as repair, knowledge_evidence, replay
from .benchmarks.officeqa import evidence, facts, prompting

REVIEW_POLICY = 'obvious_fact_verifier_targeted_repair_v1'


@dataclass
class Call:
    name: str
    input: dict
    messages: list
    complete: Callable


def grouping_call(records, round_id):
    text(round_id, 'round ID')
    saved = current().build_facts(records)
    def complete(parsed):
        evidence.validate_grouping(parsed, saved['facts'])
        return {**saved, 'round_id': round_id, 'grouping': parsed}
    return Call('grouping', {'bundle': saved, 'round_id': round_id},
                prompting.grouping_messages(saved), complete)


def diagnosis_call(saved):
    payload = evidence.diagnosis_input(saved)
    def complete(parsed):
        diagnosis.validate_diagnosis(parsed, payload)
        return {**saved, 'diagnosis': parsed}
    return Call('diagnosis', saved, prompting.diagnosis_messages(saved), complete)


def preconditioner_call(saved, active_memory):
    saved = {**deepcopy(saved), 'memory': deepcopy(active_memory)}
    payload = evidence.preconditioner_input(saved)
    def complete(parsed):
        normalized, effective = normalize_update_patches(parsed, payload)
        return {**saved, 'adjustments': parsed, 'preconditioner': normalized, 'effective_plan': effective}
    return Call('preconditioner', saved, prompting.preconditioner_messages(saved), complete)


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
    messages = prompting.replay_messages(bundle)
    def complete(parsed):
        replay.validate_result(parsed, bundle['payload'])
        return {'replay': parsed}
    return Call('replay', bundle, messages, complete)


def review_input(bundle, candidate, memory_root):
    """Retrieve only historical archives explicitly cited by changed/new targets."""
    replay.validate_result(candidate, bundle['payload'])
    targets, _ = knowledge_evidence.select_targets(candidate, bundle['payload']['memory'])
    contexts = {ref.rsplit('/', 1)[0] for target in targets for ref in target['knowledge']['evidence'] if '/' in ref}
    historical = {}
    for cid in sorted(contexts):
        require(cid and '/' not in cid and '..' not in cid, 'Unsafe historical context')
        archive = json.loads((Path(memory_root) / 'archive' / f'{cid}.json').read_text())
        require(archive['context_id'] == cid and archive.get('memory_contract') == memory.MULTI_KNOWLEDGE_CONTRACT,
                'Historical archive identity/contract mismatch')
        memory.validate_entries(archive['result'], archive['context']['payload'],
                                memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        historical[cid] = archive['context']
    return evidence.build_input(bundle, candidate, historical)


def verifier_call(value):
    evidence.compact(value)
    require(bool(value['targets']), 'Verifier requires targets')
    background = value['context']['execution_context']['background']
    messages = prompting._messages('verifier', value, background)
    return Call('verifier', value, messages, lambda parsed: verifier.validate_result(parsed, value))


def repair_call(value, candidate, payload):
    repair.validate_repair_input(value, candidate, payload)
    require(bool(value['targets']), 'Repair requires authorized targets')
    background = value['context']['execution_context']['background']
    messages = prompting._messages('repair', value, background)
    def complete(parsed):
        repair.merge(parsed, value, candidate, payload)
        return parsed
    return Call('repair', {'view': value, 'candidate': candidate, 'payload': payload}, messages, complete)


def output_files(call, result, parsed):
    if call.name != 'editor':
        return {}
    files = {}
    if isinstance(parsed['patch'], str):
        files['patch.diff'] = parsed['patch']
    if result['candidate_text'] is not None:
        files.update({'candidate.md': result['candidate_text'], 'actual.diff': result['actual_diff']})
    return files
