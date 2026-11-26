"""Independent selective-Gate training, with recoverable Memory-first publication.

Memory HEAD publishes the selected text and history atomically. state.json is
the round cursor: it may lag one committed round after interruption, but must
be reconciled before any next-round execution. No Candidate score is assigned
to a newly composed Selected Skill.
"""
from pathlib import Path

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27_1.evolution import (
    EMPTY_MEMORY, _lock, _initial_state, _relative, _load_checkpoint, _watch_round, _prefix,
)
from src.skill_evolution.v27_1.facts import build_parent_bundle
from .campaign import RUNTIME_VERSION
from src.skill_evolution.v27_1 import gate, memory
from . import config as settings, stages, diagnosis, preconditioner, editor, replay
from .stages import Stopped, read, save, freeze, freeze_text, now
from src.skill_evolution.v27_1.actor_io import read_skill

def _implementation():
    return {'runtime_version': RUNTIME_VERSION, 'method': settings.method_config(), 'prompts': settings.render_prompts()}


def _initialize(root, config):
    settings.validate_config(config)
    started = (root / 'state.json').exists()
    if not started:
        allowed = {'.lock', 'config.json', 'initial_config.json', 'runtime.json', 'implementation.json',
                   'initial_skill.md', 'initial_memory.json', 'state.tmp'}
        allowed |= {Path(name).with_suffix('.tmp').name for name in allowed if name.endswith('.json')}
        allowed.add('initial_skill.md.tmp')
        require(all(path.is_file() and path.name in allowed for path in root.iterdir()),
                'Missing official state or nonempty unrelated campaign directory')
    for name, value in (('config', config), ('initial_config', config),
                        ('runtime', current().runtime_snapshot(config)), ('implementation', _implementation()),
                        ('initial_memory', EMPTY_MEMORY)):
        freeze(root / f'{name}.json', value, read_only=started)
    freeze_text(root / 'initial_skill.md', config['initial_skill']['text'], read_only=started)
    if not started: save(root / 'state.json', _initial_state())


def initialize(campaign, config):
    root = Path(campaign).resolve()
    with _lock(root): _initialize(root, config)
    return root


def _config(root):
    config = read(root / 'config.json')
    freeze(root / 'initial_config.json', config, read_only=True)
    settings.validate_config(config)
    freeze(root / 'initial_memory.json', EMPTY_MEMORY, read_only=True)
    freeze_text(root / 'initial_skill.md', config['initial_skill']['text'], read_only=True)
    return config


def _check_contract(root, config):
    freeze(root / 'config.json', config, read_only=True)
    freeze(root / 'initial_config.json', config, read_only=True)
    freeze(root / 'implementation.json', _implementation(), read_only=True)
    freeze(root / 'runtime.json', current().runtime_snapshot(config), read_only=True)


def _actors(root, rd, side, tasks, skill_file, *, config, resume, read_only, generate):
    adapter, folder = current(), rd / side
    role = 'parent' if side == 'parent_runs' else 'candidate'
    _check_contract(root, config)
    if (folder / 'records.json').exists():
        records = adapter.actor_adapter.read_batch(folder)
    else:
        require(not read_only, 'Missing completed Actor batch')
        if folder.exists(): require(resume, 'Interrupted Actor batch requires explicit resume')
        completed = all((folder / 'actor' / adapter.actor_adapter.task_key(task) / 'result.json').is_file()
                        for task in tasks)
        require(callable(generate) or completed, 'Explicit generator required before new Actor execution')
        records = adapter.actor_batch(tasks, skill_file, folder, {'split': 'train', 'role': role})
    require([r['task_id'] for r in records] == tasks, 'Actor batch order/coverage differs')
    skill = read_skill(skill_file)
    require(all(r['execution']['skill'] == skill and r['task']['split'] == 'train' and
                r['provenance']['role'] == role for r in records), 'Actor role/Skill differs')
    adapter.register_archive(folder)
    return records


