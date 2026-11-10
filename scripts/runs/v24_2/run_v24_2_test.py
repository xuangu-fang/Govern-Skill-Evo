"""Evaluate the final published V24.2 Skill with V24.1's held-out ALFWorld runner."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.skill_evolution.v24_1 import evaluation
from src.skill_evolution.v24_1.benchmark import using_benchmark
from src.skill_evolution.v24_1.benchmarks.alfworld.actor.run_task import SPLIT_ROOT
from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from src.skill_evolution.v24_2 import campaign
from src.skill_evolution.v24_2.storage import read, same_contract
from src.skill_evolution.v27.facts import require


def published_skill(root, config, version):
    require(same_contract(read(root / 'contract.json'), version.contract(config)), 'Training contract differs')
    head, state = campaign.current(root)
    batches = config['batches']
    require(state['next_round'] == len(batches) + 1, 'Training is incomplete')
    selected = state['selected']
    cursor = head
    for number in range(len(batches), 0, -1):
        round_dir = root / 'rounds' / f'R{number:02}'
        publication = read(round_dir / 'publication.json')
        require(campaign.digest(publication) == cursor and publication['next_round'] == number + 1,
                'Round publication differs from committed training history')
        require(read(round_dir / 'round_input.json') ==
                {'previous': publication['previous'], 'tasks': batches[number - 1]},
                'Published round differs from frozen batch')
        cursor = publication['previous']
    initial = dict(previous=None, next_round=1, selected=config['initial_skill']['text'], memory={'rounds': []})
    require(cursor == campaign.digest(initial), 'Training history differs from frozen initial state')
    return head, selected


def prepare_test(root, adapter, *, version=campaign, load_skill=published_skill):
    config = read(root / 'config.json')
    require(config['mode'] == 'official', 'Test requires an official training campaign')
    head, selected = load_skill(root, config, version)
    # HEAD is authoritative if training stopped just before exporting final_skill.md.
    exported = root / 'final_skill.md'
    if exported.exists():
        require(exported.read_bytes() == selected.encode(), 'Final Skill export differs from published Skill')

    baseline = campaign.BASELINE.parents[1]
    tasks = read(baseline / 'data/test.json')
    require(len(tasks) == 134 and tasks == read(SPLIT_ROOT / 'test/items.json'), 'Frozen Test manifest differs')
    train = config['task_items'].values()
    for key in ('id', 'gamefile'):
        values = {t[key] for t in tasks}
        require(len(values) == len(tasks) and values.isdisjoint(t[key] for t in train),
                f'Duplicate Test {key} or overlap with optimization')
    files = {}
    for task in tasks:
        game = Path(config['environment_root']) / task['gamefile']
        for path in (game, game.parent / 'initial_state.pddl'):
            files[str(path)] = path.read_bytes().decode('utf-8')
    runtime = read(root / 'runtime.json')
    require(runtime == read(campaign.BASELINE.with_name('runtime.json')) == adapter.runtime_snapshot(config),
            'Test Actor runtime differs from frozen training runtime')
    actor_config = dict(config, task_items={t['id']: t for t in tasks}, environment_files=files)
    return dict(campaign=str(root), training_head=head, skill_text=selected, actor_config=actor_config,
                tasks=tasks, runtime=runtime, initial_reference=read(campaign.BASELINE.with_name(
                    'initial_baseline_reference.json')))


def completed_archive(output, bundle):
    """Read a relocated, finished Test with its original receipts and input unchanged."""
    saved = read(output / 'input.json')
    if saved['campaign'] == bundle['campaign']:
        return None
    require(resolve_experiment_path(saved['campaign']) == Path(bundle['campaign'])
            and dict(saved, campaign=bundle['campaign']) == bundle, 'Evaluation inputs changed')
    result = read(output / 'summary.json')
    require(result['status'] == 'complete' and read(output / 'progress.json')['status'] == 'complete',
            'Archived evaluation is incomplete')
    evaluation.ev._check_contract(output)
    require((output / 'final_skill.md').read_text() == bundle['skill_text'], 'Archived Skill differs')
    tasks = bundle['tasks']
    require(len(result['tasks']) == result['completed'] == len(tasks), 'Archived task count differs')
    successes = 0
    for task, row in zip(tasks, result['tasks']):
        uid = task['id']
        episode = output / 'episodes' / uid.replace(':', '_')
        trajectory = resolve_experiment_path(read(episode / 'result.json')['trajectory']).resolve()
        require(trajectory.is_relative_to(episode / 'attempts') and
                trajectory == resolve_experiment_path(row['trajectory']).resolve(), 'Archived receipt differs')
        record = evaluation.check_record(trajectory, uid, bundle)
        require((row['task_id'], row['success'], row['steps'], row['termination']) ==
                (uid, record['won'], len(record['steps']), record['status']), 'Archived result differs')
        successes += record['won']
    require(successes == result['success'], 'Archived success count differs')
    return result


def main(*, version=campaign, description=__doc__, load_skill=published_skill, evaluate=evaluation.run):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--campaign', required=True, type=Path)
    parser.add_argument('--evaluation', required=True, type=Path, help='separate Test output directory')
    parser.add_argument('--resume', action='store_true', help='reuse verified episodes in this evaluation')
    parser.add_argument('--validate-only', action='store_true', help='check Test inputs without running any episode')
    args = parser.parse_args()
    source, output = args.campaign.resolve(), args.evaluation.resolve()
    require(not output.is_relative_to(source) and not source.is_relative_to(output),
            'Training and Test need separate, non-nested directories')
    adapter = ALFWorldAdapter()
    with using_benchmark(adapter):
        bundle = prepare_test(source, adapter, version=version, load_skill=load_skill)
        if args.validate_only:
            print(f"Validated {len(bundle['tasks'])} Test tasks for training HEAD {bundle['training_head']}")
            return
        result = completed_archive(output, bundle) if args.resume and (output/'input.json').exists() else None
        if result is None:
            result = evaluate(output, bundle=bundle, resume=args.resume)
    print(f"Test: {result['success']}/{result['completed']} ({result['success_rate']:.2%})")


if __name__ == '__main__':
    main()
