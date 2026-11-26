"""Use the v26.4 Replay prompt for verified EM transitions."""
from dataclasses import replace

from . import protocol, _shared_replay as shared
from ._shared_replay import (
    CONTRACT_VERSION, PROMPT_PATH, ReplayCall, _validate_output, build_replay_from_editor,
    model_input, replay_input, skip_replay, validate_bundle, validate_input, validate_replay,
)

PROMPT_VERSION = protocol.REPLAY_VERSION


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    protocol.require(prompt_version == PROMPT_VERSION, 'Unknown replay prompt version')
    return protocol.render_prompt(PROMPT_PATH, background)


def replay_call(bundle):
    call = shared.replay_call(bundle)
    return replace(call, prompt_version=PROMPT_VERSION) if call is not None else None
