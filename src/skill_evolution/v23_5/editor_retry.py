"""Explicit one-round Editor retry extension; no implicit reset on resume."""
import difflib
import fcntl
import hashlib
from pathlib import Path

from src.skill_evolution.v23.facts import require
from . import retry_401

DIRECTORY = 'amendments/editor_retry_v1'
ALLOWED_FILES = {f'src/skill_evolution/v23_5/{name}.py' for name in
                 ('evolution', 'feedback_retry', 'retry_401', 'editor_retry')}


def approved_contract(root):
    root = Path(root)
    previous = retry_401.approved_contract(root)
    folder = root/DIRECTORY
    if not folder.exists():
        return previous
    info = retry_401.read(folder/'authorization.json')
    approved = retry_401.read(folder/'contract.json')
    require(info['previous_contract_sha256'] == retry_401.digest(previous), 'Previous retry source changed')
    require(info['approved_contract_sha256'] == retry_401.digest(approved), 'Editor retry source changed')
    require(info['config_sha256'] == retry_401.digest(retry_401.read(root/'config.json')), 'Editor retry config changed')
    grant = retry_401.read(folder/'grant.json')
    require(info['grant_sha256'] == retry_401.digest(grant), 'Editor retry grant changed')
    require(grant['stage'] == 'editor' and grant['previous_limit'] == 6 and
            grant['additional_requests'] == 6 and grant['total_limit'] == 12,
            'Unsupported Editor retry grant')
    return approved


def request_limit(root, rd, name, base):
    folder = Path(root)/DIRECTORY
    if not folder.exists():
        return base
    approved_contract(root)
    grant = retry_401.read(folder/'grant.json')
    if Path(rd).name != grant['round'] or name != grant['stage']:
        return base
    require(base == grant['previous_limit'], 'Editor base request budget differs')
    return grant['total_limit']


def enable(campaign, *, round_number, reason):
    from . import evolution as ev
    root = Path(campaign).resolve(); folder = root/DIRECTORY
    require(type(round_number) is int and round_number > 0 and bool(reason.strip()),
            'Explicit round and authorization reason required')
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = ev.frozen_contract()
        if folder.exists():
            require(approved_contract(root) == current and
                    ev.read(folder/'grant.json')['round'] == f'R{round_number:02}',
                    'Existing Editor extension differs')
            return ev.read(folder/'authorization.json')
        stop = ev.read(root/'stop.json'); cfg = ev._config(root)
        require(not cfg['method'].get('knowledge_review'),
                'Knowledge review campaigns use the fixed shared request budget; extensions are not supported')
        require(stop['kind'] == 'technical' and stop['round'] == round_number and stop['stage'] == 'editor'
                and ev.read(root/'state.json')['next_round'] == round_number,
                'Extension requires the stopped Editor round')
        require(cfg['max_attempts'] == 6, 'Expected six initial attempts')
        ev.check_runtime(root)
        stage = root/'rounds'/f'R{round_number:02}'/'editor'
        attempts = sorted(p for p in (stage/'attempts').iterdir() if p.is_dir())
        require(not (stage/'result.json').exists() and [p.name for p in attempts] ==
                [f'{i:03}' for i in range(1, 7)], 'Editor has not exhausted exactly six attempts')
        require(all(ev.read(p/'run.json')['status'] == 'invalid' and
                    ev.read(p/'error.json')['retryable'] for p in attempts),
                'Editor extension requires retryable failed attempts')
        previous = retry_401.approved_contract(root)
        changed = {p for p in previous.keys() | current.keys() if previous.get(p) != current.get(p)}
        require(changed <= ALLOWED_FILES, 'Unrelated Editor retry source changes')
        grant = {'round': f'R{round_number:02}', 'stage': 'editor', 'previous_limit': 6,
                 'additional_requests': 6, 'total_limit': 12}
        info = {'reason': reason, 'at': ev.now(), 'grant_sha256': retry_401.digest(grant),
                'previous_contract_sha256': retry_401.digest(previous),
                'approved_contract_sha256': retry_401.digest(current), 'config_sha256': retry_401.digest(cfg),
                'stop_at_authorization': stop, 'changed_files': sorted(changed),
                'source_diff': '\n'.join(''.join(difflib.unified_diff(
                    previous.get(p, '').splitlines(True), current.get(p, '').splitlines(True),
                    fromfile='previous/'+p, tofile='approved/'+p)) for p in sorted(changed)),
                'preserved_attempt_files': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for attempt in attempts for p in attempt.rglob('*') if p.is_file()}}
        ev.save(folder/'contract.json', current)
        ev.save(folder/'grant.json', grant)
        ev.save(folder/'authorization.json', info)
        return info
