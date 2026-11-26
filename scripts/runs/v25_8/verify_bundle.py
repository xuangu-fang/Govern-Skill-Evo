"""Verify the published v25.8 experiment bundle and optionally its original records."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.skill_evolution.shared.offline_records import offline_records

RUN_ID = 'v25_8_spreadsheetbench_official_20261118_232447'
PUBLISHED = ROOT / 'experiments/methods/v25_8' / RUN_ID
SOURCE = Path('artifacts/methods/v25_8') / RUN_ID


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def digest(data):
    return sha256(data).hexdigest()


def commit_id(state):
    encoded = json.dumps(state, ensure_ascii=False, allow_nan=False, sort_keys=True,
                         separators=(',', ':')).encode()
    return digest(encoded)


def source_path(recorded, within):
    """Rebase recorded paths onto this checkout while preserving their archive key."""
    path = Path(recorded)
    if path.is_absolute():
        for parent in path.parents:
            if parent.name == 'artifacts':
                path = path.relative_to(parent.parent)
                break
    require(path.is_relative_to(within) and '..' not in path.parts,
            f'Archived path outside {within}: {recorded}')
    return path


def metrics(rows):
    successes = sum(row['hard'] for row in rows)
    return (len(rows), successes, successes / len(rows),
            sum(row['per_cell_pass_rate'] for row in rows) / len(rows))


def check_metrics(summary, rows, name):
    completed, success, hard, per_cell = metrics(rows)
    require((completed, success) == (summary['completed'], summary['success'])
            and isclose(hard, summary['hard']) and isclose(per_cell, summary['per_cell_pass_rate']),
            f'Evaluation metrics differ: {name}')


def check_selected_files(training, path_type):
    expected = {'config/train.json', 'config/test.json', 'config/contract.json', 'config/runtime.json',
                *(f'results/skills/R{number:02}.md' for number in range(9))}
    require(set(training['selected_files']) == expected, 'Unexpected set of selected files')
    for name, row in training['selected_files'].items():
        content = (PUBLISHED / name).read_bytes()
        require(digest(content) == row['sha256'], f'Selected file differs: {name}')
        if path_type is not None:
            source = source_path(row['source'], SOURCE)
            require(path_type(ROOT / source).read_bytes() == content,
                    f'Selected file differs from the archive: {name}')
    for path, expected_sha in read(PUBLISHED / 'config/contract.json').items():
        require(digest((ROOT / path).read_bytes()) == expected_sha, f'Frozen source differs: {path}')


def check_training(training, train, path_type):
    campaign = SOURCE / 'campaign'
    head = read(path_type(ROOT / campaign / 'HEAD.json'))
    launch = read(path_type(ROOT / SOURCE / 'launch.json'))
    require(head == training['head'] and launch['started_at'] == training['started_at']
            and launch['model'] == train['actor_model'] == training['actor_model']
            and launch['rounds'] == len(train['batches'])
            and launch['training_tasks'] == training['training_tasks'],
            'Archived campaign identity differs')
    previous = None
    commit = training['rounds'][0]['parent_commit']
    optimized = 0
    for number in range(9):
        round_id = f'R{number:02}'
        selected = (PUBLISHED / 'results/skills' / (round_id + '.md')).read_bytes()
        state = read(path_type(ROOT / campaign / 'commits' / (commit + '.json')))
        require(commit_id(state) == commit and state['previous'] == previous
                and state['next_round'] == number + 1 and state['selected'].encode() == selected,
                f'Publication differs at {round_id}')
        if number:
            row = training['rounds'][number - 1]
            folder = path_type(ROOT / campaign / 'rounds' / round_id)
            batch = read(folder / 'input.json')
            result = read(folder / 'result.json')
            gate = read(folder / 'gate.json')
            require(batch == {'parent_commit': previous, 'tasks': train['batches'][number - 1]}
                    and row['parent_commit'] == previous and row['commit'] == result['commit'] == commit
                    and row['skill_sha256'] == digest(selected)
                    and gate['selection']['selected_text'].encode() == selected
                    and gate['selected_execution_source'] == result['source'] == row['selected_execution_source'],
                    f'Round inputs or selection differ at {round_id}')
            decisions = Counter(item['gate_decision'] for item in gate['decisions'])
            expected_decisions = {'Retain': row['retained'], 'Reject': row['rejected'], 'Defer': row['deferred']}
            require(dict(decisions) == {key: count for key, count in expected_decisions.items() if count},
                    f'Gate decisions differ at {round_id}')
            for arm in ('parent', 'candidate'):
                runs = folder / (arm + '_runs')
                skill = (runs / 'skill.md').read_bytes()
                if arm == 'parent':
                    parent_skill = PUBLISHED / 'results/skills' / f'R{number - 1:02}.md'
                    require(skill == parent_skill.read_bytes(), f'Parent Skill differs at {round_id}')
                records = [read(runs / task.replace(':', '_') / 'trajectory.json') for task in batch['tasks']]
                require(all(record['task'] == train['task_items'][task] and record['skill'].encode() == skill
                            and record['model'] == train['actor_model'] and record['actor_complete']
                            for task, record in zip(batch['tasks'], records))
                        and sum(record['score']['hard'] for record in records) == row[arm + '_success'],
                        f'Training trajectories differ at {round_id}/{arm}')
                optimized += len(records)
        if number < 8:
            previous, commit = commit, training['rounds'][number]['commit']
    require((PUBLISHED / 'results/skills/R00.md').read_bytes() == train['initial_skill']['text'].encode()
            and commit == head
            and path_type(ROOT / campaign / 'final_skill.md').read_bytes() == selected,
            'Final exported Skill differs from HEAD')
    return optimized


def read_episode(task, directory, bundle, path_type):
    episode = directory / 'episodes' / task.replace(':', '_')
    receipt = read(path_type(ROOT / episode / 'result.json'))
    trajectory = source_path(receipt['trajectory'], episode / 'attempts')
    require(trajectory.name == 'trajectory.json' and trajectory.parent.parent == episode / 'attempts',
            f'Trajectory receipt is outside the task attempt: {task}')
    record = read(path_type(ROOT / trajectory))
    config = bundle['actor_config']
    require(record['task'] == config['task_items'][task] and record['skill'] == bundle['skill_text']
            and record['model'] == config['actor_model'] and record['protocol'] == config['actor_profile']
            and record['executor'] == config['executor'] and record['actor_complete']
            and record['status'] == 'completed',
            f'Evaluation trajectory differs: {trajectory}')
    score = record['score']
    return {'task_id': task, 'hard': score['hard'], 'per_cell_pass_rate': score['per_cell_pass_rate'],
            'code_attempts': record['code_attempts'], 'termination': record['termination'],
            'trajectory': trajectory}


def check_retry(expected, bundle, path_type):
    retry = expected['independent_retry']
    source = source_path(retry['source'], Path(expected['source']).parent)
    folder = path_type(ROOT / source)
    result = read(folder / 'result.json')
    request = read(folder / 'request.json')['body']
    score = read(folder / 'score.json')
    task = bundle['actor_config']['task_items'][retry['task_id']]
    limits = result['max_completion_tokens'], request['max_completion_tokens'], retry['max_completion_tokens']
    require(result['status'] == 'scored' and result['task_id'] == retry['task_id']
            and result['model'] == request['model'] == expected['actor_model']
            and limits == (128000, 128000, 128000)
            and any(message['role'] == 'system' and bundle['skill_text'] in message['content']
                    for message in request['messages'])
            and any(message['role'] == 'user' and task['instruction'] in message['content']
                    for message in request['messages']),
            'Independent retry task, Actor, budget or Skill differs')
    for key in ('hard', 'per_cell_pass_rate'):
        require(score[key] == result['score'][key] == retry[key], f'Independent retry score differs: {key}')
    return score, result['cohort_after_single_retry']


def check_evaluation(expected, test, skill, path_type):
    directory = source_path(expected['source'], Path('artifacts'))
    folder = path_type(ROOT / directory)
    bundle = read(folder / 'input.json')
    config = bundle['actor_config']
    cohort = test['test_tasks']
    require(config['test_tasks'] == cohort and bundle['tasks'] == [test['task_items'][t] for t in cohort]
            and bundle['skill_text'].encode() == skill == (folder / 'final_skill.md').read_bytes()
            and config['actor_model'] == expected['actor_model'],
            f'Evaluation input or Skill differs: {directory}')
    source_summary = source_path(expected['source_summary'], directory.parent)
    summary = read(path_type(ROOT / source_summary))
    missing = {item['task_id'] for item in summary.get('unscored', [])}
    retry = expected.get('independent_retry')
    require(missing == ({retry['task_id']} if retry else set()), f'Unexpected unscored tasks: {directory}')
    require(len(list((folder / 'episodes').glob('*/result.json'))) == expected['standard_receipts'],
            f'Unexpected number of episode receipts: {directory}')
    rows = [read_episode(task, directory, bundle, path_type) for task in cohort if task not in missing]
    require(len(rows) == len(summary['tasks']) == expected['standard_receipts'],
            f'Unexpected number of scored tasks: {directory}')
    for row, original in zip(rows, summary['tasks']):
        require(row['trajectory'] == source_path(original['trajectory'], directory)
                and all(row[key] == value for key, value in original.items() if key != 'trajectory'),
                f'Receipt and archived summary disagree: {directory}/{row["task_id"]}')
    if retry:
        require(summary['status'] == 'partial' and summary['cohort'] == len(cohort), 'Invalid partial summary')
        check_metrics({'completed': summary['scored'], 'success': summary['success'],
                       'hard': summary['hard_among_scored'],
                       'per_cell_pass_rate': summary['per_cell_pass_rate_among_scored']}, rows, directory)
        extra, total = check_retry(expected, bundle, path_type)
        rows.append(extra)
        check_metrics({**total, 'completed': total['scored']}, rows, directory)
    else:
        require(summary['status'] == 'complete' and read(folder / 'progress.json')['status'] == 'complete',
                f'Incomplete evaluation: {directory}')
        check_metrics(summary, rows, directory)
    check_metrics(expected, rows, directory)


def verify(path_type=None):
    training = read(PUBLISHED / 'results/training_summary.json')
    train = read(PUBLISHED / 'config/train.json')
    test = read(PUBLISHED / 'config/test.json')
    require(training['run_id'] == RUN_ID and training['source'] == SOURCE.as_posix()
            and training['status'] == 'complete' and len(train['batches']) == 8
            and training['training_tasks'] == sum(map(len, train['batches'])) == 120
            and train['test_tasks'] == test['test_tasks']
            and len(set(test['test_tasks'])) == len(test['test_tasks']) == 280
            and [row['round'] for row in training['rounds']] == [f'R{i:02}' for i in range(1, 9)],
            'Training or test cohort differs')
    check_selected_files(training, path_type)
    names = read(PUBLISHED / 'results/evaluations.json')
    require(len(names) == len(set(names)) == 19, 'Evaluation list differs')
    evaluated = []
    for name in names:
        relative = Path(name)
        require(len(relative.parts) == 3 and relative.parts[0] == 'results'
                and relative.name == 'summary.json' and '..' not in relative.parts, 'Invalid evaluation summary path')
        row = read(PUBLISHED / relative)
        skill_name = f'results/skills/{row["round"]}.md'
        require(row['training_id'] == RUN_ID and row['evaluation_id'] == relative.parent.name
                and row['evaluated_skill'] == skill_name and skill_name in training['selected_files']
                and row['status'] == 'complete' and row['completed'] == 280
                and 0 <= row['success'] <= 280 and 0 <= row['per_cell_pass_rate'] <= 1
                and row['standard_receipts'] + int('independent_retry' in row) == 280
                and isclose(row['hard'], row['success'] / 280),
                f'Evaluation identity differs: {name}')
        skill = (PUBLISHED / skill_name).read_bytes()
        require(digest(skill) == row['skill_sha256'], f'Evaluated Skill differs: {name}')
        if path_type is not None:
            check_evaluation(row, test, skill, path_type)
        evaluated.append(row)
    require(len({row['source'] for row in evaluated}) == 19, 'Duplicate evaluation source')
    report = {'run_id': RUN_ID, 'rounds': len(training['rounds']), 'evaluations': len(evaluated)}
    if path_type is not None:
        report.update(standard_receipts=sum(row['standard_receipts'] for row in evaluated),
                      independent_retries=sum('independent_retry' in row for row in evaluated),
                      training_trajectories=check_training(training, train, path_type))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true', help='also check the original training and test records')
    args = parser.parse_args()
    if args.archive:
        with offline_records('spreadsheetbench') as archived_path:
            result = verify(archived_path)
    else:
        result = verify()
    print(json.dumps(result, indent=2))
