"""One explicit Actor profile and single-pass prompt rendering."""
import ast
import json
from pathlib import Path
import re
import openpyxl

HERE = Path(__file__).parent
PROMPTS = HERE / 'prompts'
EXECUTION_HISTORY = 'execution_only_v1'
DEFAULTS = dict(preview_rows=5, preview_columns=20, preview_cell_chars=40,
    preview_max_chars=100000, max_code_attempts=30, actor_max_output_tokens=16384,
    request_attempts_total=6, request_timeout_seconds=300, program_timeout_seconds=600,
    actor_task_timeout_seconds=600, runtime_error_detail_chars=3000,
    score_coordinate_limit=100, score_missing_sheet_limit=100,
    allowed_libraries='Python standard library, openpyxl, pandas',
    formula_policy_description='No additional formula recalculation; grading reads saved cell values with data_only=True.')


class InputError(ValueError):
    pass


def separate_budgets(profile):
    return profile.get('attempt_budget_policy','responses_v1')=='program_executions_v1'


def execution_history(profile):
    return profile.get('actor_history_policy','cumulative_responses_v1')==EXECUTION_HISTORY


def generation_messages(messages, repair):
    """Temporary format correction never mutates the formal transcript."""
    from copy import deepcopy
    return deepcopy(messages + ([{'role':'assistant','content':repair['response']},repair['feedback']] if repair else []))


def format_feedback(detail, profile):
    return {'role':'user','content':
        '# Previous Program Validation Error\n'
        'The previous response failed pre-execution validation; no program was executed.\n'
        'Return exactly one complete python fenced block without surrounding text.\n'
        'Correct the following validation error:\n'+detail[:profile['runtime_error_detail_chars']]+
        ('\n[Validation detail truncated]' if len(detail)>profile['runtime_error_detail_chars'] else '')}


def render(template, values):
    missing = set(re.findall(r'\{\{(\w+)\}\}', template)) - set(values)
    if missing:
        raise InputError(f'Missing template values: {sorted(missing)}')
    return re.sub(r'\{\{(\w+)\}\}', lambda m: str(values[m[1]]), template)


def template(name):
    return (PROMPTS / name).read_text()


def preview(path, profile):
    wb = openpyxl.load_workbook(path, data_only=False)
    chunks = []
    try:
        for ws in wb.worksheets:
            chunks.append(f'## Sheet: {ws.title} (dim={ws.dimensions}, max_row={ws.max_row}, max_col={ws.max_column})')
            for row in ws.iter_rows(max_row=min(ws.max_row, profile['preview_rows']),
                                    max_col=min(ws.max_column, profile['preview_columns'])):
                cells = []
                for cell in row:
                    value = '' if cell.value is None else str(cell.value)
                    limit = profile['preview_cell_chars']
                    if len(value) > limit:
                        value = value[:limit-3] + '...'
                    cells.append(f'{cell.coordinate}={value}')
                chunks.append(' | '.join(cells))
            if ws.max_row > profile['preview_rows']:
                chunks.append(f"... ({ws.max_row-profile['preview_rows']} more rows)")
            if ws.max_column > profile['preview_columns']:
                chunks.append(f"... ({ws.max_column-profile['preview_columns']} more columns)")
            chunks.append('')
    finally:
        wb.close()
    value = '\n'.join(chunks)
    if len(value) > profile['preview_max_chars']:
        raise InputError('Workbook preview exceeds 100000-character limit; no truncation')
    return value


def initial_messages(task, skill, workbook_preview, profile):
    values = {**time_fields(profile), 'skill': skill or '', 'instruction': task['instruction'],
              'instruction_type': task['instruction_type'], 'answer_region': task['answer_region'],
              'workbook_preview': workbook_preview}
    return [{'role': 'system', 'content': render(template('actor_system.md'), values)},
            {'role': 'user', 'content': render(template('actor_initial.md'), values)}]


def feedback(category, detail, exit_status, used, profile):
    limit = profile['runtime_error_detail_chars']
    return {'role': 'user', 'content': render(template('actor_runtime_feedback.md'), {
        'error_category': category, 'exit_status': exit_status,
        'error_detail_prefix': detail[:limit], 'detail_truncated': str(len(detail) > limit).lower(),
        'code_attempts_used': used, 'code_attempts_remaining': profile['max_code_attempts']-used})}


