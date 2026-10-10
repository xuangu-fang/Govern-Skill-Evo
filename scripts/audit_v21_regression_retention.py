"""Audit a saved v21 Memory response offline, without rewriting its history."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.skill_evolution.edit_tracking_v19 import encode
from src.skill_evolution.evolution_replay_v19 import _load
from src.skill_evolution.memory_generation_v19 import _read_call
from src.skill_evolution.memory_store_v19 import require
from src.skill_evolution.modification_evidence_v21 import load_modification_evidence
from src.skill_evolution.memory_update_v21 import (
    MemoryUpdateInput, validate_memory_update, regression_retention_report, _save_once,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--expected-ref', required=True)
    parser.add_argument('--update', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    require(not args.output.resolve().is_relative_to(args.update.resolve()),
            'offline audit output must be outside the historical update directory')
    evidence = load_modification_evidence(args.evidence, expected_ref=args.expected_ref)
    request = MemoryUpdateInput(evidence, encode(_load(args.update/'input.json')))
    raw = _read_call(args.update, _load(args.update/'request.json'))
    result = validate_memory_update(raw, request=request, wire=True)
    require(result.payload == _load(args.update/'result.json'), 'saved Memory result differs')
    report = regression_retention_report(request, result)
    _save_once(args.output, report)
    print(json.dumps({'audit': str(args.output.resolve()),
                      'uncited_pair_refs': report['uncited_pair_refs'],
                      'one_sided_pair_refs': report['one_sided_pair_refs'],
                      'unreadable_pair_refs': report['unreadable_pair_refs'],
                      'model_calls': 0, 'history_modified': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
