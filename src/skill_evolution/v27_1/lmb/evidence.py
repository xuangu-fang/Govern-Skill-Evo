"""LMB pair validation; no legacy Grouping dispatch."""
from copy import deepcopy
from src.skill_evolution.v27.facts import require
from . import protocol as p
from .facts import validate_envelope, validate_run, validate_saved
from src.skill_evolution.v27.benchmark import current

def verify_pair(parent, candidate, *, implementation_review=None):
    require(implementation_review is None, 'No runtime implementation amendments')
    validate_envelope(parent); validate_envelope(candidate)
    require(parent['provenance']['role'] == 'parent' and candidate['provenance']['role'] == 'candidate', 'Pair roles differ')
    require(parent['run_id'] != candidate['run_id'], 'Pair reuses execution identity')
    require(p.equal(parent['task'], candidate['task']), 'Pair task differs')
    if not p.equal(parent['execution']['actor'], candidate['execution']['actor']):
        accept = getattr(current().actor_adapter, 'authorized_budget_pair', None)
        require(accept is not None and accept(parent, candidate), 'Pair Actor conditions differ')
    for key in ('case_sha256', 'task_context_sha256', 'scorer'):
        require(p.equal(parent['provenance'][key], candidate['provenance'][key]), f'Pair {key} differs')
    require(p.equal(parent['execution']['initial_messages'][1:], candidate['execution']['initial_messages'][1:]), 'Paired task messages differ')


def pair_result(run):
    o = run['outcome']
    return {k: o[k] for k in ('status', 'model_rounds', 'tool_calls', 'api_requests')} | deepcopy(o['score'])


def relabel(run, ref):
    run = deepcopy(run); old = run['ref']; run['ref'] = ref
    run['initial']['ref'] = ref + ':0'; run['outcome']['ref'] = ref + ':outcome'
    for a in run['attempts']:
        a['ref'] = ref + a['ref'][len(old):]
    return validate_run(run)


