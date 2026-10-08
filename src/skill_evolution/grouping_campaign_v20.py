"""v20 Grouping adapter with an explicit, bounded model budget.

The grouping contract and card preparation remain v17-compatible. v20 owns the
request budget so a difficult partition does not inherit the v19 16K ceiling.
"""
from pathlib import Path

from .edit_tracking_v19 import encode, parse
from .experience_grouping_v17 import prepare_grouping_request, REPAIR_INSTRUCTION
from .experience_grouping_contract_v17 import validate_grouping_output, bind_grouping_result
from .memory_generation_v19 import _call, _read_call
from .memory_store_v19 import require
from .evolution_replay_v19 import _save, _load, _file_digest, _lock


GROUPING_REASONING_EFFORT = 'high'
GROUPING_MAX_COMPLETION_TOKENS = 24_000


def _request(batch, scope):
    prepared = prepare_grouping_request(batch, scope=scope)
    return {**prepared, 'model': prepared['model'].removeprefix('openai/'),
            'reasoning_effort': GROUPING_REASONING_EFFORT,
            'max_completion_tokens': GROUPING_MAX_COMPLETION_TOKENS,
            'timeout_seconds': 300, 'max_retries': 0}


def _group(batch, scope, root, call):
    request = _request(batch, scope)
    aliases = tuple(request['alias_to_source']['task_ref'])
    current = request
    for attempt in range(2):
        raw = call(root / f'attempt-{attempt + 1}', current)
        try:
            output = parse(raw)
            validate_grouping_output(output, task_refs=aliases)
        except (ValueError, TypeError) as exc:
            if attempt == 1:
                raise
            current = {**request, 'user_prompt': encode({
                'original_input': parse(request['user_prompt']),
                'repair_instruction': REPAIR_INSTRUCTION,
                'previous_response': raw,
                'validation_error': str(exc),
            })}
            continue
        mapped = parse(encode(output))
        for group in mapped['groups']:
            group['members'] = [request['alias_to_source']['task_ref'][m]
                                for m in group['members']]
        result = bind_grouping_result(batch.payload, mapped, scope=scope)
        return {**result, 'alias_to_source': request['alias_to_source']}
    raise AssertionError('unreachable')


def _files(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob('*.json')
                  if p.name != 'validation.json')


def run_campaign_grouping_v20(batch, *, scope, artifact_dir, transport=None, resume=False):
    """Run or resume v20 Grouping with a 24K high-reasoning ceiling."""
    root = Path(artifact_dir)
    bound = {'request': _request(batch, scope),
             'scope': {'round_id': scope.round_id,
                       'parent_skill_digest': scope.parent_skill_digest,
                       'experiences': [vars(r) for r in scope.experiences]}}
    with _lock(root):
        if root.exists():
            require(resume, 'existing grouping requires resume')
            require(_load(root / 'input.json') == bound, 'grouping input changed')
            if ((root / 'validation.json').exists() and
                    _load(root / 'validation.json').get('status') == 'COMPLETE'):
                marker = _load(root / 'validation.json')
                require(marker == {'status': 'COMPLETE',
                                   'files': {n: _file_digest(root / n)
                                             for n in _files(root)}},
                        'grouping checksum mismatch')
                expected = _group(batch, scope, root, _read_call)
                require(_load(root / 'groups.json') == expected,
                        'groups differ from saved response')
                return expected
        else:
            require(not resume, 'grouping resume requires existing output')
            root.mkdir(parents=True)
            _save(root / 'input.json', bound)
        _save(root / 'validation.json', {'status': 'RUNNING'})
        try:
            result = _group(batch, scope, root,
                            lambda d, r: _call(d, r, transport))
            if (root / 'groups.json').exists():
                require(_load(root / 'groups.json') == result,
                        'grouping output changed')
            else:
                _save(root / 'groups.json', result)
            _save(root / 'validation.json', {
                'status': 'COMPLETE',
                'files': {n: _file_digest(root / n) for n in _files(root)},
            })
            return result
        except BaseException as exc:
            _save(root / 'validation.json', {
                'status': 'INCOMPLETE', 'error_type': type(exc).__name__,
            })
            raise
