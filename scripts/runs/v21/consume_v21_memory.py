"""Preflight or run v21 Memory consumption against an existing Current Diagnosis batch."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.skill_evolution.v19.edit_tracking_v19 import encode
from src.skill_evolution.v19.review_contract_v19 import CurrentDiagnosisInput, CurrentFindings
from src.skill_evolution.v21.modification_evidence_v21 import load_modification_evidence
from src.skill_evolution.v21.memory_consumption_v21 import build_issue_fusion_input, build_issue_fusion_request, run_memory_consumption


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, help='Published or explicitly imported updated-evidence.json')
    parser.add_argument('--expected-ref', required=True, help='Trusted evidence content reference')
    parser.add_argument('--current-source', required=True,
        help='JSON containing parent_skill, current_requests and current_findings; no diagnosis is rerun')
    parser.add_argument('--model', default='deepseek-v4-pro')
    parser.add_argument('--run', action='store_true', help='Explicitly call Fusion/Review/Editor')
    parser.add_argument('--output', help='New independent directory, required with --run')
    args = parser.parse_args()
    if args.run and not args.output:
        parser.error('--run requires --output')
    source = json.loads(Path(args.current_source).read_text())
    evidence = load_modification_evidence(args.evidence, expected_ref=args.expected_ref)
    kwargs = dict(memory_evidence=evidence, parent_skill=source['parent_skill'],
        current_requests=tuple(CurrentDiagnosisInput(encode(r['payload']), encode(r['provenance']))
                               for r in source['current_requests']),
        current_findings=tuple(CurrentFindings(encode(f)) for f in source['current_findings']))
    if args.run:
        audit = run_memory_consumption(**kwargs, output=args.output, model=args.model)
        result = {'status': audit['result']['status'], 'generation_ref': audit['result']['input_ref'],
                  'audit': str(Path(args.output).resolve()/'generation/generation-audit.json'),
                  'active_head_written': False}
    else:
        fusion = build_issue_fusion_input(**kwargs)
        prompt = build_issue_fusion_request(fusion, model=args.model)
        result = {'input_ref': fusion.input_ref, 'memory_evidence_ref': evidence.evidence_ref,
                  'memory_issues': len(fusion.payload['memory_issues']),
                  'summarized_issues': sum('current_understanding' in i for i in fusion.payload['memory_issues']),
                  'input_budget': prompt['input_budget'], 'model_calls': 0, 'active_head_written': False}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
