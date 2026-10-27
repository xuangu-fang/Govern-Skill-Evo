import json

import os

from pathlib import Path

import subprocess

from src.skill_evolution.v24.benchmarks.alfworld.actor.skill_runtime import write_record, LEGACY_INJECTION

from src.skill_evolution.v24.facts import require

from src.skill_evolution.v24.contracts.model_routing import model_for_endpoint

ROOT = Path(__file__).resolve().parents[5]


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    write_record(path, value)


def runtime_snapshot(config):
    # Synthetic runners use a nonexistent interpreter; real runs freeze installed packages.
    if not Path(config['actor_python']).is_file():
        return None
    code = ('import importlib.metadata as m,json,sys; '
            'print(json.dumps({"python":sys.version,"packages":{n:m.version(n) '
            'for n in ["alfworld","textworld","numpy","requests"]}}))')
    return json.loads(subprocess.check_output([config['actor_python'], '-c', code], text=True))


def check_environment_route(config):
    """Endpoint is frozen explicitly; process .env cannot silently choose the method."""
    cfg = config['call_config']
    base = cfg['endpoint'].removesuffix('/chat/completions')
    require(cfg['model'] == model_for_endpoint(base, cfg['model']), 'Frozen model/endpoint mismatch')
    require(config['actor_base_url'] == base and config['actor_model'] == cfg['model'],
            'Actor/module route differs')


def check_live_environment(config):
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env', override=False)
    check_environment_route(config)
    cfg = config['call_config']
    require(os.environ.get('OPENAI_BASE_URL', '').rstrip('/') == cfg['endpoint'].removesuffix('/chat/completions'),
            'Live endpoint differs from frozen Campaign; configure matching endpoint and credentials explicitly')
    require(bool(os.environ.get('OPENAI_API_KEY')), 'API key is not configured')


def actor_command(task, skill_file, directory, config, *, final=False):
    """One Actor protocol for optimization, paired Gate rollouts and final Test."""
    split = task.split(':')[0]
    if final:
        require(split == 'test', 'Final evaluation permits Test only')
        purpose = 'final'
    else:
        require(split in config.get('optimization_splits', ['train']), 'Task outside optimization pool')
        purpose = 'optimization' if 'val' in config.get('optimization_splits', []) else 'learning'
    cmd = [config['actor_python'], '-m', 'src.skill_evolution.v24.benchmarks.alfworld.actor.run_task_skill', '--model', config['actor_model'],
           '--split', split, '--purpose', purpose, '--task-id', task, '--max-steps', str(config['max_steps']),
           '--request-attempts', str(config['actor_request_attempts']), '--strict-response', '--archive-responses',
           '--output-root', str(directory),
           '--skill-injection', config.get('actor_skill_injection', LEGACY_INJECTION)]
    if 'actor_output_format' in config:
        cmd += ['--output-format', config['actor_output_format']]
    if config.get('actor_retry_invalid_actions', False):
        cmd += ['--retry-invalid-actions']
    if config.get('actor_action_feedback', False):
        cmd += ['--action-feedback']
    if skill_file is not None: cmd += ['--skill-file', str(skill_file)]
    return cmd


def actor_task(task, skill_file, directory, config, *, final=False):
    """Use the shared command builder; no task-level automatic restart."""
    check_live_environment(config)
    for filename, content in config.get('environment_files', {}).items():
        require(Path(filename).read_bytes().decode('utf-8') == content, 'Frozen environment file changed')
    if 'task_items' in config:
        from src.skill_evolution.v24.benchmarks.alfworld.actor.run_task import SPLIT_ROOT
        actual = next((item for item in read(SPLIT_ROOT/task.split(':')[0]/'items.json') if item['id'] == task), None)
        require(actual == config['task_items'][task], 'Frozen task mapping changed before execution')
    cmd = actor_command(task, skill_file, directory, config, final=final)
    save(directory/'command.json', cmd)
    process_env = os.environ.copy()
    if 'environment_root' in config:
        process_env['ALFWORLD_DATA'] = config['environment_root']
    if 'actor_base_url' in config:
        process_env['OPENAI_BASE_URL'] = config['actor_base_url']
    with (directory/'process.log').open('w') as out:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, env=process_env)
    paths = list(directory.rglob('trajectory.json'))
    require(len(paths) == 1, f'Actor exit {proc.returncode}: missing/ambiguous trajectory')
    return paths[0]

