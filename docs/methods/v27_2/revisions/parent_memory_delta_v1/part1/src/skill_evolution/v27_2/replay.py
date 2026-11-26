"""Build the v27.2 replay request with the v27.1 input/output contract."""
from copy import deepcopy
import json
from src.skill_evolution.v27_1 import replay_input_view
from src.skill_evolution.v27_1.replay import (
    CONTRACT_VERSION, ReplayCall, replay_input, build_replay_from_editor, skip_replay, _finish,
)
from .prompts import render

PROMPT_VERSION = 'v27_2_lmb_replay_v1'


def replay_call(bundle):
    """Return a prepared call, or None for no flips; use skip_replay for its receipt."""
    frozen = deepcopy(bundle)
    view = replay_input(frozen)
    if not view['pairs']:
        return None
    payload = replay_input_view.model_input(view)
    messages = [
        {'role': 'system', 'content': render('replay', frozen['background'])},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                             separators=(',', ':'), allow_nan=False)},
    ]

    def complete(parsed):
        return _finish(frozen, parsed, called=True)

    return ReplayCall('replay', PROMPT_VERSION, CONTRACT_VERSION,
                      deepcopy(frozen), messages, complete)
