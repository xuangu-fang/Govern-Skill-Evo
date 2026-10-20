"""Run the isolated V22 v3 runtime with endpoint-based Actor and evolution model routing."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE / 'revision'))

from src.skill_evolution.v22.continual_runner import main

if __name__ == '__main__':
    args = sys.argv[1:]
    if not any(arg == '--env-file' or arg.startswith('--env-file=') for arg in args):
        args += ['--env-file', str(ROOT / '.env')]
    raise SystemExit(main(args))
