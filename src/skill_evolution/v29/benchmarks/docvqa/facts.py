"""Complete text-only facts from completed training Actor records."""
from copy import deepcopy
import re
from . import protocol as p
from .scoring import score
from src.skill_evolution.v27.benchmark import current


def project_execution(case, execution, *, ref, run_id):
    """Project a checked execution. No summaries, hidden fields or image bytes."""
    p.validate_case(case)
    p.require(case.metadata['split'] == 'train', 'Test cannot enter optimization evidence')
    p.require(isinstance(ref, str) and re.fullmatch(r'[PQ][1-9]\d*', ref), 'Invalid run reference')
    p.nonempty_text(run_id, 'Run ID')
    p.validate_config(execution['actor'])
    p.require(execution['termination'] == 'stop', 'Expected a completed stop response')
    p.require(type(execution['api_requests']) is int and 1 <= execution['api_requests'] <= 6,
              'Invalid request count')
    p.require(execution['initial_messages'] == p.messages_for_case(case, execution['skill']),
              'Messages differ from the executed task/Skill')
    answer, metrics = score(execution['content'], case.reference)
    p.require(answer == execution['answer'] and metrics == execution['metrics'], 'Derived score differs')
    messages = p.text_projection(execution['initial_messages'], case.payload['image_path'])
    return {'ref': ref, 'task_id': case.case_id, 'run_id': run_id,
            'initial': {'ref': ref + ':0', 'task': deepcopy(dict(case.payload)), 'messages': messages},
            'attempts': [{'ref': ref + ':1', 'request_context': p.FORMAL_CONTEXT,
                          'request_messages': deepcopy(messages),
                          'assistant': {'role': 'assistant', 'content': execution['content']}}],
            'outcome': {'ref': ref + ':outcome', 'status': 'completed', 'termination': 'stop',
                        'answer': answer, 'reference_answers': deepcopy(case.reference),
                        'model_rounds': 1, 'tool_calls': 0, 'api_requests': execution['api_requests'],
                        'score': metrics}}


def build_facts(records, *, adapter, directory):
    """Check against an explicit batch archive; no implicit source lookup."""
    p.require(isinstance(records, list) and records, 'Missing completed records')
    p.require(records == adapter.read_batch(directory), 'Records differ from the completed batch')
    role = records[0]['provenance']['role']
    p.require(role in ('parent', 'candidate'), 'Test cannot enter optimization evidence')
    skill = records[0]['execution']['skill']
    prefix = 'P' if role == 'parent' else 'Q'
    runs = []
    for index, record in enumerate(records, 1):
        p.require(record['provenance']['role'] == role and record['execution']['skill'] == skill,
                  'Mixed execution roles or Skills')
        runs.append(project_execution(adapter.dataset.case(record['task_id']), record['execution'],
                    ref=f'{prefix}{index}', run_id=record['run_id']))
    return {'facts': {'parent': skill, 'runs': runs}, 'background': p.actor_config(),
            'sources': [{k: run[k] for k in ('ref', 'task_id', 'run_id')} for run in runs]}


def run_references(run):
    return {run['ref'], run['initial']['ref'], run['outcome']['ref'],
            *[attempt['ref'] for attempt in run['attempts']]}


def validate_envelope(record):
    return current().validate_record(record)


def parent_text(record):
    return record['execution']['skill']


def validate_run(run):
    p.require(isinstance(run, dict), 'Expected execution facts')
    ref = run.get('ref')
    p.require(isinstance(ref, str) and re.fullmatch(r'[PQ][1-9]\d*', ref), 'Invalid run reference')
    record = current().source_record(run.get('run_id'))
    prefix = 'P' if record['provenance']['role'] == 'parent' else 'Q'
    p.require(ref.startswith(prefix), 'Execution role differs from its evidence reference')
    expected = current().project_record(record, ref)
    p.require(run == expected, 'Text evidence differs from the completed execution')
    return run


def validate_saved(saved):
    p.fields(saved['facts'], ('parent', 'runs'), 'Facts')
    records = [current().source_record(run['run_id']) for run in saved['facts']['runs']]
    expected = current().build_facts(records, role='parent')
    for key in ('facts', 'background'):
        p.require(saved[key] == expected[key], 'Saved Parent evidence differs')
    if 'sources' in saved:
        p.require(saved['sources'] == expected['sources'], 'Saved evidence sources differ')
    return saved