def _publish(root, rd, config, before, previous, selection, execution_source, outcome, prepared, *,
             checkpoint, audit, session):
    freeze(rd / 'selection.json', {'selection': selection, 'selected_execution_source': execution_source}, read_only=audit)
    freeze_text(rd / 'selected.md', selection['selected_text'], read_only=audit)
    if prepared is not None: freeze(rd / 'memory_prepared.json', prepared, read_only=audit)
    _watch_round(session, rd)
    checkpoint('memory_prepared')
    _check_contract(root, config)
    session.verify()
    if prepared is None:
        require(not (rd / 'memory_prepared.json').exists() and not (rd / 'memory_receipt.json').exists(),
                'Unexpected Memory publication for a round without Effective Updates')
        committed = previous
        if not audit:
            require(memory.load_memory(root / 'memory')['head'] == previous['head'], 'Unexpected Memory advance')
    elif audit:
        receipt = read(rd / 'memory_receipt.json')
        committed = memory.load_memory(root / 'memory', head=receipt['head'])
        require(committed['memory'] == {'rounds': previous['memory']['rounds'] + [prepared['round']]} and
                settings.same(committed['selection'], selection) and
                committed['selected_execution_source'] == execution_source, 'Memory publication differs')
        freeze(rd / 'memory_receipt.json', committed, read_only=True)
    else:
        checkpoint('before_memory_commit')
        _check_contract(root, config); session.verify()
        require(settings.same(read(root / 'state.json'), before), 'Round cursor changed before Memory commit')
        committed = memory.commit_memory(root / 'memory', prepared, expected_head=previous['head'])
        checkpoint('after_memory_commit')
        freeze(rd / 'memory_receipt.json', committed)
        require(memory.load_memory(root / 'memory')['head'] == committed['head'], 'Memory advanced beyond this round')
    selected_path = before['parent'] if selection['selected_text'] == read_skill(rd / 'parent.md') else str((rd / 'selected.md').relative_to(root))
    after = {'next_round': before['next_round'] + 1, 'parent': selected_path, 'memory_head': committed['head']}
    result = {'status': 'completed', 'outcome': outcome, 'before': before, 'after': after,
              'selection': selection, 'selected_execution_source': execution_source}
    freeze(rd / 'result.json', result, read_only=audit)
    session.watch_file(rd / 'result.json')
    if (rd / 'memory_receipt.json').exists(): session.watch_file(rd / 'memory_receipt.json')
    if not audit:
        checkpoint('before_publish')
        _check_contract(root, config); session.verify()
        require(settings.same(read(root / 'state.json'), before), 'Round cursor changed during publication')
        require(memory.load_memory(root / 'memory')['head'] == committed['head'], 'Memory HEAD changed before cursor update')
        save(root / 'state.json', after)
        checkpoint('after_publish')
    return result


