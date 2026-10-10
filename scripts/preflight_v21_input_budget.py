"""Compare v21 prompt costs on the same saved evidence, without model/rollout calls."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.skill_evolution.edit_tracking_v19 import encode, parse, digest
from src.skill_evolution.evidence_wire_v21 import expand
from src.skill_evolution.modification_evidence_v21 import load_modification_evidence, open_memory_evidence
from src.skill_evolution.memory_update_v21 import build_memory_update_input, build_memory_update_request
from src.skill_evolution.memory_consumption_v21 import (
    build_issue_fusion_input, build_issue_fusion_request, build_generation_input,
)
from src.skill_evolution.issue_fusion_v20 import validate_issue_fusion
from src.skill_evolution.evidence_review_v20 import build_evidence_review_request
from src.skill_evolution.review_contract_v19 import CurrentDiagnosisInput, CurrentFindings
from src.skill_evolution.memory_store_v19 import require


def comparison(before, prompt, canonical=None):
    after = prompt['input_budget']['proxy_input_tokens']
    row = {'before_tokens': before, 'after_tokens': after,
           'reduction_percent': round(100 * (before - after) / before, 2),
           'input_budget': prompt['input_budget'], 'prompt_version': prompt['prompt_version']}
    if canonical is not None:
        restored = expand(parse(prompt['user_prompt']), prompt['reference_map'])
        require(restored == canonical, 'optimized request changed canonical evidence')
        row.update(canonical_sha256=digest(encode(canonical)), exact_roundtrip=True,
            events=len(canonical['events']), trajectories=len(canonical['trajectories']),
            pairs=len(canonical['pairs']), source_records=len(canonical['source_records']))
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', default='artifacts', help='Root containing the saved step-2/3/4 fixtures')
    parser.add_argument('--output', default='artifacts/v21_current_understanding/report.json')
    args = parser.parse_args()
    root = Path(args.artifacts)
    prior_update = parse((root/'v21_memory_step3_preflight.json').read_text())
    prior_reviews = parse((root/'v21_memory_step4_preflight/check.json').read_text())
    evidence = load_modification_evidence(root/'v21_evidence_step2/round-04.json',
                                          expected_ref=prior_update['evidence_ref'])
    update = build_memory_update_input(evidence)
    report = {'schema_version': 'v21_input_optimization_v1',
              'baseline': 'Same source evidence as saved step-3/4 preflights; Memory scope now also covers '
                          'all current label regressions. Not a same-scope compression comparison or actual campaign round.',
              'memory_update': comparison(prior_update['input_budget']['proxy_input_tokens'],
                                         build_memory_update_request(update), update.payload)}
    # Reconstruct only the former selection for comparison; it is never dispatched.
    data = evidence.payload
    previous = open_memory_evidence(evidence,
        proposal_refs=[p['proposal_issue_id'] for p in data['proposals']])
    require(len(previous['pairs']) == prior_update['loaded_pairs']
            and len(previous['events']) == prior_update['loaded_events'], 'baseline selection changed')
    report['memory_update'].update(baseline_input_ref=prior_update['input_ref'], input_ref=update.input_ref,
        scope_changed=set(previous['pairs']) != set(update.payload['pairs']))
    coverage = {'scanned_current_pairs': len(data['current_pair_refs']),
                'previous_loaded_pairs': len(previous['pairs']), 'loaded_pairs': len(update.payload['pairs']),
                'regressions': []}
    for ref in update.payload['regression_pair_refs']:
        pair = data['archive']['pairs'][ref]
        row = {'pair_ref': ref, 'task_ref': pair['task_ref'], 'previously_loaded': ref in previous['pairs'],
               'loaded': ref in update.payload['pairs']}
        for role in ('parent', 'candidate'):
            meta = update.payload['trajectories'][pair[role]]
            row[role] = {k: meta['supervision'][k] for k in ('success', 'compliant')}
            expected = {r for r, e in data['archive']['events'].items() if e['trajectory_ref'] == pair[role]}
            require(expected and expected <= update.payload['events'].keys(), 'incomplete regression originals')
            row[role + '_events'] = len(expected)
        coverage['regressions'].append(row)
    report['regression_coverage'] = coverage
    report['issue_boundaries'] = [{
        'issue_id': i['issue_id'],
        'explicit_source_records': len(update.payload['issue_source_refs'][i['issue_id']]),
        'other_loaded_source_records': len(set(update.payload['source_records']) -
                                          set(update.payload['issue_source_refs'][i['issue_id']]))}
        for i in update.payload['memory_issues']]
    history = load_modification_evidence(root/'v21_memory_step4_preflight/round-03-import.json',
                                         expected_ref=prior_reviews['evidence_ref'])
    source = parse((root/'v20_pilot_001_continuation_grouping24k/round-04/generation/source.json').read_text())
    kwargs = dict(memory_evidence=history, parent_skill=source['parent_skill'],
        current_requests=tuple(CurrentDiagnosisInput(encode(r['payload']), encode(r['provenance']))
                               for r in source['current_requests']),
        current_findings=tuple(CurrentFindings(encode(f)) for f in source['current_findings']))
    fusion = build_issue_fusion_input(**kwargs)
    summarized = sum('current_understanding' in i for i in fusion.payload['memory_issues'])
    report['current_understanding'] = {'summarized_issues': summarized,
        'legacy_full_history_issues': len(fusion.payload['memory_issues']) - summarized,
        'note': 'Legacy real artifacts have no synthesized issue understanding; no summary is fabricated.'}
    report['fusion'] = comparison(prior_reviews['fusion_input_budget']['proxy_input_tokens'],
                                  build_issue_fusion_request(fusion))
    # Exact same controlled selections as the step-4 preflight; no model decisions.
    issues = [{'current_finding_refs': [], 'memory_issue_refs': [i['issue_id']], 'memory_attempt_refs': [],
        'issue_statement': i['problem'], 'decision': 'PROPOSE',
        'reason': 'Offline source-closure fixture only; inspect existing historical evidence.',
        'related_rule_refs': []} for i in fusion.payload['memory_issues']]
    current_ids = [f['finding_id'] for f in fusion.payload['current_findings']]
    if current_ids:
        issues.append({'current_finding_refs': current_ids, 'memory_issue_refs': [], 'memory_attempt_refs': [],
            'issue_statement': 'Current-batch fixture only.', 'decision': 'PROPOSE',
            'reason': 'Offline current-source closure.', 'related_rule_refs': []})
    result = validate_issue_fusion(encode({'schema_version': 'issue_fusion_response_v20.1',
        'issues': issues, 'unassociated_findings': []}), request=fusion)
    generation = build_generation_input(**kwargs, fusion_input=fusion, fusion_result=result)
    requests = generation.build_review_inputs()
    require(len(requests) == len(prior_reviews['reviews']), 'review fixture count changed')
    report['reviews'] = []
    for request, old in zip(requests, prior_reviews['reviews']):
        p = request.payload
        expected_issues = {i['issue_id'] for i in p['memory_issues']}
        require(set(p['issue_source_refs']) == expected_issues and all(
            set(refs) <= p['source_records'].keys() for refs in p['issue_source_refs'].values()),
            'review issue source scope differs from selected issues')
        require((len(p['events']), len(p['pairs']), len(p['known_counterevidence_refs'])) ==
                (old['events'], old['pairs'], old['counterevidence']), 'review fixture scope changed')
        row = comparison(old['input_budget']['proxy_input_tokens'], build_evidence_review_request(request), p)
        row.update(historical_issues=len(p['memory_issues']), counterevidence=old['counterevidence'])
        row['explicit_issue_sources'] = {iid: len(refs) for iid, refs in p['issue_source_refs'].items()}
        row['loaded_attempts'] = sum(len(i['attempts']) for i in p['memory_issues'])
        report['reviews'].append(row)
    report.update(model_calls=0, replay_calls=0, active_head_written=False, evidence_pruned=False,
                  token_method='cl100k_base_PROXY_NOT_GATEWAY_TOKENIZER')
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        require(parse(output.read_text()) == report, 'existing report differs; choose a new output path')
    else:
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(encode({'output': str(output.resolve()),
        'memory_update': report['memory_update']['after_tokens'], 'fusion': report['fusion']['after_tokens'],
        'reviews': [r['after_tokens'] for r in report['reviews']], 'exact_roundtrip': True, 'model_calls': 0}))


if __name__ == '__main__':
    main()
