"""Prepare the reviewed v26.2 prompt with the v26.1 input and output contracts."""
from dataclasses import replace
from ..v26_1 import preconditioner as baseline
from ..v26_1.preconditioner import (
    CONTRACT_VERSION, INPUT_VIEW, PreconditionerCall, _compile, compile_effective_plan,
    model_input, preconditioner_input, validate_input, validate_memory_view,
    validate_model_input, validate_preconditioner,
)
from . import protocol

PROMPT_VERSION = protocol.PRECONDITIONER_VERSION
PROMPT_PATH = protocol.PRECONDITIONER_PATH


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    protocol.require(prompt_version == PROMPT_VERSION, 'Unknown preconditioner prompt version')
    return protocol.render_prompt(PROMPT_PATH, background)


def preconditioner_call(saved, memory):
    call = baseline.preconditioner_call(saved, memory)
    system = {'role': 'system', 'content': render_prompt(call.input['background'])}
    return replace(call, prompt_version=PROMPT_VERSION, messages=[system, *call.messages[1:]])
