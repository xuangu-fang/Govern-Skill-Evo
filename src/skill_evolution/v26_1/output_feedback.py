"""Narrow v29.4 output-error boundary; source and implementation errors are fatal."""
from copy import deepcopy
import json
from pathlib import Path

from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.json_response import parse_json_response
from . import evidence, protocol
from src.skill_evolution.v29.output_feedback import (POLICY, OutputValidationError,
                                                     TechnicalValidationError, policy)
from . import facts, diagnosis, preconditioner, editor, replay

TIMELINE = protocol.IDENTITY['evidence_version']


def request_messages(base, context):
    policy(context)
    messages = deepcopy(base)
    view = None if context is None else context.get('execution_view')
    require(view in (None, TIMELINE), 'Unsupported execution input view')
    # OfficeQA builders already project and encode the authorized formal facts.
    if context is None or context.get('feedback_from') is None:
        return messages
    require(context['policy'] == POLICY, 'Feedback requires its versioned policy')
    source = Path(context['feedback_from'])
    previous = json.loads((source/'response.json').read_text())
    error = json.loads((source/'error.json').read_text())
    require(error['kind'] == 'output_validation' and previous['finish_reason'] == 'stop',
            'Feedback source is not a complete output validation failure')
    diagnostic = error['diagnostic']
    require(isinstance(previous['content'], str), 'Feedback source has no response body')
    messages.extend([
        {'role': 'assistant', 'content': previous['content']},
        {'role': 'user', 'content': (
            '# Previous Output Validation Error\n\n'
            f"Location: {diagnostic['location']}\nError: {diagnostic['error']}\n\n"
            'Correct the reported error and return the complete JSON object under the original '
            'output contract. Preserve unaffected content. This diagnostic is not task evidence '
            'and does not expand reference permissions.')},
    ])
    return messages


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
            facts.validate_parent_bundle, facts.build_parent_bundle)}
        outputs = {fn.__code__ for fn in (
            diagnosis._validate_output, preconditioner._compile, editor.construct_candidate,
            replay._validate_output)}
        if (not set(codes).intersection(excluded) and set(codes).intersection(outputs) and
                codes[-1] in (require.__code__, protocol.require.__code__)):
            raise OutputValidationError(location, str(exc)) from exc
        raise
