"""Immutable Memory commits, atomic Active index and lossless referenced sources."""
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import re

from src.adapters.alfworld.skill_runtime import write_record
from .diagnosis import fields, links
from .facts import require, text, STATUSES


def empty_memory():
    return {"entries": [], "sources": {}}


def run_references(run):
    return {run['ref'], f"{run['ref']}:0", f"{run['ref']}:outcome", *[s['step'] for s in run['steps']]}


def run_menus(run, menus):
    used = {state['commands_ref'] for state in
            [run['initial'], *[s[side] for s in run['steps'] for side in ('before', 'after')]]} - {None}
    require(used <= menus.keys(), 'Missing command source')
    return {key: deepcopy(value) for key, value in menus.items() if key in used}


def validate_run(run, menus):
    fields(run, ('ref', 'task', 'initial', 'steps', 'outcome'), 'Run')
    require(isinstance(run['ref'], str) and re.fullmatch(r'[PQ][1-9]\d*', run['ref']), 'Invalid execution ID')
    text(run['task'], 'task')
    require(isinstance(run['steps'], list), 'steps must be an array')
    for state in [run['initial'], *[s[side] for s in run['steps'] for side in ('before', 'after')]]:
        fields(state, ('observation', 'commands_ref'), 'State')
        text(state['observation'], 'observation')
        require(state['commands_ref'] is None or state['commands_ref'] in menus, 'Missing command reference')
    for menu in menus.values():
        require(isinstance(menu, list) and all(isinstance(c, str) and c != 'help' for c in menu), 'Invalid visible menu')
    previous = run['initial']
    for i, step in enumerate(run['steps'], 1):
        fields(step, ('step', 'before', 'action', 'after', 'feedback'), 'Step')
        require(step['step'] == f"{run['ref']}:{i}" and step['before'] == previous, 'Broken execution continuity')
        # Empty commands are valid recorded evidence of an invalid Actor action.
        require(isinstance(step['action'], str), 'Invalid action')
        if i < len(run['steps']):
            require(not step['feedback'].get('done') and not step['feedback'].get('won'), 'Step follows terminal state')
        require(isinstance(step['feedback'], dict), 'Invalid feedback')
        previous = step['after']
    fields(run['outcome'], ('status', 'success', 'end_reason'), 'Outcome')
    status = run['outcome']['status']
    require(status in STATUSES and run['outcome']['end_reason'] == status, 'Invalid termination')
    expected = status == 'success' if status in {'success', 'environment_ended', 'step_limit'} else None
    require(run['outcome']['success'] is expected, 'Outcome confuses interruption and failure')
    return run


def validate_memory(memory):
    """Return resolvable historical fact refs; never infer support from prose."""
    fields(memory, ('entries', 'sources'), 'Memory')
    require(isinstance(memory['entries'], list) and isinstance(memory['sources'], dict), 'Invalid Memory collections')
    allowed, ids = set(), set()
    for key, source in memory['sources'].items():
        require(isinstance(key, str) and '/' in key, 'History needs context-qualified references')
        context, local = key.rsplit('/', 1)
        text(context, 'historical context')
        if local == 'diff':
            fields(source, ('parent', 'diff', 'execution_context'), 'Edit source')
            require(source['parent'] is None or isinstance(source['parent'], str), 'Invalid historical Parent')
            text(source['diff'], 'historical diff')
            require(isinstance(source['execution_context'], dict) and bool(source['execution_context']), 'Missing historical execution context')
            allowed.add(key)
        else:
            fields(source, ('run', 'command_sets'), 'Execution source')
            require(isinstance(source['command_sets'], dict), 'Invalid command sets')
            run = validate_run(source['run'], source['command_sets'])
            require(run['ref'] == local, 'Source identity differs')
            require(f'{context}/diff' in memory['sources'], 'Execution source lacks historical edit/context')
            allowed.update(f'{context}/{r}' for r in run_references(run))
    for entry in memory['entries']:
        fields(entry, ('id', 'knowledge', 'evidence'), 'Active MemoryEntry')
        mid = text(entry['id'], 'Memory ID')
        require(re.fullmatch(r'M[1-9]\d*', mid) and mid not in ids, 'Duplicate or invalid Memory ID')
        ids.add(mid)
        text(entry['knowledge'], 'knowledge')
        links(entry['evidence'], allowed, 'Memory evidence')
        require(any(r.endswith('/diff') for r in entry['evidence']) and
                any(not r.endswith('/diff') for r in entry['evidence']), 'Memory requires edit and execution evidence')
    return allowed


def validate_entries(result, payload):
    fields(result, ('entries',), 'Replay')
    require(isinstance(result['entries'], list), 'entries must be an array')
    history = validate_memory(payload['memory'])
    allowed = {'diff'} | history
    for run in payload['runs']:
        allowed.update(run_references(run))
    active = {e['id'] for e in payload['memory']['entries']}
    revised = set()
    for entry in result['entries']:
        fields(entry, ('revises', 'knowledge', 'evidence'), 'Memory proposal')
        require(isinstance(entry['revises'], list), 'revises must be an array')
        if entry['revises']:
            links(entry['revises'], active, 'revises')
        require(not revised.intersection(entry['revises']), 'Repeated revision target')
        revised.update(entry['revises'])
        text(entry['knowledge'], 'knowledge')
        links(entry['evidence'], allowed, 'evidence')
        require(any(r == 'diff' or r.endswith('/diff') for r in entry['evidence']) and
                any(r != 'diff' and not r.endswith('/diff') for r in entry['evidence']),
                'Entry requires actual edit and execution evidence')
    return result


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _state(root):
    path = root / 'active.json'
    state = _read(path) if path.exists() else {'active_ids': [], 'commits': []}
    fields(state, ('active_ids', 'commits'), 'Active index')
    require(all(isinstance(state[k], list) and len(state[k]) == len(set(state[k])) for k in state), 'Invalid Active index')
    return state


