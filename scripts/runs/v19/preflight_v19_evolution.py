"""Construct all benchmark-v4 Evolution environments without model calls."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New output directory; never overwritten')
    args = parser.parse_args()
    from loguru import logger
    logger.remove(); logger.add(sys.stderr, level='WARNING')
    from src.skill_evolution.v19.evolution_benchmark_v19 import BenchmarkEvolutionV19
    backend = BenchmarkEvolutionV19()
    initial = (backend.freeze / 'S0.md').read_bytes().decode('utf-8')
    result = backend.preflight(artifact_dir=args.output,
                              skills=(initial, '', '- Verify applicable conditions before acting.\n'))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
