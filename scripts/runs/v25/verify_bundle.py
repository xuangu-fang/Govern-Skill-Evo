"""Offline audit of the v25 SpreadsheetBench training records and three first tests."""
import argparse
import json
import sys
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.runs.spreadsheetbench.legacy_archive import check_publications, read_records
PUBLISHED = ROOT / 'experiments/methods/v25'


def read(path):
    return json.loads(Path(path).read_text())


def require(value, message):
    if not value:
        raise ValueError(message)


def check_archive(record, summary, skill, task_ids):
    campaign = ROOT / record['campaign']
    state = read(campaign / 'state.json')
    require(state['next_round'] == 9 and (campaign / state['parent']).read_text() == skill,
            f"Retained Skill differs: {campaign.name}")
    after = state
    for number in range(8, 0, -1):
        result = read(campaign / 'rounds' / f'R{number:02}' / 'result.json')
        require(result['status'] == 'completed' and result['after'] == after and after['next_round'] == number + 1,
                f"Round publication differs: {campaign} R{number:02}")
        after = result['before']
    require(after['next_round'] == 1, 'Initial round differs')

    terminal = ROOT / summary['raw_summary']
    raw = read(terminal)
    inputs = read(ROOT / summary['raw_input'])
    old_campaign = Path(record['original_campaign'])
    bound_campaign = Path(inputs['campaign']) if 'campaign' in inputs else Path(inputs['skill_source']).parents[len(Path(state['parent']).parts) - 1]
    require(bound_campaign.parts[-len(old_campaign.parts):] == old_campaign.parts, 'Test points to another training run')
    if 'skill_text' in inputs:
        require(inputs['skill_text'] == skill and (terminal.parent / 'final_skill.md').read_text() == skill,
                'Bound Skill differs')
        ids = [task['id'] for task in inputs['tasks']]
    else:
        require(Path(inputs['skill_source']).parts[-len(Path(state['parent']).parts):] == Path(state['parent']).parts,
                'Four-way arm selected a different training result')
        ids = inputs['tasks']
    rows = raw['tasks']
    require(ids == task_ids == [r['task_id'] for r in rows], 'Actual test cohort differs')
    require(all(raw[k] == summary[k] for k in ('status', 'completed', 'success', 'hard', 'per_cell_pass_rate')),
            'Raw summary differs')
    require(sum(r['hard'] for r in rows) == raw['success'] and
            isclose(sum(r['per_cell_pass_rate'] for r in rows) / len(rows), raw['per_cell_pass_rate']),
            'Task totals differ')
    for row in rows:
        path = Path(row['trajectory'])
        # Match the old run-relative path even when the checkout root changes.
        idx = path.parts.index('episodes')
        old_test = Path(summary['original_test_directory'])
        require(path.parts[:idx][-len(old_test.parts):] == old_test.parts, 'Trajectory belongs to another test')
        record_path = terminal.parent.joinpath(*path.parts[idx:])
        trace = read(record_path)
        require(trace['task']['id'] == row['task_id'] and trace['skill'] == skill and
                all(trace['score'][k] == row[k] for k in ('hard', 'per_cell_pass_rate')),
                f"Incorrect task/Skill/score: {row['task_id']}")
    return len(rows)


@read_records
def verify(archive=False):
    index = read(PUBLISHED / 'runs.json')
    require(len(index) == len(set(index)) == 10, 'Training index differs')
    completed = {}
    trajectories = 0
    for name in index:
        exp = PUBLISHED / name
        record = read(exp / 'record.json')
        require(record['experiment_id'] == name, 'Wrong experiment directory')
        evidence = read(exp / record['status_evidence'])
        require(evidence and (exp / record['configuration']).is_file(), 'Missing input or status evidence')
        if archive:
            require(read(ROOT / record['raw_status_evidence']) == evidence, 'Archived status differs')
            state_file = ROOT / record['campaign'] / 'state.json'
            rounds = read(state_file)['next_round'] - 1 if state_file.exists() else None
            require(rounds == record['published_rounds'], 'Recorded training progress differs')
        tests = list((exp / 'results').glob('*/summary.json'))
        if record['status'] != '完成训练':
            require(not tests, 'Incomplete run unexpectedly owns a completed test')
            continue
        require(len(tests) == 1, 'Expected one test for this training ID')
        result = tests[0]
        summary = read(result)
        require(summary['training_id'] == name and summary['evaluation_id'] == result.parent.name,
                'Test bound to wrong experiment')
        skill = (exp / record['retained_skill']).read_text()
        check_publications(exp, skill.encode(), Path if archive else None)
        require(skill.strip() and (result.parent / summary['evaluated_skill']).read_text() == skill,
                'Published and tested Skills differ')
        task_ids = read(exp / 'config/test_tasks.json')
        require(len(task_ids) == len(set(task_ids)) == summary['completed'] == 280 and
                summary['status'] in ('complete', 'completed') and summary['hard'] == summary['success'] / len(task_ids),
                'Invalid published metrics')
        if archive:
            trajectories += check_archive(record, summary, skill, task_ids)
        completed[name] = [summary['success'], len(task_ids)]
    require(len(completed) == 3, 'Completed experiment count differs')
    report = dict(training_records=len(index), completed=completed, incomplete=len(index) - len(completed))
    if archive:
        report['trajectories_verified'] = trajectories
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true', help='also read original round publications and all test trajectories')
    print(json.dumps(verify(parser.parse_args().archive), ensure_ascii=False, indent=2))
