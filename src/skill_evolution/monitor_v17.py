"""Matched Monitor execution and exact-count Four-Delta selection. No learner input."""
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path

STATES = ('CS', 'CF', 'VS', 'VF')


class MonitorRejected(ValueError):
    pass


@dataclass(frozen=True)
class MonitorTask:
    task_id: str
    seed: int


@dataclass(frozen=True)
class MonitorInput:
    round_id: str
    tasks: tuple[MonitorTask, ...]
    parent_skill: str
    candidate_skill: str
    benchmark_config_digest: str


@dataclass(frozen=True)
class MonitorCall:
    task_id: str
    rollout_index: int
    seed: int
    role: str
    skill: str
    skill_digest: str
    benchmark_config_digest: str


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def validate_input(value):
    if not isinstance(value, MonitorInput) or not isinstance(value.tasks, tuple) or not value.tasks:
        raise MonitorRejected('nonempty MonitorInput required')
    if not isinstance(value.round_id, str) or not value.round_id.strip():
        raise MonitorRejected('round required')
    if not isinstance(value.parent_skill, str) or not isinstance(value.candidate_skill, str):
        raise MonitorRejected('Skill text required')
    h = value.benchmark_config_digest
    if not isinstance(h, str) or len(h) != 64 or any(c not in '0123456789abcdef' for c in h):
        raise MonitorRejected('benchmark/config digest required')
    ids = []
    for task in value.tasks:
        if not isinstance(task, MonitorTask) or not isinstance(task.task_id, str) or not task.task_id.strip() or type(task.seed) is not int or task.seed < 0:
            raise MonitorRejected('invalid task/seed')
        ids.append(task.task_id)
    if len(ids) != len(set(ids)):
        raise MonitorRejected('duplicate task')


def expected_calls(value):
    validate_input(value)
    for task in sorted(value.tasks, key=lambda t: t.task_id):
        for role, skill in [('PARENT', value.parent_skill), ('CANDIDATE', value.candidate_skill)]:
            yield MonitorCall(task.task_id, 1, task.seed, role, skill, digest(skill), value.benchmark_config_digest)


