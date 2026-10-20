"""Sequential V23 rounds with bounded attempts and one atomic state publication."""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from threading import Event

from src.adapters.alfworld.skill_runtime import write_record, execution_protocol
from . import grouping, diagnosis, preconditioner, editor, replay, memory, gate, prompts
from .facts import build_facts, require, COMPLETE
from .model_routing import model_for_endpoint, route_call_config

MODULES = {'grouping': grouping, 'diagnosis': diagnosis, 'preconditioner': preconditioner,
           'editor': editor, 'replay': replay}
ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    write_record(path, value)


def now():
    return datetime.now(timezone.utc).isoformat()


class Stopped(RuntimeError):
    """A preserved technical or semantic stop; only explicit resume can continue."""


def frozen_contract():
    paths = list(Path(__file__).parent.glob('*.py')) + list(Path(__file__).parent.glob('*prompt.md'))
    paths += [prompts.CONTEXT_PATH]
    paths += list((ROOT/'src/adapters/alfworld').glob('*.py'))
    return {str(p.relative_to(ROOT)): p.read_bytes().decode('utf-8') for p in sorted(paths)}


def message_byte_limit(config):
    """Accept the explicit name while retaining old frozen configurations."""
    limit = config.get('max_message_utf8_bytes', config.get('max_input_bytes'))
    require(type(limit) is int and limit > 0, 'Invalid message byte capacity')
    if 'max_message_utf8_bytes' in config and 'max_input_bytes' in config:
        require(limit == config['max_input_bytes'], 'Conflicting message byte capacities')
    return limit


def validate_config(config):
    workers = config.get('actor_max_workers', 1)
    require(type(workers) is int and workers > 0, 'actor_max_workers must be a positive integer')
    require(isinstance(config['batches'], list) and bool(config['batches']), 'Missing batches')
    ids = [t for batch in config['batches'] for t in batch]
    require(all(isinstance(b, list) and b for b in config['batches']), 'Empty batch')
    splits = config.get('optimization_splits', ['train'])
    require(splits in (['train'], ['train', 'val']), 'Optimization permits Train and explicit Selection only')
    require(all(isinstance(t, str) and t.split(':')[0] in splits and ':' in t for t in ids),
            'Task outside frozen optimization splits')
    if 'val' in splits:
        require(set(config.get('task_items', {})) == set(ids), 'Merged pool requires frozen task identities')
    require(len(ids) == len(set(ids)), 'Tasks must be distinct across this Campaign')
    require(config['max_attempts'] == 3, 'Module request budget must be three')
    require(config['actor_request_attempts'] == 3, 'Actor step request budget must be three')
    require(config['max_steps'] == 50, 'Use the verified Actor step budget')
    require(type(config['continue_no_change']) is bool, 'Missing no-change policy')
    require(type(config['max_input_chars']) is int and config['max_input_chars'] > 0, 'Invalid input capacity')
    message_byte_limit(config)
    require(config['call_config'] == grouping.call_configuration(
        base_url=config['call_config']['endpoint'].removesuffix('/chat/completions'),
        model=config['call_config']['model'], max_tokens=config['call_config']['max_tokens'],
        timeout=config['call_config']['timeout_seconds']), 'Unsupported module configuration')


def initialize(campaign, config):
    """Freeze content; initial state is always No Skill and empty Memory."""
    root = Path(campaign).resolve(); validate_config(config)
    root.mkdir(parents=True, exist_ok=True)
    if (root/'config.json').exists():
        require(read(root/'config.json') == config, 'Campaign config changed')
    else:
        save(root/'config.json', config)
    if not (root/'initial_config.json').exists():
        require(not (root/'state.json').exists(), 'Missing frozen configuration')
        save(root/'initial_config.json', config)
    require(read(root/'initial_config.json') == config, 'Frozen config changed')
    if not (root/'contract.json').exists():
        require(not (root/'state.json').exists(), 'Missing frozen contract')
        save(root/'contract.json', frozen_contract())
    if not (root/'state.json').exists():
        require(not (root/'rounds').exists(), 'Missing official state in started Campaign')
        save(root/'initial_memory/active.json', {'active_ids': [], 'commits': []})
        save(root/'state.json', {'next_round': 1, 'parent': None, 'active_memory': 'initial_memory'})
    return root