def _execute_round(root, config, state, *, generate, resume, hook=None, audit=False, committed_recovery=False):
    current().begin_round()
    number = state['next_round']; rd = root / 'rounds' / f'R{number:02}'
    rid = f'{root.name}_R{number:02}'
    read_only = audit or committed_recovery
    parent = read_skill(_relative(root, state['parent']))
    previous = _prefix(root, state['memory_head'])
    if previous['head'] is not None:
        require(parent == previous['selection']['selected_text'], 'Parent differs from committed Selected Skill')
    tasks = config['batches'][number - 1]
    freeze(rd / 'round_input.json', {'round_id': rid, 'state': state, 'parent': parent,
                                   'memory': previous['memory'], 'tasks': tasks}, read_only=read_only)
    freeze_text(rd / 'parent.md', parent, read_only=read_only)
    phase = 'parent_runs'

    def checkpoint(name):
        nonlocal phase
        phase = name
        if not audit:
            save(rd / 'progress.json', {'stage': name, 'at': now()})
            if hook: hook(name)

    def check_execution():
        _check_contract(root, config)
        if not audit:
            require(settings.same(read(root / 'state.json'), state), 'Round cursor changed during execution')

    options = dict(max_attempts=config['max_attempts'], max_input_chars=config['max_input_chars'],
                   max_message_utf8_bytes=config['max_message_utf8_bytes'], generate=generate,
                   resume=resume, read_only=read_only, check_contract=check_execution,
                   retry_delay_seconds=config['retry_delay_seconds'])

    def model(call):
        checkpoint(call.name)
        return stages.run_stage(rd / call.name, call, call_config=config['module_calls'][call.name], **options)

    try:
        with current().memory_operation() as session:
            def publish(outcome, prepared=None, result=None):
                selection = result['selection'] if result else (
                    prepared['selection'] if prepared else
                    {'selected_update_ids': [], 'selected_text': parent, 'actual_diff': ''})
                source = result['selected_execution_source'] if result else 'parent'
                return _publish(root, rd, config, state, previous, selection, source, outcome, prepared,
                                checkpoint=checkpoint, audit=audit, session=session)

            checkpoint('parent_runs')
            check_execution()
            parents = _actors(root, rd, 'parent_runs', tasks, rd / 'parent.md', config=config,
                              resume=resume, read_only=read_only, generate=generate)
            saved = build_parent_bundle(parents, rid)
            _, diagnosed = model(diagnosis.diagnosis_call(saved))
            if diagnosed['diagnosis']['decision'] == 'no_change':
                return publish('diagnosis_no_change')
            _, adjusted = model(preconditioner.preconditioner_call(diagnosed, previous['memory']))
            if adjusted['effective_plan'] is None:
                return publish('preconditioner_withdrawn')
            editor_path, edited = model(editor.editor_call(adjusted))
            if edited['editor_status'] == 'needs_revision':
                raise Stopped('semantic: Editor patch=null cannot faithfully implement the Update')
            if edited['editor_status'] == 'no_change':
                return publish('editor_no_change', memory.prepare_no_change(previous, edited=edited))
            checkpoint('candidate_runs')
            check_execution()
            candidates = _actors(root, rd, 'candidate_runs', tasks, editor_path / 'candidate.md', config=config,
                                 resume=resume, read_only=read_only, generate=generate)
            checkpoint('pairs')
            bundle = replay.build_replay_from_editor(edited, parents, candidates)
            freeze(rd / 'pairs/input.json', bundle, read_only=read_only)
            checkpoint('replay')
            _, replayed = stages.run_replay_stage(rd / 'replay', bundle, call_config=config['module_calls']['replay'], **options)
            checkpoint('gate')
            result = gate.evaluate_gate(replayed)
            freeze(rd / 'gate/result.json', result, read_only=read_only)
            checkpoint('memory')
            prepared = memory.prepare_append(previous, replayed=replayed, gate_result=result)
            return publish('gate_completed', prepared, result)
    except (Exception, KeyboardInterrupt) as exc:
        if not audit:
            stop = {'round': number, 'stage': phase, 'kind': 'semantic' if str(exc).startswith('semantic:') else 'technical',
                    'error_type': type(exc).__name__, 'error': str(exc)[:1000], 'at': now()}
            save(rd / 'stop.json', stop); save(root / 'stop.json', stop)
        raise


def run_campaign(campaign, *, config=None, generate=None, resume=False, hook=None, max_rounds=None):
    require(max_rounds is None or (type(max_rounds) is int and max_rounds > 0), 'Invalid round limit')
    root = Path(campaign).resolve()
    with _lock(root):
        if config is not None: _initialize(root, config)
        config = _config(root); _check_contract(root, config)
        state, pending = _load_checkpoint(root, config)
        if state['next_round'] <= len(config['batches']):
            settings.validate_config(config, executable=True)
            rd = root / 'rounds' / f"R{state['next_round']:02}"
            if pending or rd.exists(): require(resume, 'Interrupted campaign requires explicit resume')
            if (root / 'stop.json').exists():
                stop = read(root / 'stop.json')
                if stop['round'] == state['next_round']:
                    require(resume, 'Stopped campaign requires explicit resume')
                    require(stop['kind'] != 'semantic', 'Editor null blocks publication; no semantic resampling')
        count = 0
        while state['next_round'] <= len(config['batches']):
            _check_contract(root, config)
            result = _execute_round(root, config, state, generate=generate, resume=resume, hook=hook,
                                    committed_recovery=pending)
            state, pending = result['after'], False
            count += 1
            if max_rounds is not None and count >= max_rounds: return result
        return {'status': 'complete', 'state': state}


def run_round(campaign, **kwargs):
    return run_campaign(campaign, max_rounds=1, **kwargs)


def resume_round(campaign, **kwargs):
    return run_round(campaign, resume=True, **kwargs)


def final_parent(campaign):
    """Read-only checkpoint verification; exporting never validates a new subset."""
    root = Path(campaign).resolve()
    require((root / 'state.json').is_file(), 'Missing campaign')
    with _lock(root):
        config = _config(root); _check_contract(root, config)
        state, pending = _load_checkpoint(root, config)
        require(not pending and state['next_round'] == len(config['batches']) + 1, 'Campaign is not complete')
        return _relative(root, state['parent'])
