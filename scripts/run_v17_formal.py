"""Frozen formal v17 experiment. Default is preflight only; --run starts models."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--resume', action='store_true', help='Reuse completed Evolution tasks in an interrupted run')
    parser.add_argument('--total-rounds', type=int, help='Explicitly extend a resumed campaign to this total round count')
    parser.add_argument('--output', type=Path, default=ROOT / 'experiments/v17_formal_001')
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    from loguru import logger
    logger.remove(); logger.add(sys.stderr, level='WARNING')
    from src.skill_evolution.formal_v17 import verify_freeze, preflight, run_campaign
    config = verify_freeze()
    print(preflight({**config, 'rounds': args.total_rounds or config['rounds']}), flush=True)
    if args.run:
        run_campaign(config, args.output.resolve(), resume=args.resume, total_rounds=args.total_rounds)


if __name__ == '__main__':
    main()
