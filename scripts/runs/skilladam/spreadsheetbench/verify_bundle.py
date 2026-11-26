"""Audit published SpreadsheetBench SkillAdam records, optionally including all original trajectories."""
import argparse
import json
import sys
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.runs.spreadsheetbench.legacy_archive import read_records
from scripts.runs.spreadsheetbench.native_archive import verify_native
PUBLISHED = ROOT / 'experiments/methods/skilladam/spreadsheetbench'

FEEDBACK_EVALUATIONS = {
    'skilladam_spreadsheetbench_v25_5_feedback_20261108_234037': 4,
    'skilladam_spreadsheetbench_v25_5_feedback_20261112_201115': 2,
    'skilladam_spreadsheetbench_v41_feedback_20261116_142340': 6,
    'skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006': 12,
}


def read(p):
    return json.loads(Path(p).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_test(summary, cohort, skill):
    terminal = ROOT / summary['raw_summary']
    raw = read(terminal)
    inputs = read(ROOT / summary['raw_input'])
    if 'skill_text' in inputs:
        require(inputs['skill_text'] == skill == (terminal.parent / 'final_skill.md').read_text(), 'Input Skill differs')
        ids = [task['id'] for task in inputs['tasks']]
        actor = inputs['actor_config']
        require(all(actor[k] == summary[k] for k in ('actor_model', 'actor_base_url', 'actor_max_workers')), 'Actor differs')
    else:
        require(inputs['arm'] == 'skilladam', 'Wrong four-way arm')
        ids = inputs['tasks']
    rows = raw['tasks']
    require(ids == cohort == [row['task_id'] for row in rows], 'Test IDs differ')
    require(all(raw[k] == summary[k] for k in ('status', 'completed', 'success', 'hard', 'per_cell_pass_rate')), 'Raw metrics differ')
    require(sum(row['hard'] for row in rows) == summary['success'] and
            isclose(sum(row['per_cell_pass_rate'] for row in rows) / len(rows), summary['per_cell_pass_rate']), 'Task totals differ')
    origin = Path(summary['old_directory'])
    for row in rows:
        parts = Path(row['trajectory']).parts
        i = parts.index('episodes')
        require(parts[:i][-len(origin.parts):] == origin.parts, 'Unexpected trajectory source')
        trace = read(terminal.parent.joinpath(*parts[i:]))
        require(trace['task']['id'] == row['task_id'] and trace['skill'] == skill and
                all(trace['score'][k] == row[k] for k in ('hard', 'per_cell_pass_rate')),
                f"Task/Skill/score mismatch: {row['task_id']}")
    return len(rows)


@read_records
def verify(archive=False):
    index = read(PUBLISHED / 'runs.json')
    require(len(index) == len(set(index)) == 8, 'Training index differs')
    report = {'records': len(index), 'completed_trainings': 0, 'evaluations': {}}
    total = 0
    for path in index:
        run = PUBLISHED / path
        record = read(run / 'record.json')
        require(record['experiment_id'] == run.name and record['profile'] == run.parent.name, 'Unexpected training ID')
        require((ROOT / record['source_config']).is_file(), 'Missing source configuration')
        evidence = read(ROOT / record['status_evidence']) if str(record['status_evidence']).endswith('.json') else (ROOT / record['status_evidence']).read_text()
        require(bool(evidence), 'Missing state evidence')
        if archive:
            require((ROOT / record['raw_status_evidence']).read_bytes() == (ROOT / record['status_evidence']).read_bytes(), 'Status receipt differs')
            ck = ROOT / record['raw_run'] / 'campaign/checkpoint.json'
            checkpoint = read(ck) if ck.is_file() else None
            require((checkpoint['next_iteration'] if checkpoint else 0) == record['completed_iterations'], 'Progress differs')
        tests = list((run / 'results').glob('*/summary.json'))
        if record['status'] != '完成训练':
            require(not tests and record['final_skill'] is None, 'Incomplete run owns a final test')
            continue
        report['completed_trainings'] += 1
        cohort = read(run / 'config/test_tasks.json')
        skill = (ROOT / record['final_skill']).read_text()
        require(skill.strip() and record['completed_iterations'] == 8 and len(cohort) == len(set(cohort)) == 280, 'Incomplete training/test cohort')
        if archive:
            shared = read((ROOT / record['source_config']).with_name('shared_config.json'))
            require([i['training_case_ids'] for i in checkpoint['iterations']] == shared['batches'] ==
                    [i['validation_case_ids'] for i in checkpoint['iterations']], 'Native training/Gate batches differ')
            require(checkpoint['current_skill'] == skill and not checkpoint['pending_post_decision'] and
                    len(checkpoint['iterations']) == 8, 'Native checkpoint or retained Skill differs')
        require(len(tests) == (2 if record['profile'] == 'aligned_actor' else 1), 'Wrong evaluation count')
        for f in tests:
            summary = read(f)
            require(summary['training_id'] == run.name and summary['evaluation_id'] == f.parent.name and
                    summary['completed'] == len(cohort) and summary['status'] in ('complete', 'completed') and
                    summary['hard'] == summary['success'] / len(cohort), 'Published metrics differ')
            require((f.parent / summary['evaluated_skill']).read_text() == skill, 'Evaluated Skill differs')
            report['evaluations'][f.parent.name] = [summary['success'], len(cohort)]
            if archive:
                total += check_test(summary, cohort, skill)
    require(report['completed_trainings'] == 4 and len(report['evaluations']) == 5, 'Index incomplete')
    for name, count in FEEDBACK_EVALUATIONS.items():
        directory = PUBLISHED / 'trajectory_feedback' / name
        tests = verify_native(directory, count, Path if archive else None)
        for key, result in tests.items():
            report['evaluations'][f'{name}/{key}'] = result
            total += result[1]
    report['records'] += len(FEEDBACK_EVALUATIONS) - 1
    report['completed_trainings'] += len(FEEDBACK_EVALUATIONS) - 1
    if archive:
        report['verified_trajectories'] = total
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true', help='also check original checkpoints and test trajectories')
    print(json.dumps(verify(parser.parse_args().archive), ensure_ascii=False, indent=2))
