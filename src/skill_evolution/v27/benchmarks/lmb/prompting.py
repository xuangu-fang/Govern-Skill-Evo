"""Reviewed standalone LMB Prompts; exact user projections and frozen context."""
import json
from pathlib import Path
from ...benchmark import current
from ...facts import require
from . import evidence, protocol as p, replay_input_view

PROMPT_VERSIONS={name:f'v27_lmb_{name}_v6' for name in ('grouping','diagnosis','preconditioner','editor','replay')}
PROMPT_VERSIONS['replay'] = 'v27_lmb_replay_v8'
RESOURCE_NAMES=frozenset(f'{name}.md' for name in PROMPT_VERSIONS)|{'method_validation_feedback.md'}

def resource_path(key):
    require(key in RESOURCE_NAMES,'Unknown LMB Prompt resource')
    return Path(__file__).with_name('prompts')/key

def render(module,background,*,prompt_version=None):
    require(module in PROMPT_VERSIONS,'Unreviewed method module is disabled')
    require(prompt_version in (None,PROMPT_VERSIONS[module]),'Unknown Prompt version')
    p.execution_context(background)
    s=current().resource(f'{module}.md').read_text()
    base=p.VENDOR_PROMPT.format(skill_section='')
    require(s.split('<actor_base_protocol>\n')[1].split('\n</actor_base_protocol>')[0]==base,'Frozen base protocol mismatch')
    require(p.execution_context(background) in s,'Prompt runtime mismatch')
    return s

def prompt_identity(module):
    require(module in PROMPT_VERSIONS,'Unreviewed module')
    return {'prompt_version':PROMPT_VERSIONS[module],'facts_version':p.FACTS_VERSION,
            'input_view':replay_input_view.INPUT_VIEW if module == 'replay' else p.MODEL_INPUT_VIEW,
            'resources_sha256':{name:p.file_digest(current().resource(name)) for name in (f'{module}.md','method_validation_feedback.md')},
            'actor_base_prompt_sha256':p.digest(p.VENDOR_PROMPT.format(skill_section=''))}

def _messages(module,payload,background):
    return [{'role':'system','content':render(module,background)},
            {'role':'user','content':json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False)}]

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
    return _messages('replay', replay_input_view.model_input(evidence.model_input(bundle)), bundle['background'])


