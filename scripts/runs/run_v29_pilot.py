"""Run or resume only DocVQA R01 using the existing campaign and transports."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from src.skill_evolution.v27.transport import HTTPGenerator
from src.skill_evolution.v29 import evolution as ev
from src.skill_evolution.v29.config import validate_config
from src.skill_evolution.v29.campaign import CampaignAdapter
from src.skill_evolution.v29.benchmarks.docvqa.actor import ChatTransport
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset


def run_pilot(directory, config, *, generate, resume=False):
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.pilot.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = (root / 'state.json').exists()
        ev.require(resume == started, 'Use --resume only for an existing pilot')
        validate_config(config, executable=True)
        if started:
            ev.require(ev.read(root / 'config.json') == config, 'Pilot configuration changed')
            state = ev.read(root / 'state.json')
            ev.require(state['next_round'] in (1, 2), 'Pilot advanced beyond R01')
            if state['next_round'] == 2:
                return ev.read(root / 'rounds/R01/result.json')
        return ev.run_round(root, config=config, generate=generate, resume=resume,
                            hook=lambda stage: print(f'{ev.now()} {stage}', flush=True))


def read_credentials(path, config):
    credentials = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.removeprefix('export ').split('=', 1)
        credentials[key.strip()] = value.strip().strip('\"\'')
    ev.require(bool(credentials.get('OPENAI_API_KEY')), 'Missing OPENAI_API_KEY')
    endpoint = credentials.get('OPENAI_BASE_URL', '').rstrip('/') + '/chat/completions'
    ev.require(endpoint == config['actor']['endpoint'] and
               all(c['endpoint'] == endpoint for c in config['module_calls'].values()),
               'Endpoint differs from selected env file')
    return credentials


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    parser.add_argument('--config', required=True)
    parser.add_argument('--env-file', default=str(ROOT / '.env'))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    config = ev.read(args.config)
    actor = DocVQAActorAdapter(DocVQADataset())
    actor.workers = 15
    adapter = CampaignAdapter(actor)
    with adapter.using():
        validate_config(config, executable=True)
        if args.validate_only:
            print(json.dumps({'status': 'valid', 'first_batch_size': len(config['batches'][0]),
                              'workers': actor.workers, 'stop_after_round': 1}))
            return
        credentials = read_credentials(args.env_file, config)
        actor.transport = ChatTransport(credentials['OPENAI_API_KEY'])
        result = run_pilot(args.directory, config, generate=HTTPGenerator(credentials['OPENAI_API_KEY']),
                           resume=args.resume)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
