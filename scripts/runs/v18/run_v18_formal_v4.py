"""Frozen formal v18 experiment on benchmark v4; default is preflight only."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--pilot', action='store_true', help='Run exactly one end-to-end round in an isolated output')
    parser.add_argument('--resume', action='store_true', help='Reuse completed Evolution tasks in an interrupted run')
    parser.add_argument('--total-rounds', type=int, help='Compatibility option: must equal the frozen four-round limit')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if (args.resume or args.total_rounds is not None) and not args.run:
        parser.error('--resume/--total-rounds require --run')
    if args.pilot and not args.run:
        parser.error('--pilot requires --run')
    if args.pilot and args.total_rounds is not None:
        parser.error('--pilot cannot be combined with --total-rounds')
    output = args.output or ROOT / ('artifacts/methods/v18/pilot/v18_v4_pilot_002' if args.pilot else 'artifacts/methods/v18/formal/v18_v4_formal_002')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    from loguru import logger
    logger.remove(); logger.add(sys.stderr, level='WARNING')
    from src.skill_evolution.v18.formal_v18_v4 import campaign_lock, verify_freeze, preflight, run_campaign
    config = verify_freeze()
    if args.total_rounds is not None and (not args.resume or args.total_rounds != config['rounds']):
        parser.error('--total-rounds requires --resume and must equal the frozen round limit')
    preflight_rounds = 1 if args.pilot else (args.total_rounds or config['rounds'])
    print(preflight({**config, 'rounds': preflight_rounds}), flush=True)
    if args.run:
        output = output.resolve()
        with campaign_lock(output):
            run_campaign(config, output, resume=args.resume,
                         total_rounds=args.total_rounds, pilot=args.pilot)


if __name__ == '__main__':
    main()
