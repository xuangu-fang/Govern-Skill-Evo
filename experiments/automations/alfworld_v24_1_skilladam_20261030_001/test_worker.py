"""One-shot detached final Test supervisor, with both-training and time barriers."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import execution_dir, frozen_file, load_plan
sys.path.insert(0, str(HERE))
from evaluate_skilladam import completed_skill


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def barrier():
    plan = load_plan(HERE / 'plan.json')
    deadline = datetime.fromisoformat(read(HERE / 'test_start_condition.json')[
        'both_training_finished_before_utc'].replace('Z', '+00:00'))
    times = {}
    for name, job in plan['jobs'].items():
        state = read(execution_dir(name) / (name + '.state.json'))
        if state['status'] != 'process_exited' or state.get('exit_code') != 0:
            raise ValueError(name + ' training has not successfully exited')
        finished = datetime.fromisoformat(state['finished_at'])
        if finished >= deadline:
            raise ValueError(name + ' training completed after the authorized deadline')
        times[name] = state['finished_at']
    for path, expected in plan['frozen_inputs_sha256'].items():
        if hashlib.sha256(frozen_file(path).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen input changed: ' + path)
    completed_skill(plan)
    v = ROOT / plan['jobs']['v24_1']['experiment'] / 'data/test.json'
    s = ROOT / plan['jobs']['skilladam']['experiment'] / 'splits/test/items.json'
    if read(v) != read(s) or len(read(v)) != 134:
        raise ValueError('Test task sets differ')
    return plan, times


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', choices=['v24_1', 'skilladam'])
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    folder = execution_dir(args.job, test=True)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / (args.job + '.test.dispatch.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | (0 if args.worker else fcntl.LOCK_NB))
        plan, times = barrier()
        job = plan['jobs'][args.job]
        output = ROOT / job['test_output']
        receipt = folder / (args.job + '.test.process.json')
        state_path = folder / (args.job + '.test.state.json')
        if output.exists() or state_path.exists():
            raise ValueError('Test already exists; no automatic repeat')
        if not args.launch and not args.worker:
            print(json.dumps({'status': 'ready', 'training_finished_at': times, 'model_requests': 0}))
            return
        if args.worker:
            state = {'job': args.job, 'status': 'starting', 'supervisor_pid': os.getpid(),
                     'started_at': datetime.now(timezone.utc).isoformat(),
                     'command': job['test_command'], 'training_finished_at': times,
                     'output': str(output)}
            save(state_path, state)
            try:
                proc = subprocess.Popen(job['test_command'], cwd=ROOT, stdin=subprocess.DEVNULL)
                state.update(status='running', pid=proc.pid)
                save(state_path, state)
                code = proc.wait()
                state.update(status='process_exited', exit_code=code,
                             finished_at=datetime.now(timezone.utc).isoformat())
                save(state_path, state)
            except BaseException as exc:
                state.update(status='supervisor_failed', error_type=type(exc).__name__)
                save(state_path, state)
                raise
            return
        if receipt.exists():
            raise ValueError('Test already dispatched')
        command = [sys.executable, str(Path(__file__).resolve()), args.job, '--worker']
        log = folder / (args.job + '.test.log')
        with log.open('xb') as handle:
            proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=handle,
                stderr=subprocess.STDOUT, start_new_session=True,
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1'})
        record = {'pid': proc.pid, 'command': command, 'log': str(log),
                  'dispatched_at': datetime.now(timezone.utc).isoformat()}
        save(receipt, record)
        awake = subprocess.Popen(['/usr/bin/caffeinate', '-i', '-w', str(proc.pid)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        record['caffeinate_pid'] = awake.pid
        save(receipt, record)
        print(json.dumps(record))


if __name__ == '__main__':
    main()
