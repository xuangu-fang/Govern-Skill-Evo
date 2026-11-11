#!/usr/bin/env python3
"""Launch authorized overnight jobs once; schedules are owned by the Codex app."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from alfworld_aligned_common import read, write, sha, require, configure_runtime, run_batch

PLAN = ROOT / 'experiments/baselines/overnight_20261025'
STATE = ROOT / 'artifacts/baselines/overnight_20261025'


def now():
    return datetime.now(timezone.utc).isoformat()


def config():
    return read(PLAN / 'schedule.json')


def check(target):
    lock = read(PLAN / 'manifest.json')
    for name, expected in lock['files'].items():
        require(sha(ROOT / name) == expected, f'Frozen overnight input changed: {name}')
    job = config()['jobs'][target]
    subprocess.run([job['python'], str(ROOT / job['entrypoint'])], cwd=ROOT,
                   env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, check=True)
    return job


def final_skill_for_test(training, expected_rounds=6):
    training = Path(training)
    completed = read(training / 'completion.json')
    checkpoint = read(training / 'checkpoint.json')
    require(completed['status'] == 'complete' and completed['mode'] == 'formal',
            'Formal SkillAdam training has not completed')
    require(len(completed['iterations']) == expected_rounds and
            checkpoint['next_iteration'] == expected_rounds and
            checkpoint['pending_post_decision'] is None,
            'Training or Momentum is incomplete; final Test refused')
    skill = (training / 'final_skill.md').read_text()
    require(bool(skill.strip()) and skill == checkpoint['current_skill'],
            'Final Skill differs from training checkpoint')
    return skill


def evaluate_skilladam_final(job):
    import run_skilladam_aligned as sa
    sa.check()
    training = ROOT / job['output_root']
    skill = final_skill_for_test(training)
    actor = read(sa.EXPERIMENT / 'actor.json')
    items = read(sa.EXPERIMENT / 'splits/test/items.json')
    require(len(items) == 134 and len({x['id'] for x in items}) == 134 and
            all(x['id'].startswith('test:') for x in items), 'Invalid final Test manifest')
    output = training / 'evaluation/final'
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / 'final_skill.md'
    snapshot.write_text(skill)
    write(output / 'launch.json', {'started_at': now(), 'skill_sha256': sha(snapshot),
          'source_skill': str(training / 'final_skill.md'), 'tasks': [x['id'] for x in items],
          'training_checkpoint_sha256': sha(training / 'checkpoint.json'), 'actor': actor})
    configure_runtime(actor)
    rows = run_batch(actor, items, skill, output)
    require([r['id'] for r in rows] == [x['id'] for x in items], 'Test coverage differs')
    success = sum(r['hard'] for r in rows)
    write(output / 'summary.json', {'status': 'complete', 'target': 'SkillAdam Final',
          'finished_at': now(), 'completed': len(rows), 'success': success,
          'success_rate': success / len(rows), 'skill_sha256': sha(snapshot), 'tasks': rows})


def worker(target):
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / f'{target}.worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state_path = STATE / f'{target}.state.json'
        state = {'target': target, 'status': 'running', 'stage': 'preflight',
                 'pid': os.getpid(), 'started_at': now()}
        write(state_path, state)
        try:
            job = check(target)
            state['stage'] = 'training_and_native_evaluation' if target == 'skillopt' else 'training'
            write(state_path, state)
            command = [job['python'], str(ROOT / job['entrypoint']), *job['arguments']]
            subprocess.run(command, cwd=ROOT, check=True,
                           env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1'})
            if target == 'skilladam':
                state['stage'] = 'final_test'
                write(state_path, state)
                evaluate_skilladam_final(job)
            else:
                summary = read(ROOT / job['output_root'] / 'summary.json')
                require(summary['final_test_skipped'] is True, 'Unexpected SkillOpt Final Test policy')
                require(summary['baseline_test_hard'] is not None and summary['test_hard'] is not None,
                        'SkillOpt Initial/Best Test incomplete')
            state.update(status='complete', stage='complete', finished_at=now())
            write(state_path, state)
        except BaseException as exc:
            state.update(status='stopped', finished_at=now(), error_type=type(exc).__name__)
            write(state_path, state)
            raise


def launch(target):
    job = check(target)
    require(datetime.now(timezone.utc) >= datetime.fromisoformat(job['not_before']),
            'Scheduled start time has not arrived')
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / f'{target}.launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt = STATE / f'{target}.process.json'
        if receipt.exists():
            print(json.dumps({'status': 'already_dispatched', **read(receipt)}, ensure_ascii=False))
            return
        require(not (ROOT / job['output_root']).exists(), 'Output already exists; refusing another run')
        command = [job['python'], str(Path(__file__).resolve()), target, '--worker']
        log_path = STATE / f'{target}.log'
        with log_path.open('xb') as log:
            proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1'})
        write(receipt, {'pid': proc.pid, 'started_at': now(), 'command': command,
                        'log': str(log_path), 'output_root': job['output_root']})
        # Keep this worker's machine awake while it runs, without changing power settings.
        subprocess.Popen(['/usr/bin/caffeinate', '-i', '-w', str(proc.pid)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        time.sleep(1)
        require(proc.poll() is None, f'Worker exited during launch; inspect {log_path}')
        print(json.dumps({'status': 'started', 'pid': proc.pid, 'log': str(log_path)}, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', choices=['skilladam', 'skillopt'])
    parser.add_argument('--start', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        worker(args.target)
    elif args.start:
        launch(args.target)
    else:
        check(args.target)
        print('Offline preflight passed; no experiment started.')


if __name__ == '__main__':
    main()