def summarize_monitor(value, rows):
    """Reject missing/extra/mismatched rows; incomplete observations never feed Gate."""
    expected = {(c.task_id, c.role): c for c in expected_calls(value)}
    if type(rows) is not list:
        raise MonitorRejected('rows list required')
    found = {}
    fields = {'task_id', 'rollout_index', 'seed', 'role', 'skill_digest', 'benchmark_config_digest',
              'status', 'success', 'compliant', 'initial_state_digest', 'error'}
    for row in rows:
        if type(row) is not dict or set(row) != fields:
            raise MonitorRejected('exact result fields required')
        if type(row['task_id']) is not str or type(row['role']) is not str:
            raise MonitorRejected('invalid task/role')
        key = (row['task_id'], row['role'])
        if key not in expected or key in found:
            raise MonitorRejected('unexpected or duplicate result')
        call = expected[key]
        for field in ('rollout_index', 'seed', 'skill_digest', 'benchmark_config_digest'):
            if type(row[field]) is not type(getattr(call, field)) or row[field] != getattr(call, field):
                raise MonitorRejected('result binding mismatch')
        if row['status'] == 'COMPLETE':
            h = row['initial_state_digest']
            if type(row['success']) is not bool or type(row['compliant']) is not bool or row['error'] is not None or not isinstance(h, str) or len(h) != 64 or any(c not in '0123456789abcdef' for c in h):
                raise MonitorRejected('invalid completed observation')
        elif row['status'] == 'ERROR':
            if row['success'] is not None or row['compliant'] is not None or row['initial_state_digest'] is not None or not isinstance(row['error'], str) or not row['error']:
                raise MonitorRejected('invalid error observation')
        else:
            raise MonitorRejected('invalid result status')
        found[key] = row
    if set(found) != set(expected):
        raise MonitorRejected('incomplete result manifest')
    if any(row['status'] == 'ERROR' for row in rows):
        return {'status': 'INCOMPLETE', 'decision': None, 'reason': 'execution/evaluation error'}
    for task in value.tasks:
        if found[(task.task_id, 'PARENT')]['initial_state_digest'] != found[(task.task_id, 'CANDIDATE')]['initial_state_digest']:
            return {'status': 'INCOMPLETE', 'decision': None, 'reason': 'initial state mismatch'}
    matrix = {a: {b: 0 for b in STATES} for a in STATES}
    counts = {role: {q: 0 for q in STATES} for role in ('PARENT', 'CANDIDATE')}
    for task in value.tasks:
        pair = []
        for role in counts:
            row = found[(task.task_id, role)]
            state = ('C' if row['compliant'] else 'V') + ('S' if row['success'] else 'F')
            counts[role][state] += 1
            pair.append(state)
        matrix[pair[0]][pair[1]] += 1
    metrics = {role: {'S': c['CS'] + c['VS'], 'C': c['CS'] + c['CF'], 'CS': c['CS'], 'VF': c['VF']} for role, c in counts.items()}
    delta = {k: metrics['CANDIDATE'][k] - metrics['PARENT'][k] for k in ('S', 'C', 'CS', 'VF')}
    accepted = all(delta[k] >= 0 for k in ('S', 'C', 'CS')) and delta['VF'] <= 0 and any(v != 0 for v in delta.values())
    n = len(value.tasks)
    return {'status': 'COMPLETE', 'decision': 'ACCEPT' if accepted else 'RETAIN',
            'matched_samples': n, 'quadrant_counts': counts, 'transition_counts': matrix,
            'metric_counts': metrics, 'delta_counts': delta,
            'delta_rates': {k: v / n for k, v in delta.items()}}


def run_monitor(value, *, backend, artifact_dir):
    """Backend(call) returns only labels and initial-state digest; fresh environment per call.

    Detailed audit remains on the Monitor side. Public return deliberately exposes
    only status/decision, not labels, transitions or trajectories to the learner.
    """
    calls = list(expected_calls(value))
    directory = Path(artifact_dir)
    directory.mkdir(parents=True, exist_ok=False)
    def save(name, data):
        path = directory / name
        temp = directory / (name + '.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n')
        temp.replace(path)
    save('validation.json', {'status': 'RUNNING', 'decision': None})
    save('input.json', {**asdict(value), 'tasks': [asdict(t) for t in sorted(value.tasks, key=lambda t: t.task_id)],
                        'parent_skill_digest': digest(value.parent_skill), 'candidate_skill_digest': digest(value.candidate_skill), 'rollouts_per_task': 1})
    rows = []
    for call in calls:
        row = {k: v for k, v in asdict(call).items() if k != 'skill'}
        try:
            result = backend(call)
            if type(result) is not dict or set(result) != {'success', 'compliant', 'initial_state_digest'} or type(result['success']) is not bool or type(result['compliant']) is not bool:
                raise MonitorRejected('invalid backend observation')
            h = result['initial_state_digest']
            if not isinstance(h, str) or len(h) != 64 or any(c not in '0123456789abcdef' for c in h):
                raise MonitorRejected('invalid initial-state digest')
            row.update(status='COMPLETE', error=None, **result)
        except Exception as exc:
            row.update(status='ERROR', success=None, compliant=None, initial_state_digest=None, error=type(exc).__name__)
        rows.append(row)
        save('results.json', rows)
    summary = summarize_monitor(value, rows)
    save('summary.json', summary)
    hashes = {n: hashlib.sha256((directory / n).read_bytes()).hexdigest() for n in ('input.json', 'results.json', 'summary.json')}
    public = {'status': summary['status'], 'decision': summary['decision']}
    save('validation.json', {**public, 'artifact_sha256': hashes})
    return public
