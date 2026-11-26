from ..benchmark import current as benchmark_current

from .diagnosis import fields

from ..facts import require, text


def validate_input(payload, frozen_tasks):
    fields(payload, ('pairs',), 'Gate input')
    require(isinstance(frozen_tasks, list) and bool(frozen_tasks), 'Missing frozen tasks')
    for task in frozen_tasks:
        text(task, 'frozen task')
    require(len(set(frozen_tasks)) == len(frozen_tasks), 'Duplicate frozen task')
    require(isinstance(payload['pairs'], list) and bool(payload['pairs']), 'Empty Gate pairs')
    tasks, identities = set(), set()
    for pair in payload['pairs']:
        fields(pair, ('task_id', 'parent', 'candidate'), 'Gate pair')
        tid = text(pair['task_id'], 'task_id')
        require(tid not in tasks, 'Duplicate task'); tasks.add(tid)
        for side in ('parent', 'candidate'):
            fields(pair[side], ('run_id', 'success'), side)
            rid = text(pair[side]['run_id'], 'run_id')
            require(rid not in identities, 'Duplicate execution'); identities.add(rid)
            require(type(pair[side]['success']) is bool, 'Success must be an environment boolean')
    require(tasks == set(frozen_tasks), 'Gate tasks differ from frozen task set')
    return payload


def decide_gate(payload, frozen_tasks):
    """Pure decision over verified results; callers must establish provenance first."""
    validate_input(payload, frozen_tasks)
    p = sum(pair['parent']['success'] for pair in payload['pairs'])
    q = sum(pair['candidate']['success'] for pair in payload['pairs'])
    return {'decision': 'ACCEPT' if q > p else 'RETAIN',
            'parent_success': p, 'candidate_success': q, 'compared': len(payload['pairs'])}


def build_gate(*args, **kwargs):
    return benchmark_current().build_gate(*args, **kwargs)


RULE = 'ACCEPT iff candidate_success > parent_success; otherwise RETAIN'
