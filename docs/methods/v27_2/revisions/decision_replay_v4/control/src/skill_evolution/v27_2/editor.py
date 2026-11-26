"""Build the v27.2 editor request with the v27.1 input/output contract."""
from copy import deepcopy
import json
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27_1.editor import (
    CONTRACT_VERSION, EditorCall, editor_input, construct_candidate,
)
from .prompts import render

PROMPT_VERSION = 'v27_2_lmb_editor_v1'


def editor_call(saved):
    frozen = deepcopy(saved)
    payload = editor_input(frozen)
    messages = [
        {'role': 'system', 'content': render('editor', frozen['background'])},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                             separators=(',', ':'), allow_nan=False)},
    ]

    def complete(parsed):
        with current().memory_operation():
            checked = editor_input(frozen)
            constructed = construct_candidate(parsed, checked)
        return {**deepcopy(frozen), 'editor': deepcopy(parsed), **constructed}

    return EditorCall('editor', PROMPT_VERSION, CONTRACT_VERSION,
                      deepcopy(frozen), messages, complete)
