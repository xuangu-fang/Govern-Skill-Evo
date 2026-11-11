"""Exercise the two changed prompts on recorded training-side Actor trajectories."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.skill_evolution.v24_2 import method
from src.skill_evolution.v24_2.storage import freeze, read
from src.skill_evolution.v24_8 import campaign
from src.skill_evolution.v24_8.stages import stage

ARCHIVE = ROOT / 'artifacts/methods/v24_7/v24_7_alfworld_20261108_020254'
CASES = {
    'search': [('R04', 'train:0034'), ('R04', 'train:0031'), ('R05', 'val:0007'),
               ('R05', 'val:0002'), ('R05', 'val:0004')],
    'pick_two': [('R04', 'train:0036'), ('R04', 'train:0037'), ('R04', 'train:0038')],
}

# Competing commands to inspect in the recorded pre-action menu. Never sent to the model.
PROBES = {
    'search': [('P1', 9, 'go to drawer 5'), ('P1', 49, 'go to shelf 5'),
               ('P3', 13, 'go to countertop 1'), ('P3', 31, 'go to cabinet 5'),
               ('P4', 2, 'go to desk 1'), ('P5', 3, 'go to sidetable 1')],
    'pick_two': [('P1', 38, 'go to drawer 1'), ('P2', 10, 'go to coffeetable 1'),
                 ('P3', 10, 'go to cabinet 2'), ('P3', 12, 'go to cabinet 1')],
}


def review_windows(name, facts):
    runs = {run['ref']: run for run in facts['runs']}
    windows = []
    for ref, number, alternative in PROBES[name]:
        run = runs[ref]
        index = number - 1
        step = run['steps'][index]
        menu = facts['command_sets'][step['before']['commands_ref']]
        if not {step['action'], alternative}.issubset(menu) or step['action'] == alternative:
            raise ValueError(f"No such recorded choice at {step['step']}")
        history = [{'observation': s['before']['observation'], 'action': s['action']}
                   for s in run['steps'][max(0, index - 2):index]]
        windows.append(dict(step=step['step'], goal=run['task'], history=history,
                            observation=step['before']['observation'], menu=menu,
                            actual=step['action'], alternative=alternative))
    return windows


def verify_case(name, output, generate):
    root = output / name
    records = []
    refs = {}
    config = campaign.configuration()
    adapter = campaign.ALFWorldAdapter()
    previous = read(ARCHIVE / 'rounds/R03/publication.json')
    for number, (rd, task) in enumerate(CASES[name], 1):
        folder = ARCHIVE / 'rounds' / rd / 'parent_runs' / task.replace(':', '_')
        record = read(folder / read(folder / 'record.json')['trajectory'])
        adapter.check_record(record, task, previous['selected'], config)
        records.append(record)
        refs[f'P{number}'] = {'round': rd, 'task': task}
    facts = adapter.build_facts(records)['facts']
    freeze(root / 'sources.json', refs)
    freeze(root / 'review_windows.json', review_windows(name, facts))
    if generate is None:
        for module in ('diagnosis', 'preconditioner'):
            if not (root / module / 'result.json').is_file():
                raise ValueError(f'Missing saved {module} response for {name}; use --generate to collect it')
    _, plan = stage(root, 'diagnosis', facts, method.diagnosis, config, generate)
    if not plan:
        raise ValueError(f'{name}: no proposal to review')
    payload = method.preconditioner_input(facts, plan, previous['memory'])
    _, effective = stage(root, 'preconditioner', payload, method.effective_plan, config, generate)
    if not effective:
        raise ValueError(f'{name}: no effective update')
    freeze(root / 'editor_input.json', method.editor_input(facts['parent'], effective))
    print(f"{name}: {len(records)} archived runs; {len(effective['updates'])} effective update(s)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', choices=CASES)
    parser.add_argument('--generate', action='store_true', help='Allow new module requests for missing responses')
    args = parser.parse_args()
    generate = None
    if args.generate:
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env', override=False)
        generate = campaign.HTTPGenerator(os.environ['OPENAI_API_KEY'])
    for name in ([args.case] if args.case else CASES):
        verify_case(name, args.output, generate)


if __name__ == '__main__':
    main()
