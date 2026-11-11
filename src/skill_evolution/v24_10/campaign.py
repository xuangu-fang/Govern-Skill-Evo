"""Publish the selected Skill and its outcome and efficiency evidence together."""
import hashlib
import os
from pathlib import Path

from src.skill_evolution.v24_1.benchmark import using_benchmark
from src.skill_evolution.v24_1.benchmarks.alfworld.actor.skill_runtime import output_protocol
from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
from src.skill_evolution.v24_1.benchmarks.alfworld.runtime import check_live_environment
from src.skill_evolution.v24_2 import campaign as baseline, method
from src.skill_evolution.v24_2.campaign import BASELINE, batch, current, digest, publish, writer
from src.skill_evolution.v24_2.storage import freeze, freeze_text, read
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.transport import HTTPGenerator
from . import PROMPTS, ROOT, STAGES, system_prompt
from src.skill_evolution.v24_6 import gate
from .stages import stage


VERSION = 'alfworld_v24_10_v1'


def configuration():
    return dict(baseline.configuration(), method=VERSION)


def contract(config):
    require(config['method'] == VERSION, 'Expected V24.10 method')
    result = baseline.contract(dict(config, method=baseline.VERSION))
    protocol = output_protocol(config['actor_output_format'])
    editor = system_prompt('editor')
    for field in ('system_prompt', 'initial_template', 'history_template'):
        require(f'<{field}>\n{protocol[field]}\n</{field}>' in editor, 'Editor protocol binding differs')
    result['config_sha256'] = digest(config)
    files = list(Path(__file__).parent.glob('*.py')) + [PROMPTS / f'{name}.md' for name in STAGES]
    files.append(Path(gate.__file__).resolve())
    result['files'].update({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    return result


def prepare(root, config=None):
    root = Path(root).resolve()
    config = configuration() if config is None else config
    with writer(root):
        require(all(p.name in {'.v24_2.lock', 'config.json', 'contract.json', 'HEAD.json', 'commits',
                               'rounds', 'final_skill.md', 'offline_report.json', 'runtime.json', 'launch'} for p in root.iterdir()),
                'Unrelated campaign directory')
        require(not (root / 'offline_report.json').exists() or config['mode'] == 'offline_fixture',
                'Fixture report in an official campaign directory')
        frozen_contract = contract(config)
        freeze(root / 'config.json', config)
        freeze(root / 'contract.json', frozen_contract)
        if not (root / 'HEAD.json').exists():
            require(not (root / 'rounds').exists(), 'Round history exists without HEAD')
            publish(root, None, dict(previous=None, next_round=1, selected=config['initial_skill']['text'],
                                     memory={'rounds': []}))
        return current(root)[1]


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
                replay_view, audit = gate.replay_input(adapter, tasks, view, edits, built, parents, children)
                freeze(rd / 'pair_audit.json', audit)
                pairs = replay_view['pairs']
                if pairs:
                    _, events = model('replay', replay_view, gate.knowledge)
            decisions, selection = gate.select(view, edits, pairs, events)
            selected = selection['selected_text']
            source = 'parent' if selected == parent else 'candidate' if selected == built['candidate_text'] else None
            freeze(rd / 'gate.json', dict(decisions=decisions, selection=selection, selected_execution_source=source))
            first = 1 + sum(len(r['entries']) for r in memory['rounds'])
            record = dict(round_id=rd.name, source_updates=[
                dict(id=u['id'], text=u['text'], gate_decision=d['gate_decision'])
                for u, d in zip(effective['updates'], decisions)], entries=[
                    dict(id=f'M{first + index}', direction=pair['direction'],
                         parent_steps=pair['parent_steps'], candidate_steps=pair['candidate_steps'],
                         steps_saved=pair['steps_saved'], knowledge=event)
                    for index, (pair, event) in enumerate(zip(pairs, events))])
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
