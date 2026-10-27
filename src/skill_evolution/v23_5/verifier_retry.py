"""Explicit, round-local recovery from exhausted Verifier length failures."""
import difflib
import fcntl
import hashlib
from pathlib import Path

from src.skill_evolution.v23.facts import require
from . import editor_retry, retry_401

DIRECTORY = 'amendments/verifier_retry_v1'
ALLOWED_FILES = {f'src/skill_evolution/v23_5/{name}.py' for name in
                 ('evolution', 'feedback_retry', 'verifier_retry')}


def approved_contract(root):
    root = Path(root)
    previous = editor_retry.approved_contract(root)
    folder = root/DIRECTORY
    if not folder.exists():
        return previous
    info = retry_401.read(folder/'authorization.json')
    approved = retry_401.read(folder/'contract.json')
    grant = retry_401.read(folder/'grant.json')
    require(info['previous_contract_sha256'] == retry_401.digest(previous), 'Previous Verifier source changed')
    require(info['approved_contract_sha256'] == retry_401.digest(approved), 'Approved Verifier source changed')
    require(info['config_sha256'] == retry_401.digest(retry_401.read(root/'config.json')), 'Verifier config changed')
    require(info['grant_sha256'] == retry_401.digest(grant), 'Verifier retry grant changed')
    require(grant['stage'] == 'verifier' and grant['previous_limit'] == 6 and
            grant['total_limit'] == 12 and grant['max_tokens'] == 2 * grant['previous_max_tokens'] and
            grant['timeout_seconds'] == 2 * grant['previous_timeout_seconds'], 'Invalid Verifier retry grant')
    return approved


def grant_for(root, rd, name):
    folder = Path(root)/DIRECTORY
    if not folder.exists() or name != 'verifier':
        return None
    approved_contract(root)
    grant = retry_401.read(folder/'grant.json')
    return grant if Path(rd).name == grant['round'] else None


def call_config(root, rd, name, base, path=None):
    grant = grant_for(root, rd, name)
    if grant is None:
        return base
    # Reload old evidence with its original configuration, including recovery dirs.
    if path is not None:
        number = int(Path(path).relative_to(Path(rd)/name/'attempts').parts[0])
        if number <= grant['previous_limit']:
            return base
    require(base['max_tokens'] == grant['previous_max_tokens'] and
            base['timeout_seconds'] == grant['previous_timeout_seconds'], 'Verifier base budget differs')
    return {**base, 'max_tokens': grant['max_tokens'], 'timeout_seconds': grant['timeout_seconds']}


def request_limit(root, rd, name, base):
    grant = grant_for(root, rd, name)
    if grant is None:
        return base
    require(base == grant['previous_limit'], 'Verifier base request limit differs')
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
                    ev.read(folder/'grant.json')['round'] == f'R{round_number:02}', 'Existing Verifier extension differs')
            return ev.read(folder/'authorization.json')
        cfg = ev._config(root); stop = ev.read(root/'stop.json')
        require(cfg['method'].get('knowledge_review') and cfg['max_attempts'] == 6,
                'Expected reviewed campaign with six initial attempts')
        require(stop['kind'] == 'technical' and stop['stage'] == 'verifier' and
                stop['round'] == round_number == ev.read(root/'state.json')['next_round'],
                'Extension requires the stopped Verifier round')
        ev.check_runtime(root)
        rd = root/'rounds'/f'R{round_number:02}'; stage = rd/'verifier'
        attempts = sorted(p for p in (stage/'attempts').iterdir() if p.is_dir())
        require(not (stage/'result.json').exists() and [p.name for p in attempts] ==
                [f'{i:03}' for i in range(1, 7)], 'Verifier has not exhausted exactly six attempts')
        require(all(ev.read(p/'error.json')['retryable'] for p in attempts) and
                ev.read(attempts[-1]/'error.json')['kind'] == 'truncated',
                'Verifier extension requires retryable failures ending in truncation')
        previous = editor_retry.approved_contract(root)
        changed = {p for p in previous.keys() | current.keys() if previous.get(p) != current.get(p)}
        require(changed <= ALLOWED_FILES, 'Unrelated Verifier retry source changes')
        base = ev.stage_call_config(cfg, 'verifier')
        grant = {'round': rd.name, 'stage': 'verifier', 'previous_limit': 6, 'total_limit': 12,
                 'previous_max_tokens': base['max_tokens'], 'max_tokens': base['max_tokens'] * 2,
                 'previous_timeout_seconds': base['timeout_seconds'], 'timeout_seconds': base['timeout_seconds'] * 2}
        info = {'reason': reason, 'at': ev.now(), 'grant_sha256': retry_401.digest(grant),
                'previous_contract_sha256': retry_401.digest(previous),
                'approved_contract_sha256': retry_401.digest(current), 'config_sha256': retry_401.digest(cfg),
                'state_at_authorization': ev.read(root/'state.json'), 'stop_at_authorization': stop,
                'changed_files': sorted(changed),
                'source_diff': '\n'.join(''.join(difflib.unified_diff(
                    previous.get(p, '').splitlines(True), current.get(p, '').splitlines(True),
                    fromfile='previous/'+p, tofile='approved/'+p)) for p in sorted(changed)),
                'preserved_files': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (root/'rounds').rglob('*') if p.is_file() and
                    p not in (rd/'progress.json', rd/'stop.json')}}
        ev.save(folder/'contract.json', current)
        ev.save(folder/'grant.json', grant)
        ev.save(folder/'authorization.json', info)
        return info
