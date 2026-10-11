"""Project a completed round into v21 learning evidence without any model calls."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.skill_evolution.benchmark_adapter_v20 import BenchmarkAdapterV20, DEFAULT_CONFIG
from src.skill_evolution.modification_evidence_v21 import (
    prepare_memory_evidence, load_modification_evidence,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--round-dir', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--config', default=str(DEFAULT_CONFIG), help='Frozen source benchmark config')
    parser.add_argument('--history', nargs=2, action='append', default=[], metavar=('PATH', 'EXPECTED_REF'),
                        help='Explicitly imported/committed evidence, never guessed from neighboring folders')
    args = parser.parse_args()
    adapter = BenchmarkAdapterV20.from_config(args.config)
    history = tuple(load_modification_evidence(p, expected_ref=ref) for p, ref in args.history)
    evidence = prepare_memory_evidence(round_dir=args.round_dir, backend=adapter.evolution,
                                       output=args.output, history=history)
    print(json.dumps({'evidence_ref': evidence.evidence_ref,
                      'matched_pairs': len(evidence.payload['current_pair_refs']),
                      'output': str(Path(args.output).resolve()), 'model_calls': 0,
                      'memory_committed': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
