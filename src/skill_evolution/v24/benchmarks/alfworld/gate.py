from src.skill_evolution.v24.benchmark import current as benchmark_current
from src.skill_evolution.v24.facts import build_facts, require
from src.skill_evolution.v24.storage import validate_skill
from src.skill_evolution.v24.contracts.replay import verify_pair
from src.skill_evolution.v24.contracts.gate import validate_input

def build_gate(parent_records, candidate_records, frozen_tasks, *, parent_skill,
               candidate_skill, implementation_review=None):
    """Audit raw executions with existing facts/pair checks, then expose only results.

    This entry point also supports future Validation batches independently of the
    Editor's training lineage. Skill texts must come from the frozen experiment.
    """
    p, q = build_facts(parent_records), build_facts(candidate_records)
    require(p['facts']['parent'] == parent_skill, 'Executed Parent differs')
    require(q['facts']['parent'] == candidate_skill, 'Executed Candidate differs')
    require(p['background'] == q['background'], 'Actor background differs')
    require({r['task']['id'] for r in parent_records} ==
            {r['task']['id'] for r in candidate_records} == set(frozen_tasks),
            'Incomplete or mismatched frozen task set')
    by_task = {r['task']['id']: (r, f) for r, f in zip(candidate_records, q['facts']['runs'])}
    payload, audit = {'pairs': []}, []
    for parent, pf in zip(parent_records, p['facts']['runs']):
        candidate, qf = by_task[parent['task']['id']]
        verify_pair(parent, candidate, implementation_review=implementation_review)
        pair = {'task_id': parent['task']['id']}
        row = {'task_id': parent['task']['id'], 'verified': True}
        for side, raw, fact in (('parent', parent, pf), ('candidate', candidate, qf)):
            validate_skill(raw['skill'])
            require(benchmark_current().is_complete(raw), f'{side} {raw["run_id"]}: incomplete/technical outcome')
            require(not raw.get('error_type') and not raw.get('error_stage'), 'Recorded technical failure')
            if 'won' in raw:
                require(type(raw['won']) is bool, 'Invalid raw environment success')
            pair[side] = {'run_id': raw['run_id'], 'success': fact['outcome']['success']}
            row[side] = {**pair[side], 'termination': fact['outcome']['end_reason'],
                         'steps': len(fact['steps'])}
        payload['pairs'].append(pair); audit.append(row)
    validate_input(payload, frozen_tasks)
    return {'input': payload, 'audit': audit}
