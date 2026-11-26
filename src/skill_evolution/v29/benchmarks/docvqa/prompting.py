"""Reviewed DocVQA system prompts and exact module-specific user projections."""
import json
from pathlib import Path
from src.skill_evolution.v27.benchmark import current
from . import evidence, protocol as p, replay_input_view

PROMPT_VERSIONS = {name: f'v29_docvqa_{name}_v1' for name in
                   ('grouping', 'diagnosis', 'preconditioner', 'editor', 'replay')}
PROMPT_VERSIONS['replay'] = 'v29_docvqa_replay_v2'
RESOURCE_NAMES = frozenset(f'{name}.md' for name in PROMPT_VERSIONS)


def prompt_versions():
    """Version IDs belong to the context-local adapter, never process-global state."""
    return dict(getattr(current(), 'prompt_versions', PROMPT_VERSIONS))


def resource_path(key):
    p.require(key in RESOURCE_NAMES, 'Unknown DocVQA module resource')
    return Path(__file__).with_name('prompts') / key


def render(module, background, *, prompt_version=None):
    p.require(module in PROMPT_VERSIONS, 'Unknown or disabled method module')
    p.require(prompt_version in (None, prompt_versions()[module]), 'Unknown Prompt version')
    text = current().resource(f'{module}.md').read_text(encoding='utf-8')
    base = text.split('<actor_base_protocol>\n')[1].split('\n</actor_base_protocol>')[0]
    p.require(base == p.actor_base_protocol(), 'Method/Actor base protocol differs')
    p.require(p.execution_context(background) in text, 'Method/Actor runtime differs')
    return text


def _messages(module, payload, background):
    return [{'role': 'system', 'content': render(module, background)},
            {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                                 separators=(',', ':'), allow_nan=False)}]


def grouping_messages(saved):
    evidence.validate_saved(saved)
    return _messages('grouping', saved['facts'], saved['background'])


def diagnosis_messages(saved):
    return _messages('diagnosis', evidence.diagnosis_input(saved), saved['background'])


def preconditioner_messages(saved):
    return _messages('preconditioner', evidence.preconditioner_model_input(saved), saved['background'])


def editor_messages(saved, adjustments):
    payload = evidence.editor_model_input(saved, adjustments)
    return None if payload is None else _messages('editor', payload, saved['background'])


def replay_messages(bundle):
    payload = replay_input_view.model_input(evidence.model_input(bundle))
    return _messages('replay', payload, bundle['background'])
