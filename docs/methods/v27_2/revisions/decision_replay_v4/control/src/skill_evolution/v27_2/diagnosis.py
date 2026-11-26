"""Build the v27.2 diagnosis request with the v27.1 input/output contract."""
from copy import deepcopy
import json
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import text
from src.skill_evolution.v27_1.diagnosis import (
    CONTRACT_VERSION, INPUT_VIEW, DiagnosisCall, diagnosis_input, model_input, _validate_output,
)
from .prompts import render

PROMPT_VERSION = 'v27_2_lmb_diagnosis_v2'


def diagnosis_call(saved):
    frozen = deepcopy(saved)
    text(frozen.get('round_id'), 'round ID')
    payload = model_input(frozen)
    messages = [
        {'role': 'system', 'content': render('diagnosis', frozen['background'])},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                             separators=(',', ':'), allow_nan=False)},
    ]

    def complete(parsed):
        # Recheck completed sources at completion; exposed input objects are copies.
        with current().memory_operation():
            checked = diagnosis_input(frozen)
            _validate_output(parsed, checked)
        return {**deepcopy(frozen), 'diagnosis': deepcopy(parsed)}

    return DiagnosisCall('diagnosis', PROMPT_VERSION, CONTRACT_VERSION,
                         deepcopy(frozen), messages, complete)