def _skill(root, state):
    return None if state['parent'] is None else (root/state['parent']).read_bytes().decode('utf-8')


def final_parent(campaign):
    """Read the officially retained Skill only after every frozen round is published."""
    root = Path(campaign).resolve()
    config, state = _config(root), read(root/'state.json')
    require(state['next_round'] == len(config['batches']) + 1, 'Campaign is not complete')
    previous = {'next_round': 1, 'parent': None, 'active_memory': 'initial_memory'}
    for number in range(1, state['next_round']):
        result = read(root/'rounds'/f'R{number:02}'/'result.json')
        require(result['status'] == 'completed' and result['before'] == previous,
                'Missing or inconsistent round publication')
        previous = result['after']
    require(previous == state, 'Final publication differs from official state')
    if state['parent'] is None:
        return None
    path = root/state['parent']
    require(bool(path.read_bytes().decode('utf-8').strip()), 'Missing final Parent')
    return path


def _check_contract(root):
    expected = read(root/'contract.json')
    for change in sorted((root/'recoveries').glob('*.json')):
        expected.update(read(change).get('contract_changes', {}))
    require(expected == frozen_contract(), 'Frozen source/Prompt changed; explicit reviewed recovery required')


def _config(root):
    value = read(root/'config.json')
    require(value == read(root/'initial_config.json'), 'Frozen config changed')
    for change in sorted((root/'recoveries').glob('*.json')):
        record = read(change)
        if record.get('stage_config'):
            value.setdefault('stage_configs', {})[record['stage']] = record['stage_config']
        if record.get('input_limits'):
            value.pop('max_input_bytes', None)
            value.update(record['input_limits'])
    return value


def record_recovery(root, recovery_file):
    """Explicit failed-stage-only amendments; completed stage semantics stay frozen."""
    root = Path(root); proposal = read(recovery_file); stop = read(root/'stop.json')
    require(stop['kind'] == 'technical' and stop['stage'] in MODULES, 'No amendable failed model stage')
    name = stop['stage']; require(proposal['stage'] == name and proposal['reason'].strip(), 'Recovery stage/reason differs')
    expected = read(root/'contract.json')
    for path in sorted((root/'recoveries').glob('*.json')):
        expected.update(read(path).get('contract_changes', {}))
    actual = frozen_contract(); changed = {k: v for k, v in actual.items() if expected.get(k) != v}
    allowed = {f'src/skill_evolution/v23/{name}.py', f'src/skill_evolution/v23/{name}_prompt.md'}
    limits = proposal.get('input_limits')
    if limits is not None:
        require(set(proposal) <= {'stage', 'reason', 'input_limits', 'orchestrator_change'},
                'Capacity recovery cannot alter model parameters or other settings')
        require(set(limits) == {'max_input_chars', 'max_message_utf8_bytes'} and
                all(type(v) is int and v > 0 for v in limits.values()), 'Invalid recovery input limits')
        # Explicitly reviewed before/after content authorizes only this adapter.
        # All prompts, modules and Actor sources retain the original freeze.
        key = 'src/skill_evolution/v23/evolution.py'
        allowed = {key}
        approval = proposal.get('orchestrator_change')
        require(approval == ({'before': expected[key], 'after': actual[key]} if changed else None),
                'Capacity adapter change requires exact reviewed before/after content')
    require(set(changed) <= allowed and set(expected) == set(actual), 'Upstream/shared implementation changed; use a new Campaign')
    cfg = proposal.get('call_config')
    if cfg is not None:
        validation = deepcopy(_config(root)); validation['call_config'] = cfg; validate_config(validation)
    revisions = root/'recoveries'; revisions.mkdir(exist_ok=True)
    save(revisions/f'{len(list(revisions.glob("*.json")))+1:03}.json',
         {'stage': name, 'reason': proposal['reason'], 'stage_config': cfg,
          'input_limits': limits, 'previous_input_limits': {
              'max_input_chars': _config(root)['max_input_chars'],
              'max_message_utf8_bytes': message_byte_limit(_config(root))}, 'stop': stop,
          'contract_changes': changed, 'previous_content': {k: expected[k] for k in changed}, 'at': now()})


