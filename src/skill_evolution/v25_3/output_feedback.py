"""Identify correctable model-output errors at the four optimizer contracts."""
from traceback import walk_tb

from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.json_response import parse_json_response
from src.skill_evolution.v28.output_feedback import OutputValidationError, TechnicalValidationError
from src.skill_evolution.v28_5.editor import _validate_model_input
from . import method


_OUTPUT = {fn.__code__ for fn in (
    method.diagnosis, method.effective_plan, method.construct_candidate, method.knowledge)}
_INPUT = {method.refs.__code__, _validate_model_input.__code__}


def checked_output(name, validate, content, payload):
    try:
        parsed = parse_json_response(content)
    except ValueError as exc:
        raise OutputValidationError(f'{name} response', str(exc)) from exc
    try:
        return parsed, validate(parsed, payload)
    except TechnicalValidationError:
        raise
    except ValueError as exc:
        # Match the reference stages: only a deliberate output-contract assertion
        # can request a correction. Shared validators also check trusted inputs.
        frames = [frame.f_code for frame, _ in walk_tb(exc.__traceback__)]
        if (_OUTPUT.intersection(frames) and not _INPUT.intersection(frames)
                and frames[-1] is require.__code__):
            raise OutputValidationError(f'{name} output', str(exc)) from exc
        raise
