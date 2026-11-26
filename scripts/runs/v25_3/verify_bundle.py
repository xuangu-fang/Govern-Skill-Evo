"""Check the published SpreadsheetBench v25.3 records offline."""
import argparse
import json
import sys
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.runs.spreadsheetbench.legacy_archive import check_publications, read_records
PUBLISHED = ROOT / 'experiments/methods/v25_3'
ARCHIVE = ROOT / 'artifacts/methods/v25_3'
RUN = 'v25_3_spreadsheetbench_proxy'
CANCELLED = 'v25_3_spreadsheetbench_20261106_1200'


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_archive(config, evaluation, summary, skill, cancelled):
    campaign = ARCHIVE / RUN / 'campaign'
    terminal = ROOT / summary['raw_summary']
    test = terminal.parent
    raw = read(terminal)
    require(read(campaign / 'config.json') == config, 'Archived training configuration differs')
    head = read(campaign / 'HEAD.json')
    for number in range(len(config['batches']), 0, -1):
        round_id = f'R{number:02}'
        require(read(campaign / 'rounds' / round_id / 'result.json')['commit'] == head, f'{round_id} result differs')
        state = read(campaign / 'commits' / (head + '.json'))
        require(state['next_round'] == number + 1, f'{round_id} cursor differs')
        if number == len(config['batches']):
            require(state['selected'] == skill, 'Final published state differs')
        head = state['previous']
    initial = read(campaign / 'commits' / (head + '.json'))
    require(initial['next_round'] == 1 and initial['previous'] is None, 'Initial state differs')
    require((campaign / 'final_skill.md').read_text() == skill, 'Training export differs')

    inputs = read(test / 'input.json')
    require(inputs['actor_config'] == evaluation and inputs['skill_text'] == skill, 'Evaluation inputs differ')
    require((test / 'final_skill.md').read_text() == skill, 'Archived evaluation Skill differs')
    ids = evaluation['test_tasks']
    require([t['id'] for t in inputs['tasks']] == ids, 'Bound tasks differ')
    require([row['task_id'] for row in raw['tasks']] == ids, 'Raw test cohort differs')
    for key in ('completed', 'success', 'hard', 'per_cell_pass_rate', 'status'):
        require(raw[key] == summary[key], f'Archived metric differs: {key}')
    require(sum(row['hard'] for row in raw['tasks']) == summary['success'], 'Task successes differ')
    require(isclose(sum(row['per_cell_pass_rate'] for row in raw['tasks']) / len(ids),
                    summary['per_cell_pass_rate']), 'Mean cell pass rate differs')
    old_test = Path(inputs['campaign']).parent / 'test'
    for row in raw['tasks']:
        trajectory = read(test / Path(row['trajectory']).relative_to(old_test))
        require(trajectory['task']['id'] == row['task_id'] and
                all(trajectory['score'][key] == row[key] for key in ('hard', 'per_cell_pass_rate')),
                f"Trajectory differs: {row['task_id']}")
    cancelled_run = ARCHIVE / CANCELLED
    require(read(cancelled_run / 'launch/status.json') == cancelled, 'Cancellation receipt differs')
    state = read(cancelled_run / 'commits' / (read(cancelled_run / 'HEAD.json') + '.json'))
    require(state['next_round'] == 1 and not (cancelled_run / 'rounds').exists(), 'Cancelled run contains training')
    return len(ids)


@read_records
def verify(archive=False):
    run = PUBLISHED / RUN
    config = read(run / 'config/config.json')
    evaluation = read(run / 'config/evaluation/config.json')
    results = run / 'results'
    first_test = results / (RUN + '_test280')
    summary = read(first_test / 'summary.json')
    skill = (results / 'final_skill.md').read_text()
    check_publications(run, skill.encode(), Path if archive else None)
    require(skill.strip() and (first_test / summary['evaluated_skill']).read_text() == skill, 'Test Skill differs')
    rounds = read(results / 'training_complete.json')['rounds']
    require(rounds == len(config['batches']) == 8 and all(len(b) == 15 for b in config['batches']), 'Batch layout differs')
    ids = config['test_tasks']
    require(evaluation['test_tasks'] == ids and len(set(ids)) == len(ids) == 280, 'Published test cohort differs')
    require(summary['training_id'] == RUN and summary['status'] == 'complete' and summary['completed'] == len(ids)
            and summary['hard'] == summary['success'] / len(ids), 'Invalid published metrics')
    cancelled = read(PUBLISHED / CANCELLED / 'reports/status.json')
    require(cancelled['phase'] == 'cancelled_before_training' and cancelled['completed_rounds'] == 0,
            'Cancellation evidence differs')
    report = dict(rounds=rounds, completed=len(ids), success=summary['success'], cancelled_rounds=0)
    if archive:
        report['trajectories_verified'] = verify_archive(config, evaluation, summary, skill, cancelled)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true', help='also verify original training and per-task records')
    print(json.dumps(verify(parser.parse_args().archive), indent=2))