def _retryable(exc, directory):
    import requests
    if (directory/'http_status.json').exists():
        status = read(directory/'http_status.json')['status_code']
        if status >= 300:
            body = (directory/'http_response.txt').read_text(errors='replace')
            return status in {429, 500, 502, 503, 504} and not any(x in body for x in ('insufficient_quota', 'quota_exceeded'))
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    # Only failures after a response, not bad inputs or a broken persistence layer.
    return isinstance(exc, (ValueError, KeyError, IndexError, TypeError)) and (
        (directory/'response.json').exists() or (directory/'http_response.txt').exists())


def configuration_from_environment(config):
    """Resolve a new run before freezing it; never mutate a historical config."""
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env', override=False)
    base = os.environ.get('OPENAI_BASE_URL', '').rstrip('/')
    result = deepcopy(config)
    result['call_config'] = route_call_config(config['call_config'], base)
    for name, cfg in result.get('stage_configs', {}).items():
        result['stage_configs'][name] = route_call_config(cfg, base)
    if 'actor_model' in result:
        result['actor_model'] = model_for_endpoint(base, result['actor_model'])
        result['actor_base_url'] = base
    return result


def check_environment_route(config):
    require(configuration_from_environment(config) == config,
            'Configured endpoint/model differs from environment route; use a new Campaign/output directory')


def _generator(config):
    check_environment_route(config)
    cfg = config['call_config']
    base = os.environ.get('OPENAI_BASE_URL', '').rstrip('/')
    return grouping.live_generator(base_url=base, key=os.environ.get('OPENAI_API_KEY'),
        model=cfg['model'], max_tokens=cfg['max_tokens'], timeout=cfg['timeout_seconds'])


def _model_stage(root, rd, name, invoke, config, generate, resume):
    stage = rd/name; stage.mkdir(exist_ok=True)
    cfg = config.get('stage_configs', {}).get(name, config['call_config'])
    marker = stage/'result.json'
    def run(path, gen):
        _check_contract(root)
        return invoke(path, gen, cfg)
    if marker.exists():
        selected = read(marker)
        return stage/selected['path'], run(stage/selected['path'], None)
    attempts = stage/'attempts'; attempts.mkdir(exist_ok=True)
    existing = sorted(p for p in attempts.iterdir() if p.is_dir())
    # Recover a completed write or an interrupted response without a new API call.
    if existing and not (existing[-1]/'error.json').exists():
        last = existing[-1]
        meta = read(last/'run.json') if (last/'run.json').exists() else {}
        if meta.get('status') == 'valid':
            value = run(last, None)
            save(marker, {'path': str(last.relative_to(stage))}); return last, value
        if (last/'response.json').exists() or ((last/'http_response.txt').exists() and (last/'http_status.json').exists()):
            try:
                response = read(last/'response.json') if (last/'response.json').exists() else grouping.response_value(read(last/'http_response.txt'))
                require(meta.get('call_config') == cfg, 'Recovery parameters differ')
                def cached(messages, dest):
                    require(read(last/'messages.json') == messages, 'Recovery messages differ')
                    save(dest/'recovered_from.json', {'path': str(last), 'additional_requests': 0})
                    return response
                recovered = last/'recovered'
                value = run(recovered, cached)
                save(marker, {'path': str(recovered.relative_to(stage))}); return recovered, value
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                save(last/'error.json', {'type': type(exc).__name__, 'error': str(exc), 'recovery': True})
        else:
            save(last/'error.json', {'type': 'Interrupted', 'error': 'Request outcome/usage may be unknown', 'usage': None})
    if existing and not resume:
        raise Stopped(f'{name}: prior attempts require explicit resume')
    for offset in range(config['max_attempts']):
        path = attempts/f'{len(existing)+offset+1:03}'
        started = time.monotonic(); called = False
        def request(messages, dest):
            nonlocal called
            require(len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) <= message_byte_limit(config), 'Input exceeds frozen byte budget')
            called = True
            gen = generate if generate is not None else _generator({**config, 'call_config': cfg})
            return gen(messages, dest)
        try:
            value = run(path, request)
            save(path/'attempt.json', {'elapsed_seconds': time.monotonic()-started, 'request_invoked': called, 'at': now()})
            save(marker, {'path': str(path.relative_to(stage))})
            return path, value
        except Exception as exc:
            retry = called and _retryable(exc, path)
            save(path/'error.json', {'type': type(exc).__name__, 'error': str(exc), 'retryable': retry,
                 'elapsed_seconds': time.monotonic()-started, 'request_invoked': called, 'at': now()})
            if not retry or offset == config['max_attempts']-1:
                raise Stopped(f'{name}: {type(exc).__name__}: {exc}') from exc
            time.sleep(config.get('retry_delay_seconds', 0) * (offset+1))


