import argparse
from pathlib import Path
from .campaign import current, prepare, run_round


def main():
    parser = argparse.ArgumentParser(description='ALFWorld V24.2 campaign')
    parser.add_argument('command', choices=('prepare', 'run-round', 'status'))
    parser.add_argument('--campaign', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        state = prepare(args.campaign)
    elif args.command == 'run-round':
        state = run_round(args.campaign)
    else:
        _, state = current(args.campaign)
    print(f"next_round={state['next_round']} memory_rounds={len(state['memory']['rounds'])}")


if __name__ == '__main__':
    main()
