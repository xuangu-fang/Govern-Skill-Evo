"""One writer, one atomic HEAD for Selected Skill, append-only Memory and round cursor."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import fcntl
import hashlib
from pathlib import Path

from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.storage import write_record
from ..v25_2 import cli as v25_2_inputs
from . import BASELINE, PACKAGE, method
from .baseline.benchmarks.spreadsheetbench import actor, scoring
from .baseline.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from .stages import digest, freeze, read, stage


def check_assets(config):
    assets = {v25_2_inputs.workbook_path(name): info
              for name, info in read(BASELINE / 'dataset_manifest.json').items()}
    for task in config['task_items'].values():
        for key in ('input_path', 'answer_path'):
            path = Path(task[key])
            require(hashlib.sha256(path.read_bytes()).hexdigest() == assets[path]['sha256'],
                    f'Workbook differs from frozen dataset: {path}')


def configuration():
    manifest = read(BASELINE / 'frozen_manifest.json')
    for path, sha in manifest.items():
        if path in ('config.json', 'initial_skill.md', 'dataset_manifest.json'):
            require(hashlib.sha256((BASELINE / path).read_bytes()).hexdigest() == sha, f'Changed v25.2 input: {path}')
    config = v25_2_inputs.read_config(BASELINE / 'config.json')
    config['candidate'] = 'v25_3_spreadsheetbench'
    config['module_max_tokens'].update(editor=32_768, preconditioner=32_768, replay=32_768)
    config['method'] = dict(version='v25_3_selective_updates_v1', stages=['diagnosis', 'preconditioner', 'editor', 'replay'],
                            gate='selective_hard_v1', memory='rounds_effective_updates_v1')
    SpreadsheetBenchAdapter().validate_config(config)
    check_assets(config)
    return config


@contextmanager
def writer(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.v25_3.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def _publish(root, state, previous):
    expected = read(root / 'HEAD.json') if (root / 'HEAD.json').exists() else None
    require(expected == previous, 'Campaign HEAD changed')
    head = digest(state)
    freeze(root / 'commits' / (head + '.json'), state)
    write_record(root / 'HEAD.json', head)
    return head


def current(root):
    head = read(root / 'HEAD.json')
    require(isinstance(head, str) and len(head) == 64 and all(c in '0123456789abcdef' for c in head),
            'Invalid campaign HEAD')
    state = read(root / 'commits' / (head + '.json'))
    require(head == digest(state), 'Invalid campaign HEAD commit')
    return head, state


def _contract():
    from src.skill_evolution.v27 import json_response, storage, transport
    from src.skill_evolution.v27.contracts import editor as patch_format, diagnosis as plan_format
    from src.skill_evolution.v28 import output_feedback as feedback_types
    from src.skill_evolution.v28_5 import editor as mapped_editor
    from src.skill_evolution.v29_2 import explicit_references

    files = sorted(p for p in PACKAGE.rglob('*') if p.suffix in ('.py', '.md'))
    files.extend(Path(module.__file__) for module in
                 (json_response, storage, transport, feedback_types, mapped_editor, patch_format, plan_format, explicit_references))
    source = Path(v25_2_inputs.__file__).parent
    files.extend(p for p in source.rglob('*') if p.is_file() and
                 (p.suffix in ('.py', '.md', '.json') or p.name == 'Dockerfile'))
    files.extend((BASELINE / 'frozen_manifest.json', BASELINE / 'campaign/runtime.json'))
    return {str(p.relative_to(PACKAGE.parents[2])): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def prepare(root, config=None):
    root = Path(root).resolve()
    config = configuration() if config is None else config
    with writer(root):
        require(all(p.name in {'.v25_3.lock','config.json','contract.json','HEAD.json','commits','rounds',
                               'runtime.json', 'final_skill.md'} for p in root.iterdir()), 'Unrelated campaign directory')
        if (root / 'HEAD.json').exists():
            require(read(root / 'config.json') == config and read(root / 'contract.json') == _contract(),
                    'Prepared campaign identity differs')
            return current(root)[1]
        require(not (root / 'rounds').exists(), 'Campaign lost its HEAD')
        freeze(root / 'config.json', config)
        freeze(root / 'contract.json', _contract())
        state = dict(previous=None, next_round=1, selected=config['initial_skill']['text'], memory={'rounds': []})
        _publish(root, state, None)
        return state


def _batch(adapter, tasks, skill, directory, config):
    directory.mkdir(parents=True, exist_ok=True)
    skill_path = directory / 'skill.md'
    if skill_path.exists():
        require(skill_path.read_bytes() == skill.encode(), 'Saved execution Skill differs')
    else:
        tmp = skill_path.with_suffix('.tmp')
        tmp.write_bytes(skill.encode())
        tmp.replace(skill_path)

    def one(task):
        item = config['task_items'][task]
        require(item['split'] in ('train', 'val') and task not in config['test_tasks'], 'Test task in optimizer')
        require(not any(x['task_id'] == task for x in config['dataset'].get('metadata_issues', [])),
                'Unresolved task metadata')
        scoring.regions(item['answer_region'])
        # Pass exact Skill text. Reading a patch-produced CRLF file in universal
        # newline mode would silently execute a different Candidate.
        path = actor.run(item, skill, directory / task.replace(':', '_'), config,
                         generate=adapter.generate, execute=adapter.execute, score=adapter.score)
        record = adapter.check_record(read(path), task, skill, config)
        require(Path(record['input_snapshot']).read_bytes() == Path(record['task']['input_path']).read_bytes(),
                'Execution snapshot differs from the original input')
        return record

    with ThreadPoolExecutor(max_workers=min(len(tasks), config['actor_max_workers'])) as workers:
        return list(workers.map(one, tasks))


def _round(rd, previous, config, adapter, generate):
    number, parent = previous['next_round'], previous['selected']
    tasks = config['batches'][number - 1]
    memory = previous['memory']
    records = _batch(adapter, tasks, parent, rd / 'parent_runs', config)
    payload = adapter.build_facts(records)['facts']
    _, plan = stage(rd, 'diagnosis', payload, method.diagnosis, config, generate)
    if plan is None:
        return parent, memory, {'outcome': 'diagnosis_no_change'}
    pre_input = method.preconditioner_input(payload, plan, memory)
    _, effective = stage(rd, 'preconditioner', pre_input, method.effective_plan, config, generate)
    if effective is None:
        return parent, memory, {'outcome': 'all_withdrawn'}
    editor_input = method.editor_input(parent, effective)
    edits, built = stage(rd, 'editor', editor_input, method.construct_candidate, config, generate)
    if built['editor_status'] == 'needs_revision':
        raise RuntimeError('Editor blocked faithful implementation; round not published')
    pairs, events = [], []
    if built['editor_status'] == 'candidate':
        candidates = _batch(adapter, tasks, built['candidate_text'], rd / 'candidate_runs', config)
        replay = method.replay_input(adapter, tasks, editor_input, edits, built, records, candidates)
        pairs = replay['pairs']
        if pairs:
            _, events = stage(rd, 'replay', replay, method.knowledge, config, generate)
    decisions, selection = method.gate(editor_input, edits, pairs, events)
    selected = selection['selected_text']
    source = 'parent' if selected == parent else 'candidate' if selected == built['candidate_text'] else None
    gate_result = dict(decisions=decisions, selection=selection, selected_execution_source=source)
    freeze(rd / 'gate.json', gate_result)
    count = sum(len(r['entries']) for r in memory['rounds'])
    record = dict(round_id=rd.name, source_updates=[
        {'id': u['id'], 'text': u['text'], 'gate_decision': d['gate_decision']}
        for u, d in zip(effective['updates'], decisions)],
        entries=[{'id': f'M{count+i}', 'knowledge': item} for i, item in enumerate(events, 1)])
    return selected, {'rounds': [*memory['rounds'], record]}, {'outcome': built['editor_status'], 'source': source}


def run(root, generate, *, adapter=None, limit=None, expected_config=None):
    root = Path(root).resolve()
    adapter = adapter or SpreadsheetBenchAdapter()
    with writer(root):
        config = read(root / 'config.json')
        require(config == (configuration() if expected_config is None else expected_config), 'Configuration changed')
        require(read(root / 'contract.json') == _contract(), 'Method sources changed since preparation')
        head, state = current(root)
        if config['dataset']['kind'] != 'synthetic_offline' and state['next_round'] <= len(config['batches']):
            runtime = adapter.runtime_snapshot(config)
            require(runtime == read(BASELINE / 'campaign/runtime.json'), 'Docker runtime differs from v25.2')
            freeze(root / 'runtime.json', runtime)
        completed = 0
        while state['next_round'] <= len(config['batches']) and (limit is None or completed < limit):
            number = state['next_round']
            rd = root / 'rounds' / f'R{number:02}'
            freeze(rd / 'input.json', {'parent_commit': head, 'tasks': config['batches'][number - 1]})
            selected, memory, result = _round(rd, state, config, adapter, generate)
            state = dict(previous=head, next_round=number + 1, selected=selected, memory=memory)
            freeze(rd / 'result.json', {**result, 'commit': digest(state)})
            head = _publish(root, state, head)
            completed += 1
        if state['next_round'] > len(config['batches']):
            output = root / 'final_skill.md'
            tmp = output.with_suffix('.tmp')
            tmp.write_bytes(state['selected'].encode())
            tmp.replace(output)
        return state