def actor_task(task, skill_file, directory, config):
    """Use the existing ALFWorld runner; no task-level automatic restart."""
    check_environment_route(config)
    for filename, content in config.get('environment_files', {}).items():
        require(Path(filename).read_bytes().decode('utf-8') == content, 'Frozen environment file changed')
    split = task.split(':')[0]
    require(split in config.get('optimization_splits', ['train']), 'Task outside optimization pool')
    if 'task_items' in config:
        from src.adapters.alfworld.run_task import SPLIT_ROOT
        actual = next((item for item in read(SPLIT_ROOT/split/'items.json') if item['id'] == task), None)
        require(actual == config['task_items'][task], 'Frozen task mapping changed before execution')
    purpose = 'optimization' if 'val' in config.get('optimization_splits', []) else 'learning'
    cmd = [config['actor_python'], '-m', 'src.adapters.alfworld.run_task_skill', '--model', config['actor_model'],
           '--split', split, '--purpose', purpose, '--task-id', task, '--max-steps', str(config['max_steps']),
           '--request-attempts', str(config['actor_request_attempts']), '--strict-response', '--archive-responses',
           '--output-root', str(directory)]
    if skill_file is not None: cmd += ['--skill-file', str(skill_file)]
    save(directory/'command.json', cmd)
    process_env = os.environ.copy()
    if 'environment_root' in config:
        process_env['ALFWORLD_DATA'] = config['environment_root']
    if 'actor_base_url' in config:
        process_env['OPENAI_BASE_URL'] = config['actor_base_url']
    with (directory/'process.log').open('w') as out:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, env=process_env)
    paths = list(directory.rglob('trajectory.json'))
    require(len(paths) == 1, f'Actor exit {proc.returncode}: missing/ambiguous trajectory')
    return paths[0]


