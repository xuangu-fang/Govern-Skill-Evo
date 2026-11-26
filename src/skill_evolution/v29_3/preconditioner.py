"""v29.3 Preconditioner prompt; validation and compilation use v29.2 unchanged."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from src.skill_evolution.v27.facts import require
from src.skill_evolution.v29.benchmarks.docvqa import protocol
from src.skill_evolution.v29_2 import preconditioner as base

PROMPT_VERSION = 'v29_3_docvqa_preconditioner_v1'
CONTRACT_VERSION = base.CONTRACT_VERSION
INPUT_VIEW = base.INPUT_VIEW
PROMPT_PATH = Path(__file__).with_name('prompts') / 'preconditioner.md'
PreconditionerCall = base.PreconditionerCall
validate_memory_view = base.validate_memory_view
preconditioner_input = base.preconditioner_input
validate_input = base.validate_input
model_input = base.model_input
validate_model_input = base.validate_model_input
compile_effective_plan = base.compile_effective_plan
validate_preconditioner = base.validate_preconditioner


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    require(prompt_version == PROMPT_VERSION, 'Unknown Preconditioner prompt version')
    prompt = PROMPT_PATH.read_text(encoding='utf-8')
    marker, end = '<actor_base_protocol>\n', '\n</actor_base_protocol>'
    require(prompt.count(marker) == prompt.count(end) == 1, 'Invalid Actor protocol quotation')
    require(prompt.split(marker)[1].split(end)[0] == protocol.actor_base_protocol(),
            'Preconditioner/Actor base protocol differs')
    require(protocol.execution_context(background) in prompt, 'Preconditioner/Actor runtime differs')
    return prompt


def preconditioner_call(saved, memory):
    call = base.preconditioner_call(saved, memory)
    messages = deepcopy(call.messages)
    messages[0]['content'] = render_prompt(call.input['background'])
    return replace(call, prompt_version=PROMPT_VERSION, messages=messages)
