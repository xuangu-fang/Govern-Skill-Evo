"""Reviewed standalone SearchQA Prompts; exact user projections and frozen context."""
import json
from pathlib import Path
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import require
from . import evidence, protocol as p, replay_input_view

PROMPT_VERSIONS={name:f'v28_searchqa_{name}_v1' for name in ('grouping','diagnosis','preconditioner','editor','replay')}
PROMPT_VERSIONS['replay'] = 'v28_searchqa_replay_v3'
RESOURCE_NAMES=frozenset(f'{name}.md' for name in PROMPT_VERSIONS)|{'method_validation_feedback.md'}

def resource_path(key):
    require(key in RESOURCE_NAMES,'Unknown SearchQA Prompt resource')
    return Path(__file__).with_name('prompts')/key

def render(module,background,*,prompt_version=None):
    require(module in PROMPT_VERSIONS,'Unreviewed method module is disabled')
    require(prompt_version in (None,current().prompt_versions[module]),'Unknown Prompt version')
    p.execution_context(background)
    s=current().resource(f'{module}.md').read_text()
    # Change only the runtime budget description; preserve the method instructions.
    s=s.replace(p.execution_context(p.ACTOR), p.execution_context(background))
    base=p.actor_base_protocol()
    require(s.split('<actor_base_protocol>\n')[1].split('\n</actor_base_protocol>')[0]==base,'Frozen base protocol mismatch')
    require(p.execution_context(background) in s,'Prompt runtime mismatch')
    return s

def prompt_identity(module):
    require(module in PROMPT_VERSIONS,'Unreviewed module')
    # Standalone callers retain v28; bound method calls carry their own profile.
    try:
        versions = current().prompt_versions
    except RuntimeError:
        versions = PROMPT_VERSIONS
    return {'prompt_version':versions[module],'facts_version':p.FACTS_VERSION,
            'input_view':replay_input_view.INPUT_VIEW if module == 'replay' else p.MODEL_INPUT_VIEW}

def _messages(module,payload,background):
    return [{'role':'system','content':render(module,background)},
            {'role':'user','content':json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False)}]

def grouping_messages(saved):
    evidence.validate_saved(saved)
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
    return _messages('replay', replay_input_view.model_input(evidence.model_input(bundle)), bundle['background'])


