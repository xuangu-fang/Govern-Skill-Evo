"""Check the v25.4 training record and its four independent SpreadsheetBench evaluations."""
import argparse
import json
import sys
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.runs.spreadsheetbench.legacy_archive import check_publications, read_records
RUN = 'v25_4_spreadsheetbench_proxy'
PUBLISHED = ROOT / 'experiments/methods/v25_4' / RUN
ARCHIVE = ROOT / 'artifacts/methods/v25_4' / RUN
# Published suffix, location relative to the historical run, number of evaluated tasks.
EVALUATIONS = (
    ('test280', 'test', 280),
    ('full_40w_20261108_1650', 'reruns/full_40w_20261108_1650/test', 280),
    ('four_test_tasks_20261108_113020', 'reruns/four_test_tasks_20261108_113020', 4),
    ('unique_failures_20261108_101739', 'reruns/unique_failures_20261108_101739', 10),
)


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_training(config, skill):
    campaign = ARCHIVE / 'campaign'
    require(read(campaign / 'config.json') == config, 'Training config differs')
    require((campaign / 'final_skill.md').read_text() == skill, 'Archived training export differs')
    head = read(campaign / 'HEAD.json')
    for number in range(len(config['batches']), 0, -1):
        label = f'R{number:02}'
        require(read(campaign / 'rounds' / label / 'result.json')['commit'] == head, f'{label} commit differs')
        state = read(campaign / 'commits' / (head + '.json'))
        require(state['next_round'] == number + 1, f'{label} cursor differs')
        if number == len(config['batches']):
            require(state['selected'] == skill, 'Selected final Skill differs')
        head = state['previous']
    initial = read(campaign / 'commits' / (head + '.json'))
    require(initial['next_round'] == 1 and initial['previous'] is None, 'Initial state differs')


def check_archive(summary, relative, ids, skill, config):
    terminal = ROOT / summary['raw_summary']
    folder = terminal.parent
    raw = read(terminal)
    inputs = read(folder / 'input.json')
    historical_campaign = Path(inputs['campaign'])
    require(historical_campaign.parts[-2:] == (RUN, 'campaign'), 'Different training source')
    require(inputs['skill_text'] == skill == (folder / 'final_skill.md').read_text(), 'Bound Skill differs')
    require(inputs['tasks'] == [config['task_items'][i] for i in ids], 'Bound tasks differ')
    actor = inputs['actor_config']
    require(actor['test_tasks'] == config['test_tasks'], 'Test cohort in Actor configuration differs')
    require(all(actor[key] == summary[key] for key in ('actor_model', 'actor_base_url', 'actor_max_workers')),
            'Actor or concurrency differs')
    if summary['scope'] != '同一 Skill 全量复测':
        require(actor == config, 'Expected the original evaluation configuration')
    records = raw['tasks']
    require([r['task_id'] for r in records] == ids, 'Evaluated task order differs')
    for key in ('status', 'completed', 'success', 'hard', 'per_cell_pass_rate'):
        require(raw[key] == summary[key], f'{folder.name}: published {key} differs')
    require(sum(r['hard'] for r in records) == summary['success'], 'Task successes differ')
    require(isclose(sum(r['per_cell_pass_rate'] for r in records) / len(ids), summary['per_cell_pass_rate']),
            'Mean cell pass rate differs')
    historical_folder = historical_campaign.parent / relative
    for row in records:
        trajectory = read(folder / Path(row['trajectory']).relative_to(historical_folder))
        require(trajectory['task']['id'] == row['task_id'] and
                all(trajectory['score'][key] == row[key] for key in ('hard', 'per_cell_pass_rate')),
                f"Trajectory differs: {row['task_id']}")
    return len(records)


@read_records
def verify(archive=False):
    config = read(PUBLISHED / 'config/config.json')
    evaluation = read(PUBLISHED / 'config/evaluation/config.json')
    results = PUBLISHED / 'results'
    rounds = read(results / 'training_complete.json')['rounds']
    require(rounds == len(config['batches']) == 8 and all(len(b) == 15 for b in config['batches']), 'Batch layout differs')
    cohort = evaluation['test_tasks']
    require(config['test_tasks'] == cohort and len(set(cohort)) == len(cohort) == 280, 'Test split differs')
    skill = (results / 'final_skill.md').read_text()
    check_publications(PUBLISHED, skill.encode(), Path if archive else None)
    require(skill.strip(), 'Empty final Skill')
    report = {'rounds': rounds, 'evaluations': {}}
    if archive:
        check_training(config, skill)
    total = 0
    for suffix, relative, size in EVALUATIONS:
        evaluation_id = RUN + '_' + suffix
        published = results / evaluation_id
        summary = read(published / 'summary.json')
        ids = cohort if size == len(cohort) else summary['task_ids']
        require(len(set(ids)) == len(ids) == size and set(ids) <= set(cohort), f'{suffix}: cohort differs')
        require(summary['evaluation_id'] == evaluation_id and summary['training_id'] == RUN, 'Run binding differs')
        require(summary['completed'] == size and summary['status'] == 'complete' and
                summary['hard'] == summary['success'] / size, f'{suffix}: invalid metrics')
        require((published / summary['evaluated_skill']).read_text() == skill, f'{suffix}: different Skill')
        require(ROOT / summary['raw_summary'] == ARCHIVE.with_name(evaluation_id) / 'summary.json', 'Wrong archive')
        report['evaluations'][suffix] = [summary['success'], size]
        if archive:
            total += check_archive(summary, relative, ids, skill, evaluation)
    if archive:
        report['trajectories_verified'] = total
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true', help='verify rounds, inputs and all 574 evaluation trajectories')
    print(json.dumps(verify(parser.parse_args().archive), indent=2))
