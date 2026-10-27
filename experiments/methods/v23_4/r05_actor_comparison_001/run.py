"""Paired fresh R05 rollouts with immutable Skills and bounded technical restarts."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time

from experiments.methods.v23_4.archive_io import archive_glob, resolve, runtime_root
from src.skill_evolution.v23 import evolution as ev
from src.adapters.alfworld.run_task import SPLIT_ROOT

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
UPSTREAM = HERE.with_name('semantic_generation_007')
HISTORY = ROOT / 'artifacts/methods/v23/v23_alfworld_formal_001/S1'
COMPLETE = {'success', 'environment_ended', 'step_limit'}


def read(path):
    return json.loads(resolve(path).read_text())


def sha(path):
    return hashlib.sha256(resolve(path).read_bytes()).hexdigest()


def save(path, value):
    path = resolve(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def verify():
    frozen = read(HERE / 'config/freeze.json')
    for path, digest in frozen['sha256'].items():
        assert sha(path) == digest, path
    cfg = read(HERE / 'config/actor.json')
    ev.check_environment_route(cfg)
    return cfg


def prepare():
    old_freeze = read(UPSTREAM / 'config/freeze.json')
    hashes = {str(ROOT / p): h for p, h in old_freeze['sha256'].items()}
    for path, digest in hashes.items():
        assert sha(path) == digest, path
    material = read(UPSTREAM / 'config/material.json')
    attempt = UPSTREAM / 'runs/R05_editor/attempt_001'
    assert read(UPSTREAM / 'runs/R05_editor/selected.json')['attempt'] == 1
    from src.skill_evolution.v23 import editor
    from src.skill_evolution.v22.diagnosis_editor import parse_json_response
    response = read(attempt / 'response.json')
    parsed = parse_json_response(response['content'])
    assert response['finish_reason'] == 'stop' and parsed == read(attempt / 'parsed.json')
    status, candidate = editor.validate_editor(parsed, material['parent'])
    assert status == 'candidate' and candidate == (attempt / 'candidate.md').read_text()
    assert editor.actual_diff(material['parent'], candidate) == (attempt / 'actual.diff').read_text()
    old = ev._config(HISTORY)
    rd = read(HISTORY / 'rounds/R05/round_input.json')
    assert rd['parent'] == material['parent']
    tasks = rd['tasks']
    assert tasks == [f'val:{n:04}' for n in range(1, 11)]
    cfg = ev.configuration_from_environment(old)
    cfg['task_items'] = {t: old['task_items'][t] for t in tasks}
    games = [Path(cfg['environment_root']) / item['gamefile'] for item in cfg['task_items'].values()]
    cfg['environment_files'] = {str(p): old['environment_files'][str(p)] for p in games}
    assert cfg['actor_max_workers'] == 8 and cfg['max_steps'] == 50 and cfg['actor_request_attempts'] == 3
    for path, content in cfg['environment_files'].items():
        assert Path(path).read_bytes().decode('utf-8') == content
    (HERE / 'config').mkdir(parents=True, exist_ok=True)
    for name, value in [('parent', material['parent']), ('candidate', candidate)]:
        with (HERE / f'config/{name}.md').open('x') as f:
            f.write(value)
    save(HERE / 'config/actor.json', cfg)
    save(HERE / 'config/plan.json', {
        'tasks': tasks, 'arms': ['parent', 'candidate'], 'workers': 8,
        'max_task_restarts': 3, 'max_episodes': 80, 'max_steps_per_episode': 50,
        'request_attempts_per_step': 3, 'historical_actor_model': old['actor_model'],
        'historical_actor_base_url': old['actor_base_url'],
        'current_actor_model': cfg['actor_model'], 'current_actor_base_url': cfg['actor_base_url'],
        'scope': 'Ten development tasks, fresh paired rollouts; no Test evaluation or adoption.',
        'upstream': str(attempt), 'created_at': ev.now()})
    paths = [HERE / 'run.py', HERE / 'PROTOCOL.md', *HERE.glob('config/*'),
             *archive_glob(attempt, '*.json'), attempt / 'candidate.md', attempt / 'actual.diff',
             UPSTREAM / 'config/freeze.json', UPSTREAM / 'runs/R05_editor/selected.json',
             HISTORY / 'rounds/R05/round_input.json', SPLIT_ROOT / 'val/items.json', *games]
    paths += list((ROOT / 'src/adapters/alfworld').glob('*.py'))
    paths += list((SPLIT_ROOT / 'protocol/skillopt_native').glob('*'))
    hashes.update({str(p.resolve()): sha(p) for p in paths if p.is_file()})
    save(HERE / 'config/freeze.json', {'at': ev.now(), 'sha256': hashes})
    verify()
    print('Frozen ten paired tasks, two Skills, same Actor settings, eight workers.', flush=True)


def retryable(record):
    if record['status'] in COMPLETE:
        return False
    if record.get('error_stage') in {'environment_setup', 'reset', 'environment_step'}:
        return True
    if record.get('error_stage') != 'model_request':
        return False
    attempts = [a for s in record.get('steps', []) for a in s.get('transport_attempts', [])]
    last = attempts[-1] if attempts else {}
    code = last.get('http_status')
    if code in {408, 429, 500, 502, 503, 504}:
        return True
    return code is None or (200 <= code < 300 and record.get('error_type') in {'ValueError', 'KeyError', 'IndexError', 'TypeError'})


def one(arm, task, cfg, runner=ev.actor_task):
    folder = runtime_root(HERE) / 'runs' / arm / task.replace(':', '_')
    folder.mkdir(parents=True, exist_ok=True)
    if resolve(folder / 'selected.json').exists():
        return read(folder / 'selected.json')
    for number in range(1, 5):
        dest = folder / f'attempt_{number:03}'
        marker = dest / 'attempt.json'
        if resolve(marker).exists():
            prior = read(marker)
            if prior['complete']:
                save(folder / 'selected.json', prior)
                return prior
            if not prior['retryable']:
                return prior
            continue
        if resolve(dest).exists():
            raise RuntimeError('Interrupted attempt requires explicit inspection before continuing')
        verify()
        dest.mkdir()
        print('START', arm, task, number, flush=True)
        save(dest / 'started.json', {'at': ev.now(), 'attempt': number})
        began = time.monotonic()
        try:
            path = Path(runner(task, HERE / f'config/{arm}.md', dest, cfg))
            record = read(path)
            assert record['task'] == cfg['task_items'][task]
            assert record['skill']['text'] == (HERE / f'config/{arm}.md').read_text()
            outcome = {'arm': arm, 'task': task, 'attempt': number, 'trajectory': str(path),
                       'status': record['status'], 'won': record['won'],
                       'steps': sum(s['phase'] == 'executed' for s in record['steps']),
                       'complete': record['status'] in COMPLETE, 'retryable': retryable(record)}
        except (OSError, ValueError) as exc:
            # Preserve process artifacts; never hide a valid rollout behind a retry.
            found = list(dest.rglob('trajectory.json'))
            if found and read(found[0]).get('status') in COMPLETE:
                raise
            outcome = {'arm': arm, 'task': task, 'attempt': number, 'status': 'process_error',
                       'complete': False, 'retryable': True, 'error_type': type(exc).__name__}
        outcome.update(finished_at=ev.now(), elapsed_seconds=round(time.monotonic()-began, 3))
        save(marker, outcome)
        print('END', arm, task, number, outcome['status'], outcome.get('steps'), flush=True)
        if outcome['complete']:
            save(folder / 'selected.json', outcome)
            return outcome
        if not outcome['retryable']:
            return outcome
        if number < 4:
            time.sleep((15, 30, 60)[number-1])
    return read(folder / 'attempt_004/attempt.json')


def run():
    cfg = verify()
    plan = read(HERE / 'config/plan.json')
    with (runtime_root(HERE) / 'live.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with ThreadPoolExecutor(max_workers=plan['workers']) as pool:
            futures = [pool.submit(one, arm, task, cfg) for task in plan['tasks'] for arm in plan['arms']]
            outcomes = [f.result() for f in as_completed(futures)]
        save(HERE / 'completion.json', {'at': ev.now(), 'outcomes': outcomes})
    print('Finished', len(outcomes), 'jobs;', sum(r['complete'] for r in outcomes), 'complete episodes', flush=True)


if __name__ == '__main__':
    assert sys.argv[1:] in [['prepare'], ['run']]
    prepare() if sys.argv[1] == 'prepare' else run()
