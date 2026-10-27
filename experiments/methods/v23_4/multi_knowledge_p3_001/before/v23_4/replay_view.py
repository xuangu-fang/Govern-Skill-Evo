"""Deterministic Replay-only view; complete facts and Memory storage stay unchanged."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from src.skill_evolution.v23 import replay as original
from src.skill_evolution.v23.facts import require, text
from src.skill_evolution.v23.memory import load_memory, run_menus, validate_memory
from src.skill_evolution.v23_3.memory_view import compact_memory

FORMAT = 'v23_4_replay_pairs_memory_v3_v1'
LEGACY = 'entries_sources'
FORMAT_PATH = Path(__file__).with_name('replay_view_prompt.md')


def history_pair_sources(directory, memory):
    """Capture immutable archive locations, after checking the requested snapshot."""
    require(load_memory(directory) == memory, 'Historical Memory snapshot differs')
    result = {}
    for context in sorted({key.rsplit('/', 1)[0] for key in memory['sources']}):
        require(re.fullmatch(r'[A-Za-z0-9_-]+', context), 'Unsafe historical context')
        path = (Path(directory) / 'archive' / f'{context}.json').resolve()
        result[context] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return result


def _historical_pairs(memory, sources):
    validate_memory(memory)
    contexts = {key.rsplit('/', 1)[0] for key in memory['sources']}
    require(isinstance(sources, dict) and set(sources) == contexts,
            'Provide explicit pairing provenance for every historical context')
    visible = {key for key in memory['sources'] if not key.endswith('/diff')}
    pairs, paired = [], set()
    for context in sorted(contexts):
        location = sources[context]
        if location is None:
            continue  # Explicit unknown provenance, never guessed from P/Q IDs.
        require(isinstance(location, dict) and set(location) == {'path', 'sha256'},
                'Invalid historical pairing provenance')
        path = Path(text(location['path'], 'historical archive path'))
        require(path.is_absolute(), 'Historical archive path must be absolute')
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == location['sha256'], 'Historical archive hash differs')
        archive = json.loads(raw)
        require(archive['context_id'] == context, 'Historical archive context differs')
        saved = archive['context']
        payload = original.validate_payload(saved['payload'])
        if 'pair_audit' in saved:
            _current_pairs(saved)  # Preserve the archived task-identity checks when available.
        edit = {'parent': payload['parent'], 'diff': payload['diff'],
                'execution_context': saved['execution_context']}
        require(memory['sources'][f'{context}/diff'] == edit, 'Historical edit source differs')
        runs = {r['ref']: r for r in payload['runs']}
        for key in sorted(visible):
            cid, rid = key.rsplit('/', 1)
            if cid != context:
                continue
            require(rid in runs, 'Historical execution missing from archive')
            expected = {'run': runs[rid], 'command_sets': run_menus(runs[rid], payload['command_sets'])}
            require(memory['sources'][key] == expected, 'Historical execution source differs')
        for pair in payload['pairs']:
            p, q = pair['parent'], pair['candidate']
            require(runs[p]['task'] == runs[q]['task'], 'Historical paired task descriptions differ')
            parent, candidate = f'{context}/{p}', f'{context}/{q}'
            if parent in visible and candidate in visible:
                pairs.append({'context': context, 'parent': parent, 'candidate': candidate})
                paired.update((parent, candidate))
    return pairs, sorted(visible - paired)


def _current_pairs(bundle):
    payload = bundle['payload']
    runs = {r['ref']: r for r in payload['runs']}
    audits = bundle.get('pair_audit')
    require(isinstance(audits, list) and len(audits) == len(payload['pairs']), 'Missing current pair audit')
    by_pair = {}
    for audit in audits:
        pair = audit['pair']
        key = (pair['parent'], pair['candidate'])
        require(key not in by_pair and audit['verified'] is True, 'Invalid current pair audit')
        by_pair[key] = audit
    require(set(by_pair) == {(p['parent'], p['candidate']) for p in payload['pairs']},
            'Current pair audit coverage differs')
    results, ordered, tasks = [], [], set()
    for pair in payload['pairs']:
        p, q = pair['parent'], pair['candidate']
        audit = by_pair[p, q]
        task_id = text(audit['task']['id'], 'verified task ID')
        require(task_id not in tasks, 'Current task identity reused')
        tasks.add(task_id)
        for side, ref in (('parent', p), ('candidate', q)):
            require(audit[side]['ref'] == ref and audit[side]['task_id'] == task_id,
                    'Current task identity differs from pair audit')
        require(runs[p]['task'] == runs[q]['task'], 'Current paired task descriptions differ')
        row = {**pair, 'task_id': task_id}
        for side, ref in (('parent', p), ('candidate', q)):
            run = runs[ref]
            row[f'{side}_result'] = {'status': run['outcome']['status'],
                                    'success': run['outcome']['success'], 'steps': len(run['steps'])}
            ordered.append(deepcopy(run))
        results.append(row)
    return results, ordered


def model_input(bundle, *, history_sources=None):
    """View construction also supports explicitly identified offline evaluation bundles.

    Production callers validate Editor lineage separately before using this function.
    No archive paths or hashes are sent to the model.
    """
    payload = original.validate_payload(bundle['payload'])
    pairs, runs = _current_pairs(bundle)
    view = {key: deepcopy(payload[key]) for key in ('parent', 'diff', 'plan', 'command_sets')}
    view.update(pairs=pairs, runs=runs, memory=compact_memory(payload['memory']))
    historical, unpaired = _historical_pairs(payload['memory'], {} if history_sources is None else history_sources)
    view['memory'].update(pairs=historical, unpaired_runs=unpaired)
    return view