def _actors(root, rd, side, tasks, skill_file, config, runner, resume):
    expected = None if skill_file is None else Path(skill_file).read_bytes().decode('utf-8')
    stopped = Event()

    def execute(task):
        try:
            return one(task)
        except BaseException:
            stopped.set()
            raise

    def one(task):
        _check_contract(root)
        folder = rd/side/task.replace(':', '_'); folder.mkdir(parents=True, exist_ok=True)
        marker = folder/'result.json'
        def checked(path):
            record = read(path); facts = build_facts([record])
            require(record['task']['id'] == task and record['status'] in COMPLETE, 'Incomplete Actor task')
            require(facts['facts']['parent'] == expected, 'Actor used a different Skill')
            require(record['model'] == config['actor_model'], 'Actor model differs')
            if 'task_items' in config:
                require(record['task'] == config['task_items'][task], 'Frozen task identity differs')
                require(record['request_policy'] == {'max_attempts': 3, 'strict_response': True}, 'Actor retry policy differs')
            require(record['protocol'] == execution_protocol(config['max_steps']), 'Actor protocol differs')
            return record
        if marker.exists():
            path = Path(read(marker)['trajectory']); record = checked(path)
        else:
            attempts = folder/'attempts'; attempts.mkdir(exist_ok=True)
            previous = sorted(p for p in attempts.iterdir() if p.is_dir())
            path = None
            if previous:
                found = list(previous[-1].rglob('trajectory.json'))
                if len(found) == 1 and read(found[0]).get('status') in COMPLETE:
                    path = found[0]; record = checked(path)
                elif not resume:
                    raise Stopped(f'{side}/{task}: explicit resume needed')
            if path is None:
                dest = attempts/f'{len(previous)+1:03}'; dest.mkdir()
                path = Path(runner(task, skill_file, dest, config)).resolve()
                record = checked(path)
            save(marker, {'trajectory': str(path)})
        return str(path), record

    workers = min(config.get('actor_max_workers', 1), len(tasks))
    results, pending, index = {}, {}, 0
    # Threads only supervise independent Actor subprocesses. Never queue the whole batch:
    # a failed task stops replenishment; already started tasks finish and save their records.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        try:
            while index < len(tasks) or pending:
                while index < len(tasks) and len(pending) < workers and not stopped.is_set():
                    pending[pool.submit(execute, tasks[index])] = index
                    index += 1
                if not pending:
                    break
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                # Examine failures before submitting replacements for any completed task.
                for future in done:
                    if future.exception() is not None:
                        future.result()
                for future in done:
                    results[pending.pop(future)] = future.result()
        except BaseException:
            stopped.set()
            raise
    ordered = [results[i] for i in range(len(tasks))]
    return [path for path, _ in ordered], [record for _, record in ordered]


def _prepare_memory(source, dest):
    """Fork the immutable archive using hard links; only the local index changes."""
    source, dest = Path(source), Path(dest)
    memory.load_memory(source)
    base = read(source/'active.json')
    dest.mkdir(parents=True, exist_ok=True)
    if (dest/'base.json').exists():
        require(read(dest/'base.json') == {'source': str(source), 'state': base}, 'Memory base changed')
    else:
        save(dest/'base.json', {'source': str(source), 'state': base})
    (dest/'archive').mkdir(exist_ok=True)
    for cid in base['commits']:
        old, new = source/'archive'/f'{cid}.json', dest/'archive'/f'{cid}.json'
        if new.exists(): require(new.read_bytes() == old.read_bytes(), 'Immutable archive differs')
        else:
            try: os.link(old, new)
            except OSError: shutil.copyfile(old, new)
    if not (dest/'active.json').exists(): save(dest/'active.json', base)
    memory.load_memory(dest)


