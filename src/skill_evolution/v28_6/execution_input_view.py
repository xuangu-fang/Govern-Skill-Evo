"""Lossless request-local display for Diagnosis and Preconditioner.

Callers first validate full archives and select authorized runs. This codec only
removes verified duplicates; the full audit payload and top-level Parent remain.
"""
from copy import deepcopy
import json

from src.skill_evolution.v28.benchmarks.searchqa.protocol import fields, require, FORMAL_CONTEXT

FORMAT = 'execution_shared_initial_v1'
INPUT_VIEW = 'v28_5_shared_execution_text_v1'
MODULE_FIELDS = {
    'diagnosis': ('parent', 'runs'),
    'preconditioner': ('parent', 'plan', 'runs', 'memory'),
}


def exact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def _fields(view, module, *, compact=False):
    require(module in MODULE_FIELDS, 'Unknown shared execution input module')
    fields(view, (*MODULE_FIELDS[module], *(('shared_initial',) if compact else ())),
           f'{module} execution view')
    require(isinstance(view['runs'], list) and bool(view['runs']), 'Missing execution runs')


def _model_input(view, module):
    result = deepcopy(view)
    table, keys = {}, {}
    for run in result['runs']:
        attempts = run['attempts']
        require(isinstance(attempts, list) and len(attempts) == 1, 'Expected one completed round')
        attempt = attempts[0]
        messages = run['initial']['messages']
        require(isinstance(messages, list) and bool(messages), 'Missing initial messages')
        require(attempt.get('request_context') == FORMAL_CONTEXT, 'Unexpected request context')
        require('request_messages' in attempt and exact(attempt['request_messages']) == exact(messages),
                'Formal request differs from initial messages')
        answer = run['outcome']['answer']
        content = attempt['assistant']['content']
        require(isinstance(content, str) and 'raw_content' in answer and answer['raw_content'] == content,
                'Answer raw_content differs from ordinary assistant content')
        del attempt['request_messages']
        del answer['raw_content']
        for index, message in enumerate(messages):
            require(isinstance(message, dict) and 'shared_message' not in message,
                    'Expected complete initial message')
            if message.get('role') != 'system':
                continue
            value = exact(message)
            if value not in keys:
                key = f'system_{len(keys) + 1}'
                keys[value] = key
                table[key] = message
            messages[index] = {'shared_message': keys[value]}
    result['shared_initial'] = {'format': FORMAT, 'messages': table}
    return result


def model_input(view, *, module):
    """Compact a verified, already scoped view without mutating it."""
    _fields(view, module)
    try:
        return _model_input(view, module)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError('Invalid complete execution view') from exc


def restore_model_input(view, *, module):
    """Restore exact text, message order, roles and metadata; reject ambiguous views."""
    _fields(view, module, compact=True)
    try:
        result = deepcopy(view)
        shared = result.pop('shared_initial')
        fields(shared, ('format', 'messages'), 'Shared initial table')
        require(shared['format'] == FORMAT and isinstance(shared['messages'], dict),
                'Unknown shared initial format')
        for run in result['runs']:
            messages = run['initial']['messages']
            require(isinstance(messages, list), 'Invalid initial messages')
            for index, message in enumerate(messages):
                require(isinstance(message, dict), 'Invalid initial message')
                if 'shared_message' not in message:
                    continue
                key = message['shared_message']
                require(set(message) == {'shared_message'} and isinstance(key, str)
                        and key in shared['messages'], 'Invalid shared message reference')
                restored = shared['messages'][key]
                require(isinstance(restored, dict) and restored.get('role') == 'system',
                        'Only complete system messages may be shared')
                messages[index] = deepcopy(restored)
            require(isinstance(run['attempts'], list) and len(run['attempts']) == 1,
                    'Expected one completed round')
            attempt = run['attempts'][0]
            answer = run['outcome']['answer']
            require('request_messages' not in attempt and 'raw_content' not in answer,
                    'Expected compact execution fields')
            attempt['request_messages'] = deepcopy(messages)
            answer['raw_content'] = attempt['assistant']['content']
        # Reject unused table entries, inline systems, reordered keys and pointers
        # that do not follow deterministic first-occurrence assignment.
        require(exact(model_input(result, module=module)) == exact(view),
                'Noncanonical shared execution view')
        return result
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError('Invalid compact execution view') from exc


def validate_model_input(view, *, original, module):
    restored = restore_model_input(view, module=module)
    # JSON object key positions are not execution information; message object key
    # order is additionally checked by canonical projection above and below.
    require(restored == original and exact(model_input(original, module=module)) == exact(view),
            'Shared execution view differs from verified input')
    return view
