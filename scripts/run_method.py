"""Launch an existing runner with an explicit canonical runtime directory.

Runner flags and run/resume semantics are unchanged. This convenience entrypoint
selects a canonical output; --print-command only prints the invocation.
"""
import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNERS = {
    'v17': ('v17', 'run_v17_formal.py'),
    'v18': ('v18', 'run_v18_formal.py'),
    'v18-v4': ('v18', 'run_v18_formal_v4.py'),
    'v19': ('v19', 'run_v19.py'),
    'v20': ('v20', 'run_v20.py'),
}


def command_for(runner, run_id, stage, forwarded):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', run_id):
        raise ValueError('run-id must be a single directory name')
    if stage not in (None, 'pilot', 'formal'):
        raise ValueError('stage must be pilot or formal')
    if any(arg == '--output' or arg.startswith('--output=') for arg in forwarded):
        raise ValueError('use run-id and stage to select the output directory')
    version, script = RUNNERS[runner]
    output = ROOT / 'artifacts/methods' / version
    if stage:
        output /= stage
    output /= run_id
    return [sys.executable, str(ROOT / 'scripts/runs' / version / script),
            *forwarded, '--output', str(output)]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    separator = argv.index('--') if '--' in argv else len(argv)
    own, forwarded = argv[:separator], argv[separator + 1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner', choices=RUNNERS)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--stage', choices=('pilot', 'formal'))
    parser.add_argument('--print-command', action='store_true')
    args = parser.parse_args(own)
    try:
        command = command_for(args.runner, args.run_id, args.stage, forwarded)
    except ValueError as error:
        parser.error(str(error))
    if args.print_command:
        print(shlex.join(command))
        return 0
    # Preserve caller cwd and environment, including relative config arguments.
    return subprocess.call(command)


if __name__ == '__main__':
    raise SystemExit(main())
