"""Verify native SkillAdam and SkillOpt publications against their original records."""
from hashlib import sha256
import json
from math import isclose
from pathlib import Path

from scripts.runs.spreadsheetbench.verify_archive import (
    ROOT, check_evaluation, check_metrics, read, read_episode, require, source_path,
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def check_copies(published, manifest, path_type):
    for name, record in manifest.items():
        selected = published / name
        require(digest(selected) == record['sha256'], f'Published bytes differ: {selected}')
        if path_type is not None:
            require(selected.read_bytes() == path_type(ROOT / record['source']).read_bytes(),
                    f'Published file differs from its original: {selected}')


def check_adam_checkpoints(published, training, path_type):
    campaign = ROOT / training['source'] / 'campaign'
    snapshots = training['checkpoints']
    require([row['round'] for row in snapshots] == list(range(9))
            and training['config_origin'] in ('archived_run', 'reused_aligned_actor'),
            'SkillAdam checkpoint index differs')
    config = (published / 'config/shared_config.json' if training['config_origin'] == 'archived_run'
              else ROOT / training['source_config'])
    require(config.is_file(), 'Published SkillAdam Actor configuration is missing')
    checkpoint = None if path_type is None else read(path_type(campaign / 'checkpoint.json'))
    if checkpoint is not None:
        require(checkpoint['next_iteration'] == len(checkpoint['iterations']) == 8
                and not checkpoint['pending_post_decision'], 'SkillAdam training is incomplete')
        batches = read(config)['batches']
        require(len(batches) == 8, 'SkillAdam batch count differs')
    for row in snapshots:
        current = published / row['skill']
        require(digest(current) == row['sha256'], f'SkillAdam snapshot differs: {current}')
        if checkpoint is None:
            continue
        number = row['round']
        if number:
            step = checkpoint['iterations'][number - 1]
            require(step['accepted'] == row['accepted']
                    and step['training_case_ids'] == step['validation_case_ids'] == batches[number - 1],
                    f'SkillAdam native decision or batch differs at R{number:02}')
        binding = read(path_type(ROOT / row['batch_source']))
        require(binding['skill'].encode() == current.read_bytes(), f'SkillAdam binding differs: {current}')
    if checkpoint is not None:
        final = (published / snapshots[-1]['skill']).read_bytes()
        require(checkpoint['current_skill'].encode() == final
                == path_type(campaign / 'final_skill.md').read_bytes(),
                'SkillAdam final publication differs')


def check_skillopt_selection(published, training, path_type):
    results = published / 'results'
    selected = read(results / 'selection.json')
    history = read(results / 'history.json')
    step = selected['best_step']
    require(training['steps'] == len(history) == 8 and selected == training['selection']
            and selected['best_origin'] == f'step_{step:04}'
            and history[step - 1]['selection_hard'] == selected['best_selection_hard']
            and history[-1]['best_step'] == step
            and digest(results / 'best_skill.md') == selected['sha256']
            and (results / 'best_skill.md').read_bytes() == (results / 'skills' / f'R{step:02}.md').read_bytes(),
            'SkillOpt Selection or final Skill differs')
    require([row['action'] for row in training['slow_updates']] == ['inject_placeholder', *['reject'] * 3],
            'Slow Update history differs')
    if path_type is None:
        return
    campaign = ROOT / training['source'] / 'campaign'
    folder = campaign / 'steps' / f'step_{step:04}' / 'selection_eval'
    binding = read(path_type(folder / 'binding.json'))
    rows = [json.loads(line) for line in path_type(folder / 'results.jsonl').read_text().splitlines()]
    require(binding['skill'].encode() == (results / 'best_skill.md').read_bytes()
            and {row['id'] for row in rows} == {task.removeprefix('val:') for task in binding['tasks']}
            and len(rows) == 40
            and isclose(sum(row['hard'] for row in rows) / len(rows), selected['best_selection_hard']),
            'SkillOpt Best selection receipts differ')
    for row in training['slow_updates']:
        original = read(path_type(ROOT / row['source']))
        require(all(original[key] == value for key, value in row.items() if key not in ('source', 'epoch')),
                f'SkillOpt Slow Update history differs at epoch {row["epoch"]}')


def check_skillopt_retry(expected, test_tasks, bundle, skill, directory, path_type):
    retry = expected['independent_retry']
    uid = retry['task_id']
    folder = path_type(ROOT / retry['source'])
    request = read(folder / 'request.json')['body']
    score = read(folder / 'score.json')
    summary = read(path_type(ROOT / expected['source_summary']))
    original = path_type(ROOT / directory)
    require(summary['retry_task'] == uid and summary['status'] == 'complete'
            and uid in test_tasks and not (original / 'episodes' / uid.replace(':', '_') / 'result.json').exists()
            and len(list((original / 'episodes').glob('*/result.json'))) == expected['standard_receipts']
            and request['model'] == summary['model'] == expected['actor_model']
            and request['max_completion_tokens'] == summary['retry_max_completion_tokens'] == 128000
            and read(folder / 'execution.json')['output_openable']
            and any(message['role'] == 'system' and skill.decode() in message['content']
                    for message in request['messages']),
            'SkillOpt retry request, execution or source differs')
    require(score['hard'] == summary['retry_hard'] == retry['hard']
            and score['per_cell_pass_rate'] == retry['per_cell_pass_rate'], 'SkillOpt retry score differs')
    rows = [read_episode(task, directory, bundle, path_type) if task != uid else {'task_id': task, **score}
            for task in test_tasks]
    require([row['task_id'] for row in summary['tasks']] == test_tasks, 'SkillOpt combined Test task set differs')
    for row, original_row in zip(rows, summary['tasks']):
        require(all(row[key] == original_row[key] for key in ('hard', 'per_cell_pass_rate')),
                f'SkillOpt combined score differs for {row["task_id"]}')
    check_metrics(summary, rows, directory)
    check_metrics(expected, rows, directory)


def verify_native(published, expected_count, path_type=None):
    training = read(published / 'results/checkpoints.json')
    check_copies(published, training['configs'], path_type)
    require(training['run_id'] == published.name and training['status'] == 'complete', 'Native run identity differs')
    if training['method'] == 'SkillAdam':
        check_adam_checkpoints(published, training, path_type)
    else:
        require(training['method'] == 'SkillOpt', 'Unexpected native method')
        check_copies(published, training['snapshots'], path_type)
        check_skillopt_selection(published, training, path_type)
    test_tasks = training['test_tasks']
    require(len(test_tasks) == len(set(test_tasks)) == 280, 'Native Test cohort differs')
    names = read(published / 'results/evaluations.json')
    require(len(names) == len(set(names)) == expected_count, 'Native evaluation list differs')
    sources = set()
    results = {}
    for name in names:
        row = read(published / name)
        skill = published / row['evaluated_skill']
        require(row['training_id'] == training['run_id'] and row['source'] not in sources
                and row['completed'] == 280 and digest(skill) == row['skill_sha256']
                and row['standard_receipts'] + int('independent_retry' in row) == row['completed']
                and isclose(row['success'] / row['completed'], row['hard']),
                f'Native evaluation summary differs: {name}')
        sources.add(row['source'])
        results[Path(name).parent.name] = [row['success'], row['completed']]
        if path_type is not None:
            directory = source_path(row['source'], Path('artifacts'))
            folder = path_type(ROOT / directory)
            bundle = read(folder / 'input.json')
            config = bundle['actor_config']
            campaign = Path(row['campaign'])
            require(source_path(bundle['campaign'], campaign) == campaign
                    and config['test_tasks'] == test_tasks
                    and bundle['tasks'] == [config['task_items'][task] for task in test_tasks]
                    and config['actor_model'] == row['actor_model']
                    and config['actor_max_workers'] == row['actor_max_workers']
                    and bundle['skill_text'].encode() == skill.read_bytes() == (folder / 'final_skill.md').read_bytes(),
                    f'Native test binding differs: {directory}')
            if 'independent_retry' in row:
                check_skillopt_retry(row, test_tasks, bundle, skill.read_bytes(), directory, path_type)
            else:
                check_evaluation(row, campaign, config, skill.read_bytes(), path_type)
    return results