def _archive(root, state):
    entries, contexts, active = {}, {}, []
    for cid in state['commits']:
        require(re.fullmatch(r'[A-Za-z0-9_-]+', cid), 'Invalid context ID')
        commit = _read(root / 'archive' / f'{cid}.json')
        require(commit['context_id'] == cid and commit['before_active_ids'] == active, 'Broken commit lineage')
        validate_entries(commit['result'], commit['context']['payload'])
        history = validate_memory(commit['context']['payload']['memory'])
        require(len(commit['entries']) == len(commit['result']['entries']), 'Archived proposal count differs')
        for stored, proposal in zip(commit['entries'], commit['result']['entries']):
            fields(stored, ('id', 'context_id', 'revises', 'knowledge', 'evidence'), 'Archived entry')
            expected = {**proposal, 'id': stored['id'], 'context_id': cid,
                        'evidence': [r if r in history else f'{cid}/{r}' for r in proposal['evidence']]}
            require(stored == expected, 'Archived entry differs from validated proposal')
        contexts[cid] = commit['context']
        for e in commit['entries']:
            require(e['id'] not in entries and e['context_id'] == cid, 'Duplicate archived identity')
            entries[e['id']] = e
        revised = {r for e in commit['entries'] for r in e['revises']}
        require(revised <= set(active), 'Archived revision target is not active')
        active = [mid for mid in active if mid not in revised] + [e['id'] for e in commit['entries']]
        require(active == commit['after_active_ids'], 'Broken Active transition')
    require(active == state['active_ids'], 'Active index differs from immutable commits')
    return entries, contexts


def load_memory(directory):
    """One atomic index snapshot; only committed immutable files are visible."""
    root = Path(directory)
    state = _state(root)
    archive, contexts = _archive(root, state)
    view = empty_memory()
    for mid in state['active_ids']:
        entry = archive[mid]
        view['entries'].append({k: deepcopy(entry[k]) for k in ('id', 'knowledge', 'evidence')})
        for ref in entry['evidence']:
            cid, local = ref.rsplit('/', 1)
            require(cid in contexts, 'Historical context unavailable')
            context = contexts[cid]
            edit_key = f'{cid}/diff'
            view['sources'][edit_key] = {'parent': context['payload']['parent'], 'diff': context['payload']['diff'],
                                        'execution_context': deepcopy(context['execution_context'])}
            if local != 'diff':
                rid = local.split(':', 1)[0]
                run = next((r for r in context['payload']['runs'] if r['ref'] == rid), None)
                require(run is not None and local in run_references(run), 'Archived execution reference unavailable')
                view['sources'][f'{cid}/{rid}'] = {'run': deepcopy(run),
                    'command_sets': run_menus(run, context['payload']['command_sets'])}
    validate_memory(view)
    return view


def commit_memory(directory, *, context_id, context, result):
    """Immutable commit file then atomic index switch, with crash-safe exact replay.

    Uncommitted files are never exposed as Active. An interrupted commit must be
    recovered with identical input before a different commit can be submitted.
    The context ID includes experiment identity, e.g. v23_replay_memory_001_R1.
    """
    require(isinstance(context_id, str) and re.fullmatch(r'[A-Za-z0-9_-]+', context_id), 'Unsafe context ID')
    from .replay import validate_payload
    validate_payload(context['payload'])
    require(isinstance(context.get('execution_context'), dict) and bool(context['execution_context']), 'Missing context')
    validate_entries(result, context['payload'])
    root = Path(directory)
    (root / 'archive').mkdir(parents=True, exist_ok=True)
    with (root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = _state(root)
        entries, _ = _archive(root, state)
        path = root / 'archive' / f'{context_id}.json'
        if context_id in state['commits']:
            old = _read(path)
            require(old['context'] == context and old['result'] == result, 'Committed round differs')
            return deepcopy(old)
        pending = {p.stem for p in (root / 'archive').glob('*.json')} - set(state['commits'])
        require(pending <= {context_id}, 'Recover the pending Memory commit first')
        require(context['payload']['memory'] == load_memory(root), 'Active snapshot changed before commit')
        next_id = max([int(mid[1:]) for mid in entries] or [0]) + 1
        new_entries = []
        history = validate_memory(context['payload']['memory'])
        for offset, proposal in enumerate(result['entries']):
            new_entries.append({**deepcopy(proposal), 'id': f'M{next_id + offset}', 'context_id': context_id,
                'evidence': [r if r in history else f'{context_id}/{r}' for r in proposal['evidence']]})
        revised = {r for e in new_entries for r in e['revises']}
        active = [mid for mid in state['active_ids'] if mid not in revised] + [e['id'] for e in new_entries]
        commit = {'context_id': context_id, 'context': deepcopy(context), 'result': deepcopy(result),
                  'before_active_ids': state['active_ids'], 'after_active_ids': active, 'entries': new_entries}
        if path.exists():
            require(_read(path) == commit, 'Interrupted commit differs from recovery request')
        else:
            write_record(path, commit)
        write_record(root / 'active.json', {'active_ids': active, 'commits': state['commits'] + [context_id]})
        return commit
