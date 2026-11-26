"""SearchQA campaign with v27 stage ordering and atomic Skill/Memory publication."""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import re
import shutil

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.contracts import memory
from .config import validate_config, REVIEW_DISABLED
from . import modules
from .stages import Stopped, read, save, freeze, freeze_text, now, run_stage
from .benchmarks.searchqa import evidence

MEMORY_CONTRACT = memory.MULTI_KNOWLEDGE_CONTRACT


@contextmanager
def _lock(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def _initial_state(config):
    return {'next_round': 1, 'parent': 'initial_skill.md' if config['initial_skill'] else None,
            'active_memory': 'initial_memory'}


def _initialize(root, config):
    require(re.fullmatch(r'[A-Za-z0-9_-]+', root.name) is not None, 'Campaign directory name must be a safe Memory context ID')
    validate_config(config)
    dataset_root = getattr(current().dataset, 'root', None)
    if dataset_root is not None:
        protected = Path(dataset_root).resolve()
        require(not root.is_relative_to(protected) and not protected.is_relative_to(root),
                'Campaign output must be separate from frozen data')
    started = (root / 'state.json').exists()
    for name, value in [('config', config), ('initial_config', config),
                        ('runtime', current().runtime_snapshot(config))]:
        freeze(root / f'{name}.json', value, read_only=started)
    if not started and not (root / 'contract.json').exists():
        save(root / 'contract.json', current().source_snapshot())  # Audit only; never a resume gate.
    if config['initial_skill']:
        freeze_text(root / 'initial_skill.md', config['initial_skill']['text'], read_only=started)
    elif (root / 'initial_skill.md').exists():
        raise ValueError('Unexpected initial Skill')
    freeze(root / 'initial_memory/active.json', {'active_ids': [], 'commits': []}, read_only=started)
    if not started:
        require(not (root / 'rounds').exists(), 'Missing official state in a started Campaign')
        save(root / 'state.json', _initial_state(config))


def initialize(campaign, config):
    root = Path(campaign).resolve()
    with _lock(root): _initialize(root, config)
    return root


def _check_contract(root):
    require(not list((root / 'recoveries').glob('*.json')) and not list((root / 'amendments').rglob('*.json')),
            'V28 does not permit runtime budget/configuration amendments')
    require(read(root / 'config.json') == read(root / 'initial_config.json'), 'Frozen configuration changed')


def _config(root):
    value = read(root / 'config.json')
    freeze(root / 'initial_config.json', value, read_only=True)
    validate_config(value)
    if value['initial_skill']:
        freeze_text(root / 'initial_skill.md', value['initial_skill']['text'], read_only=True)
    else:
        require(not (root / 'initial_skill.md').exists(), 'Unexpected initial Skill')
    freeze(root / 'initial_memory/active.json', {'active_ids': [], 'commits': []}, read_only=True)
    return value


def _relative(root, value):
    require(isinstance(value, str), 'Invalid Campaign path')
    path = (root / value).resolve()
    require(path.is_relative_to(root) and path != root, 'Campaign path escapes root')
    return path


def _skill(root, state):
    return None if state['parent'] is None else _relative(root, state['parent']).read_bytes().decode('utf-8')


def _completed_actor_journal(folder, tasks):
    task_key = current().actor_adapter.task_key
    return all((folder/'actor'/task_key(task)/'result.json').is_file() for task in tasks)


def _actors(root, rd, side, tasks, skill_file, *, resume, read_only, generate):
    adapter = current(); folder = rd / side
    split = adapter.dataset.case(tasks[0]).metadata['split']
    config = {'split': split, 'role': 'parent' if side == 'parent_runs' else 'candidate'}
    expected = None if skill_file is None else skill_file.read_bytes().decode('utf-8')
    _check_contract(root)
    marker = folder / 'records.json'
    if marker.exists():
        records = read(marker)
    else:
        require(not read_only, 'Missing completed Actor batch')
        if folder.exists(): require(resume, 'Interrupted Actor batch requires explicit resume')
        require(callable(generate) or _completed_actor_journal(folder, tasks),
                'Explicit method generator required before new Actor requests')
        # One common SearchQA pool, its original work directory and six-attempt budgets.
        records = adapter.actor_batch(tasks, skill_file, folder, config)
        freeze(marker, records)
    require(isinstance(records, list) and len(records) == len(tasks)
            and {r['task_id'] for r in records} == set(tasks), 'Actor batch coverage differs')
    adapter.actor_adapter._check_batch_records(records, tasks, expected, config, folder)
    adapter.register_archive(folder)
    return records  # Preserve completion order; pairs later use task identity.


def _prepare_memory(source, dest, *, session):
    current().load_memory(source)
    base = read(source / 'active.json')
    freeze(dest / 'base.json', {'source': str(source), 'state': base})
    session.checks.watch_file(dest / 'base.json')
    (dest / 'archive').mkdir(exist_ok=True)
    for cid in base['commits']:
        old, new = source / 'archive' / f'{cid}.json', dest / 'archive' / f'{cid}.json'
        if new.exists(): require(new.read_bytes() == old.read_bytes(), 'Immutable Memory archive differs')
        else:
            try: os.link(old, new)
            except OSError: shutil.copyfile(old, new)
            else: session.linked(old, new)
    if not (dest / 'active.json').exists(): save(dest / 'active.json', base)
    session.adopt(source, dest)


def _publish(root, rd, config, state, selected, mem, outcome, *, checkpoint, hook=None, read_only=False):
    after = {'next_round': state['next_round']+1, 'parent': selected, 'active_memory': mem}
    current().load_memory(_relative(root, mem))
    if selected is not None: require(bool(_relative(root, selected).read_text().strip()), 'Empty next Parent')
    result = {'status': 'completed', 'outcome': outcome, 'before': state, 'after': after}
    freeze(rd / 'result.json', result, read_only=read_only)
    if not read_only:
        checkpoint('before_publish')
        _check_contract(root)
        freeze(root / 'runtime.json', current().runtime_snapshot(config), read_only=True)
        require(read(root / 'state.json') == state, 'Official state changed during round')
        current().verify_memory_operation()
        save(root / 'state.json', after)
        if hook: hook('after_publish')
    return result


def _finish_replay(root, rd, config, state, bundle, replayed, gate, candidate_path, *,
                   checkpoint, hook=None, read_only=False):
    rid = f"{root.name}_R{state['next_round']:02}"
    memory_root = _relative(root, state['active_memory'])
    with current().memory_operation() as session:
        selected = candidate_path if gate['result']['decision'] == 'ACCEPT' else state['parent']
        if selected is not None:
            selected_file = _relative(root, selected)
            expected = bundle['candidate'] if gate['result']['decision'] == 'ACCEPT' else bundle['payload']['parent']
            require(selected_file.read_bytes().decode('utf-8') == expected, 'Selected Skill differs from verified execution')
            session.checks.watch_file(selected_file)
        checkpoint('knowledge_review')
        result, verdicts, repaired = deepcopy(replayed), None, None
        disabled = config['method']['knowledge_review'] == REVIEW_DISABLED
        require(disabled, 'Knowledge review must remain disabled')
        freeze(rd / 'knowledge_review/candidate.json', result, read_only=read_only)
        review_result = {'policy': modules.REVIEW_POLICY, 'targets': None,
               'conflicts': sum(r['verdict'] == 'CONFLICT' for r in verdicts['results']) if verdicts else 0,
               'repair_applied': repaired is not None, 'second_semantic_verification': False}
        if disabled:
            review_result.update(policy=REVIEW_DISABLED, status='disabled', conflicts=None)
        freeze(rd / 'knowledge_review/result.json', review_result, read_only=read_only)
        checkpoint('memory')
        dest = rd / 'memory'
        if read_only:
            commit = read(dest / 'archive' / f'{rid}.json')
            require(commit['result'] == result and commit['context'] == bundle, 'Published Memory differs from reviewed result')
            base = read(memory_root / 'active.json')
            require(read(dest / 'active.json')['commits'] == base['commits'] + [rid], 'Memory commit chain differs')
        else:
            _prepare_memory(memory_root, dest, session=session)
            current().commit_memory(dest, context_id=rid, context=bundle, result=result)
        view = current().load_memory(dest)
        freeze(dest / 'view.json', view, read_only=read_only)
        session.written(dest / 'view.json', view)
        checkpoint('memory_prepared')
        return _publish(root, rd, config, state, selected, str(dest.relative_to(root)), gate['result']['decision'],
                        checkpoint=checkpoint, hook=hook, read_only=read_only)


def _execute_round(root, config, state, *, generate, resume, hook=None, read_only=False):
    number = state['next_round']; rd = root / 'rounds' / f'R{number:02}'
    rid = f'{root.name}_R{number:02}'
    parent = _skill(root, state); memory_root = _relative(root, state['active_memory'])
    active = current().load_memory(memory_root)
    tasks = config['batches'][number-1]
    frozen = {'round_id': rid, 'state': state, 'parent': parent, 'memory': active, 'tasks': tasks, 'config': config}
    freeze(rd / 'round_input.json', frozen, read_only=read_only)
    pfile = None if parent is None else rd / 'parent.md'
    if pfile: freeze_text(pfile, parent, read_only=read_only)
    phase = 'parent_runs'

    def checkpoint(name):
        nonlocal phase
        phase = name
        if not read_only:
            save(rd / 'progress.json', {'stage': name, 'at': now()})
            if hook: hook(name)

    def model(call):
        checkpoint(call.name)
        return run_stage(rd / call.name, call, call_config=config['module_calls'][call.name],
                         max_attempts=config['max_attempts'], max_input_chars=config['max_input_chars'],
                         max_message_utf8_bytes=config['max_message_utf8_bytes'], generate=generate,
                         resume=resume, read_only=read_only, check_contract=lambda: _check_contract(root),
                         retry_delay_seconds=config.get('retry_delay_seconds', 0))

    def publish(selected, mem, outcome):
        return _publish(root, rd, config, state, selected, mem, outcome,
                        checkpoint=checkpoint, hook=hook, read_only=read_only)

    try:
        checkpoint('parent_runs')
        parents = _actors(root, rd, 'parent_runs', tasks, pfile, resume=resume, read_only=read_only, generate=generate)
        _, grouped = model(modules.grouping_call(parents, rid))
        _, diagnosed = model(modules.diagnosis_call(grouped))
        if diagnosed['diagnosis']['decision'] == 'no_change':
            return publish(state['parent'], state['active_memory'], 'no_change')
        _, adjusted = model(modules.preconditioner_call(diagnosed, active))
        if adjusted['effective_plan'] is None:
            return publish(state['parent'], state['active_memory'], 'no_change')
        editor_path, edited = model(modules.editor_call(adjusted))
        if edited['editor_status'] == 'no_change':
            return publish(state['parent'], state['active_memory'], 'no_change')
        if edited['editor_status'] == 'needs_revision':
            raise Stopped('semantic: Editor patch=null cannot faithfully implement the Plan')
        checkpoint('candidate_runs')
        candidates = _actors(root, rd, 'candidate_runs', tasks, editor_path / 'candidate.md',
                             resume=resume, read_only=read_only, generate=generate)
        checkpoint('pairs')
        bundle = evidence.build_replay_from_editor(edited, str(editor_path), parents, candidates, memory=active)
        freeze(rd / 'pairs/input.json', bundle, read_only=read_only)
        checkpoint('gate')
        gate = current().build_gate(parents, candidates, tasks, parent_skill=parent, candidate_skill=edited['candidate_text'],
                                    parent_directory=rd/'parent_runs', candidate_directory=rd/'candidate_runs')
        freeze(rd / 'gate/result.json', gate, read_only=read_only)
        _, replayed = model(modules.replay_call(bundle))
        candidate = replayed['replay']
        return _finish_replay(root, rd, config, state, bundle, candidate, gate,
                              str((editor_path / 'candidate.md').relative_to(root)),
                              checkpoint=checkpoint, hook=hook, read_only=read_only)
    except (Exception, KeyboardInterrupt) as exc:
        if not read_only:
            stop = {'round': number, 'stage': phase, 'kind': 'semantic' if str(exc).startswith('semantic:') else 'technical',
                    'error_type': type(exc).__name__, 'error': str(exc)[:1000], 'at': now()}
            save(rd / 'stop.json', stop); save(root / 'stop.json', stop)
        raise


def _audit_published(root, config):
    state = read(root / 'state.json')
    require(isinstance(state, dict) and set(state) == {'next_round', 'parent', 'active_memory'}, 'Invalid official state')
    require(type(state['next_round']) is int and 1 <= state['next_round'] <= len(config['batches'])+1, 'Invalid round cursor')
    prior = _initial_state(config)
    for _ in range(1, state['next_round']):
        result = _execute_round(root, config, prior, generate=None, resume=False, read_only=True)
        prior = result['after']
    require(prior == state, 'Official state differs from verified publications')
    return state


def run_campaign(campaign, *, config=None, generate=None, resume=False, hook=None, max_rounds=None):
    """All public mutation runs under one writer lock. No generator is inferred."""
    require(max_rounds is None or (type(max_rounds) is int and max_rounds > 0), 'Invalid round limit')
    root = Path(campaign).resolve()
    with _lock(root):
        if config is not None: _initialize(root, config)
        _check_contract(root); config = _config(root)
        freeze(root / 'runtime.json', current().runtime_snapshot(config), read_only=True)
        state = _audit_published(root, config)
        if (root / 'stop.json').exists():
            stop = read(root / 'stop.json')
            if state['next_round'] <= stop['round']:
                require(resume, 'Stopped Campaign requires explicit resume')
                require(stop['kind'] != 'semantic', 'Semantic blocker requires upstream revision; no resampling')
        elif (root / 'rounds' / f"R{state['next_round']:02}" / 'round_input.json').exists():
            require(resume, 'Interrupted Campaign requires explicit resume')
        session = root / 'sessions'; session.mkdir(exist_ok=True)
        save(session / f'{len(list(session.glob("*.json")))+1:03}.json', {'resume': resume, 'at': now()})
        count = 0
        while read(root / 'state.json')['next_round'] <= len(config['batches']):
            _check_contract(root)
            freeze(root / 'runtime.json', current().runtime_snapshot(config), read_only=True)
            result = _execute_round(root, config, read(root / 'state.json'), generate=generate, resume=resume, hook=hook)
            count += 1
            if result['outcome'] == 'no_change' and not config['continue_no_change']: return result
            if max_rounds is not None and count >= max_rounds: return result
        return {'status': 'complete', 'state': read(root / 'state.json')}


def run_round(campaign, **kwargs):
    return run_campaign(campaign, max_rounds=1, **kwargs)


def resume_round(campaign, **kwargs):
    return run_round(campaign, resume=True, **kwargs)


def final_parent(campaign):
    """Revalidate all published dependencies without a model or Actor invocation."""
    root = Path(campaign).resolve()
    require((root / 'config.json').is_file(), 'Missing Campaign')
    with _lock(root):
        _check_contract(root); config = _config(root)
        freeze(root / 'runtime.json', current().runtime_snapshot(config), read_only=True)
        state = _audit_published(root, config)
        require(state['next_round'] == len(config['batches'])+1, 'Campaign is not complete')
        return None if state['parent'] is None else _relative(root, state['parent'])
