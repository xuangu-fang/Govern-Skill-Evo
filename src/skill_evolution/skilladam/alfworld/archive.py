"""Read native SkillAdam training decisions and ALFWorld Test trajectories."""
import json

from scripts.runs.alfworld.alfworld_aligned_common import read, require, result_from_record, validate_trajectory
from src.skill_evolution.shared.experiment_paths import ROOT, resolve_experiment_path


def read_evaluation(root, training_run, items, actor, skill):
    inputs = read(root / 'inputs.json')
    report = read(root / 'summary.json')
    require(inputs['actor'] == actor and inputs['tasks'] == items and inputs['skill'] == skill
            and (root / 'actor_skill.md').read_text() == skill, 'Final Test inputs differ')
    with (root / 'results.jsonl').open() as stream:
        rows = [json.loads(line) for line in stream]
    require(rows == report['tasks'] and len(items) == report['completed'] == len(rows) == 134
            and report['status'] == 'complete' and report['training_updated'] is False,
            'Incomplete Test or inconsistent results')
    successes = 0
    for item, row in zip(items, rows):
        path = resolve_experiment_path(row['trajectory'])
        task_root = root / 'episodes' / item['id'].replace(':', '_')
        require(path.is_relative_to(task_root), 'Unexpected trajectory location')
        record = validate_trajectory(path, actor, item, skill)
        require(result_from_record(record, item, row['trajectory']) == row, f"Result differs for {item['id']}")
        successes += int(record['won'])
    require(successes == report['success'] and successes / len(items) == report['success_rate'],
            'Test totals differ from trajectories')
    return dict(run_id=root.name, training_run=training_run, status=report['status'], completed=len(rows),
                success=successes, success_rate=report['success_rate'], final_skill='../final_skill.md',
                source=str((root / 'summary.json').relative_to(ROOT)))


def read_training(output, config):
    cfg = read(config / 'skilladam.json')
    actor = read(config / 'actor.json')
    completion = read(output / 'completion.json')
    checkpoint = read(output / 'checkpoint.json')
    skill = (output / 'final_skill.md').read_text()
    records = completion['iterations']
    batches = [r['training_case_ids'] for r in records]
    require(completion['status'] == 'complete' and checkpoint['next_iteration'] == len(records) == 6
            and records == checkpoint['iterations'] and checkpoint['pending_post_decision'] is None
            and skill == checkpoint['current_skill'] == (output / 'current_skill.md').read_text(),
            'Training summary, checkpoint or Skill differ')
    require(batches == read(resolve_experiment_path(actor['reference_campaign']))['batches']
            and batches == [r['validation_case_ids'] for r in records]
            and [uid for batch in batches for uid in batch] == cfg['native']['optimization_case_ids'],
            'Training or Gate batches differ from the original plan')
    iterations = [dict(iteration=r['iteration'], tasks=len(r['training_case_ids']),
                       baseline_success=sum(int(v['hard']) for v in r['baseline']['case_metrics'].values()),
                       candidate_success=sum(int(v['hard']) for v in r['candidate']['case_metrics'].values()),
                       accepted=r['accepted'], reason=r['reason'], patch_mode=r['patch_mode']) for r in records]
    training = dict(run_id=output.name, status=completion['status'], optimization_tasks=sum(map(len, batches)),
                    iterations=iterations, final_skill='final_skill.md',
                    source=str((output / 'completion.json').relative_to(ROOT)))
    return training, skill
