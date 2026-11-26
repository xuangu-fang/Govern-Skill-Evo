"""Narrow v27.1 output-error boundary; source and implementation errors are fatal."""
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.json_response import parse_json_response
from .lmb import evidence, protocol
from copy import deepcopy
import json
from pathlib import Path
from src.skill_evolution.v28.output_feedback import OutputValidationError, TechnicalValidationError
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


POLICY = 'previous_output_validation_error_v1'
TIMELINE = protocol.FACTS_VERSION


def request_messages(base, context):
    """Only the immediately preceding invalid output is temporary feedback."""
    if context is None:
        return deepcopy(base)
    require(context['policy'] == POLICY, 'Unsupported output retry policy')
    require(context.get('execution_view') == TIMELINE, 'Unsupported LMB execution input view')
    messages = deepcopy(base)
    if context.get('feedback_from') is None:
        return messages
    source = Path(context['feedback_from'])
    previous = json.loads((source / 'response.json').read_text())
    error = json.loads((source / 'error.json').read_text())
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
