"""Versioned request feedback; only explicit output-validation boundaries opt in."""
from copy import deepcopy
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v23.facts import require

LEGACY = 'unchanged_request_v1'
POLICY = 'previous_output_validation_error_v1'
INSTRUCTION = ('If validation feedback is provided, correct the reported errors and return '
               'the complete output under the same contract.')


class OutputValidationError(ValueError):
    def __init__(self, location, detail):
        self.diagnostic = {'location': location, 'error': detail[:600]}
        super().__init__(f'{location}: {detail[:600]}')


class TechnicalValidationError(ValueError):
    """An identified validator defect must never be reported as a content error."""


def output_call(location, function, *args, **kwargs):
    """Wrap known checks only, never arbitrary ValueErrors or persistence failures.

    Recognition uses executing functions, not exception text. Input/archive
    validation nested inside a shared validator is explicitly excluded.
    """
    try:
        return function(*args, **kwargs)
    except TechnicalValidationError:
        raise
    except ValueError as exc:
        frames = []
        cause = exc
        while cause is not None:
            if isinstance(cause, TechnicalValidationError):
                raise
            tb = cause.__traceback__
            while tb:
                frames.append(tb.tb_frame)
                tb = tb.tb_next
            deepest = cause
            cause = cause.__cause__
        excluded = {'validate_memory', 'normalize_memory', 'validate_payload', 'validate_bundle',
                    'preconditioner_input', 'diagnosis_input', 'project_payload', 'knowledge_only',
                    'validate_repair_input'}
        if any(f.f_code.co_name == 'check' and
               str(f.f_locals.get('location', '')).startswith('input') for f in frames):
            raise
        if any(f.f_code.co_name in excluded for f in frames):
            raise
        # The shared normalizer/compiler rechecks the input schema internally.
        if any(f.f_code.co_name == 'fields' and f.f_locals.get('name') == 'Input' for f in frames):
            raise
        origin = frames[-1].f_code
        path = Path(origin.co_filename)
        root = Path(__file__).parent.parent
        from .update_patch import OutputSchemaError
        if (isinstance(exc, OutputSchemaError) and path == root/'v23_5/update_patch.py'
                and any(f.f_code.co_name == '_validate_output_schema' for f in frames)):
            raise OutputValidationError(exc.location, exc.detail) from exc
        approved_callers = {root/p for p in (
            'v23/facts.py', 'v23/diagnosis.py', 'v23/memory.py', 'v23/grouping.py',
            'v23_5/editor.py', 'v23_5/replay.py', 'v23_5/update_patch.py',
            'v23_5/plan.py', 'v23_5/memory_view.py', 'shared/unnumbered_patch.py')}
        known = ((path == root/'v23/facts.py' and origin.co_name == 'require'
                  and len(frames) > 1 and Path(frames[-2].f_code.co_filename) in approved_callers) or
                 (path.name == 'diagnosis_editor.py' and origin.co_name in
                  {'parse_json_response', '_text', 'object_pairs', 'invalid_constant'}) or
                 (path.name == 'update_patch.py' and origin.co_name in
                  {'prose', '_prose_references', 'normalize_update_patches'}) or
                 (path.name == 'unnumbered_patch.py' and origin.co_name == 'apply_patch') or
                 (path.name == 'preconditioner.py' and origin.co_name == 'parse_json_response'))
        known = known or (path == root/'v23_5/knowledge_verifier.py' and
                          origin.co_name in {'check', 'invalid_constant', 'parse_output'})
        # json.loads raises from the standard library beneath our parser.
        known = known or (isinstance(deepest, json.JSONDecodeError) and any(
            f.f_code.co_name == 'parse_json_response' or
            (f.f_code.co_name == 'parse_output' and
             Path(f.f_code.co_filename) == root/'v23_5/knowledge_verifier.py') for f in frames))
        if not known:
            raise
        detail = str(exc)
        cause = exc
        while cause is not None:
            if isinstance(cause, json.JSONDecodeError):
                detail = (f'JSON body line {cause.lineno}, column {cause.colno} '
                          f'(char {cause.pos}): {cause.msg}')
                break
            cause = cause.__cause__
        raise OutputValidationError(location, detail) from exc


def policy(context):
    value = LEGACY if context is None else context['policy']
    require(value in (LEGACY, POLICY), 'Unsupported output retry policy')
    return value


def generation_context(generate):
    return getattr(generate, 'request_context', None)


def saved_context(directory):
    path = Path(directory)/'request_context.json'
    return json.loads(path.read_text()) if path.exists() else None


def prompt_text(path, retry_policy=LEGACY):
    require(retry_policy in (LEGACY, POLICY), 'Unsupported output retry policy')
    if retry_policy == POLICY:
        path = Path(__file__).with_name(Path(path).stem + '_feedback.md')
    return path.read_text(encoding='utf-8')


def request_messages(base, context):
    policy(context)
    messages = deepcopy(base)
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


def save_context(directory, context):
    if context is not None:
        policy(context)
        write_record(Path(directory)/'request_context.json', context)
