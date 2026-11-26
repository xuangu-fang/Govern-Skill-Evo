"""Use the approved prompt with the inherited one-adjustment-per-Original contract."""
from dataclasses import replace

from . import protocol
from . import _shared_preconditioner as shared
from ._shared_preconditioner import (
    CONTRACT_VERSION, INPUT_VIEW, PROMPT_PATH, PreconditionerCall, _compile,
    compile_effective_plan, model_input, preconditioner_input, validate_input,
    validate_memory_view, validate_model_input, validate_preconditioner,
)

PROMPT_VERSION = protocol.PRECONDITIONER_VERSION


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    protocol.require(prompt_version == PROMPT_VERSION, 'Unknown preconditioner prompt version')
    return protocol.render_prompt(PROMPT_PATH, background)


def preconditioner_call(saved, memory):
    # The shared builder reads PROMPT_PATH from this package's protocol.
    return replace(shared.preconditioner_call(saved, memory), prompt_version=PROMPT_VERSION)
