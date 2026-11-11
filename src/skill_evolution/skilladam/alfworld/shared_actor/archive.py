"""Read the original six training decisions and the completed shared Actor Test."""
import json

from scripts.runs.alfworld.alfworld_aligned_common import read, require, result_from_record, validate_trajectory
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from .paths import ARCHIVE, CONFIG, RUN_ID


def read_archive():
    config = read(CONFIG / 'skilladam.json')
    actor = read(CONFIG / 'actor.json')
    checkpoint = read(ARCHIVE / 'checkpoint.json')
    completed = read(ARCHIVE / 'completion.json')
    skill = (ARCHIVE / 'final_skill.md').read_bytes()
    iterations = completed['iterations']
    require(completed['mode'] == 'formal' and completed['status'] == 'complete'
            and checkpoint['iterations'] == iterations and checkpoint['next_iteration'] == len(iterations) == 6
            and checkpoint['pending_post_decision'] is None, 'Incomplete training or Momentum')
    require(skill == checkpoint['current_skill'].encode() == (ARCHIVE / 'current_skill.md').read_bytes(),
            'Published Skill differs from checkpoint')
    batches = [row['training_case_ids'] for row in iterations]
    require(batches == read(resolve_experiment_path(actor['reference_campaign']))['batches']
            and batches == [row['validation_case_ids'] for row in iterations]
            and [uid for batch in batches for uid in batch] == config['native']['optimization_case_ids'],
            'Optimization batches differ from frozen plan')

    evaluation = ARCHIVE.with_name(RUN_ID + '_test134')
    report = read(evaluation / 'summary.json')
    launch = read(evaluation / 'launch.json')
    items = read(CONFIG / 'splits/test/items.json')
    rows = report['tasks']
    require(skill == (evaluation / 'actor_skill.md').read_bytes() == (evaluation / 'final_skill.md').read_bytes()
            and resolve_experiment_path(launch['source_skill']) == ARCHIVE / 'final_skill.md'
            and launch['actor'] == actor, 'Test inputs differ from training export or Actor')
    require(report['status'] == 'complete' and len(items) == report['completed'] == len(rows) == 134
            and launch['tasks'] == [item['id'] for item in items], 'Incomplete Test or different task list')
    with (evaluation / 'results.jsonl').open() as stream:
        require(rows == [json.loads(line) for line in stream], 'Test report differs from saved results')
    successes = 0
    skill_text = skill.decode()
    for item, row in zip(items, rows):
        path = resolve_experiment_path(row['trajectory'])
        directory = evaluation / 'episodes' / item['id'].replace(':', '_')
        require(path.is_relative_to(directory), 'Trajectory is outside the expected task directory')
        record = validate_trajectory(path, actor, item, skill_text)
        require(result_from_record(record, item, row['trajectory']) == row, f"Result differs for {item['id']}")
        successes += int(record['won'])
    require(successes == report['success'] and successes / len(items) == report['success_rate'],
            'Test total differs from its trajectories')
    return dict(run_id=RUN_ID, published_iterations=len(iterations), completed=len(rows), success=successes)