def run_round(campaign, *, generate=None, actor_runner=actor_task, resume=False, hook=None):
    """Run one round. Call via run_campaign for the single-writer process lock."""
    root = Path(campaign).resolve(); _check_contract(root); config = _config(root)
    state = read(root/'state.json'); number = state['next_round']
    if number > len(config['batches']): return {'status': 'complete'}
    if generate is None or actor_runner is actor_task:
        check_environment_route(config)
    rd = root/'rounds'/f'R{number:02}'; rd.mkdir(parents=True, exist_ok=True)
    rid = f'{root.name}_R{number:02}'
    frozen = {'round_id': rid, 'state': state, 'parent': _skill(root, state),
              'memory': memory.load_memory(root/state['active_memory']),
              'tasks': config['batches'][number-1], 'config': read(root/'config.json')}
    if (rd/'round_input.json').exists(): require(read(rd/'round_input.json') == frozen, 'Round input changed')
    else: save(rd/'round_input.json', frozen)
    if frozen['parent'] is not None:
        pfile = rd/'parent.md'
        if pfile.exists(): require(pfile.read_bytes().decode('utf-8') == frozen['parent'], 'Parent snapshot changed')
        else: pfile.write_bytes(frozen['parent'].encode())
    else: pfile = None
    stage = 'parent_runs'
    def checkpoint(name):
        nonlocal stage
        stage = name; save(rd/'progress.json', {'stage': name, 'at': now()})
        if hook: hook(name)
    def model(name, invoke):
        checkpoint(name)
        return _model_stage(root, rd, name, invoke, config, generate, resume)
    def publish(parent, mem, outcome):
        next_state = {'next_round': number+1, 'parent': parent, 'active_memory': mem}
        memory.load_memory(root/mem)
        if parent is not None: require(bool((root/parent).read_text().strip()), 'Missing next Parent')
        save(rd/'result.json', {'status': 'completed', 'outcome': outcome, 'before': state, 'after': next_state})
        checkpoint('before_publish')
        require(read(root/'state.json') == state, 'Official state changed during round')
        save(root/'state.json', next_state)
        if hook: hook('after_publish')
        return read(rd/'result.json')
    try:
        checkpoint('parent_runs')
        pp, pr = _actors(root, rd, 'parent_runs', frozen['tasks'], pfile, config, actor_runner, resume)
        opts = {'max_input_chars': config['max_input_chars']}
        gp, g = model('grouping', lambda path, gen, cfg: grouping.run_grouping(pr, path, round_id=rid, generate=gen, call_config=cfg, **opts))
        dp, d = model('diagnosis', lambda path, gen, cfg: diagnosis.run_diagnosis(gp, path, generate=gen, call_config=cfg, **opts))
        decision = d['diagnosis']['decision']
        if decision == 'no_change': return publish(state['parent'], state['active_memory'], 'no_change')
        if decision == 'need_evidence': raise Stopped('semantic: Diagnosis need_evidence')
        cp, c = model('preconditioner', lambda path, gen, cfg: preconditioner.run_preconditioner(gp, dp, path, generate=gen, call_config=cfg, memory=frozen['memory'], **opts))
        decision = c['preconditioner']['decision']
        if decision == 'no_change': return publish(state['parent'], state['active_memory'], 'no_change')
        if decision == 'need_evidence': raise Stopped('semantic: Preconditioner need_evidence')
        ep, e = model('editor', lambda path, gen, cfg: editor.run_editor(cp, path, generate=gen, call_config=cfg, **opts))
        if e['editor_status'] == 'no_change': return publish(state['parent'], state['active_memory'], 'no_change')
        if e['editor_status'] == 'needs_revision': raise Stopped('semantic: Editor needs_revision')
        checkpoint('candidate_runs')
        qp, qr = _actors(root, rd, 'candidate_runs', frozen['tasks'], ep/'candidate.md', config, actor_runner, resume)
        checkpoint('pairs')
        bundle = replay.build_replay(ep, pr, qr, memory=frozen['memory'])
        bundle['record_paths'] = {'parent': pp, 'candidate': qp}
        paired = gate.build_gate(pr, qr, frozen['tasks'], parent_skill=frozen['parent'], candidate_skill=e['candidate_text'])
        if (rd/'pairs/input.json').exists(): require(read(rd/'pairs/input.json') == bundle, 'Paired evidence changed')
        else: save(rd/'pairs/input.json', bundle)
        checkpoint('gate')
        gfile = rd/'gate/result.json'
        if gfile.exists():
            gout = read(gfile); require(gout['input'] == paired, 'Gate input changed')
            require(gout['result'] == gate.decide_gate(paired['input'], frozen['tasks']), 'Gate result invalid')
        else:
            gout = {'input': paired, 'result': gate.decide_gate(paired['input'], frozen['tasks'])}; save(gfile, gout)
        rp, r = model('replay', lambda path, gen, cfg: replay.run_replay(bundle, path, generate=gen, call_config=cfg, **opts))
        checkpoint('memory')
        _prepare_memory(root/state['active_memory'], rd/'memory')
        memory.commit_memory(rd/'memory', context_id=rid, context=bundle, result=r['replay'])
        save(rd/'memory/view.json', memory.load_memory(rd/'memory'))
        checkpoint('memory_prepared')
        selected = str((ep/'candidate.md').relative_to(root)) if gout['result']['decision'] == 'ACCEPT' else state['parent']
        return publish(selected, str((rd/'memory').relative_to(root)), gout['result']['decision'])
    except (Exception, KeyboardInterrupt) as exc:
        stop = {'round': number, 'stage': stage, 'kind': 'semantic' if str(exc).startswith('semantic:') else 'technical',
                'error_type': type(exc).__name__, 'error': str(exc), 'at': now()}
        save(rd/'stop.json', stop); save(root/'stop.json', stop)
        raise


