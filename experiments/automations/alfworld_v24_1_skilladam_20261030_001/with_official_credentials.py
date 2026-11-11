"""Load the same official credentials as V25, then execute one frozen job command."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import frozen_file, job_command


def main(argv=None):
    command = sys.argv[1:] if argv is None else argv
    plan = json.loads((HERE / 'plan.json').read_text())
    if datetime.now(timezone.utc) < datetime.fromisoformat(plan['not_before_utc'].replace('Z', '+00:00')):
        raise ValueError('Scheduled start time has not arrived')
    allowed = [job[key][2:] for job in plan['jobs'].values()
               for key in ('train_command', 'resume_command', 'test_command')]
    if command in allowed:
        command = job_command(command)
    elif command not in [job_command(args) for args in allowed]:
        raise ValueError('Command is not in the frozen ALFWorld plan')
    for name, expected in plan['frozen_inputs_sha256'].items():
        if hashlib.sha256(frozen_file(name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Frozen input changed: {name}')
    from dotenv import dotenv_values
    official = dotenv_values(ROOT / plan['credential_source']['env_file'])
    if official.get('OPENAI_BASE_URL', '').rstrip('/') != 'https://api.deepseek.com' or not official.get('OPENAI_API_KEY'):
        raise ValueError('Repository official credentials are missing or mismatched')
    env = dict(os.environ, OPENAI_API_KEY=official['OPENAI_API_KEY'],
               OPENAI_BASE_URL='https://api.deepseek.com', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    os.chdir(ROOT)
    os.execvpe(command[0], command, env)


if __name__ == '__main__':
    main()
