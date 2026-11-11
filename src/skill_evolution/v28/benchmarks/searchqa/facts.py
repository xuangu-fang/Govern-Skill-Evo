"""Lossless content-only facts from registered, verified training archives."""
from copy import deepcopy
import re

from src.skill_evolution.v27.benchmark import current
from . import protocol as p


def validate_envelope(record):
    return current().validate_record(record)


def parent_text(record):
    return record['execution']['skill']


def run_references(run):
    return {run['ref'], run['initial']['ref'], run['outcome']['ref'],
            *[a['ref'] for a in run['attempts']]}


def _project(record, ref):
    e = record['execution']
    case = current().dataset.case(record['task_id'])
    return {'ref': ref, 'task_id': record['task_id'], 'run_id': record['run_id'],
            'initial': {'ref': ref + ':0', 'task': deepcopy(case.payload),
                        'messages': deepcopy(e['initial_messages'])},
            'attempts': [{'ref': ref + ':1', 'request_context': p.FORMAL_CONTEXT,
                          'request_messages': deepcopy(e['initial_messages']),
                          'assistant': {'role': 'assistant', 'content': e['content']}}],
            'outcome': {'ref': ref + ':outcome', 'status': 'completed',
                        'termination': e['termination'], 'answer': deepcopy(e['answer']),
                        'reference_answers': deepcopy(case.reference),
                        'model_rounds': 1, 'tool_calls': 0, 'api_requests': e['api_requests'],
                        'score': deepcopy(e['metrics'])}}


def validate_run(run):
    p.require(isinstance(run, dict), 'Run must be an object')
    ref = run.get('ref')
    p.require(isinstance(ref, str) and re.fullmatch(r'[PQ][1-9]\d*', ref), 'Invalid run reference')
    record = current().source_record(run.get('run_id'))
    expected_prefix = 'P' if record['provenance']['role'] == 'parent' else 'Q'
    # Candidate build_facts uses temporary P references, relabeled to Q for Replay.
    p.require(ref.startswith(expected_prefix) or expected_prefix == 'Q', 'Parent cannot use Candidate reference')
    p.require(p.equal(run, _project(record, ref)), 'Facts differ from verified training execution')
    return run


def build_facts(records, *, role=None):
    p.require(isinstance(records, list) and records, 'Missing completed executions')
    current().validate_batch(records)
    first = validate_envelope(records[0])
    role = role or first['provenance']['role']
    p.require(role in ('parent', 'candidate'), 'Test cannot become optimization evidence')
    skill = parent_text(first)
    runs, sources, tasks, identities = [], [], set(), set()
    for i, record in enumerate(records, 1):
        validate_envelope(record)
        p.require(record['provenance']['role'] == role and parent_text(record) == skill, 'Mixed roles/Skills')
        p.require(record['task_id'] not in tasks and record['run_id'] not in identities, 'Duplicate run/task')
        tasks.add(record['task_id']); identities.add(record['run_id'])
        run = _project(record, f'P{i}')
        runs.append(run)
        sources.append({k: run[k] for k in ('ref', 'task_id', 'run_id')})
    return {'facts': {'parent': skill, 'runs': runs},
            'background': p.background(first['execution']['actor']), 'sources': sources}


def validate_saved(saved):
    p.fields(saved['facts'], ('parent', 'runs'), 'Facts')
    records = [current().source_record(run['run_id']) for run in saved['facts']['runs']]
    expected = build_facts(records, role='parent')
    for key in ('facts', 'background'):
        p.require(p.equal(saved[key], expected[key]), 'Frozen Parent facts/background differ')
    if 'sources' in saved:
        p.require(p.equal(saved['sources'], expected['sources']), 'Frozen sources differ')
    return saved
