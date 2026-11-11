"""Learn from archived optimization trajectories, then run the frozen Actor on training-side games."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.analysis.v24_9.v24_9_general_windows import WINDOWS, compare
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from src.skill_evolution.v24_1.benchmark import using_benchmark
from src.skill_evolution.v24_2 import method
from src.skill_evolution.v24_2.storage import freeze, freeze_text, read
from src.skill_evolution.v24_9.general import campaign, pick_two
from src.skill_evolution.v24_9.general.stages import stage

ARCHIVE = ROOT / 'artifacts/methods/v24_7/v24_7_alfworld_20261108_020254'
# All records share the R03 published Skill and Memory. Two additional Pick Two
# successes are reserved for behavior checks, with no exposure during learning.
LEARN = [('R04', 'train:0034'), ('R04', 'train:0031'), ('R05', 'val:0007'),
         ('R05', 'val:0002'), ('R05', 'val:0004')]
CONTROL = [('R04', 'train:0037'), ('R04', 'train:0038')]


def archived(adapter, config, parent, rd, task):
    folder = ARCHIVE / 'rounds' / rd / 'parent_runs' / task.replace(':', '_')
    record = read(folder / read(folder / 'record.json')['trajectory'])
    adapter.check_record(record, task, parent, config)
    return record


def verify(output, *, allow_requests=False):
    adapter = campaign.ALFWorldAdapter()
    config = campaign.configuration()

    def missing(*args):
        raise ValueError('Missing archived response or execution; use --generate to collect it')

    generate = actor = missing
    if allow_requests:
        campaign.check_live_environment(config)
        if adapter.runtime_snapshot(config) != read(ARCHIVE / 'runtime.json'):
            raise ValueError('Actor runtime differs from archive')
        generate = campaign.HTTPGenerator(os.environ['OPENAI_API_KEY'])
        actor = adapter.actor_task
    previous = read(ARCHIVE / 'rounds/R03/publication.json')
    parent = previous['selected']
    sources = LEARN + CONTROL
    records = [archived(adapter, config, parent, *source) for source in sources]
    source_name = str(ARCHIVE.relative_to(ROOT))
    if (output / 'sources.json').exists():
        source_name = read(output / 'sources.json')['archive']
        if resolve_experiment_path(source_name) != ARCHIVE:
            raise ValueError('Archived trajectory source differs')
    freeze(output / 'sources.json', dict(archive=source_name, learn=LEARN,
                                          controls=CONTROL, parent_memory='R03'))
    facts = adapter.build_facts(records[:len(LEARN)])['facts']

    def model(name, payload, validate):
        if not allow_requests and not (output / name / 'result.json').is_file():
            raise ValueError(f'Missing archived {name} result; use --generate to collect it')
        system_text = None
        if name == 'preconditioner' and not allow_requests:
            first = read(output / name / 'attempts/001/messages.json')[0]['content']
            if first != campaign.system_prompt(name):
                # The early general experiment and this offline run used the same Prompt.
                system_text = (ROOT / 'experiments/methods/v24_9/v24_9_general_alfworld_20261108_125258'
                               / 'config/preconditioner.md').read_text()
        return stage(output, name, payload, validate, config, generate, system_text=system_text)

    _, plan = model('diagnosis', facts, method.diagnosis)
    if not plan:
        return 'diagnosis_no_change'
    _, effective = model('preconditioner', method.preconditioner_input(facts, plan, previous['memory']),
                         method.effective_plan)
    if not effective:
        return 'all_withdrawn'
    view = method.editor_input(parent, effective)
    edits, built = model('editor', view, pick_two.edit)
    if built['editor_status'] != 'candidate':
        return built['editor_status']
    pick_two.check_scope(config['initial_skill']['text'], built['candidate_text'])
    freeze_text(output / 'candidate.md', built['candidate_text'])
    window_records = dict(zip(sources, records))
    for rd, task, *_ in WINDOWS:
        if (rd, task) not in window_records:
            window_records[rd, task] = archived(adapter, config, parent, rd, task)
    compare(output, config, window_records, built['candidate_text'], allow_requests=allow_requests)
    tasks = [task for _, task in sources]
    if not allow_requests and any(not (output / 'candidate_runs' / t.replace(':', '_') /
                                      'record.json').is_file() for t in tasks):
        raise ValueError('Missing archived Candidate execution; use --generate to collect it')
    children = campaign.batch(output, 'candidate_runs', tasks, built['candidate_text'], config, adapter, actor)
    replay, audit = campaign.gate.replay_input(adapter, tasks[:len(LEARN)], view, edits, built,
                                              records[:len(LEARN)], children[:len(LEARN)])
    events = model('replay', replay, campaign.gate.knowledge)[1] if replay['pairs'] else []
    decisions, selection = campaign.gate.select(view, edits, replay['pairs'], events)
    pick_two.check_scope(parent, selection['selected_text'])
    freeze(output / 'learning_gate.json', dict(decisions=decisions, selection=selection, audit=audit))
    freeze(output / 'paired_results.json', [
        dict(task=t, held_out=i >= len(LEARN), parent_success=p['won'], parent_steps=len(p['steps']),
             candidate_success=c['won'], candidate_steps=len(c['steps']),
             actions=[s['action'] for s in c['steps']])
        for i, (t, p, c) in enumerate(zip(tasks, records, children))])
    if not replay['pairs']:
        # Exercise the fourth prompt on an actual eligible event without adding
        # any votes to the current candidate. Both runs and patch are historical.
        reference = output / 'historical_replay_R02'
        historical_input = read(ARCHIVE / 'rounds/R02/replay/input.json')
        if not allow_requests and not (reference / 'replay/result.json').is_file():
            raise ValueError('Missing historical Replay result; use --generate to collect it')
        stage(reference, 'replay', historical_input, campaign.gate.knowledge, config, generate)
    return 'candidate_evaluated'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--generate', action='store_true', help='Allow missing model calls and Actor episodes')
    args = parser.parse_args()
    with using_benchmark(campaign.ALFWorldAdapter()):
        print(verify(args.output.resolve(), allow_requests=args.generate), flush=True)