def check_capacity(messages, config):
    raw = json.dumps(messages, ensure_ascii=False)
    if len(raw) > config['max_input_chars'] or len(raw.encode()) > config['max_message_utf8_bytes']:
        raise InputError('Complete Actor history exceeds configured input capacity; no truncation')


def background(profile):
    views = {}
    for key, name in [('actor_system_prompt', 'actor_system.md'), ('actor_initial_template', 'actor_initial.md'),
                      ('actor_runtime_feedback_template', 'actor_runtime_feedback.md')]:
        value = template(name)
        slots = {k: f'[runtime field: {k}]' for k in re.findall(r'\{\{(\w+)\}\}', value)}
        views[key] = render(value, {**slots, **time_fields(profile)})
    return {**profile, **views}


def execution_context(value):
    return render(template('execution_context.md'), time_fields(value)).rstrip()


def time_fields(profile):
    """Zero disables only the cumulative task deadline; per-operation caps remain."""
    actor_history=('You retain the complete messages within this task, but each execution starts in\n'
                   'a fresh directory with the original input.')
    context_history=('Within a task, the model retains the original messages and every complete\n'
                     'assistant response and returned runtime-feedback message. It has no')
    evidence_history=('These templates describe what can be sent. The saved messages for a specific\n'
                      'execution determine what was actually sent.')
    total=profile['actor_task_timeout_seconds'];program=profile['program_timeout_seconds']
    request=profile['request_timeout_seconds']
    if total==0:
        actor_time=(f'There is no cumulative Actor task time limit. Each API request has a\n'
                    f'{request}-second timeout, and each program execution has a {program}-second\n'
                    'timeout. These per-operation limits do not reduce a shared task time budget.\n'
                    'The code-attempt and request-retry limits still apply.')
        context_time=(f'The request timeout is {request} seconds and each program execution timeout is\n'
                      f'{program} seconds. There is no cumulative Actor task time limit. Preparation,\n'
                      'requests, retry waiting, execution and output checks are recorded for\n'
                      'observability but do not consume a shared task time budget. Each request and\n'
                      'program retains its own timeout. Code-attempt and request-retry limits\n'
                      'persist across resume and are never reset.')
        exhaustion='code attempts'
    else:
        actor_time=(f'The task has a total Actor time budget of {total}\n'
                    'seconds, including preparation, requests, retry waiting, execution and output\n'
                    f'checks. A program runs for at most {program} seconds and no\n'
                    'longer than the remaining task time. Exhausting either budget ends the attempt\n'
                    'to solve this task; unused code rounds do not guarantee additional time.')
        context_time=(f'The request timeout is {request} seconds, the program\n'
                      f'timeout is {program} seconds, and the Actor task budget is\n'
                      f'{total} seconds. The task clock starts when an execution\n'
                      'slot is acquired and input preparation begins; it includes preparation,\n'
                      'requests, retry waiting, execution, and output checks. Queue waiting and\n'
                      'post-submission scoring are outside this Actor budget. In-flight operations\n'
                      'are bounded by remaining task time. These are upper limits, not guarantees\n'
                      'of that much time for every attempt.')
        exhaustion='code attempts or the Actor time budget'
    attempts=profile['max_code_attempts'];requests=profile['request_attempts_total']
    actor_attempts=(f'There are at most {attempts} code attempts, including malformed or\n'
                    'truncated responses.')
    context_attempts=(f'cross-task conversation. There are at most {attempts} code attempts;\n'
        'a complete malformed or truncated generation also consumes an attempt.\n'
        'Transport retries are counted separately, with at most\n'
        f'{requests} total request attempts per generation, including\n'
        'the first. Retries of an incomplete request keep the same messages. Remaining\n'
        'code attempts are reported after each completed response when continuing.')
    if separate_budgets(profile):
        actor_attempts=(f'There are at most {attempts} actual program executions, including the final\n'
            'successful execution. Network failures, truncated generations and malformed\n'
            'responses do not consume program executions. Generating each executable\n'
            f'program allows at most {requests} total API requests, including the first;\n'
            'network, truncation and format retries share this single request budget.')
        context_attempts=(f'cross-task conversation. At most {attempts} actual program executions are\n'
            'allowed, including successful submission. Network failures, truncated outputs\n'
            'and malformed complete responses do not consume this execution budget.\n'
            f'Generating each executable program allows at most {requests} total API requests,\n'
            'including the first. All network, truncation and format retries share this\n'
            'single budget; it is renewed only after an actual program execution.\n'
            'Network failures and truncated outputs retry with unchanged messages.\n'
            'Truncated responses remain archived but are not appended to Actor history;\n'
            'response_in_history=false identifies these events in evidence. A complete\n'
            'malformed response and its format feedback are appended. Feedback counters\n'
            'report actual program executions used and remaining. Exhausting generation\n'
            'requests records generation_incomplete, preserves the checkpoint and pauses\n'
            'the batch; it does not score the task or omit it from the denominator.')
        exhaustion='program executions' if total==0 else 'program executions or the Actor time budget'
    if execution_history(profile):
        actor_history=('You retain the initial messages, executed program responses and execution\n'
            'feedback. Format correction uses only the latest invalid response and validation\n'
            'error as temporary context; they are cleared after execution. Each execution\n'
            'starts in a fresh directory with the original input.')
        context_history=('Within a task, formal history retains the original messages, executed\n'
                         'program responses and returned execution-feedback messages. It has no')
        evidence_history=('These templates describe what can be sent. Raw archived API messages determine\n'
            'what was actually sent; execution-only evidence shows formal history and omits\n'
            'temporary format corrections even when they influenced the executed response.')
        context_attempts=(f'cross-task conversation. At most {attempts} actual program executions are\n'
            'allowed, including successful submission. Each executable program allows at most\n'
            f'{requests} total API requests, including the first. Network failures, truncation,\n'
            'empty outputs and format retries share this budget and do not consume executions.\n'
            'Technical failures, truncated and empty responses retry the current request unchanged.\n'
            'Complete invalid responses are corrected using only the latest invalid response and\n'
            'its validation error, temporarily appended to the formal execution history. This\n'
            'temporary context is replaced on another format error and cleared after execution.\n'
            'Only executed responses and actual execution feedback enter formal history.\n'
            'The execution evidence view excludes generation failures and temporary corrections;\n'
            'its request_messages reconstruct formal history, not every actual API request.\n'
            'Full requests, responses and usage remain in the raw audit archive. Generation\n'
            'budget exhaustion preserves the checkpoint and pauses without scoring the task.\n'
            'Budgets persist across resume; request allowance renews only after execution.')
    return {**profile,'actor_time_budget_description':actor_time,
            'actor_history_description':actor_history,'context_history_description':context_history,
            'evidence_history_description':evidence_history,
            'context_time_budget_description':context_time,'actor_exhaustion_conditions':exhaustion,
            'actor_attempt_budget_description':actor_attempts,'context_attempt_budget_description':context_attempts}


