"""Audited HTTP-401 retry amendment; original snapshots remain immutable."""
import difflib
import fcntl
import hashlib
import json
from pathlib import Path

from src.skill_evolution.v23.facts import require

DIRECTORY = 'amendments/http_401_retry_v1'
POLICY = {'version': 'http_401_retry_v1', 'http_status': 401,
          'max_total_attempts': 6, 'max_retries': 5,
          'scope': 'strict_actor_step_and_v23_5_module_call',
          'budget': 'shared_with_other_retryable_errors'}
ACTOR = 'src/adapters/alfworld/run_task_upstream.py'
OLD = 'transient = response.status_code in {429, 500, 502, 503, 504}'
NEW = OLD + ' or (strict_response and response.status_code == 401)'
ALLOWED_FILES = {ACTOR, 'src/adapters/alfworld/verify_skill_run.py', 'src/skill_evolution/v23_5/evolution.py',
                 'src/skill_evolution/v23_5/retry_401.py'}


def read(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def approved_contract(root):
    root = Path(root)
    original = read(root/'contract.json')
    directory = root/DIRECTORY
    if not directory.exists():
        return original
    info = read(directory/'authorization.json')
    approved = read(directory/'contract.json')
    require(info['policy'] == POLICY, 'HTTP 401 retry policy changed')
    require(info['original_contract_sha256'] == digest(original), 'Original source snapshot changed')
    require(info['approved_contract_sha256'] == digest(approved), 'Approved HTTP 401 source changed')
    require(info['config_sha256'] == digest(read(root/'config.json')), 'Original retry config changed')
    return approved


def enable(campaign, *, reason):
    from . import evolution as ev
    root = Path(campaign).resolve()
    require(bool(reason.strip()), 'Explicit authorization reason required')
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = ev.frozen_contract()
        if (root/DIRECTORY).exists():
            require(approved_contract(root) == current, 'Approved HTTP 401 source differs')
            return read(root/DIRECTORY/'authorization.json')
        require((root/'stop.json').exists() and read(root/'stop.json')['kind'] == 'technical',
                'HTTP 401 amendment requires a technically stopped Campaign')
        require(not list((root/'recoveries').glob('*.json')) and
                not (root/ev.output_budget.DIRECTORY).exists(), 'Cannot combine recovery policies')
        cfg = ev._config(root)
        require(cfg['max_attempts'] == cfg['actor_request_attempts'] == 6,
                'Five retries requires six frozen total attempts')
        ev.check_runtime(root)
        original = read(root/'contract.json')
        changed = {p for p in original.keys() | current.keys() if original.get(p) != current.get(p)}
        require(ACTOR in changed and changed <= ALLOWED_FILES, 'Unrelated HTTP 401 amendment source changes')
        require(original[ACTOR].count(OLD) == 1 and NEW not in original[ACTOR] and
                current[ACTOR] == original[ACTOR].replace(OLD, NEW),
                'Actor amendment must only add strict HTTP 401 retries')
        info = {'policy': POLICY, 'reason': reason, 'at': ev.now(),
                'original_contract_sha256': digest(original), 'approved_contract_sha256': digest(current),
                'config_sha256': digest(cfg), 'state_at_authorization': read(root/'state.json'),
                'stop_at_authorization': read(root/'stop.json'), 'changed_files': sorted(changed),
                'source_diff': '\n'.join(''.join(difflib.unified_diff(
                    original.get(p, '').splitlines(True), current.get(p, '').splitlines(True),
                    fromfile='original/'+p, tofile='approved/'+p)) for p in sorted(changed))}
        ev.save(root/DIRECTORY/'contract.json', current)
        ev.save(root/DIRECTORY/'authorization.json', info)
        return info


def implementation_review(root, parents, candidates):
    """Permit only exact old/new Actor hashes, including retained old/old pairs."""
    from . import evolution as ev
    require(len(parents) == len(candidates), 'Actor pair count differs')
    pairs = [(p['implementation']['files'], q['implementation']['files']) for p, q in zip(parents, candidates)]
    if all(a == b for a, b in pairs):
        return None
    root = Path(root)
    require((root/DIRECTORY/'authorization.json').exists(), 'Actor change requires HTTP 401 authorization')
    approved = approved_contract(root)
    ev._check_contract(root)
    original = read(root/'contract.json')
    def hashes(contract):
        return {n: hashlib.sha256(contract['src/adapters/alfworld/'+n].encode()).hexdigest()
                for n in ('run_task_skill.py', 'skill_runtime.py', 'run_task_upstream.py', 'run_task.py')}
    old, new = hashes(original), hashes(approved)
    require(all((a == old and b in (old, new)) or (a == new and b == new) for a, b in pairs),
            'Actor pair not covered by HTTP 401 amendment')
    return {'parent_files': old, 'candidate_files': new,
            'reason': 'User-authorized HTTP 401 retries within the existing six-attempt limit. '
                      'Completed old-policy episodes are reused; the interrupted episode is restarted. '
                      'Only HTTP error handling differs; this is an execution-condition difference.',
            'diff': read(root/DIRECTORY/'authorization.json')['source_diff']}
