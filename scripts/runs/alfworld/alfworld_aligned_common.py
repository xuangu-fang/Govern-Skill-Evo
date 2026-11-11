"""Frozen ALFWorld baseline inputs and shared Actor subprocess bridge.

Importing this module performs no execution. The Actor CLI is the same one
used by alfworld_verified_feedback_001; no second action/retry implementation.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess

from src.skill_evolution.shared.experiment_paths import ROOT, resolve_experiment_path

EXPERIMENT = ROOT / 'experiments/baselines/alfworld/alfworld_current_actor_20261025'
UPSTREAM = ROOT / 'external/SkillOpt'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def frozen_input(name):
    """Locate the input bytes named by the original baseline manifests."""
    path = ROOT / name
    if path.is_relative_to(ROOT):
        snapshot = EXPERIMENT / 'provenance/before_layout' / path.relative_to(ROOT)
        if snapshot.is_file():
            return snapshot
    return resolve_experiment_path(path)


def actor_command(actor, item, output, skill_file=None):
    split = item['id'].split(':', 1)[0]
    purpose = {'train': 'learning', 'val': 'selection', 'test': 'final'}[split]
    command = [actor['python'], '-m', 'src.adapters.alfworld.run_task_skill',
               '--model', actor['model'], '--split', split, '--purpose', purpose,
               '--task-id', item['id'], '--max-steps', str(actor['max_steps']),
               '--skill-injection', actor['skill_injection'],
               '--output-format', actor['output_format'],
               '--request-attempts', str(actor['request_attempts']),
               '--strict-response', '--retry-invalid-actions', '--action-feedback',
               '--archive-responses', '--output-root', str(output)]
    if skill_file is not None:
        command.extend(['--skill-file', str(skill_file)])
    return command


def check():
    """Read-only, offline check; never loads credentials or constructs an env."""
    from skillopt.config import flatten_config, load_config
    actor = read(EXPERIMENT / 'actor.json')
    cfg = flatten_config(load_config(str(EXPERIMENT / 'skillopt.yaml')))
    no = read(EXPERIMENT / 'noskill.json')
    lock = read(EXPERIMENT / 'manifest.json')
    for relative, expected in lock['files'].items():
        require(sha(frozen_input(relative)) == expected, f'Frozen input changed: {relative}')
    for relative, expected in lock['environment_files'].items():
        require(sha(Path(actor['environment_root']) / relative) == expected,
                f'Environment changed: {relative}')
    # Only the split and initial-Skill paths changed when the config moved.
    frozen_yaml = frozen_input('experiments/baselines/alfworld_current_actor_20261025/skillopt.yaml')
    original_cfg = flatten_config(load_config(str(frozen_yaml)))
    for key in ('split_dir', 'skill_init'):
        original_cfg[key] = str(resolve_experiment_path(original_cfg[key]).relative_to(ROOT))
    require(cfg == original_cfg, 'SkillOpt configuration differs from the original experiment')
    original = read(ROOT / actor['reference_campaign'])
    require(actor['model'] == original['actor_model'], 'Actor model differs')
    require(actor['call_config'] == original['call_config'], 'Actor call parameters differ')
    require(actor['request_attempts'] == original['actor_request_attempts'] == 6,
            'Actor attempt budget differs')
    require(actor['output_format'] == original['actor_output_format'] == 'action_only_v1',
            'Output contract differs')
    require(actor['skill_injection'] == original['actor_skill_injection'] == 'skillopt_user_v1',
            'Skill injection differs')
    require(actor['max_steps'] == original['max_steps'] == cfg['max_steps'] == 50,
            'Step budget differs')
    require(actor['workers'] == original['actor_max_workers'] == cfg['workers'] == 8,
            'Worker count differs')
    require(actor['python'] == original['actor_python'], 'Actor Python differs')
    require(actor['strict_response'] is True and actor['retry_invalid_actions'] is True
            and actor['action_feedback'] is True and original['actor_retry_invalid_actions'] is True
            and original['actor_action_feedback'] is True, 'Action retry flags differ')
    require(actor['history_length'] == 2 and actor['environment_seed'] == 42,
            'History/environment seed differs')
    require(actor['optimizer_request_attempts'] == 3, 'Optimizer transport budget changed')
    require((EXPERIMENT / 'initial_skill.md').read_text() == original['initial_skill']['text'],
            'Initial skill differs')
    require(cfg['slow_update_gate_with_selection'] is True and cfg['eval_final_skill'] is False,
            'Slow gate / final test policy differs')
    require(no['skill_mode'] == 'none' and no['split'] == 'test' and no['purpose'] == 'final',
            'No Skill is not a pure test-only baseline')
    require(no['actor_config'] == 'actor.json' and no['tasks'] == 'splits/test/items.json'
            and no['expected_tasks'] == 134, 'No Skill manifest reference differs')
    counts = {}
    all_paths = set()
    for split, n in [('train', 39), ('val', 18), ('test', 134)]:
        tasks = read(EXPERIMENT / f'splits/{split}/items.json')
        require(len(tasks) == n, f'{split} size differs')
        require(tasks == read(ROOT / f'benchmarks/alfworld/editions/skillopt_39_18_134/{split}/items.json'),
                f'{split} differs from shared Actor task lookup')
        paths = {t['gamefile'] for t in tasks}
        require(len(paths) == n and not paths & all_paths, 'Duplicate or overlapping tasks')
        require(all(t['id'].startswith(split + ':') for t in tasks), 'Split/id mismatch')
        all_paths.update(paths)
        counts[split] = n
    old = read(ROOT / 'artifacts/baselines/skillopt/alfworld_deepseek_v23_4_formal_20261023/config.json')
    preserved = ['num_epochs', 'train_size', 'batch_size', 'accumulation', 'seed',
                 'minibatch_size', 'merge_batch_size', 'analyst_workers', 'failure_only',
                 'max_analyst_rounds', 'edit_budget', 'min_edit_budget', 'lr_scheduler',
                 'lr_control_mode', 'skill_update_mode', 'use_slow_update', 'slow_update_samples',
                 'longitudinal_pair_policy', 'use_meta_skill', 'use_skill_aware_reflection',
                 'use_gate', 'sel_env_num', 'test_env_num', 'eval_test', 'max_steps',
                 'max_completion_tokens', 'workers', 'max_api_workers']
    for key in preserved:
        require(cfg[key] == old[key], f'Unexpected method change: {key}')
    for python in (actor['python'], actor['skillopt_python']):
        require(Path(python).is_file(), 'Configured Python is missing')
    return {'status': 'prepared', 'offline_check': 'passed', 'model_requests': 0,
            'split_counts': counts, 'skillopt_test_targets': ['initial', 'best'],
            'final_skill_test': 'disabled', 'actor_request_attempts': 6,
            'slow_update_gate_with_selection': True,
            'preserved_method_parameters': preserved}


def validate_trajectory(path, actor, item, skill_text):
    from src.adapters.alfworld.verify_skill_run import verify_record
    from src.adapters.alfworld.response_archive import verify_response_archive
    from src.adapters.alfworld.skill_runtime import execution_protocol, digest
    record = read(path)
    audit = verify_record(record)
    require(record['task'] == item, 'Actor task differs from manifest')
    require(record['model'] == actor['model'], 'Trajectory model differs')
    require(record['skill']['text'] == skill_text, 'Trajectory skill differs')
    require(record['skill']['mode'] == ('none' if skill_text is None else 'fixed'),
            'Trajectory skill mode differs')
    require(record['request_policy'] == {'max_attempts': 6, 'strict_response': True},
            'Trajectory retry policy differs')
    require(record['protocol']['invalid_output_policy'] == 'previous_action_validation_error_v1',
            'Trajectory feedback policy differs')
    require(record['protocol'] == execution_protocol(50, actor['skill_injection'],
            output_format=actor['output_format'], retry_invalid_actions=True, action_feedback=True),
            'Trajectory execution protocol differs')
    require(record['backend_id'] == digest((actor['base_url'] + '/chat/completions').encode()),
            'Trajectory backend differs')
    for event in record['steps']:
        for attempt in event.get('transport_attempts', []):
            verify_response_archive(path, attempt)
    require(audit['episode_complete'],
            'Actor technical failure/interruption; batch stopped, not scored or automatically rerun')
    return record


def result_from_record(record, item, path):
    executed = [s for s in record['steps'] if s['phase'] == 'executed']
    task_type = item['task_type']
    if task_type == 'pick_and_place_simple':
        task_type = 'pick_and_place'
    return {'id': item['id'], 'hard': int(record['won']), 'soft': float(record['won']),
            'n_turns': len(executed), 'fail_reason': '' if record['won'] else record['status'],
            'agent_ok': True, 'task_type': task_type, 'instruction_type': task_type,
            'gamefile': record['gamefile'], 'task_description': record['goal'],
            'trajectory': str(path)}


def run_batch(actor, items, skill_text, output, tracker=None):
    """Run once per task; saved complete episodes are audited before reuse.

    Technical failures stop the batch rather than becoming optimizer evidence.
    An incomplete saved episode requires explicit recovery, never silent resampling.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    skill_file = None
    if skill_text is not None:
        require(bool(skill_text.strip()), 'Empty Skill is not the No Skill baseline')
        skill_file = output / 'actor_skill.md'
        if skill_file.exists():
            require(skill_file.read_text() == skill_text, 'Saved rollout skill changed')
        else:
            skill_file.write_text(skill_text)
    def one(item):
        directory = output / 'episodes' / item['id'].replace(':', '_')
        paths = list(directory.glob('*/trajectory.json')) if directory.exists() else []
        if paths:
            require(len(paths) == 1, 'Multiple episode attempts require explicit resolution')
        else:
            require(not directory.exists(), 'Incomplete episode directory; explicit recovery required')
            directory.mkdir(parents=True)
            with (directory / 'actor.log').open('wb') as log:
                completed = subprocess.run(actor_command(actor, item, directory, skill_file),
                                           cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                           env={**os.environ, 'ALFWORLD_DATA': actor['environment_root'],
                                                'PYTHONDONTWRITEBYTECODE': '1'})
            require(completed.returncode == 0, f'Actor stopped: {directory}/actor.log')
            paths = list(directory.glob('*/trajectory.json'))
            require(len(paths) == 1, 'Actor did not produce one trajectory')
        record = validate_trajectory(paths[0], actor, item, skill_text)
        conversation = [{'step': s['step'] - 1, 'action': s['action'], 'reasoning': None,
                         'model_response': s['model_response']['content'],
                         'env_feedback': s['observation'], 'reward': s['reward'], 'done': s['done']}
                        for s in record['steps'] if s['phase'] == 'executed']
        write(output / 'predictions' / item['id'] / 'conversation.json', conversation)
        return result_from_record(record, item, paths[0]), record
    with ThreadPoolExecutor(max_workers=actor['workers']) as pool:
        completed = list(pool.map(one, items))
    results = []
    known_input = known_output = unknown = requests = 0
    for result, record in completed:
        results.append(result)
        for step in record['steps']:
            for attempt in step.get('transport_attempts', []):
                requests += 1
                usage = attempt.get('usage')
                if usage:
                    known_input += usage.get('prompt_tokens', 0)
                    known_output += usage.get('completion_tokens', 0)
                    if tracker is not None:
                        tracker.record('rollout', usage.get('prompt_tokens', 0),
                                       usage.get('completion_tokens', 0))
                else:
                    unknown += 1
    write(output / 'actor_usage.json', {'requests': requests, 'unknown_usage_requests': unknown,
                                      'known_prompt_tokens': known_input,
                                      'known_completion_tokens': known_output,
                                      'includes_rejected_responses': True})
    path = output / 'results.jsonl'
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in results))
    return results


