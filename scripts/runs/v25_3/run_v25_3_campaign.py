"""Prepare, inspect or explicitly run the SpreadsheetBench v25.3 optimizer."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.skill_evolution.v25_3 import campaign
from src.skill_evolution.v27.transport import HTTPGenerator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'status', 'run'])
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--rounds', type=int, help='maximum rounds to advance in this invocation')
    args = parser.parse_args()
    if args.rounds is not None and (args.action != 'run' or args.rounds < 1):
        parser.error('--rounds requires run and a positive value')
    root = args.campaign.resolve()
    if args.action == 'prepare':
        state = campaign.prepare(root)
    elif args.action == 'status':
        _, state = campaign.current(root)
    else:
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env', override=False)
        if os.environ.get('OPENAI_BASE_URL', '').rstrip('/') != campaign.configuration()['actor_base_url']:
            parser.error('OPENAI_BASE_URL must match the frozen Actor endpoint')
        # Frozen Actor workers invoke python -m from their own process.
        os.environ['PYTHONPATH'] = os.pathsep.join(filter(None, [str(ROOT), os.environ.get('PYTHONPATH')]))
        state = campaign.run(root, HTTPGenerator(os.environ.get('OPENAI_API_KEY')), limit=args.rounds)
    print(f"{root}: {state['next_round'] - 1} completed rounds, "
          f"{len(state['memory']['rounds'])} Memory rounds")


if __name__ == '__main__':
    main()
