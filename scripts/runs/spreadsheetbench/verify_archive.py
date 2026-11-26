"""Verify SpreadsheetBench publication bundles and their original offline records."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from math import isclose
from pathlib import Path

from src.skill_evolution.shared.offline_records import offline_records

ROOT = Path(__file__).resolve().parents[3]


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
            if parent.name == within.parts[0]:
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


def check_selected_files(published, source, training, path_type):
    expected = {'config/train.json', 'config/test.json', 'config/contract.json', 'config/runtime.json',
                *(f'results/skills/R{number:02}.md' for number in range(len(training['rounds']) + 1))}
    if training['status'] == 'prepared':
        expected.add('config/offline_acceptance.json')
    require(set(training['selected_files']) == expected, 'Unexpected set of selected files')
    for name, row in training['selected_files'].items():
        content = (published / name).read_bytes()
        require(digest(content) == row['sha256'], f'Selected file differs: {name}')
        if path_type is not None:
            original = source_path(row['source'], source)
            require(path_type(ROOT / original).read_bytes() == content,
                    f'Selected file differs from the archive: {name}')
    contract = read(published / 'config/contract.json')
    historical = training.get('historical_sources', {})
    require(historical.keys() <= contract.keys(), 'Historical source is outside the contract')
    for path, expected_sha in contract.items():
        actual = historical.get(path, path)
        require(digest((ROOT / actual).read_bytes()) == expected_sha, f'Frozen source differs: {path}')
    if path_type is not None and training.get('historical_replay_request'):
        request = source_path(training['historical_replay_request'], Path('artifacts/methods'))
        messages = read(path_type(ROOT / request))
        prompt, marker, _ = messages[0]['content'].partition('\nFor structured basis use exact run/step IDs.')
        replay_key = f'src/skill_evolution/{source.parts[2]}/prompts/replay.md'
        require(messages[0]['role'] == 'system' and marker
                and digest(prompt.encode()) == contract[replay_key],
                'Historical Replay request differs from its frozen prompt')


def check_training(published, source, training, train, path_type):
    campaign = source / 'campaign'
    head = read(path_type(ROOT / campaign / 'HEAD.json'))
    rounds = training['rounds']
    require(head == training['head'], 'Archived campaign HEAD differs')
    if training.get('launch'):
        launch_path = source_path(training['launch'], source)
        launch = read(path_type(ROOT / launch_path))
        require(launch['started_at'] == training['started_at']
                and launch['model'] == train['actor_model'] == training['actor_model']
                and launch['rounds'] == len(train['batches'])
                and launch['training_tasks'] == training['training_tasks'],
                'Archived launch identity differs')
    else:
        require(not (ROOT / source / 'launch.json').exists(), 'Published record omits an archived launch')
    if not rounds:
        require(not (ROOT / campaign / 'rounds').exists() and not (ROOT / source / 'test').exists(),
                'Prepared campaign contains training or evaluation results')
    previous = None
    commit = rounds[0]['parent_commit'] if rounds else head
    optimized = 0
    previous_skill = None
    for number in range(len(rounds) + 1):
        round_id = f'R{number:02}'
        selected = (published / 'results/skills' / (round_id + '.md')).read_bytes()
        state = read(path_type(ROOT / campaign / 'commits' / (commit + '.json')))
        require(commit_id(state) == commit and state['previous'] == previous
                and state['next_round'] == number + 1 and state['selected'].encode() == selected,
                f'Publication differs at {round_id}')
        if number:
            row = rounds[number - 1]
            folder = path_type(ROOT / campaign / 'rounds' / round_id)
            optimized += check_round(folder, train, row, commit, previous, selected, previous_skill)
        previous_skill = selected
        if number < len(rounds):
            previous, commit = commit, rounds[number]['commit']
    require((published / 'results/skills/R00.md').read_bytes() == train['initial_skill']['text'].encode()
            and commit == head, 'Initial or final publication differs')
    if rounds:
        require(path_type(ROOT / campaign / 'final_skill.md').read_bytes() == selected,
                'Final exported Skill differs from HEAD')
    return optimized


def check_round(folder, train, row, commit, previous, selected, previous_skill):
    round_id = row['round']
    number = int(round_id[1:])
    batch = read(folder / 'input.json')
    result = read(folder / 'result.json')
    outcome = row.get('outcome', 'candidate')
    require(batch == {'parent_commit': previous, 'tasks': train['batches'][number - 1]}
            and row['parent_commit'] == previous and row['commit'] == result['commit'] == commit
            and row['skill_sha256'] == digest(selected) and result['outcome'] == outcome,
            f'Round inputs or publication differ at {round_id}')
    gate_path = folder / 'gate.json'
    if gate_path.is_file():
        gate = read(gate_path)
        require(gate['selection']['selected_text'].encode() == selected
                and gate['selected_execution_source'] == result.get('source') == row['selected_execution_source'],
                f'Gate selection differs at {round_id}')
        decisions = Counter(item['gate_decision'] for item in gate['decisions'])
        expected = {'Retain': row['retained'], 'Reject': row['rejected'], 'Defer': row['deferred']}
        require(dict(decisions) == {key: count for key, count in expected.items() if count},
                f'Gate decisions differ at {round_id}')
    else:
        require(outcome in ('diagnosis_no_change', 'all_withdrawn') and selected == previous_skill
                and row['candidate_success'] is None
                and row['retained'] == row['rejected'] == row['deferred'] == 0,
                f'No-change publication differs at {round_id}')
    count = 0
    for arm in ('parent', 'candidate'):
        runs = folder / (arm + '_runs')
        paths = {task: runs / task.replace(':', '_') / 'trajectory.json' for task in batch['tasks']}
        seen = set(runs.glob('*/trajectory.json'))
        if arm == 'candidate' and row['candidate_success'] is None:
            require(not seen, f'Unexpected Candidate trajectories at {round_id}')
            continue
        require(seen == set(paths.values()), f'Training task set differs at {round_id}/{arm}')
        skill = (runs / 'skill.md').read_bytes()
        if arm == 'parent':
            require(skill == previous_skill, f'Parent Skill differs at {round_id}')
        total = 0
        for task, path in paths.items():
            record = read(path)
            require(record['task'] == train['task_items'][task] and record['skill'].encode() == skill
                    and record['model'] == train['actor_model'] and record['actor_complete'],
                    f'Training trajectory differs at {round_id}/{arm}/{task}')
            total += record['score']['hard']
        require(total == row[arm + '_success'], f'Training score differs at {round_id}/{arm}')
        count += len(paths)
    return count


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


def check_evaluation(expected, campaign, test, skill, path_type):
    directory = source_path(expected['source'], Path('artifacts'))
    folder = path_type(ROOT / directory)
    bundle = read(folder / 'input.json')
    config = bundle['actor_config']
    cohort = expected.get('subset_tasks', test['test_tasks'])
    require(source_path(bundle['campaign'], campaign) == campaign
            and config['test_tasks'] == test['test_tasks']
            and bundle['tasks'] == [test['task_items'][t] for t in cohort]
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


def verify(version, run_id, evaluation_count, path_type=None):
    published = ROOT / 'experiments/methods' / version / run_id
    source = Path('artifacts/methods') / version / run_id
    training = read(published / 'results/training_summary.json')
    train = read(published / 'config/train.json')
    test = read(published / 'config/test.json')
    rounds = len(training['rounds'])
    status = training['status']
    require(training['run_id'] == run_id and training['source'] == source.as_posix()
            and (status, rounds) in (('complete', 8), ('prepared', 0))
            and training['actor_model'] == train['actor_model'] == test['actor_model']
            and len(train['batches']) == 8 and all(len(batch) == 15 for batch in train['batches'])
            and training['training_tasks'] == sum(map(len, train['batches'])) == 120
            and train['test_tasks'] == test['test_tasks']
            and len(set(test['test_tasks'])) == len(test['test_tasks']) == 280
            and [row['round'] for row in training['rounds']] == [f'R{i:02}' for i in range(1, rounds + 1)],
            'Training or test cohort differs')
    check_selected_files(published, source, training, path_type)
    names = read(published / 'results/evaluations.json')
    require(len(names) == len(set(names)) == evaluation_count
            and (status == 'complete' or not names), 'Evaluation list differs')
    evaluated = []
    for name in names:
        relative = Path(name)
        require(len(relative.parts) == 3 and relative.parts[0] == 'results'
                and relative.name == 'summary.json' and '..' not in relative.parts, 'Invalid evaluation summary path')
        row = read(published / relative)
        skill_name = f'results/skills/{row["round"]}.md'
        cohort = row.get('subset_tasks', test['test_tasks'])
        total = len(cohort)
        require(total > 0 and len(set(cohort)) == total and set(cohort) <= set(test['test_tasks'])
                and row['training_id'] == run_id and row['evaluation_id'] == relative.parent.name
                and row['evaluated_skill'] == skill_name and skill_name in training['selected_files']
                and row['status'] == 'complete' and row['completed'] == total
                and 0 <= row['success'] <= total and 0 <= row['per_cell_pass_rate'] <= 1
                and row['standard_receipts'] + int('independent_retry' in row) == total
                and isclose(row['hard'], row['success'] / total),
                f'Evaluation identity differs: {name}')
        skill = (published / skill_name).read_bytes()
        require(digest(skill) == row['skill_sha256'], f'Evaluated Skill differs: {name}')
        if path_type is not None:
            check_evaluation(row, source / 'campaign', test, skill, path_type)
        evaluated.append(row)
    require(len({row['source'] for row in evaluated}) == evaluation_count, 'Duplicate evaluation source')
    report = {'run_id': run_id, 'rounds': rounds, 'evaluations': len(evaluated)}
    if path_type is not None:
        report.update(standard_receipts=sum(row['standard_receipts'] for row in evaluated),
                      independent_retries=sum('independent_retry' in row for row in evaluated),
                      training_trajectories=check_training(published, source, training, train, path_type))
    return report


def main(version, runs):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true', help='also check the original training and test records')
    if len(runs) > 1:
        parser.add_argument('--run', choices=runs, help='verify one run from this version')
    args = parser.parse_args()
    selected = getattr(args, 'run', None)
    checks = {selected: runs[selected]} if selected else runs
    if args.archive:
        with offline_records('spreadsheetbench') as path_type:
            reports = [verify(version, run, count, path_type) for run, count in checks.items()]
    else:
        reports = [verify(version, run, count) for run, count in checks.items()]
    print(json.dumps(reports[0] if len(reports) == 1 else reports, indent=2))
