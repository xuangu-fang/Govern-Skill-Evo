#!/usr/bin/env python3
"""Load explicit credentials and dispatch a full V26 Campaign to the shared CLI."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.runs.run_v26_pilot import read_credentials
from src.skill_evolution.v26 import cli
from src.skill_evolution.v26.facts import require
from src.skill_evolution.v26.stages import read


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    parser.add_argument('--config', required=True)
    parser.add_argument('--env-file', default=str(ROOT / '.env'))
    release = ROOT / 'data/officeqa/releases/763a8366abf2a3605c381d53586d844dc60fa756'
    parser.add_argument('--prepared-root', default=str(release / 'prepared'))
    parser.add_argument('--parsed-root', default=str(release / 'upstream/treasury_bulletins_parsed'))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args(argv)
    if args.validate_only:
        require(not args.resume, '--validate-only cannot resume a Campaign')
        cli.main(['run', args.directory, '--config', args.config,
                  '--prepared-root', args.prepared_root, '--parsed-root', args.parsed_root, '--validate-only'])
        return
    require(args.resume or not (Path(args.directory) / 'state.json').exists(),
            'Existing Campaign requires explicit --resume')
    config = read(args.config)
    credentials = read_credentials(args.env_file)
    endpoint = credentials.get('OPENAI_BASE_URL', '').rstrip('/') + '/chat/completions'
    require(config['actor']['endpoint'] == endpoint, 'Actor endpoint differs from selected env file')
    require(all(call['endpoint'] == endpoint for call in config['module_calls'].values()),
            'Method endpoint differs from selected env file')
    key_name = 'V26_CAMPAIGN_API_KEY'
    previous = os.environ.get(key_name)
    os.environ[key_name] = credentials['OPENAI_API_KEY']
    try:
        cli.main(['run', args.directory, '--config', args.config,
                  '--prepared-root', args.prepared_root, '--parsed-root', args.parsed_root,
                  '--actor-key-env', key_name, '--method-key-env', key_name,
                  *(['--resume'] if args.resume else [])])
    finally:
        if previous is None:
            os.environ.pop(key_name, None)
        else:
            os.environ[key_name] = previous


if __name__ == '__main__':
    main()
