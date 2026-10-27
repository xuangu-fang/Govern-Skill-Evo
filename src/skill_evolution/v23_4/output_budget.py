"""Explicit, audited opt-in to request-local truncation recovery.

Original Campaign configuration, contracts and completed records remain immutable.
Only six consecutive length responses at one budget permit doubling that budget.
"""
from copy import deepcopy
import difflib
import hashlib
import json
from pathlib import Path

from src.skill_evolution.v23.facts import require

POLICY = {'version': 'length_retry_double_v1', 'initial_max_tokens': 16384,
          'length_attempts_per_budget': 6, 'multiplier': 2,
          'scope': 'module_call_and_actor_step', 'other_error_attempts': 3}
DIRECTORY = 'amendments/output_budget_v1'
ALLOWED_FILES = {
    'src/skill_evolution/v23_4/output_budget.py',
    'src/skill_evolution/v23_4/budget_actor.py',
    'src/skill_evolution/v23_4/evolution.py',
    'src/skill_evolution/v23_4/evaluation.py',
    'src/skill_evolution/v23_4/benchmark.py',
    'src/adapters/alfworld/run_task_skill.py',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def amendment(root):
    path = Path(root)/DIRECTORY/'authorization.json'
    if not path.exists():
        return None
    value = read(path)
    require(value['policy'] == POLICY, 'Output budget policy changed')
    require(value['original_contract_sha256'] == digest(read(Path(root)/'contract.json')),
            'Original contract changed after budget amendment')
    approved = read(path.parent/'contract.json')
    require(value['approved_contract_sha256'] == digest(approved), 'Approved recovery source changed')
    require(value['config_sha256'] == digest(read(Path(root)/'config.json')),
            'Original configuration changed after budget amendment')
    return value


def enable(root, current_contract, *, reason):
    from . import evolution as ev
    root = Path(root)
    if amendment(root):
        require(read(root/DIRECTORY/'contract.json') == current_contract, 'Recovery source changed')
        return amendment(root)
    original = read(root/'contract.json')
    changed = {p for p in original.keys() | current_contract.keys()
               if original.get(p) != current_contract.get(p)}
    require(changed <= ALLOWED_FILES, 'Budget amendment includes unrelated source/Prompt changes')
    cfg = ev._config(root)
    require(cfg['call_config']['max_tokens'] == POLICY['initial_max_tokens'], 'Unexpected initial token budget')
    require(not list((root/'recoveries').glob('*.json')), 'Legacy recovery cannot be combined with budget amendment')
    value = {'policy': deepcopy(POLICY), 'reason': reason, 'at': ev.now(),
             'original_contract_sha256': digest(original), 'approved_contract_sha256': digest(current_contract),
             'config_sha256': digest(cfg), 'state_at_authorization': read(root/'state.json'),
             'changed_files': sorted(changed),
             'source_diff': '\n'.join(''.join(difflib.unified_diff(
                 original.get(p, '').splitlines(True), current_contract.get(p, '').splitlines(True),
                 fromfile='original/'+p, tofile='approved/'+p)) for p in sorted(changed))}
    ev.save(root/DIRECTORY/'contract.json', current_contract)
    ev.save(root/DIRECTORY/'authorization.json', value)
    return value


def is_length(directory):
    directory = Path(directory)
    try:
        if (directory/'response.json').exists():
            return read(directory/'response.json').get('finish_reason') == 'length'
        if (directory/'http_status.json').exists() and not 200 <= read(directory/'http_status.json')['status_code'] < 300:
            return False
        return read(directory/'http_response.txt')['choices'][0].get('finish_reason') == 'length'
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return False


def module_budget(attempts, base, *, before=None):
    """Reconstruct the authorized budget from immutable prior attempt evidence."""
    tokens, streak = base, 0
    for path in sorted(Path(attempts).glob('[0-9]*')):
        if not path.is_dir() or (before is not None and path.name >= before):
            continue
        meta = read(path/'run.json')
        require(meta['call_config']['max_tokens'] == tokens, 'Unaudited module output budget')
        if is_length(path):
            streak += 1
            if streak == POLICY['length_attempts_per_budget']:
                tokens *= POLICY['multiplier']; streak = 0
        else:
            streak = 0
    return tokens, streak


def implementation_review(root, parents, candidates):
    """Review the exact Actor source change for the mixed old/new R03 pair."""
    pairs = [(p['implementation']['files'], q['implementation']['files']) for p, q in zip(parents, candidates)]
    if all(a == b for a, b in pairs):
        return None
    info = amendment(root)
    require(info is not None, 'Actor source difference requires an authorized amendment')
    original = read(Path(root)/'contract.json')
    approved = read(Path(root)/DIRECTORY/'contract.json')
    def expected(contract):
        return {n: hashlib.sha256(contract['src/adapters/alfworld/'+n].encode()).hexdigest()
                for n in ('run_task_skill.py', 'skill_runtime.py', 'run_task_upstream.py', 'run_task.py')}
    old, new = expected(original), expected(approved)
    for name in ('budget_actor.py', 'output_budget.py'):
        new['v23_4/'+name] = hashlib.sha256(approved['src/skill_evolution/v23_4/'+name].encode()).hexdigest()
    require(all(a == old and b == new for a, b in pairs), 'Actor versions not covered by recovery amendment')
    return {'parent_files': old, 'candidate_files': new,
            'reason': 'User-authorized request-local token recovery. Old completed Parent results retained; '
                      'Candidate uses opt-in six-length-then-double policy. This is a recorded execution-condition difference.',
            'diff': info['source_diff']}


def validate_actor(path, record):
    """Verify actual per-step parameters and doubling against archived responses."""
    from src.adapters.alfworld.response_archive import verify_response_archive
    from src.adapters.alfworld.skill_runtime import object_digest
    require(record.get('output_budget_policy') == POLICY, 'Actor output recovery policy differs')
    for step in record['steps']:
        tokens, streak, other = POLICY['initial_max_tokens'], 0, 0
        attempts = step.get('transport_attempts', [])
        for index, attempt in enumerate(attempts):
            params = attempt['request_parameters']
            expected = {'model': record['model'], 'temperature': 1.0, 'max_tokens': tokens,
                        'reasoning_effort': 'medium', 'thinking': {'type': 'enabled'}, 'stream': False}
            require(params == expected, 'Actor generation parameters differ from authorized budget')
            require(attempt['request_sha256'] == object_digest({**params, 'messages': step['messages']}),
                    'Actor request hash differs')
            verify_response_archive(path, attempt)
            status = attempt.get('http_status', 0)
            reason = None
            if status:
                try:
                    raw = read(Path(path).parent/attempt['raw_response']['path'])
                    reason = raw['choices'][0].get('finish_reason') if 200 <= status < 300 else None
                except (ValueError, KeyError, IndexError, TypeError):
                    pass
            if reason == 'length':
                streak += 1
                if streak == POLICY['length_attempts_per_budget']:
                    tokens *= POLICY['multiplier']; streak = 0
            elif index < len(attempts)-1:
                require(not status or status in {429, 500, 502, 503, 504} or 200 <= status < 300,
                        'Actor retried a permanent HTTP error')
                other += 1; streak = 0
                require(other < POLICY['other_error_attempts'], 'Actor non-length retry budget exceeded')
