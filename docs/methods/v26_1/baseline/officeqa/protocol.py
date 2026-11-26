"""Versioned evidence schema, separate from the unchanged public Actor protocol."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from skilladam.benchmarks.officeqa.rollout import TOOL_SCHEMAS
from skilladam.benchmarks.officeqa import tool_runtime

from src.adapters.officeqa.data import PROFILE
from src.adapters.officeqa.execution import EXECUTION_CONFIG
from src.adapters.officeqa.local import source_references
from ...facts import require, text

RECORD_VERSION = 'v26_officeqa_execution_v1'
FACTS_VERSION = 'v26_officeqa_formal_evidence_v1'
INPUT_VIEW = 'v26_officeqa_pairs_formal_v1'
SCORE_VIEW = 'officeqa_em_f1_no_reference_answers_v1'
EM_GATE = 'officeqa_em_exact_v1'
FORMAL_CONTEXT = 'formal_history_without_temporary_format_feedback_v1'
IDENTITY = {'name': 'OfficeQA', 'execution_profile': PROFILE, 'evidence_version': FACTS_VERSION}


def exact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def equal(left, right):
    return exact(left) == exact(right)


def digest(value):
    return hashlib.sha256(exact(value).encode()).hexdigest()


def fields(value, names, label):
    require(isinstance(value, dict) and set(value) == set(names), f'{label}: unexpected fields')


def integer(value, name, *, minimum=0):
    require(type(value) is int and value >= minimum, f'Invalid {name}')
    return value


def score_view(metrics):
    fields(metrics, ('em', 'f1'), 'OfficeQA scores')
    for name, value in metrics.items():
        require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1,
                f'Invalid {name} score')
    require(metrics['em'] in (0, 1), 'EM must be binary')
    return deepcopy(metrics)


def public_task(case):
    """Only declared task data; never copy reference answers or arbitrary metadata."""
    payload = case.payload
    result = {'id': case.case_id, 'split': case.metadata['split'],
              **{key: deepcopy(payload[key]) for key in
                 ('question', 'source_files', 'source_docs', 'category', 'task_type')}}
    return validate_task(result)


def validate_task(task):
    fields(task, ('id', 'split', 'question', 'source_files', 'source_docs', 'category', 'task_type'), 'Task')
    text(task['id'], 'task ID'); text(task['question'], 'question')
    require(task['split'] in ('train', 'validation', 'test') and task['task_type'] == 'officeqa', 'Invalid task type/split')
    require(isinstance(task['category'], str), 'Invalid category')
    require(isinstance(task['source_files'], list) and isinstance(task['source_docs'], list), 'Sources must be arrays')
    source_references(task['source_files'], task['source_docs'])
    return task


def source_pages(task):
    """These are declared locators, not a claim that every page reached the model."""
    return [{'file': name, 'source_page': page, 'url': url}
            for name, page, url in source_references(task['source_files'], task['source_docs'])]


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def background(actor):
    # Explicit allowlist: endpoints and raw request diagnostics are not method evidence.
    limits = actor.get('task_max_completion_tokens', {})
    require(isinstance(limits, dict) and all(isinstance(t, str) and type(n) is int and n > 0
            for t, n in limits.items()), 'Invalid task output budget background')
    return {**({'task_max_completion_tokens': deepcopy(limits)} if limits else {}),
            'version': FACTS_VERSION, 'profile': PROFILE, 'score_view': SCORE_VIEW,
            'max_model_rounds': 24, 'tool_names': ['glob', 'read', 'grep'],
            'tool_schemas': deepcopy(list(TOOL_SCHEMAS)),
            'tool_output_limits': {'read_chars': tool_runtime._MAX_READ_CHARS,
                                   'grep_matches': tool_runtime._MAX_GREP_MATCHES,
                                   'glob_matches': tool_runtime._MAX_GLOB_MATCHES},
            'oracle_limits': {'page_chars': tool_runtime._MAX_ORACLE_PAGE_CHARS,
                              'total_chars': tool_runtime._MAX_ORACLE_CONTEXT_CHARS},
            'max_tool_calls_per_round': None, 'max_total_tool_calls': None,
            'request_attempts_total': EXECUTION_CONFIG['request_attempts_total'],
            'request_timeout_seconds': actor['request_timeout_seconds'],
            'connect_timeout_seconds': actor['connect_timeout_seconds'],
            'model': actor['model'], 'max_completion_tokens': actor['max_completion_tokens'],
            'temperature': actor['temperature'], 'reasoning_effort': actor['reasoning_effort'],
            'reasoning_mode': actor['reasoning_mode'], 'token_limit_field': actor['token_limit_field'],
            'request_context': FORMAL_CONTEXT, 'answer_feedback_to_actor': False}


def execution_context(value):
    require(value.get('version') == FACTS_VERSION, 'Wrong OfficeQA evidence version')
    return ('OfficeQA uses recorded initial messages and accepted assistant/tool exchanges. '
            'Initial input can contain rendered source pages; document availability alone is not observation. '
            'Source page numbers are URL/parsed-page identifiers, not TXT line numbers. '
            'read start/limit and grep line labels refer to transformed text. '
            'The available tools are local glob/read/grep, with no program execution tool. '
            'Paths are redacted in the archive; a displayed path prefix does not establish access permission. '
            'Temporary format corrections and failed generations remain in the raw audit, outside this view. '
            'A round reference includes one accepted assistant response and all its committed tool observations; '
            'an individual tool reference includes only that call, its observation, and its formal request context. '
            'Scores are post-execution EM/F1; reference answers and score correction are never Actor feedback. '
            'A completed round-limit termination is distinct from an incomplete generation. '
            'The recorded execution settings are: ' + exact(value))