def extract_code(response):
    match = re.fullmatch(r'\s*```python\s*\n(.*?)\n```\s*', response, re.S)
    if not match or '```' in match[1]:
        raise ValueError('Return exactly one complete python fenced block without surrounding text')
    raw = match[1] + '\n'
    tree = ast.parse(raw)
    protected = {'INPUT_PATH', 'OUTPUT_PATH'}
    allowed, replacements = set(), []
    lines = raw.encode().splitlines(keepends=True)
    starts = [0]
    for line in lines: starts.append(starts[-1] + len(line))
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and
                isinstance(node.targets[0], ast.Name) and node.targets[0].id in protected):
            if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
                raise ValueError('Only simple top-level literal path bindings may be adapted')
            allowed.add(id(node.targets[0]))
            replacements.append((starts[node.lineno-1]+node.col_offset,
                                 starts[node.end_lineno-1]+node.end_col_offset))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) and node.id in protected and id(node) not in allowed:
            raise ValueError('Complex path rebinding is not supported')
        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in protected or
            isinstance(node, ast.arg) and node.arg in protected or
            isinstance(node, ast.alias) and (node.asname or node.name) in protected):
            raise ValueError('Complex path rebinding is not supported')
    actual = raw.encode()
    for start, end in reversed(replacements): actual = actual[:start] + b'pass' + actual[end:]
    return raw, actual.decode()
