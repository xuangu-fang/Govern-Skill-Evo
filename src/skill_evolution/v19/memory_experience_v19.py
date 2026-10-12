"""Lossless source-linked attempt projections; no new persistent model state.

Old Memory remains immutable. Missing legacy problem provenance stays missing.
"""

def project_attempts(memory):
    attempts = {}
    for row in memory['rounds']:
        generation = row.get('generation_reviews', {})
        findings = {f['finding_id']: f for group in generation.get('current_findings', [])
                    for f in group.get('findings', [])}
        issues = {i['issue_id']: i for i in generation.get('issues', [])}
        for edit in row['edits']:
            sources = edit.get('source_gap_refs', [])
            matched = [issues[s['diagnosis_ref']] for s in sources
                       if s.get('diagnosis_ref') in issues]
            finding_refs = sorted({ref for issue in matched for ref in issue['source_finding_refs']})
            attempts[edit['edit_id']] = {
                'edit_id': edit['edit_id'],
                'source_gap_refs': sources,
                'problems': [{'issue_id': issue['issue_id'],
                              'statement': issue['issue_statement'],
                              'source_finding_refs': issue['source_finding_refs']}
                             for issue in matched],
                'source_findings': [{k: findings[ref][k] for k in
                                    ('finding_id', 'statement', 'applicability', 'evidence_refs')}
                                   for ref in finding_refs if ref in findings],
                'attempt': {k: edit[k] for k in ('operation', 'target_blocks', 'after_text')},
                'gate_decision': row['memory_record']['gate_decision'],
                'results': [{k: record[k] for k in ('attribution_id', 'edit_ids', 'effect',
                             'associated_pair_outcome_counts', 'unattributed_context',
                             'interpretation', 'applicability', 'uncertainty', 'alternative_explanations') if k in record}
                            for record in row['attribution']['records'] if edit['edit_id'] in record['edit_ids']],
                'provenance': 'GENERATION_ISSUE_AND_FINDINGS' if matched else 'LEGACY_EDIT_SOURCE_ONLY'}
    return attempts
