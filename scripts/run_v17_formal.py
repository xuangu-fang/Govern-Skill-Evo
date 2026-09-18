"""Frozen formal v17 experiment. Default is preflight only; --run starts models."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'experiments/v17_formal_001')
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    from loguru import logger
    logger.remove(); logger.add(sys.stderr, level='WARNING')
    from src.skill_evolution.formal_v17 import verify_freeze, preflight, run_campaign
    config = verify_freeze()
    print(preflight(config), flush=True)
    if args.run:
        run_campaign(config, args.output.resolve())


if __name__ == '__main__':
    main()
