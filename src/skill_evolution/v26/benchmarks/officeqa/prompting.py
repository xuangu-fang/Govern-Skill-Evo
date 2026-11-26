"""OfficeQA method Prompts and pure message builders; no generation or retry loop.

Inputs go through the existing evidence projections before serialization. The caller
must bind the adapter explicitly and persist prompt_identity() with future run state.
"""
import hashlib
import json
from pathlib import Path
import re

from skilladam.benchmarks.officeqa.rollout import VENDOR_PROMPT

from ...benchmark import current
from ...facts import require
from . import evidence, protocol as p, input_view as iv


PROMPT_VERSIONS = {
    'grouping': 'v26_officeqa_grouping_v1',
    'diagnosis': 'v26_officeqa_diagnosis_evidence_scoped_updates_v1',
    'preconditioner': 'v26_officeqa_preconditioner_evidence_decision_boundaries_v1',
    'editor': 'v26_officeqa_editor_scope_fidelity_v1',
    'replay': 'v26_officeqa_replay_decision_fidelity_v1',
    'verifier': 'v26_officeqa_obvious_fact_verifier_v1',
    'repair': 'v26_officeqa_targeted_repair_v1',
}
RESOURCE_NAMES = frozenset(f'{name}.md' for name in PROMPT_VERSIONS) | {
    'knowledge_only_view.md', 'method_validation_feedback.md', 'execution_context.md',
    'lossless_input_view.md', 'partial_history_view.md'}


def resource_path(key):
    require(isinstance(key, str) and key in RESOURCE_NAMES, 'Unknown OfficeQA Prompt resource')
    path = Path(__file__).with_name('prompts') / key
    require(path.is_file(), 'Missing OfficeQA Prompt resource')
    return path


def _read(key):
    return current().resource(key).read_text(encoding='utf-8')


def execution_context(background):
    # Reconstruct the allowlisted background; reject accidental private/audit fields.
    require(p.equal(background, p.background(background)), 'Noncanonical OfficeQA Prompt background')
    template = _read('execution_context.md')
    require(template.count('{{recorded_context}}') == template.count('{{actor_base_prompt}}') == 1,
            'Invalid execution context template')
    values = {'recorded_context': p.execution_context(background),
              'actor_base_prompt': VENDOR_PROMPT.format(skill_section='').rstrip()}
    return re.sub(r'\{\{(recorded_context|actor_base_prompt)\}\}', lambda m: values[m[1]], template)


def render(module, background, *, prompt_version=None):
    require(module in PROMPT_VERSIONS, 'Unknown OfficeQA method module')
    require(prompt_version in (None, PROMPT_VERSIONS[module]), 'Unsupported OfficeQA Prompt version')
    template = _read(f'{module}.md').rstrip()
    context = execution_context(background)
    if module in ('grouping', 'diagnosis', 'preconditioner', 'editor'):
        require(template.count('{{execution_context}}') == 1, 'Missing/repeated execution context')
        template = template.replace('{{execution_context}}', context)
    else:
        template += '\n\n' + context
    if module in ('preconditioner', 'replay'):
        template += '\n\n' + _read('knowledge_only_view.md').rstrip()
    return template


def prompt_identity(module, *, input_view=iv.FORMAT):
    """Identity includes shared instructions and the imported native Actor protocol."""
    require(module in PROMPT_VERSIONS, 'Unknown OfficeQA method module')
    require(input_view in (iv.FORMAT, iv.LEGACY), 'Unsupported OfficeQA model input view')
    names = [f'{module}.md', 'execution_context.md', 'method_validation_feedback.md']
    if module in ('preconditioner', 'replay'):
        names.append('knowledge_only_view.md')
    if input_view == iv.FORMAT:
        names.append('lossless_input_view.md')
        if module in ('verifier', 'repair'):
            names.append('partial_history_view.md')
    return {'prompt_version': PROMPT_VERSIONS[module], 'facts_version': p.FACTS_VERSION,
            'input_view': iv.FORMAT if input_view == iv.FORMAT else (p.INPUT_VIEW if module == 'replay' else None),
            'resources_sha256': {name: hashlib.sha256(current().resource(name).read_bytes()).hexdigest()
                                 for name in names},
            'actor_base_prompt_sha256': hashlib.sha256(VENDOR_PROMPT.format(skill_section='').encode()).hexdigest()}


def _messages(module, payload, background, *, input_view=iv.FORMAT):
    messages = [{'role': 'system', 'content': render(module, background)},
            {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                                 separators=(',', ':'), allow_nan=False)}]
    return iv.model_messages(messages, _read('lossless_input_view.md'), input_view=input_view,
                             history_instruction=_read('partial_history_view.md'))


def grouping_messages(saved):
    p.fields(saved['facts'], ('parent', 'runs'), 'Grouping facts')
    runs = saved['facts']['runs']
    require(bool(runs), 'Grouping requires executions')
    for i, run in enumerate(runs, 1):
        evidence.validate_run(run)
        require(run['ref'] == f'P{i}', 'Invalid Parent reference ordering')
    require(len({r['task_id'] for r in runs}) == len(runs), 'Duplicate Grouping task')
    return _messages('grouping', saved['facts'], saved['background'])


def diagnosis_messages(saved):
    return _messages('diagnosis', evidence.diagnosis_input(saved), saved['background'])


def preconditioner_messages(saved):
    return _messages('preconditioner', evidence.preconditioner_model_input(saved), saved['background'])


def editor_messages(saved, adjustments):
    payload = evidence.editor_model_input(saved, adjustments)
    return None if payload is None else _messages('editor', payload, saved['background'])


def replay_messages(bundle):
    return _messages('replay', evidence.model_input(bundle), bundle['background'])


def verifier_messages(bundle, candidate, historical=None):
    payload, _ = evidence.build_input(bundle, candidate, historical)
    return None if not payload['targets'] else _messages('verifier', payload, bundle['background'])


def repair_messages(verifier_input, verdicts, candidate):
    """Use the original frozen Verifier input, preserving its exact source scope."""
    payload = evidence.build_repair_input(verifier_input, verdicts, candidate)
    return None if not payload['targets'] else _messages(
        'repair', payload, payload['context']['execution_context']['background'])


def validation_feedback(*, location, error):
    """Render diagnostics only; optimizer retry policy remains a separate concern."""
    require(isinstance(location, str) and bool(location.strip()), 'Missing validation location')
    require(isinstance(error, str) and bool(error.strip()), 'Missing validation error')
    # One substitution pass: diagnostics may themselves contain literal placeholders.
    return re.sub(r'\{\{(location|error)\}\}', lambda m: {'location': location, 'error': error}[m[1]],
                  _read('method_validation_feedback.md'))
