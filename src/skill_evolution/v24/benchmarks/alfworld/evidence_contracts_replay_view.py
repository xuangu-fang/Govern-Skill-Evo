from copy import deepcopy
import json
from pathlib import Path
from src.skill_evolution.v24.contracts import replay as original
from src.skill_evolution.v24.facts import require, text
from src.skill_evolution.v24.contracts.memory import run_menus, validate_memory, validate_entries, LEGACY_CONTRACT, MULTI_KNOWLEDGE_CONTRACT
from src.skill_evolution.v24.contracts.memory_view import compact_memory

def _historical_pairs(memory, sources, *, memory_contract=LEGACY_CONTRACT):
    validate_memory(memory, memory_contract=memory_contract)
    contexts = {key.rsplit('/', 1)[0] for key in memory['sources']}
    require(isinstance(sources, dict) and set(sources) == contexts,
            'Provide explicit pairing provenance for every historical context')
    visible = {key for key in memory['sources'] if not key.endswith('/diff')}
    pairs, paired = [], set()
    for context in sorted(contexts):
        location = sources[context]
        if location is None:
            continue  # Explicit unknown provenance, never guessed from P/Q IDs.
        require(isinstance(location, dict) and set(location) == {'path'},
                'Invalid historical pairing provenance')
        path = Path(text(location['path'], 'historical archive path'))
        require(path.is_absolute(), 'Historical archive path must be absolute')
        raw = path.read_bytes()
        archive = json.loads(raw)
        require(archive['context_id'] == context, 'Historical archive context differs')
        saved = archive['context']
        version = archive.get('memory_contract', LEGACY_CONTRACT)
        require(memory_contract == MULTI_KNOWLEDGE_CONTRACT or version == LEGACY_CONTRACT,
                'Legacy pairing view cannot read multi-Knowledge commits')
        payload = original.validate_payload(saved['payload'], memory_contract=version)
        validate_entries(archive['result'], payload, memory_contract=version)
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


def model_input(bundle, *, history_sources=None, memory_contract=LEGACY_CONTRACT):
    """View construction also supports explicitly identified offline evaluation bundles.

    Production callers validate Editor lineage separately before using this function.
    No archive paths or metadata are sent to the model.
    """
    payload = original.validate_payload(bundle['payload'], memory_contract=memory_contract)
    pairs, runs = _current_pairs(bundle)
    view = {key: deepcopy(payload[key]) for key in ('parent', 'diff', 'plan', 'command_sets')}
    view.update(pairs=pairs, runs=runs, memory=compact_memory(payload['memory'], memory_contract=memory_contract))
    historical, unpaired = _historical_pairs(payload['memory'], {} if history_sources is None else history_sources,
                                           memory_contract=memory_contract)
    view['memory'].update(pairs=historical, unpaired_runs=unpaired)
    return view

