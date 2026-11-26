"""Explicit v27.1 train/test; --validate-only never executes or reads credentials."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from src.skill_evolution.v27_1.lmb import protocol
from src.skill_evolution.v27.transport import HTTPGenerator
from src.skill_evolution.v27_1.lmb.actor import ChatTransport
from src.skill_evolution.v27_1.actor_io import ActorAdapter
from src.skill_evolution.v27.training import load_dataset
from src.skill_evolution.v27_1.campaign import CampaignAdapter
from src.skill_evolution.v27_1.config import validate_config
from src.skill_evolution.v27_1.actor_io import read_skill
from src.skill_evolution.v27_1 import evolution as ev
from src.skill_evolution.v27_1.evaluation import prepare_test, run_test


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


def run_training(directory, config, *, generate=None, resume=False):
    root = Path(directory).resolve()
    validate_config(config, executable=True)
    result = ev.run_campaign(root, config=config, generate=generate, resume=resume)
    ev.require(result['status'] == 'complete', 'Training did not complete')
    final = ev.final_parent(root)
    ev.freeze_text(root / 'final_skill.md', read_skill(final))
    last = ev.read(root / 'rounds' / f"R{len(config['batches']):02}" / 'result.json')
    summary = {'status': 'complete', 'method': config['method']['version'],
               'rounds_completed': len(config['batches']), 'optimization_count': sum(map(len, config['batches'])),
               'state': result['state'], 'selected_skill': str(final.relative_to(root)),
               'exported_skill': str(root / 'final_skill.md'),
               'selected_execution_source': last['selected_execution_source'],
               'selection_round': len(config['batches']), 'test_started': False}
    ev.freeze(root / 'training_summary.json', summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('train', 'test'))
    parser.add_argument('campaign')
    parser.add_argument('--config', help='Explicit v27.1 configuration; resume defaults to saved config')
    parser.add_argument('--output', help='Separate held-out Test output directory')
    parser.add_argument('--env-file', default=str(ROOT / '.env'))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'train':
        ev.require(args.config is not None or args.resume, 'Fresh training requires --config')
        ev.require(args.output is None, '--output belongs to Test only')
    else:
        ev.require(args.config is None, 'Test uses the completed campaign configuration')
        ev.require(bool(args.output), 'Test requires --output')
    config = ev.read(args.config or Path(args.campaign) / 'config.json')
    actor = ActorAdapter(load_dataset(ROOT / 'data/livemathematicianbench/prepared_v1'))
    with CampaignAdapter(actor).using():
        validate_config(config, executable=True)
        if args.validate_only:
            test = prepare_test(args.campaign, args.output) if args.command == 'test' else None
            print(json.dumps({'status': 'valid', 'method': config['method']['version'],
                              'command': args.command, 'batch_sizes': list(map(len, config['batches'])),
                              **({'test_count': len(test['tasks']), 'selected_skill': test['selected_skill']}
                                 if test is not None else {})}))
            return
        credentials = read_credentials(args.env_file, config)
        actor.transport = ChatTransport(credentials['OPENAI_API_KEY'], metadata=protocol.ACTOR)
        if args.command == 'train':
            result = run_training(args.campaign, config, generate=HTTPGenerator(credentials['OPENAI_API_KEY']), resume=args.resume)
        else:
            result = run_test(args.campaign, args.output, resume=args.resume)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
