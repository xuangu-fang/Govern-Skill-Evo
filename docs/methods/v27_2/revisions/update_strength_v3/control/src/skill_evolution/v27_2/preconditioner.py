"""Build the v27.2 preconditioner request with the v27.1 input/output contract."""
from copy import deepcopy
import json
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts.editor import actual_diff
from src.skill_evolution.v27_1.preconditioner import (
    CONTRACT_VERSION, INPUT_VIEW, PreconditionerCall, preconditioner_input, model_input, _compile,
)
from .prompts import render

PROMPT_VERSION = 'v27_2_lmb_preconditioner_v2'


def preconditioner_call(saved, memory):
    frozen = {**deepcopy(saved), 'memory': deepcopy(memory)}
    payload = model_input(frozen, frozen['memory'])
    messages = [
        {'role': 'system', 'content': render('preconditioner', frozen['background'])},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                             separators=(',', ':'), allow_nan=False)},
    ]

    def complete(parsed):
        with current().memory_operation():
            checked = preconditioner_input(frozen, frozen['memory'])
            effective = _compile(parsed, checked)
            originals = {u['id']: u['text'] for u in checked['plan']['updates']}
            # Audit-only standard diffs, not model-generated executable patches.
            diffs = {u['id']: actual_diff(originals[u['id']], u['text'])
                     for u in (effective['updates'] if effective else [])
                     if u['text'] != originals[u['id']]}
        return {**deepcopy(frozen), 'preconditioner': deepcopy(parsed),
                'effective_plan': effective, 'update_diffs': diffs}

    return PreconditionerCall('preconditioner', PROMPT_VERSION, CONTRACT_VERSION,
                             deepcopy(frozen), messages, complete)