def configure_runtime(actor):
    """Called only after explicit --start, before importing SkillOpt's backends."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    require(os.environ.get('OPENAI_API_KEY'), 'OPENAI_API_KEY is missing')
    require(os.environ.get('OPENAI_BASE_URL', '').rstrip('/') == actor['base_url'],
            'Unexpected internal proxy endpoint')
    values = {'BASE_URL': actor['base_url'], 'API_KEY': os.environ['OPENAI_API_KEY'],
              'MODEL': actor['model'], 'TEMPERATURE': '1', 'MAX_TOKENS': '16384',
              'TIMEOUT_SECONDS': '300', 'CONNECT_TIMEOUT_SECONDS': '10',
              'MAX_ATTEMPTS': str(actor['optimizer_request_attempts']),
              'EXTRA_BODY': json.dumps({'thinking': {'type': 'enabled'},
                                        'reasoning_effort': 'medium', 'stream': False})}
    for prefix in ('', 'OPTIMIZER_', 'TARGET_'):
        for key, value in values.items():
            os.environ[prefix + 'OPENAI_COMPATIBLE_' + key] = value
    # Actor uses its own shared six-attempt loop, not the optimizer SDK path.
    os.environ['TARGET_OPENAI_COMPATIBLE_MAX_ATTEMPTS'] = str(actor['request_attempts'])
    proxy_host = actor['base_url'].split('://', 1)[1]
    os.environ['NO_PROXY'] = ','.join(filter(None, [os.environ.get('NO_PROXY'), proxy_host]))
    os.environ['no_proxy'] = os.environ['NO_PROXY']
    os.environ['ALFWORLD_DATA'] = actor['environment_root']
