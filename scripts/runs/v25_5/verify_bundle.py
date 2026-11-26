"""Check the three v25.5 records and both evaluations offline."""
import argparse
import json
import sys
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.runs.spreadsheetbench.legacy_archive import check_publications, read_records
PUBLISHED = ROOT / 'experiments/methods/v25_5'
ARCHIVE = ROOT / 'artifacts/methods/v25_5'
OFFICIAL = 'v25_5_spreadsheetbench_deepseek'
PROXY = 'v25_5_spreadsheetbench_proxy'
EVALUATIONS = [('test280', 'test', 4), ('full_40w_20261108_1730', 'reruns/full_40w_20261108_1730/test', 40)]


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def initial_state(root):
    commit = read(root / 'HEAD.json')
    return read(root / 'commits' / (commit + '.json'))


def verify_rounds(config, skill):
    campaign = ARCHIVE / OFFICIAL / 'campaign'
    require(read(campaign / 'config.json') == config and (campaign / 'final_skill.md').read_text() == skill,
            'Official training inputs or export differ')
    commit = read(campaign / 'HEAD.json')
    for n in range(len(config['batches']), 0, -1):
        label = f'R{n:02}'
        require(read(campaign / 'rounds' / label / 'result.json')['commit'] == commit, f'{label} publication differs')
        state = read(campaign / 'commits' / (commit + '.json'))
        require(state['next_round'] == n + 1, f'{label} cursor differs')
        if n == len(config['batches']):
            require(state['selected'] == skill, 'Final published Skill differs')
        commit = state['previous']
    state = read(campaign / 'commits' / (commit + '.json'))
    require(state['previous'] is None and state['next_round'] == 1, 'Initial commit differs')


def verify_tasks(summary, expected, skill, old_location):
    terminal = ROOT / summary['raw_summary']
    raw, inputs = read(terminal), read(terminal.parent / 'input.json')
    ids = expected['test_tasks']
    require(inputs['actor_config'] == expected and inputs['tasks'] == [expected['task_items'][i] for i in ids],
            'Actual evaluation configuration or tasks differ')
    require(inputs['skill_text'] == skill == (terminal.parent / 'final_skill.md').read_text(), 'Bound Skill differs')
    campaign = Path(inputs['campaign'])
    require(campaign.parts[-2:] == (OFFICIAL, 'campaign'), 'Unexpected training source')
    require(all(raw[k] == summary[k] for k in ('status', 'success', 'completed', 'hard', 'per_cell_pass_rate')),
            'Original summary differs')
    rows = raw['tasks']
    require([r['task_id'] for r in rows] == ids and sum(r['hard'] for r in rows) == raw['success'], 'Task scores differ')
    require(isclose(sum(r['per_cell_pass_rate'] for r in rows) / len(ids), raw['per_cell_pass_rate']), 'Cell scores differ')
    for row in rows:
        path = Path(row['trajectory']).relative_to(campaign.parent / old_location)
        record = read(terminal.parent / path)
        require(record['task']['id'] == row['task_id'] and
                all(record['score'][k] == row[k] for k in ('hard', 'per_cell_pass_rate')),
                f"Trajectory differs: {row['task_id']}")
    return len(rows)


@read_records
def verify(archive=False):
    run = PUBLISHED / OFFICIAL
    config = read(run / 'config/config.json')
    evaluation = read(run / 'config/evaluation/config.json')
    results = run / 'results'
    rounds = read(results / 'training_complete.json')['rounds']
    require(rounds == len(config['batches']) == 8 and all(len(batch) == 15 for batch in config['batches']), 'Batch layout differs')
    ids = config['test_tasks']
    require(evaluation['test_tasks'] == ids and len(ids) == len(set(ids)) == 280, 'Test cohort differs')
    skill = (results / 'final_skill.md').read_text()
    check_publications(run, skill.encode(), Path if archive else None)
    require(skill.strip(), 'Empty final Skill')
    report = {'training_rounds': {OFFICIAL: rounds}, 'evaluations': {}}
    for name in (PROXY, PROXY + '_before_editor_revision'):
        state = initial_state(PUBLISHED / name / 'config/initial_state')
        require(state['next_round'] == 1 and state['previous'] is None, f'{name}: not an initial state')
        if archive:
            campaign = ARCHIVE / name / 'campaign'
            require(initial_state(campaign) == state and not (campaign / 'rounds').exists()
                    and not (campaign.parent / 'test').exists(), f'{name}: archived state differs')
        report['training_rounds'][name] = 0
    if archive:
        verify_rounds(config, skill)
    total = 0
    for suffix, old_location, workers in EVALUATIONS:
        eval_id = OFFICIAL + '_' + suffix
        directory = results / eval_id
        summary = read(directory / 'summary.json')
        expected = dict(evaluation, actor_max_workers=workers)
        require(summary['training_id'] == OFFICIAL and summary['evaluation_id'] == eval_id and
                ROOT / summary['raw_summary'] == ARCHIVE / eval_id / 'summary.json', 'Evaluation binding differs')
        require(summary['status'] == 'complete' and summary['completed'] == len(ids)
                and summary['hard'] == summary['success'] / len(ids), 'Invalid evaluation metrics')
        require((directory / summary['evaluated_skill']).read_text() == skill and
                all(summary[k] == expected[k] for k in ('actor_model', 'actor_base_url', 'actor_max_workers')),
                'Published Skill or Actor differs')
        report['evaluations'][suffix] = [summary['success'], summary['completed']]
        if archive:
            total += verify_tasks(summary, expected, skill, old_location)
    if archive:
        report['trajectories_verified'] = total
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true', help='also read training commits and original trajectories')
    print(json.dumps(verify(parser.parse_args().archive), indent=2))
