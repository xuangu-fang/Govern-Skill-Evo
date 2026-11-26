"""Idempotent launch/status and bounded, audited recovery grants. No scheduler of its own."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

if __package__:
    from .worker import folder_for, HOME, read, save, now, digest, verify_files, completed_training
else:
    from worker import folder_for, HOME, read, save, now, digest, verify_files, completed_training


def live(pid, side, phase):
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'command='], capture_output=True, text=True)
    command = result.stdout
    return result.returncode == 0 and str(Path(__file__).with_name('worker.py')) in command and f'--side {side}' in command and phase in command


def status(side, phase):
    folder = folder_for(side)
    receipt = folder / f'{phase}_launch.json'
    process = folder / f'{phase}_process.json'
    completion = folder / ('training_complete.json' if phase == 'train' else 'test_complete.json')
    row = {'side': side, 'phase': phase, 'status': 'not_started'}
    if completion.exists():
        row.update(read(completion)); return row
    if process.exists(): row.update(read(process))
    if receipt.exists():
        launched = read(receipt)
        row['pid'] = launched['pid']
        row['status'] = 'running' if live(launched['pid'], side, phase) else 'stopped'
    return row


def launch(side, phase, resume):
    schedule = read(HOME / 'schedule.json')
    if datetime.now(timezone.utc) < datetime.fromisoformat(schedule['not_before']):
        return {'side': side, 'status': 'waiting', 'not_before': schedule['not_before']}
    verify_files()
    if phase == 'test': completed_training()
    folder = folder_for(side)
    with (folder / '.launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        old = status(side, phase)
        if old['status'] in ('running', 'complete'): return old
        if old['status'] == 'stopped' and not resume:
            raise ValueError('Stopped process requires reviewed recovery and --resume')
        if old['status'] == 'not_started' and resume:
            raise ValueError('Cannot resume an unstarted process')
        argv = [sys.executable, str(Path(__file__).with_name('worker.py')), phase, '--side', side]
        if resume: argv += ['--resume']
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
        with (folder / f'{phase}.log').open('ab') as log:
            child = subprocess.Popen(argv, cwd=HOME, env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        receipt = {'pid': child.pid, 'argv': argv, 'at': now(), 'resume': resume}
        launches = folder / 'launches'; launches.mkdir(exist_ok=True)
        save(launches / f'{len(list(launches.glob("*.json")))+1:03}.json', receipt)
        save(folder / f'{phase}_launch.json', receipt)
        return {'side': side, 'phase': phase, 'status': 'launched', 'pid': child.pid}


def grant(side, kind, target):
    verify_files()
    folder = folder_for(side)
    target = Path(target).resolve()
    if not target.is_relative_to(folder / 'campaign') and not target.is_relative_to(folder / 'test'):
        raise ValueError('Recovery target must belong to this new run')
    for phase in ('train', 'test'):
        if status(side, phase)['status'] == 'running':
            raise ValueError('Do not grant or recover while the worker is running')
    config = read(folder / ('config.json' if side == 'v25' else 'shared_config.json'))
    if kind == 'actor':
        state = read(target / 'actor_state.json')
        if state.get('actor_complete') or state.get('termination') != 'generation_budget_exhausted':
            raise ValueError('Only interrupted Actor generation exhaustion is eligible')
        slot = 1 + sum(bool(a.get('execution_started')) for a in state['attempts'])
        requests = [r for r in state['requests'] if r['code_attempt'] == slot]
        base = config['actor_profile']['request_attempts_total']
        if len(requests) < base or requests[-1].get('retryable') is False:
            raise ValueError('Actor has not exhausted an eligible request budget')
        path = target / f'recovery_slot_{slot:03}.json'
        payload = {'schema': 'scheduled_extra3_v1', 'target': str(target), 'base_limit': base, 'extra': 3, 'slot': slot}
    elif kind == 'v25_stage':
        if side != 'v25' or not target.is_relative_to(folder / 'campaign/rounds'):
            raise ValueError('Not a V25 training stage')
        attempts = sorted((target / 'attempts').glob('[0-9][0-9][0-9]'))
        base = config['max_attempts']
        if len(attempts) < base or (target / 'result.json').exists() or not read(attempts[-1] / 'error.json')['retryable']:
            raise ValueError('V25 stage has not exhausted retryable requests')
        path = target / 'recovery_extra3.json'
        payload = {'schema': 'scheduled_extra3_v1', 'target': str(target), 'base_limit': base, 'extra': 3, 'slot': None}
    else:
        if side != 'skilladam' or not target.is_relative_to(folder / 'campaign/logical_calls'):
            raise ValueError('Not a SkillAdam Momentum call')
        if read(target / 'failure.json')['kind'] != 'momentum_update' or (target / 'success.json').exists():
            raise ValueError('Momentum failure evidence missing')
        signature = read(target / 'request.json')
        if signature['stage'] != 'momentum_update': raise ValueError('Wrong generation stage')
        path = target / 'grant.json'
        payload = {'schema': 'momentum_extra3_v1', 'request_sha256': digest(signature), 'extra': 3}
    # Exclusive creation: monitoring again cannot renew this failure's allowance.
    with path.open('x') as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    return {'status': 'granted_once', 'path': str(path), 'extra_requests': 3}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['status', 'launch', 'grant'])
    p.add_argument('--side', choices=['v25', 'skilladam', 'both'], default='both')
    p.add_argument('--phase', choices=['train', 'test'], default='train')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--kind', choices=['actor', 'v25_stage', 'momentum'])
    p.add_argument('--target')
    a = p.parse_args()
    if a.action == 'grant':
        if a.side == 'both' or not a.kind or not a.target: p.error('grant requires one side, kind and target')
        result = grant(a.side, a.kind, a.target)
    else:
        result = []
        for side in (('v25', 'skilladam') if a.side == 'both' else (a.side,)):
            result.append(status(side, a.phase) if a.action == 'status' else launch(side, a.phase, a.resume))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
