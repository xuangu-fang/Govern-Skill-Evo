from .facts import build_facts
"""V23.5 Campaign: explicit method freeze, multi-Knowledge and atomic publication.

Versioned from the V23 orchestrator; legacy entry points and archives are untouched."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
from threading import Event

from .storage import write_record
from .benchmark import current as benchmark_current
from contextvars import copy_context
from src.skill_evolution.v24.contracts import memory, gate
from . import grouping, diagnosis, preconditioner, editor, replay
from . import knowledge_review
from .config import method_config, validate_method
from .memory_view import KNOWLEDGE_ONLY
from src.skill_evolution.v24.facts import require
from src.skill_evolution.v24.contracts.model_routing import model_for_endpoint

MODULES = {'grouping': grouping, 'diagnosis': diagnosis, 'preconditioner': preconditioner,
           'editor': editor, 'replay': replay}
REVIEW_MODULES = {'verifier': knowledge_review, 'repair': knowledge_review}
ROOT = Path(__file__).resolve().parents[3]


def enabled_modules(config):
    return {**MODULES, **(REVIEW_MODULES if config['method'].get('knowledge_review') else {})}


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
METHOD = method_config()


def frozen_contract():
    directory = Path(__file__).parent
    paths = {p for p in directory.rglob('*') if p.is_file() and p.suffix in {'.py', '.md', '.json'}
             and 'benchmarks' not in p.relative_to(directory).parts}
    result = {str(p.relative_to(ROOT)): p.read_bytes().decode('utf-8') for p in sorted(paths)}
    result.update(benchmark_current().frozen_files())
    return dict(sorted(result.items()))


def message_byte_limit(config):
    """Accept the explicit name while retaining old frozen configurations."""
    limit = config.get('max_message_utf8_bytes', config.get('max_input_bytes'))
    require(type(limit) is int and limit > 0, 'Invalid message byte capacity')
    if 'max_message_utf8_bytes' in config and 'max_input_bytes' in config:
        require(limit == config['max_input_bytes'], 'Conflicting message byte capacities')
    return limit


def validate_config(config):
    validate_method(config.get('method'))
    benchmark_current().validate_config(config)
    require(not config.get('stage_configs'), 'Use module_max_tokens for per-module output budgets')
    budgets = config.get('module_max_tokens', {})
    require(isinstance(budgets, dict) and set(budgets) <= set(enabled_modules(config)), 'Unknown module output budget')
    require(all(type(v) is int and v > 0 for v in budgets.values()), 'Invalid module output budget')
    workers = config.get('actor_max_workers', 1)
    require(type(workers) is int and workers > 0, 'actor_max_workers must be a positive integer')
    require(isinstance(config['batches'], list) and bool(config['batches']), 'Missing batches')
    ids = [t for batch in config['batches'] for t in batch]
    require(all(isinstance(b, list) and b for b in config['batches']), 'Empty batch')
    schedule = config.get('epoch_schedule')
    if schedule is None:
        require(len(ids) == len(set(ids)), 'Tasks must be distinct across this Campaign')
    else:
        require(isinstance(schedule, dict), 'Invalid epoch schedule')
        epochs, rounds = schedule.get('epochs'), schedule.get('round_epochs')
        require(type(epochs) is int and epochs > 0, 'Invalid epoch count')
        require(isinstance(rounds, list) and len(rounds) == len(config['batches'])
                and all(type(e) is int for e in rounds)
                and rounds == sorted(rounds) and set(rounds) == set(range(1, epochs + 1)),
                'Invalid round epoch mapping')
        batch_size = schedule.get('batch_size')
        require(type(batch_size) is int and batch_size > 0
                and all(len(b) <= batch_size for b in config['batches']), 'Invalid epoch batch size')
        pool = set(ids)
        for epoch in range(1, epochs + 1):
            tasks = [t for e, batch in zip(rounds, config['batches']) if e == epoch for t in batch]
            require(len(tasks) == len(set(tasks)) and set(tasks) == pool,
                    'Each epoch must contain every optimization task exactly once')
    initial = config.get('initial_skill')
    if initial is not None:
        require(isinstance(initial, dict) and isinstance(initial.get('text'), str)
                and bool(initial['text'].strip()), 'Initial Skill must be nonempty')
    for key in ('max_attempts', 'actor_request_attempts'):
        require(type(config[key]) is int and 1 <= config[key] <= 6,
                f'{key} must be 1..6 total attempts (initial request included)')
    require(type(config['continue_no_change']) is bool, 'Missing no-change policy')
    require(type(config['max_input_chars']) is int and config['max_input_chars'] > 0, 'Invalid input capacity')
    message_byte_limit(config)
    require(config['call_config'] == grouping.call_configuration(
        base_url=config['call_config']['endpoint'].removesuffix('/chat/completions'),
        model=config['call_config']['model'], max_tokens=config['call_config']['max_tokens'],
        timeout=config['call_config']['timeout_seconds']), 'Unsupported module configuration')


def initial_state(config):
    return {'next_round': 1, 'parent': 'initial_skill.md' if config.get('initial_skill') else None,
            'active_memory': 'initial_memory'}


def check_initial_skill(root, config):
    if config.get('initial_skill'):
        path = root/'initial_skill.md'
        require(path.is_file() and path.read_bytes() == config['initial_skill']['text'].encode('utf-8'),
                'Frozen initial Skill changed or missing')


def initialize(campaign, config):
    """Freeze optional initial Skill content and start with empty Memory."""
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
        if config.get('initial_skill'):
            path = root/'initial_skill.md'
            if not path.exists():
                path.write_bytes(config['initial_skill']['text'].encode('utf-8'))
            check_initial_skill(root, config)
        save(root/'initial_memory/active.json', {'active_ids': [], 'commits': []})
        save(root/'state.json', initial_state(config))
    check_initial_skill(root, config)
    return root


def runtime_snapshot(config):
    return benchmark_current().runtime_snapshot(config)


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
    previous = initial_state(config)
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
        if config['method'].get('knowledge_review') and result['outcome'] in ('ACCEPT', 'RETAIN'):
            bundle = read(rd/'pairs/input.json')
            selected = read(rd/'replay/result.json')
            candidate = replay.load_replay(rd/'replay'/selected['path'])['replay']
            def load_model(name, invoke):
                selected_path = rd/name/read(rd/name/'result.json')['path']
                return selected_path, invoke(selected_path, None, stage_call_config(config, name))
            require((rd/'knowledge_review/result.json').exists() and (rd/'knowledge_review/candidate.json').exists(),
                    'Missing Knowledge review before publication')
            checked = knowledge_review.review(bundle, candidate, root/previous['active_memory'],
                rd/'knowledge_review', model=load_model, max_input_chars=config['max_input_chars'])
            committed = read(rd/'memory/archive'/f'{root.name}_R{number:02}.json')
            require(committed['result'] == checked, 'Memory differs from reviewed candidate')
        previous = after
    require(previous == state, 'Final publication differs from official state')
    if state['parent'] is None:
        return None
    path = root/state['parent']
    require(bool(path.read_bytes().decode('utf-8').strip()), 'Missing final Parent')
    return path


def _check_contract(root):
    require(not list((root/'recoveries').glob('*.json')) and not list((root/'amendments').rglob('*.json')),
            'V24 baseline does not permit runtime amendments')
    require(read(root/'contract.json') == frozen_contract(), 'Frozen source/Prompt changed; use a new Campaign')


def _config(root):
    value = read(root/'config.json')
    require(value == read(root/'initial_config.json'), 'Frozen config changed')
    validate_config(value)
    check_initial_skill(root, value)
    return value


def _retryable(exc, directory):
    import requests
    if (directory/'http_status.json').exists():
        status = read(directory/'http_status.json')['status_code']
        if status >= 300:
            body = (directory/'http_response.txt').read_text(errors='replace')
            return status == 401 or (status in {429, 500, 502, 503, 504} and not any(x in body for x in ('insufficient_quota', 'quota_exceeded')))
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


def stage_call_config(config, name):
    require(name in enabled_modules(config), 'Unknown model stage')
    cfg = dict(config['call_config'])
    cfg['max_tokens'] = config.get('module_max_tokens', {}).get(name, cfg['max_tokens'])
    return cfg


def _generator(config):
    check_live_environment(config)
    cfg = config['call_config']
    return grouping.live_generator(base_url=cfg['endpoint'].removesuffix('/chat/completions'),
        key=os.environ.get('OPENAI_API_KEY'), model=cfg['model'],
        max_tokens=cfg['max_tokens'], timeout=cfg['timeout_seconds'])


def _model_stage(root, rd, name, invoke, config, generate, resume):
    from .feedback_retry import run_stage
    return run_stage(root, rd, name, invoke, config, generate, resume)


def actor_command(task, skill_file, directory, config, *, final=False):
    return benchmark_current().actor_command(task, skill_file, directory, config, final=final)


def actor_task(task, skill_file, directory, config, *, final=False):
    return benchmark_current().actor_task(task, skill_file, directory, config, final=final)


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
            return benchmark_current().check_record(read(path), task, expected, config)
        if marker.exists():
            path = Path(read(marker)['trajectory']); record = checked(path)
        else:
            attempts = folder/'attempts'; attempts.mkdir(exist_ok=True)
            previous = sorted(p for p in attempts.iterdir() if p.is_dir())
            path = None
            if previous:
                found = list(previous[-1].rglob('trajectory.json'))
                if len(found) == 1 and benchmark_current().is_complete(read(found[0])):
                    path = found[0]; record = checked(path)
                elif not resume:
                    raise Stopped(f'{side}/{task}: explicit resume needed')
            if path is None:
                dest = attempts/f'{len(previous)+1:03}'; dest.mkdir()
                actor_cfg = dict(config)
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
                    pending[pool.submit(copy_context().run, execute, tasks[index])] = index
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
            memory_view=config['method']['memory_view'], diagnosis_version='v23_5', **opts))
        if c['effective_plan'] is None:
            return publish(state['parent'], state['active_memory'], 'no_change')
        ep, e = model('editor', lambda path, gen, cfg: editor.run_editor(cp, path, generate=gen, call_config=cfg, **opts))
        if e['editor_status'] == 'no_change': return publish(state['parent'], state['active_memory'], 'no_change')
        if e['editor_status'] == 'needs_revision': raise Stopped('semantic: Editor needs_revision')
        checkpoint('candidate_runs')
        qp, qr = _actors(root, rd, 'candidate_runs', frozen['tasks'], ep/'candidate.md', config, actor_runner, resume)
        checkpoint('pairs')
        review = None  # This frozen baseline has no runtime amendments.
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
        history = ({} if config['method']['memory_view'] == KNOWLEDGE_ONLY else
                   replay.history_pair_sources(root/state['active_memory'], frozen['memory'],
                                               memory_contract=MEMORY_CONTRACT))
        rp, r = model('replay', lambda path, gen, cfg: replay.run_replay(
            bundle, path, generate=gen, call_config=cfg, memory_contract=MEMORY_CONTRACT,
            input_view=config['method']['replay_input_view'], history_sources=history,
            prompt_version=config['method']['replay_prompt_version'], **opts))
        candidate = r['replay']
        if config['method'].get('knowledge_review'):
            checkpoint('knowledge_review')
            candidate = knowledge_review.review(bundle, candidate, root/state['active_memory'],
                rd/'knowledge_review', model=model, max_input_chars=config['max_input_chars'])
        checkpoint('memory')
        _prepare_memory(root/state['active_memory'], rd/'memory')
        memory.commit_memory(rd/'memory', context_id=rid, context=bundle, result=candidate, memory_contract=MEMORY_CONTRACT)
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
            'attempts': {name: len(list((rd/name/'attempts').glob('[0-9]*'))) for name in enabled_modules(read(root/'config.json'))}}
    result = {'cost': cost_summary(root), 'state': state, 'stop': read(root/'stop.json') if (root/'stop.json').exists() else None, 'rounds': rounds}
    
    return result


def main():
    from .cli import main as entry
    entry()


if __name__ == '__main__':
    main()
