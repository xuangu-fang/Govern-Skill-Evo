import argparse
from pathlib import Path
from .campaign import current, prepare, run_round, configuration, VERSION


def main():
    parser = argparse.ArgumentParser(description='ALFWorld general V24.10 campaign')
    parser.add_argument('command', choices=('prepare', 'run-round', 'train', 'status'))
    parser.add_argument('--campaign', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        state = prepare(args.campaign)
    elif args.command == 'run-round':
        state = run_round(args.campaign)
    elif args.command == 'train':
        state = prepare(args.campaign)
        total = len(configuration()['batches'])
        while state['next_round'] <= total:
            state = run_round(args.campaign)
            print(f"Published round {state['next_round'] - 1}/{total}", flush=True)
        run_round(args.campaign)  # Also restore the final export after an interrupted last publication.
    else:
        from src.skill_evolution.v24_2.storage import read
        if read(args.campaign / 'config.json')['method'] != VERSION:
            parser.error('Expected a V24.10 campaign')
        _, state = current(args.campaign)
    print(f"next_round={state['next_round']} memory_rounds={len(state['memory']['rounds'])}")


if __name__ == '__main__':
    main()
