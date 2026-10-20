"""Deterministic success-count Gate. No model, environment or promotion writes."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import validate_skill, write_record
from .diagnosis import fields
from .facts import build_facts, COMPLETE, require, text
from .replay import build_replay, verify_pair

RULE = 'ACCEPT iff candidate_success > parent_success; otherwise RETAIN'


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
            require(raw['status'] in COMPLETE, f'{side} {raw["run_id"]}: incomplete/technical outcome')
            require(not raw.get('error_type') and not raw.get('error_stage'), 'Recorded technical failure')
            if 'won' in raw:
                require(type(raw['won']) is bool, 'Invalid raw environment success')
            pair[side] = {'run_id': raw['run_id'], 'success': fact['outcome']['success']}
            row[side] = {**pair[side], 'termination': fact['outcome']['end_reason'],
                         'steps': len(fact['steps'])}
        payload['pairs'].append(pair); audit.append(row)
    validate_input(payload, frozen_tasks)
    return {'input': payload, 'audit': audit}


def _read(path):
    return json.loads(Path(path).read_text())


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assemble_gate(replay_directory, tasks_file):
    """Read paired archive and raw trajectories; Replay LLM output is not needed.

    tasks_file is an independent frozen JSON list, or the existing experiment
    plan with candidate_tasks. Never infer the intended set from available runs.
    """
    replay_directory, tasks_file = Path(replay_directory).resolve(), Path(tasks_file).resolve()
    frozen = _read(tasks_file)
    tasks = frozen['candidate_tasks'] if isinstance(frozen, dict) else frozen
    saved = _read(replay_directory/'input.json')
    paths = {side: [Path(p).resolve() for p in saved['record_paths'][side]]
             for side in ('parent', 'candidate')}
    records = {side: [_read(p) for p in ps] for side, ps in paths.items()}
    review = saved['pair_audit'][0]['implementation_review']
    # Rebuild and compare the original verified facts, not the learned entries.
    rebuilt = build_replay(saved['editor_directory'], records['parent'], records['candidate'],
                           memory=saved['payload']['memory'], implementation_review=review)
    require(rebuilt == {k: v for k, v in saved.items() if k != 'record_paths'},
            'Paired archive differs from original execution sources')
    assembled = build_gate(records['parent'], records['candidate'], tasks,
                          parent_skill=saved['payload']['parent'], candidate_skill=saved['candidate'],
                          implementation_review=review)
    files = [replay_directory/'input.json', tasks_file, *paths['parent'], *paths['candidate']]
    files += [p.resolve() for p in Path(saved['editor_directory']).rglob('*') if p.is_file()]
    sources = {str(p): _hash(p) for p in sorted(set(files))}
    return {**assembled, 'frozen_tasks': deepcopy(tasks), 'sources': sources,
            'origin': {'replay_directory': str(replay_directory), 'tasks_file': str(tasks_file)},
            'rule': RULE}


def load_gate(directory, *, expected_bundle=None):
    """Recheck source integrity and saved contract without executing decide_gate."""
    saved = _read(Path(directory)/'gate.json')
    fields(saved, ('bundle', 'result', 'created_at'), 'Gate archive')
    bundle, result = saved['bundle'], saved['result']
    actual = assemble_gate(**bundle['origin'])
    require(actual == bundle, 'Gate sources/input/rule changed')
    if expected_bundle is not None:
        require(bundle == expected_bundle, 'Gate archive conflicts with requested sources/input')
    fields(result, ('decision', 'parent_success', 'candidate_success', 'compared'), 'Gate result')
    for key in ('parent_success', 'candidate_success', 'compared'):
        require(type(result[key]) is int, 'Invalid Gate count')
    # Contract verification, not a second invocation of the decision entry point.
    pairs = bundle['input']['pairs']
    require(result['compared'] == len(pairs), 'Compared count differs')
    for side in ('parent', 'candidate'):
        require(result[side+'_success'] == sum(p[side]['success'] for p in pairs), 'Success count differs')
    require(result['decision'] == ('ACCEPT' if result['candidate_success'] > result['parent_success']
                                  else 'RETAIN'), 'Decision differs from rule')
    return saved


def run_gate(replay_directory, tasks_file, output_directory):
    """Atomically save a valid result, or record a technical stop with no decision."""
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        bundle = assemble_gate(replay_directory, tasks_file)
        if (directory/'gate.json').exists():
            saved = load_gate(directory, expected_bundle=bundle)
            return {**saved, 'reused': True}
        saved = {'bundle': bundle, 'result': decide_gate(bundle['input'], bundle['frozen_tasks']),
                 'created_at': datetime.now(timezone.utc).isoformat()}
        write_record(directory/'gate.json', saved)
        return {**saved, 'reused': False}
    except (ValueError, KeyError, TypeError, OSError) as exc:
        write_record(directory/'failure.json', {'error_type': type(exc).__name__, 'error': str(exc),
            'replay_directory': str(replay_directory), 'tasks_file': str(tasks_file),
            'created_at': datetime.now(timezone.utc).isoformat()})
        raise


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay-directory', required=True)
    parser.add_argument('--tasks-file', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    saved = run_gate(**vars(args))
    print(json.dumps({'result': saved['result'], 'reused': saved['reused']}, indent=2))


if __name__ == '__main__':
    main()
