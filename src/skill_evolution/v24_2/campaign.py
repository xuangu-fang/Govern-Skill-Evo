"""ALFWorld round orchestration. HEAD publishes the Skill, Memory and cursor together."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from contextvars import copy_context
import fcntl
import hashlib
import json
import os
from pathlib import Path

from src.skill_evolution.v24_1.benchmark import using_benchmark
from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
from src.skill_evolution.v24_1.benchmarks.alfworld.actor.skill_runtime import output_protocol
from src.skill_evolution.v24_1.benchmarks.alfworld.runtime import check_live_environment
from .storage import freeze, freeze_text, read, save
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.transport import HTTPGenerator
from . import method, ROOT, PROMPTS, STAGES, DOMAIN_GUIDE, system_prompt
from .stages import stage


BASELINE = (ROOT / 'experiments/methods/v24_1' /
            'alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/config/campaign.json')
VERSION = 'alfworld_v24_2_selective_success_v1'


def configuration():
    config = read(BASELINE)
    config.update(method=VERSION, mode='official')
    return config


def contract(config):
    ALFWorldAdapter().validate_config(config)
    require(config['method'] == VERSION, 'Wrong method version')
    require(config['mode'] in ('official', 'offline_fixture'), 'Unknown campaign mode')
    tasks = [t for batch in config['batches'] for t in batch]
    require(tasks and all(config['batches']) and len(tasks) == len(set(tasks)), 'Empty or repeated optimization tasks')
    if config['mode'] == 'official':
        require(config == configuration(), 'Official campaign differs from frozen baseline')
    editor = system_prompt('editor')
    protocol = output_protocol(config['actor_output_format'])
    for field in ('system_prompt', 'initial_template', 'history_template'):
        require(f'<{field}>\n{protocol[field]}\n</{field}>' in editor, 'Editor protocol binding differs')
    files = list(Path(__file__).parent.glob('*.py')) + [PROMPTS / (s + '.md') for s in STAGES]
    files.append(DOMAIN_GUIDE)
    files += [ROOT / 'src/skill_evolution' / f for f in (
        'v28_5/editor.py', 'v27/contracts/editor.py', 'v24_1/benchmarks/alfworld/gate.py',
        'v24_1/benchmarks/alfworld/facts.py', 'v24_1/benchmarks/alfworld/actor/skill_runtime.py')]
    files.extend((ROOT / 'src/skill_evolution/v24_1/benchmarks/alfworld').rglob('*.py'))
    return {'config_sha256': digest(config), 'files': {
        str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(set(files))}}


@contextmanager
def writer(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.v24_2.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def current(root):
    head = read(root / 'HEAD.json')
    require(isinstance(head, str) and len(head) == 64 and all(c in '0123456789abcdef' for c in head),
            'Invalid V24.2 HEAD')
    state = read(root / 'commits' / (head + '.json'))
    require(digest(state) == head, 'Commit differs from HEAD')
    return head, state


def publish(root, previous, state):
    require((read(root / 'HEAD.json') if (root / 'HEAD.json').exists() else None) == previous,
            'Campaign HEAD changed before publication')
    head = digest(state)
    freeze(root / 'commits' / (head + '.json'), state)
    save(root / 'HEAD.json', head)


def prepare(root, config=None):
    root = Path(root).resolve()
    config = configuration() if config is None else config
    with writer(root):
        require(all(p.name in {'.v24_2.lock', 'config.json', 'contract.json', 'HEAD.json', 'commits',
                               'rounds', 'final_skill.md', 'offline_report.json', 'runtime.json', 'launch'} for p in root.iterdir()),
                'Unrelated campaign directory')
        require(not (root / 'offline_report.json').exists() or config['mode'] == 'offline_fixture',
                'Fixture report in an official campaign directory')
        freeze(root / 'config.json', config)
        freeze(root / 'contract.json', contract(config))
        if not (root / 'HEAD.json').exists():
            require(not (root / 'rounds').exists(), 'Round history exists without HEAD')
            publish(root, None, dict(previous=None, next_round=1, selected=config['initial_skill']['text'],
                                     memory={'rounds': []}))
        return current(root)[1]


def batch(rd, side, tasks, skill, config, adapter, actor):
    directory = rd / side
    path = directory / 'skill.md'
    freeze_text(path, skill)

    def one(task):
        folder = directory / task.replace(':', '_')
        marker = folder / 'record.json'
        if marker.exists():
            receipt = read(marker)
            archive = (folder / receipt['trajectory']).resolve()
            require(archive.is_relative_to(folder / 'attempts'), 'Actor receipt points outside its task')
        else:
            attempts = folder / 'attempts'
            attempts.mkdir(parents=True, exist_ok=True)
            existing = sorted(attempts.iterdir())
            saved = list(existing[-1].rglob('trajectory.json')) if existing else []
            require(len(saved) <= 1, 'Ambiguous Actor attempt')
            if saved and adapter.is_complete(read(saved[0])):
                archive = saved[0]
            else:
                dest = attempts / f'{len(existing)+1:03}'
                dest.mkdir()
                archive = Path(actor(task, path, dest, config)).resolve()
                require(archive.is_relative_to(dest), 'Actor archive is outside the allocated attempt')
        raw = archive.read_bytes()
        record = json.loads(raw)
        adapter.check_record(record, task, skill, config)
        require(not record.get('error_stage') and not record.get('error_type'), 'Technical Actor failure')
        freeze(marker, dict(trajectory=str(archive.relative_to(folder)), sha256=hashlib.sha256(raw).hexdigest()))
        return record

    workers = min(config['actor_max_workers'], len(tasks))
    results, pending = {}, {}
    remaining = iter(tasks)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while True:
            while len(pending) < workers:
                task = next(remaining, None)
                if task is None:
                    break
                pending[pool.submit(copy_context().run, one, task)] = task
            if not pending:
                break
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                results[pending.pop(future)] = future.result()
    return [results[t] for t in tasks]


def run_round(root, *, generate=None, actor=None):
    root = Path(root).resolve()
    adapter = ALFWorldAdapter()
    with writer(root), using_benchmark(adapter):
        config = read(root / 'config.json')
        freeze(root / 'contract.json', contract(config), read_only=True)
        head, before = current(root)
        number = before['next_round']
        if number > len(config['batches']):
            freeze_text(root / 'final_skill.md', before['selected'])
            return before
        if config['mode'] == 'offline_fixture':
            require(actor is not None and generate is not None, 'Offline fixture requires injected Actor and responses')
        else:
            require(actor is None and generate is None, 'Official campaigns require the frozen Actor and transport')
            check_live_environment(config)
            runtime = adapter.runtime_snapshot(config)
            require(runtime == read(BASELINE.with_name('runtime.json')), 'Actor runtime differs from V24.1 baseline')
            freeze(root / 'runtime.json', runtime)
            generate = HTTPGenerator(os.environ['OPENAI_API_KEY'])
            actor = adapter.actor_task
        rd = root / 'rounds' / f'R{number:02}'
        parent, memory = before['selected'], before['memory']
        tasks = config['batches'][number - 1]
        freeze(rd / 'round_input.json', dict(previous=head, tasks=tasks))
        parents = batch(rd, 'parent_runs', tasks, parent, config, adapter, actor)
        facts = adapter.build_facts(parents)['facts']
        def model(name, payload, validate):
            return stage(rd, name, payload, validate, config, generate)
        _, plan = model('diagnosis', facts, method.diagnosis)
        effective = None
        outcome = 'diagnosis_no_change'
        if plan:
            pre = method.preconditioner_input(facts, plan, memory)
            _, effective = model('preconditioner', pre, method.effective_plan)
            outcome = 'all_withdrawn'
        selected, source = parent, 'parent'
        if effective:
            view = method.editor_input(parent, effective)
            edits, built = model('editor', view, method.edit)
            outcome = built['editor_status']
            require(outcome != 'needs_revision', 'Editor blocked faithful implementation; round not published')
            pairs, events = [], []
            if outcome == 'candidate':
                children = batch(rd, 'candidate_runs', tasks, built['candidate_text'], config, adapter, actor)
                replay_view, audit = method.replay_input(adapter, tasks, view, edits, built, parents, children)
                freeze(rd / 'pair_audit.json', audit)
                pairs = replay_view['pairs']
                if pairs:
                    _, events = model('replay', replay_view, method.knowledge)
            decisions, selection = method.select(view, edits, pairs, events)
            selected = selection['selected_text']
            source = 'parent' if selected == parent else 'candidate' if selected == built['candidate_text'] else None
            freeze(rd / 'gate.json', dict(decisions=decisions, selection=selection, selected_execution_source=source))
            first = 1 + sum(len(r['entries']) for r in memory['rounds'])
            directions = {p['task_id']: ('gain' if p['candidate_success'] else 'loss') for p in pairs}
            record = dict(round_id=rd.name, source_updates=[
                dict(id=u['id'], text=u['text'], gate_decision=d['gate_decision'])
                for u, d in zip(effective['updates'], decisions)], entries=[
                    dict(id=f'M{i}', direction=directions[e['task_id']], knowledge=e)
                    for i, e in enumerate(events, first)])
            memory = {'rounds': [*memory['rounds'], record]}
        state = dict(previous=head, next_round=number+1, selected=selected, memory=memory,
                     selected_execution_source=source, outcome=outcome)
        freeze_text(rd / 'selected.md', selected)
        freeze(rd / 'publication.json', state)
        freeze(root / 'contract.json', contract(config), read_only=True)
        publish(root, head, state)
        if number == len(config['batches']):
            freeze_text(root / 'final_skill.md', selected)
        return state
