"""Build or execute one v21 Memory update from a verified evidence artifact."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.skill_evolution.v21.modification_evidence_v21 import load_modification_evidence
from src.skill_evolution.v21.memory_update_v21 import build_memory_update_input, build_memory_update_request, run_memory_update


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--expected-ref', required=True)
    parser.add_argument('--issue', action='append', default=[], help='Additional historical issue to load')
    parser.add_argument('--pair', action='append', default=[], help='Additional replay pair to load')
    parser.add_argument('--model', default='deepseek-v4-pro')
    parser.add_argument('--max-input-tokens', type=int, default=800000)
    parser.add_argument('--output', help='Independent update artifact directory; required with --run')
    parser.add_argument('--run', action='store_true', help='Explicitly make one configured model call')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.resume and not args.run:
        parser.error('--resume requires --run')
    if args.run and not args.output:
        parser.error('--run requires --output')
    evidence = load_modification_evidence(args.evidence, expected_ref=args.expected_ref)
    request = build_memory_update_input(evidence, issue_refs=args.issue, pair_refs=args.pair)
    if args.run:
        result = run_memory_update(request, output=args.output, resume=args.resume,
                                   model=args.model, max_input_tokens=args.max_input_tokens)
        audit = json.loads((Path(args.output)/'regression-retention.json').read_text())
        print(json.dumps({'input_ref': request.input_ref,
                          'updated_evidence_ref': result.updated_evidence.evidence_ref,
                          'updated_issues': len(result.payload['memory_update']['issues']),
                          'regression_retention_audit': str(Path(args.output).resolve()/'regression-retention.json'),
                          'uncited_regression_pairs': len(audit['uncited_pair_refs']),
                          'one_sided_regression_pairs': len(audit['one_sided_pair_refs']),
                          'active_head_written': False}, ensure_ascii=False))
    else:
        prompt = build_memory_update_request(request, model=args.model,
                                             max_input_tokens=args.max_input_tokens)
        print(json.dumps({'input_ref': request.input_ref, 'input_budget': prompt['input_budget'],
                          'loaded_pairs': len(request.payload['pairs']),
                          'scanned_current_pairs': len(evidence.payload['current_pair_refs']),
                          'regression_pairs': len(request.payload['regression_pair_refs']),
                          'loaded_issues': len(request.payload['memory_issues']),
                          'model_calls': 0, 'active_head_written': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
