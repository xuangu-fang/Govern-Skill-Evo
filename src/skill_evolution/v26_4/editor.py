"""Use the v26.4 Editor prompt with the existing patch contract."""
from dataclasses import replace

from . import protocol, _shared_editor as shared
from ._shared_editor import (
    CONTRACT_VERSION, PROMPT_PATH, EditorCall, _validate_model_input,
    construct_candidate, construct_selected, editor_input, select_skill, validate_editor, validate_input,
)

PROMPT_VERSION = protocol.EDITOR_VERSION


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    protocol.require(prompt_version == PROMPT_VERSION, 'Unknown editor prompt version')
    return protocol.render_prompt(PROMPT_PATH, background)


def editor_call(saved):
    return replace(shared.editor_call(saved), prompt_version=PROMPT_VERSION)
