"""Narrow v28.7 output-error boundary; source and implementation errors are fatal."""
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.json_response import parse_json_response
from src.skill_evolution.v28.benchmarks.searchqa import evidence, protocol
from src.skill_evolution.v28.output_feedback import (POLICY, TIMELINE, OutputValidationError,
                                                     TechnicalValidationError, request_messages)
from . import facts, diagnosis, preconditioner, editor, replay


def output_call(location, function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except TechnicalValidationError:
        raise
    except ValueError as exc:
        if function is parse_json_response:
            raise OutputValidationError(location, str(exc)) from exc
        codes = []
        tb = exc.__traceback__
        while tb:
            codes.append(tb.tb_frame.f_code)
            tb = tb.tb_next
        excluded = {fn.__code__ for fn in (
            diagnosis.diagnosis_input, diagnosis.validate_input, preconditioner.preconditioner_input,
            preconditioner.validate_input, preconditioner.validate_memory_view,
            editor.editor_input, editor.validate_input, editor._validate_model_input,
            replay.validate_bundle, replay.build_replay_from_editor, replay.replay_input,
            evidence.validate_saved, facts.validate_parent_bundle, facts.build_parent_bundle)}
        outputs = {fn.__code__ for fn in (
            diagnosis._validate_output, preconditioner._compile, editor.construct_candidate,
            replay._validate_output)}
        if (not set(codes).intersection(excluded) and set(codes).intersection(outputs) and
                codes[-1] in (require.__code__, protocol.require.__code__)):
            raise OutputValidationError(location, str(exc)) from exc
        raise
