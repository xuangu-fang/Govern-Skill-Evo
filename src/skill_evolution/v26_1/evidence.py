"""OfficeQA execution evidence bound to recorded tasks, messages and scores."""
from copy import deepcopy
from src.skill_evolution.v26.benchmarks.officeqa.facts import audit_record
from src.skill_evolution.v26.benchmarks.officeqa.evidence import (
    run_references, validate_run, relabel, pair_result,
)
from . import protocol as p


def audit_execution(record):
    p.fields(record, ('schema', 'run_id', 'task_id', 'task', 'provenance', 'execution'), 'Execution')
    p.require(record['schema'] == p.RECORD_VERSION, 'Unknown execution schema')
    task = p.validate_task(record['task'])
    p.require(task['id'] == record['task_id'] == record['execution']['task_id'], 'Task identity differs')
    provenance = record['provenance']
    p.fields(provenance, ('batch_id', 'role'), 'Provenance')
    p.require(record['run_id'] == provenance['batch_id'] + ':' + p.digest(task['id']), 'Run identity differs')
    role = provenance['role']
    p.require(role in ('parent', 'candidate', 'evaluation') and
              (role == 'evaluation') == (task['split'] == 'test'), 'Invalid role for task split')
    return audit_record(record['execution'])


def formal_run(record, ref):
    visible = audit_execution(record)
    for n, step in enumerate(visible, 1):
        step['ref'] = f'{ref}:{n}'
        for j, tool in enumerate(step['tools'], 1):
            tool['ref'] = f'{ref}:{n}_t{j}'
    raw = record['execution']['raw_result']
    task = record['task']
    run = {'ref': ref, 'task_id': task['id'], 'run_id': record['run_id'],
           'initial': {'ref': ref + ':0', 'task': deepcopy(task),
                       'declared_source_pages': p.source_pages(task),
                       'messages': deepcopy(record['execution']['initial_messages'])},
           'attempts': visible, 'outcome': {'ref': ref + ':outcome', 'status': 'completed',
               'termination': raw['termination_reason'], 'answer': record['execution']['answer'],
               'model_rounds': raw['n_turns'], 'tool_calls': raw['n_tool_calls'], 'api_requests': raw['api_requests'],
               'score': p.score_view(record['execution']['metrics'])}}
    return validate_run(run)


def verify_pair(parent, candidate):
    p.require(parent['provenance']['role'] == 'parent' and candidate['provenance']['role'] == 'candidate',
              'Pair roles differ')
    p.require(parent['run_id'] != candidate['run_id'] and p.equal(parent['task'], candidate['task']),
              'Pair task or run identity differs')
    left, right = parent['execution'], candidate['execution']
    p.require(p.equal(left['actor'], right['actor']), 'Pair Actor conditions differ')
    p.require(p.equal(left['initial_messages'][1:], right['initial_messages'][1:]), 'Paired task messages differ')


def cost_summary(records):
    """Count all reserved HTTP attempts, including failed/unknown requests, once."""
    ids = set(); usages = []; rounds = calls = 0
    for record in records:
        audit_execution(record)
        p.require(record['run_id'] not in ids, 'Duplicate execution in cost report'); ids.add(record['run_id'])
        raw = record['execution']['raw_result']; rounds += raw['n_turns']; calls += raw['n_tool_calls']
        usages.extend(raw['usage_records'])
    result = {'model_rounds': rounds, 'tool_calls': calls, 'http_attempts': len(usages)}
    for key in ('input_tokens', 'output_tokens', 'total_tokens'):
        known = [u[key] for u in usages if u.get(key) is not None]
        result[key] = {'known_sum': sum(known), 'unknown_requests': len(usages) - len(known)}
    return result
