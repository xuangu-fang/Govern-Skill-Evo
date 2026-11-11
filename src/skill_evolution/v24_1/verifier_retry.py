"""Explicit authorization for three additional requests in one stopped Verifier round."""
import difflib
import fcntl
import hashlib
import json
from pathlib import Path

from .facts import require
from .knowledge_review import POLICY as REVIEW_POLICY

DIRECTORY = 'amendments/verifier_retry_extra3_v1'
ALLOWED_FILES = {f'src/skill_evolution/v24_1/{name}.py' for name in
                 ('evolution', 'feedback_retry', 'verifier_retry')}


def read(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def grant_folders(root):
    root = Path(root)
    first = root/DIRECTORY
    later = sorted((root/'amendments').glob('verifier_retry_extra3_v1_R[0-9][0-9]'))
    return ([first] if first.exists() else []) + later


def approved_contract(root):
    root = Path(root)
    folders = grant_folders(root)
    allowed = {folder/name for folder in folders
               for name in ('contract.json', 'grant.json', 'authorization.json')}
    require(not list((root/'recoveries').glob('*.json')) and
            set((root/'amendments').rglob('*.json')) <= allowed,
            'V24 baseline does not permit unrecognized runtime amendments')
    previous = read(root/'contract.json')
    last_round = ''
    for folder in folders:
        info, approved, grant = (read(folder/name) for name in
                                  ('authorization.json', 'contract.json', 'grant.json'))
        require(info['previous_contract_sha256'] == digest(previous), 'Previous Verifier source changed')
        require(info['approved_contract_sha256'] == digest(approved), 'Approved Verifier source changed')
        require(info['config_sha256'] == digest(read(root/'config.json')), 'Verifier config changed')
        require(info['grant_sha256'] == digest(grant), 'Verifier retry grant changed')
        require(grant['stage'] == 'verifier' and grant['previous_limit'] == 6 and
                grant['total_limit'] == 9, 'Invalid Verifier retry grant')
        require(grant['round'] > last_round and
                (folder == root/DIRECTORY or folder.name == Path(DIRECTORY).name + '_' + grant['round']),
                'Verifier grants must name distinct ordered rounds')
        changed = {p for p in previous.keys() | approved.keys() if previous.get(p) != approved.get(p)}
        require(changed <= ALLOWED_FILES, 'Unrelated Verifier retry source changes')
        previous, last_round = approved, grant['round']
    return previous


def request_limit(root, rd, name, base):
    folders = grant_folders(root)
    if not folders or name != 'verifier':
        return base
    approved_contract(root)
    for folder in folders:
        grant = read(folder/'grant.json')
        if Path(rd).resolve() == (Path(root)/'rounds'/grant['round']).resolve():
            require(base == grant['previous_limit'], 'Verifier base request limit differs')
            return grant['total_limit']
    return base


def enable(campaign, *, round_number, reason):
    from . import evolution as ev
    root = Path(campaign).resolve()
    require(type(round_number) is int and round_number > 0 and bool(reason.strip()),
            'Explicit round and authorization reason required')
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = ev.frozen_contract()
        previous = approved_contract(root)
        folders = grant_folders(root)
        rid = f'R{round_number:02}'
        for existing in folders:
            if read(existing/'grant.json')['round'] == rid:
                require(previous == current, 'Existing Verifier extension differs')
                return read(existing/'authorization.json')
        require(not folders or read(folders[-1]/'grant.json')['round'] < rid,
                'New Verifier grant must follow earlier rounds')
        folder = root/(DIRECTORY + '_' + rid) if folders else root/DIRECTORY
        cfg = ev._config(root)
        stop, state = read(root/'stop.json'), read(root/'state.json')
        require(cfg['method'].get('knowledge_review') == REVIEW_POLICY and cfg['max_attempts'] == 6,
                'Expected reviewed campaign with six initial attempts')
        require(stop['kind'] == 'technical' and stop['stage'] == 'verifier' and
                stop['round'] == round_number == state['next_round'],
                'Extension requires the stopped Verifier round')
        ev.check_runtime(root)
        rd = root/'rounds'/f'R{round_number:02}'
        stage = rd/'verifier'
        attempts = sorted(p for p in (stage/'attempts').iterdir() if p.is_dir())
        require(not (stage/'result.json').exists() and [p.name for p in attempts] ==
                [f'{i:03}' for i in range(1, 7)], 'Verifier has not exhausted exactly six attempts')
        require(all(read(p/'error.json')['retryable'] for p in attempts) and
                read(attempts[-1]/'error.json')['kind'] == 'truncated',
                'Verifier extension requires retryable failures ending in truncation')
        changed = {p for p in previous.keys() | current.keys() if previous.get(p) != current.get(p)}
        require(changed <= ALLOWED_FILES, 'Unrelated Verifier retry source changes')
        grant = {'round': rd.name, 'stage': 'verifier', 'previous_limit': 6, 'total_limit': 9}
        info = {'reason': reason, 'at': ev.now(), 'grant_sha256': digest(grant),
                'previous_contract_sha256': digest(previous), 'approved_contract_sha256': digest(current),
                'config_sha256': digest(cfg), 'state_at_authorization': state, 'stop_at_authorization': stop,
                'call_config_unchanged': ev.stage_call_config(cfg, 'verifier'),
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
