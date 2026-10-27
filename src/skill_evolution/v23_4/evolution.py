"""V23.4 Campaign: explicit method freeze, multi-Knowledge and atomic publication.

Versioned from the V23 orchestrator; legacy entry points and archives are untouched."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
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
from src.skill_evolution.v23 import grouping, memory, gate, prompts
from . import diagnosis, preconditioner, editor, replay, output_budget
from src.skill_evolution.v23_3.memory_view import FORMAT as MEMORY_VIEW
from .update_patch import CONTRACT_VERSION
from src.skill_evolution.v23.facts import build_facts, require, COMPLETE
from src.skill_evolution.v23.model_routing import model_for_endpoint

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


MEMORY_CONTRACT = memory.MULTI_KNOWLEDGE_CONTRACT
METHOD = {
    'version': 'v23_4_campaign_v1',
    'grouping': 'v23',
    'editor': 'v23_4_effective_plan_boundary_shared_v23_editor',
    'gate': gate.RULE,
    'diagnosis_version': diagnosis.PROMPT_VERSION,
    'preconditioner_contract': CONTRACT_VERSION,
    'memory_contract': MEMORY_CONTRACT,
    'memory_view': MEMORY_VIEW,
    'replay_input_view': replay.INPUT_VIEW,
    'replay_prompt_version': replay.LEARNING_PROMPT_VERSION,
    'memory_publication': 'validated_replay_after_accept_or_retain_next_round',
    'semantic_resampling': False,
}


def frozen_contract():
    """Freeze live modules, shared parsers, every composed Prompt and Actor assets."""
    from src.adapters.alfworld.run_task_upstream import PROTOCOL_ROOT
    paths = {ROOT/'src/skill_evolution/v22/diagnosis_editor.py'}
    for version in ('v23', 'v23_3', 'v23_4'):
        directory = ROOT/'src/skill_evolution'/version
        paths.update(directory.glob('*.py'))
        paths.update(p for p in directory.glob('*.md') if 'prompt' in p.name)
    paths.add(prompts.CONTEXT_PATH)
    paths.update((ROOT/'src/adapters/alfworld').glob('*.py'))
    paths.update(p for p in PROTOCOL_ROOT.iterdir() if p.is_file())
    return {str(p.relative_to(ROOT)): p.read_bytes().decode('utf-8') for p in sorted(paths)}


def message_byte_limit(config):
    """Accept the explicit name while retaining old frozen configurations."""
    limit = config.get('max_message_utf8_bytes', config.get('max_input_bytes'))
    require(type(limit) is int and limit > 0, 'Invalid message byte capacity')
    if 'max_message_utf8_bytes' in config and 'max_input_bytes' in config:
        require(limit == config['max_input_bytes'], 'Conflicting message byte capacities')
    return limit


def validate_config(config):
    require(config.get('method') == METHOD, 'Unsupported or missing V23.4 method freeze')
    require(not config.get('stage_configs'), 'Campaign v1 has one frozen module configuration')
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
    runtime = runtime_snapshot(config)
    if runtime is not None:
        if (root/'runtime.json').exists():
            require(read(root/'runtime.json') == runtime, 'Frozen runtime changed')
        else:
            require(not (root/'state.json').exists(), 'Missing frozen runtime')
            save(root/'runtime.json', runtime)
    if not (root/'state.json').exists():
        require(not (root/'rounds').exists(), 'Missing official state in started Campaign')
        save(root/'initial_memory/active.json', {'active_ids': [], 'commits': []})
        save(root/'state.json', {'next_round': 1, 'parent': None, 'active_memory': 'initial_memory'})
    return root


def runtime_snapshot(config):
    # Synthetic runners use a nonexistent interpreter; real runs freeze installed packages.
    if not Path(config['actor_python']).is_file():
        return None
    code = ('import importlib.metadata as m,json,sys; '
            'print(json.dumps({"python":sys.version,"packages":{n:m.version(n) '
            'for n in ["alfworld","textworld","numpy","requests"]}}))')
    return json.loads(subprocess.check_output([config['actor_python'], '-c', code], text=True))


def check_runtime(root):
    if (root/'runtime.json').exists():
        require(read(root/'runtime.json') == runtime_snapshot(read(root/'config.json')), 'Frozen runtime changed')


def _skill(root, state):
    return None if state['parent'] is None else (root/state['parent']).read_bytes().decode('utf-8')


def final_parent(campaign):
    """Read the officially retained Skill only after every frozen round is published."""
    root = Path(campaign).resolve()
    _check_contract(root)
    check_runtime(root)
    config, state = _config(root), read(root/'state.json')
    require(state['next_round'] == len(config['batches']) + 1, 'Campaign is not complete')
    previous = {'next_round': 1, 'parent': None, 'active_memory': 'initial_memory'}
    for number in range(1, state['next_round']):
        result = read(root/'rounds'/f'R{number:02}'/'result.json')
        require(result['status'] == 'completed' and result['before'] == previous,
                'Missing or inconsistent round publication')
        after = result['after']
        require(after['next_round'] == number + 1, 'Round sequence differs')
        rd = root/'rounds'/f'R{number:02}'
        if result['outcome'] in ('ACCEPT', 'RETAIN'):
            selected = read(rd/'editor/result.json')
            ep = rd/'editor'/selected['path']
            editor.load_editor(ep)
            expected = str((ep/'candidate.md').relative_to(root)) if result['outcome'] == 'ACCEPT' else previous['parent']
            require(after['parent'] == expected and after['active_memory'] == str((rd/'memory').relative_to(root)),
                    'Final selection differs from round result')
            gate_result = read(rd/'gate/result.json')
            require(gate_result['result'] == gate.decide_gate(gate_result['input']['input'], config['batches'][number-1])
                    and gate_result['result']['decision'] == result['outcome'], 'Gate selection differs')
        else:
            require(result['outcome'] == 'no_change' and after['parent'] == previous['parent']
                    and after['active_memory'] == previous['active_memory'], 'No-change state differs')
        memory.load_memory(root/after['active_memory'], memory_contract=MEMORY_CONTRACT)
        previous = after
    require(previous == state, 'Final publication differs from official state')
    if state['parent'] is None:
        return None
    path = root/state['parent']
    require(bool(path.read_bytes().decode('utf-8').strip()), 'Missing final Parent')
    return path


def _check_contract(root):
    require(not list((root/'recoveries').glob('*.json')), 'V23.4 freeze cannot be amended in place')
    approved = root/output_budget.DIRECTORY/'contract.json' if output_budget.amendment(root) else root/'contract.json'
    require(read(approved) == frozen_contract(), 'Frozen source/Prompt changed; use a new Campaign')


def _config(root):
    value = read(root/'config.json')
    require(value == read(root/'initial_config.json'), 'Frozen config changed')
    validate_config(value)
    return value


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


def check_environment_route(config):
    """Endpoint is frozen explicitly; process .env cannot silently choose the method."""
    cfg = config['call_config']
    base = cfg['endpoint'].removesuffix('/chat/completions')
    require(cfg['model'] == model_for_endpoint(base, cfg['model']), 'Frozen model/endpoint mismatch')
    require(config['actor_base_url'] == base and config['actor_model'] == cfg['model'],
            'Actor/module route differs')


def check_live_environment(config):
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env', override=False)
    check_environment_route(config)
    cfg = config['call_config']
    require(os.environ.get('OPENAI_BASE_URL', '').rstrip('/') == cfg['endpoint'].removesuffix('/chat/completions'),
            'Live endpoint differs from frozen Campaign; configure matching endpoint and credentials explicitly')
    require(bool(os.environ.get('OPENAI_API_KEY')), 'API key is not configured')


def _generator(config):
    check_live_environment(config)
    cfg = config['call_config']
    return grouping.live_generator(base_url=cfg['endpoint'].removesuffix('/chat/completions'),
        key=os.environ.get('OPENAI_API_KEY'), model=cfg['model'],
        max_tokens=cfg['max_tokens'], timeout=cfg['timeout_seconds'])


def _model_stage(root, rd, name, invoke, config, generate, resume):
    stage = rd/name; stage.mkdir(exist_ok=True)
    cfg = config.get('stage_configs', {}).get(name, config['call_config'])
    base_cfg = dict(cfg)
    adaptive = output_budget.amendment(root) is not None
    marker = stage/'result.json'
    def run(path, gen):
        _check_contract(root)
        return invoke(path, gen, cfg)
    def saved_config(path):
        value = read(path/'run.json')['call_config']
        expected = dict(base_cfg)
        if adaptive:
            expected['max_tokens'] = output_budget.module_budget(stage/'attempts', base_cfg['max_tokens'],
                before=path.relative_to(stage/'attempts').parts[0])[0]
        require(value == expected, 'Saved call configuration differs from authorized budget')
        return value
    if marker.exists():
        selected = read(marker)
        cfg = saved_config(stage/selected['path'])
        return stage/selected['path'], run(stage/selected['path'], None)
    attempts = stage/'attempts'; attempts.mkdir(exist_ok=True)
    existing = sorted(p for p in attempts.iterdir() if p.is_dir())
    # Recover a completed write or an interrupted response without a new API call.
    if existing and not (existing[-1]/'error.json').exists():
        last = existing[-1]
        if (last/'run.json').exists(): cfg = saved_config(last)
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
    offset, ordinary_failures = 0, 0
    while True:
        path = attempts/f'{len(existing)+offset+1:03}'
        cfg = dict(base_cfg)
        if adaptive:
            cfg['max_tokens'], streak = output_budget.module_budget(attempts, base_cfg['max_tokens'])
        started = time.monotonic(); called = False
        def request(messages, dest):
            nonlocal called
            require(len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) <= message_byte_limit(config), 'Input exceeds frozen byte budget')
            called = True
            gen = generate if generate is not None else _generator({**config, 'call_config': cfg})
            if adaptive:
                save(dest/'output_budget.json', {'policy': output_budget.POLICY, 'max_tokens': cfg['max_tokens'],
                     'prior_consecutive_length_responses': streak, 'at': now()})
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
            length_retry = adaptive and retry and output_budget.is_length(path)
            if not length_retry: ordinary_failures += 1
            if not retry or (not adaptive and offset == config['max_attempts']-1) or ordinary_failures >= config['max_attempts']:
                raise Stopped(f'{name}: {type(exc).__name__}: {exc}') from exc
            time.sleep(config.get('retry_delay_seconds', 0) * (offset+1))
            offset += 1


def actor_task(task, skill_file, directory, config):
    """Use the existing ALFWorld runner; no task-level automatic restart."""
    check_live_environment(config)
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
    if config.get('_output_budget_campaign'):
        cmd[2] = 'src.skill_evolution.v23_4.budget_actor'
        cmd += ['--budget-campaign', config['_output_budget_campaign']]
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
            if record.get('output_budget_policy'):
                require(output_budget.amendment(Path(config.get('_output_budget_campaign', root))) is not None,
                        'Actor recovery is not authorized')
                output_budget.validate_actor(path, record)
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
                actor_cfg = dict(config)
                if output_budget.amendment(root): actor_cfg['_output_budget_campaign'] = str(root)
                path = Path(runner(task, skill_file, dest, actor_cfg)).resolve()
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
    memory.load_memory(source, memory_contract=MEMORY_CONTRACT)
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
    memory.load_memory(dest, memory_contract=MEMORY_CONTRACT)


def run_round(campaign, *, generate=None, actor_runner=actor_task, resume=False, hook=None):
    """Run one round. Call via run_campaign for the single-writer process lock."""
    root = Path(campaign).resolve(); _check_contract(root); config = _config(root)
    state = read(root/'state.json'); number = state['next_round']
    if number > len(config['batches']): return {'status': 'complete'}
    if generate is None or actor_runner is actor_task:
        check_live_environment(config)
    rd = root/'rounds'/f'R{number:02}'; rd.mkdir(parents=True, exist_ok=True)
    rid = f'{root.name}_R{number:02}'
    frozen = {'round_id': rid, 'state': state, 'parent': _skill(root, state),
              'memory': memory.load_memory(root/state['active_memory'], memory_contract=MEMORY_CONTRACT),
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
        memory.load_memory(root/mem, memory_contract=MEMORY_CONTRACT)
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
        cp, c = model('preconditioner', lambda path, gen, cfg: preconditioner.run_preconditioner(gp, dp, path, generate=gen, call_config=cfg, memory=frozen['memory'], memory_contract=MEMORY_CONTRACT,
            memory_view=MEMORY_VIEW, diagnosis_version='v23_4', **opts))
        if c['effective_plan'] is None:
            return publish(state['parent'], state['active_memory'], 'no_change')
        ep, e = model('editor', lambda path, gen, cfg: editor.run_editor(cp, path, generate=gen, call_config=cfg, **opts))
        if e['editor_status'] == 'no_change': return publish(state['parent'], state['active_memory'], 'no_change')
        if e['editor_status'] == 'needs_revision': raise Stopped('semantic: Editor needs_revision')
        checkpoint('candidate_runs')
        qp, qr = _actors(root, rd, 'candidate_runs', frozen['tasks'], ep/'candidate.md', config, actor_runner, resume)
        checkpoint('pairs')
        review = output_budget.implementation_review(root, pr, qr)
        bundle = replay.build_replay(ep, pr, qr, memory=frozen['memory'], memory_contract=MEMORY_CONTRACT,
                                    implementation_review=review)
        bundle['record_paths'] = {'parent': pp, 'candidate': qp}
        paired = gate.build_gate(pr, qr, frozen['tasks'], parent_skill=frozen['parent'], candidate_skill=e['candidate_text'],
                                 implementation_review=review)
        if (rd/'pairs/input.json').exists(): require(read(rd/'pairs/input.json') == bundle, 'Paired evidence changed')
        else: save(rd/'pairs/input.json', bundle)
        checkpoint('gate')
        gfile = rd/'gate/result.json'
        if gfile.exists():
            gout = read(gfile); require(gout['input'] == paired, 'Gate input changed')
            require(gout['result'] == gate.decide_gate(paired['input'], frozen['tasks']), 'Gate result invalid')
        else:
            gout = {'input': paired, 'result': gate.decide_gate(paired['input'], frozen['tasks'])}; save(gfile, gout)
        history = replay.history_pair_sources(root/state['active_memory'], frozen['memory'],
                                              memory_contract=MEMORY_CONTRACT)
        rp, r = model('replay', lambda path, gen, cfg: replay.run_replay(
            bundle, path, generate=gen, call_config=cfg, memory_contract=MEMORY_CONTRACT,
            input_view=replay.INPUT_VIEW, history_sources=history,
            prompt_version=config['method']['replay_prompt_version'], **opts))
        checkpoint('memory')
        _prepare_memory(root/state['active_memory'], rd/'memory')
        memory.commit_memory(rd/'memory', context_id=rid, context=bundle, result=r['replay'], memory_contract=MEMORY_CONTRACT)
        save(rd/'memory/view.json', memory.load_memory(rd/'memory', memory_contract=MEMORY_CONTRACT))
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


def run_campaign(campaign, *, config=None, resume=False, **kwargs):
    root = Path(campaign).resolve(); root.mkdir(parents=True, exist_ok=True)
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if config is not None:
            initialize(root, config)
        if (root/'stop.json').exists():
            stop = read(root/'stop.json')
            if read(root/'state.json')['next_round'] <= stop['round']:
                require(resume, 'Stopped Campaign requires explicit resume')
                require(stop['kind'] != 'semantic', 'Semantic blocker requires upstream revision; no resampling')
        session = root/'sessions'; session.mkdir(exist_ok=True)
        save(session/f'{len(list(session.glob("*.json")))+1:03}.json', {'resume': resume, 'at': now()})
        _check_contract(root)
        check_runtime(root)
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
    result = {'cost': cost_summary(root), 'state': state, 'stop': read(root/'stop.json') if (root/'stop.json').exists() else None, 'rounds': rounds}
    if output_budget.amendment(root): result['output_budget_policy'] = output_budget.POLICY
    return result


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['run', 'resume', 'status', 'enable-output-budget-recovery']); p.add_argument('--campaign', required=True)
    p.add_argument('--config')
    args = p.parse_args()
    if args.action == 'enable-output-budget-recovery':
        root = Path(args.campaign).resolve()
        with (root/'.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = output_budget.enable(root, frozen_contract(), reason='Explicit user authorization on 2026-10-23: '
                'double current Preconditioner budget after six truncations; apply six-length-then-double to all modules and Actor steps.')
    elif args.action == 'status': result = status(args.campaign)
    else: result = run_campaign(args.campaign, config=read(args.config) if args.config else None,
                                resume=args.action == 'resume')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