def resume_round(campaign, **kwargs):
    return run_round(campaign, resume=True, **kwargs)


def run_campaign(campaign, *, config=None, resume=False, recovery_file=None, **kwargs):
    root = Path(campaign).resolve(); root.mkdir(parents=True, exist_ok=True)
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if config is not None:
            if not (root/'config.json').exists() and (
                    kwargs.get('generate') is None or kwargs.get('actor_runner', actor_task) is actor_task):
                config = configuration_from_environment(config)
            initialize(root, config)
        if (root/'stop.json').exists():
            stop = read(root/'stop.json')
            if read(root/'state.json')['next_round'] <= stop['round']:
                require(resume, 'Stopped Campaign requires explicit resume')
                require(stop['kind'] != 'semantic', 'Semantic blocker requires upstream revision; no resampling')
        if recovery_file is not None:
            require(resume, 'Recovery changes require resume'); record_recovery(root, recovery_file)
        session = root/'sessions'; session.mkdir(exist_ok=True)
        save(session/f'{len(list(session.glob("*.json")))+1:03}.json', {'resume': resume, 'at': now()})
        _check_contract(root)
        while read(root/'state.json')['next_round'] <= len(_config(root)['batches']):
            result = run_round(root, resume=resume, **kwargs)
            if result.get('outcome') == 'no_change' and not _config(root)['continue_no_change']:
                return result
        return {'status': 'complete', 'state': read(root/'state.json')}


def cost_summary(campaign):
    """Include failed/unknown HTTP requests; recovered parses are not new calls."""
    root = Path(campaign); usages = []; actor_calls = 0; model_calls = 0
    for path in root.rglob('trajectory.json'):
        for step in read(path).get('steps', []):
            for attempt in step.get('transport_attempts', []):
                actor_calls += 1; usages.append(attempt.get('usage'))
    for path in root.rglob('request.json'):
        if 'recovered' in path.parts: continue
        model_calls += 1; directory = path.parent
        usage = None
        if (directory/'http_response.txt').exists():
            try: usage = read(directory/'http_response.txt').get('usage')
            except (ValueError, AttributeError): pass
        elif (directory/'response.json').exists(): usage = read(directory/'response.json').get('usage')
        usages.append(usage)
    known = [u for u in usages if isinstance(u, dict)]
    result = {'actor_http_requests': actor_calls, 'module_http_requests': model_calls,
              'unknown_usage_requests': sum(not isinstance(u, dict) for u in usages)}
    for field in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
        result[field+'_known'] = sum(u.get(field, 0) or 0 for u in known)
    result['reasoning_tokens_known'] = sum((u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) or 0 for u in known)
    result['reasoning_usage_missing'] = sum('reasoning_tokens' not in (u.get('completion_tokens_details') or {}) for u in known)
    return result


def status(campaign):
    root = Path(campaign)
    state = read(root/'state.json')
    rounds = {}
    for rd in sorted((root/'rounds').glob('R*')):
        rounds[rd.name] = {'progress': read(rd/'progress.json') if (rd/'progress.json').exists() else None,
            'result': read(rd/'result.json') if (rd/'result.json').exists() else None,
            'attempts': {name: len(list((rd/name/'attempts').glob('[0-9]*'))) for name in MODULES}}
    return {'cost': cost_summary(root), 'state': state, 'stop': read(root/'stop.json') if (root/'stop.json').exists() else None, 'rounds': rounds}


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['run', 'resume', 'status']); p.add_argument('--campaign', required=True)
    p.add_argument('--config'); p.add_argument('--recovery')
    args = p.parse_args()
    if args.action == 'status': result = status(args.campaign)
    else: result = run_campaign(args.campaign, config=read(args.config) if args.config else None,
                                resume=args.action == 'resume', recovery_file=args.recovery)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
