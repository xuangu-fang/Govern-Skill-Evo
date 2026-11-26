"""Share only an unchanged executed program with its own complete response."""
from copy import deepcopy

from ...facts import require
from .protocol import extract_code

MARKER = {'from_response': 'python_fence_body_exact_v1'}


def unchanged_body(attempt):
    if attempt.get('executed') is not True or not isinstance(attempt.get('response'), str):
        return None
    try:
        raw, actual = extract_code(attempt['response'])
    except (ValueError, SyntaxError):
        return None
    # In particular, path adaptation must never be hidden behind this marker.
    return raw if raw == actual else None


def share_code(view):
    result = deepcopy(view)
    for run in result['runs']:
        for attempt in run['attempts']:
            code = attempt['executed_code']
            require(code is None or isinstance(code, str), 'Replay code already shared or invalid')
            if isinstance(code, str) and unchanged_body(attempt) == code:
                attempt['executed_code'] = deepcopy(MARKER)
    return result


def restore_code(view):
    result = deepcopy(view)
    for run in result['runs']:
        for attempt in run['attempts']:
            code = attempt['executed_code']
            if code is None or isinstance(code, str):
                continue
            require(code == MARKER, 'Invalid Replay shared code marker')
            body = unchanged_body(attempt)
            require(body is not None, 'Replay shared code requires an unchanged executed response body')
            attempt['executed_code'] = body
    return result
