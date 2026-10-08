from copy import deepcopy
from dataclasses import replace
import json

import pytest

from tests.skill_evolution.test_memory_generation_v19 import setup, case
from tests.skill_evolution.test_separated_review_v19 import inputs, response
from src.skill_evolution.current_diagnosis_v19 import validate_current_findings
from src.skill_evolution.edit_tracking_v19 import encode, digest
from src.skill_evolution.issue_memory_v20 import merge_update
from src.skill_evolution.issue_fusion_v20 import build_issue_fusion_input, validate_issue_fusion
from src.skill_evolution.evidence_review_v20 import (
    build_evidence_archive, validate_evidence_review, EvidenceReviewResult, EvidenceArchive,
    build_evidence_review_request, merge_evidence_archives,
)
from src.skill_evolution.local_generation_v20 import (
    build_generation_input, review_inputs, compile_verified, verified_editor_request,
    apply_verified_editor, run_local_generation, restore_generation, GenerationInput,
)


def proposal(currents=(), mems=(), attempts=()):
    return {'current_finding_refs': list(currents), 'memory_issue_refs': list(mems),
            'memory_attempt_refs': list(attempts), 'issue_statement': 'Improve the bounded choice.',
            'decision': 'PROPOSE', 'reason': 'Check originals and limitations.', 'related_rule_refs': []}


def prepared(setup, *, historical=False, history_only=False, two=False):
    rs = inputs(setup[2])
    fs = tuple(validate_current_findings(encode(response(r)), request=r) for r in rs)
    parent = rs[0].payload['current_skill']
    mem = {'schema_version': 'issue_memory_v20.1', 'run_id': 'test-run', 'issues': []}
    kwargs = {'run_id': 'test-run'}
    if historical:
        contexts = rs[0].payload['contexts']
        exps = deepcopy(rs[0].payload['experiences'])
        for n, exp in enumerate(exps):
            exp.update(origin='COMMITTED_HISTORICAL_OBSERVATION', source_round_id='old', trajectory_ref=f'OLD/{n}')
            for i, e in enumerate(exp['events']):
                e['evidence_ref'] = f'OLD/{n}/E{i}'
        edits = [{'edit_id': 'EDIT/old', 'operation': 'ADD', 'target_blocks': [], 'after_text': '- Old attempt\n'},
                 {'edit_id': 'EDIT/joint', 'operation': 'ADD', 'target_blocks': [], 'after_text': '- Joint attempt\n'}]
        def record(ref, exp, edits, counter=False):
            return {'ref': ref, 'kind': 'ATTRIBUTION', 'statement': 'Joint observation; limitation remains.',
                    'evidence_refs': [exp['events'][0]['evidence_ref']],
                    'counterevidence_refs': [exp['events'][1]['evidence_ref']] if counter else [],
                    'edit_refs': edits, 'source_refs': []}
        records = [record('ATTR/old', exps[0], ['EDIT/old', 'EDIT/joint']),
                   record('ATTR/failed', exps[1], ['EDIT/joint'], True),
                   record('ATTR/unrelated', exps[2], [])]
        kwargs.update(experiences=exps, contexts=contexts, records=records, edits=edits)
        mem = merge_update(mem, {'schema_version': 'issue_memory_update_v20.1', 'run_id': 'test-run',
            'round_id': 'old', 'issues': [{'new_issue_key': 'problem', 'problem': 'Bounded historical problem.',
            'source_refs': ['ATTR/old'], 'attempts': [
                {'new_attempt_key': 'one', 'approach': 'Old approach', 'assessment': 'A promising local edit from RETAIN.',
                 'edit_refs': ['EDIT/old'], 'source_refs': ['ATTR/old']},
                {'new_attempt_key': 'two', 'approach': 'Failed alternative', 'assessment': 'Did not hold in a different scope.',
                 'edit_refs': ['EDIT/joint'], 'source_refs': ['ATTR/failed']}]}]})
    archive = build_evidence_archive(**kwargs)
    f = fs[0].payload['findings'][0]['finding_id']
    selected = proposal([] if history_only else [f], [mem['issues'][0]['issue_id']] if historical else [],
                        [mem['issues'][0]['attempts'][0]['attempt_id']] if historical else [])
    if history_only:
        # Keep a validated current batch even when it has no findings.
        fs = tuple(validate_current_findings(encode({'schema_version': 'current_findings_response_v19.1',
            'summary': 'No current problem.', 'findings': []}), request=r) for r in rs)
    fusion = build_issue_fusion_input(memory=mem, parent_skill=parent, run_id='test-run', round_id='r2',
                                     current_requests=rs, current_findings=fs)
    proposals = [selected]
    if two:
        other = deepcopy(selected); other['current_finding_refs'] = []
        other['issue_statement'] = 'A second historical direction.'
        proposals.append(other)
    result = validate_issue_fusion(encode({'schema_version': 'issue_fusion_response_v20.1',
        'issues': proposals, 'unassociated_findings': []}), request=fusion)
    return build_generation_input(memory=mem, fusion_input=fusion, fusion_result=result, archive=archive,
        parent_skill=parent, current_requests=rs, current_findings=fs)


def final(request, kind='MISSING', verdict='VERIFIED', target=0):
    p = request.payload
    return {'proposal_id': p['proposal_id'], 'verdict': verdict,
        'evidence_refs': [next(iter(p['events']))], 'counterevidence_refs': p['known_counterevidence_refs'],
        'reason': 'The scope is narrowed to address the previous failure; joint evidence is not causal proof.',
        'gap': {'kind': kind, 'statement': 'Only within observed scope.',
                'related_rule_refs': [] if kind == 'MISSING' else [list(p['rules'])[target]]}
               if verdict == 'VERIFIED' else None}


def compiled(source, kinds=('MISSING',)):
    rs = review_inputs(source)
    return compile_verified(source, tuple(validate_evidence_review(encode(final(r, k)), request=r)
                                         for r, k in zip(rs, kinds)))


def editor_raw(value, status='EDITED'):
    return encode({'status': status, 'reason': 'Apply only the authorized bounded guidance.',
        'edits': [{'edit_unit_index': n, 'text': '- Bounded improvement.'}
                  for n, u in enumerate(value.plan['edit_units']) if u['operation'] != 'DELETE']
                 if status == 'EDITED' else []})


def test_current_only_roundtrip_add_and_no_history_review(setup, tmp_path):
    source = prepared(setup)
    def review(prompt):
        p = json.loads(prompt['user_prompt'])
        assert 'historical_reviews' not in p and 'input_budget' not in prompt
        return {'finish_reason': 'stop', 'raw_response': encode(final(review_inputs(source)[0]))}
    def editor(prompt):
        p = json.loads(prompt['user_prompt'])
        assert p['edit_units'][0]['verified_reviews']
        return {'finish_reason': 'stop', 'raw_response': editor_raw(compiled(source))}
    audit = run_local_generation(source=source, output=tmp_path/'v20-generation', review_transport=review, editor_transport=editor)
    assert audit['result']['candidate_skill'].startswith(source.payload['parent_skill'])
    assert audit['result']['edits'][0]['current_finding_refs']
    assert restore_generation(json.loads(encode(audit)))[1] == audit['result']
    bad = deepcopy(audit); bad['result']['candidate_skill'] += 'tampered'
    with pytest.raises(ValueError, match='Candidate changed'):
        restore_generation(bad)


def test_merged_archives_retain_finding_records_for_later_memory_refs(setup):
    rs = inputs(setup[2])
    request = rs[0].payload
    experience = deepcopy(request['experiences'][0])
    context = deepcopy(request['contexts'][0])
    finding = response(rs[0])['findings'][0]
    finding['finding_id'] = 'CF/' + 'a' * 64
    edit = {'edit_id': 'EDIT_V20/' + 'b' * 64, 'operation': 'ADD',
            'target_blocks': [], 'after_text': '- Historical edit.\n'}
    record = {'ref': finding['finding_id'], 'kind': 'FINDING',
              'statement': finding['statement'], 'evidence_refs': list(finding['evidence_refs']),
              'counterevidence_refs': [], 'edit_refs': [edit['edit_id']], 'source_refs': []}
    first = build_evidence_archive(run_id='test-run', experiences=[experience],
                                   contexts=[context], records=[record], edits=[edit])
    second = build_evidence_archive(run_id='test-run', experiences=[], contexts=[])
    merged = merge_evidence_archives(first, second)
    assert merged.payload['records'][finding['finding_id']] == record
    assert merged.payload['edits'][edit['edit_id']] == edit
    assert merged.payload['events']


@pytest.mark.parametrize('history_only', [False, True])
def test_all_attempts_joint_counterevidence_and_no_unrelated_pair(setup, history_only):
    source = prepared(setup, historical=True, history_only=history_only)
    request, = review_inputs(source); p = request.payload
    assert len(p['memory_issues'][0]['attempts']) == 2
    assert set(p['historical_edits']) == {'EDIT/old', 'EDIT/joint'}
    assert set(p['source_records']) == {'ATTR/old', 'ATTR/failed'}
    assert p['source_records']['ATTR/old']['edit_refs'] == ['EDIT/old', 'EDIT/joint']
    assert p['known_counterevidence_refs'] == ['OLD/1/E1']
    assert not any(ref.startswith('OLD/2/') for ref in p['events'])
    result = validate_evidence_review(encode(final(request)), request=request)
    value = compile_verified(source, (result,))
    applied = apply_verified_editor(editor_raw(value), editor_input=value)
    assert applied['edits'][0]['memory_issue_refs'] == source.payload['fusion_result']['issues'][0]['memory_issue_refs']
    assert 'specific failed conditions' in build_evidence_review_request(request)['system_prompt']


@pytest.mark.parametrize('kind,operation', [('MISSING','ADD'), ('NEEDS_REVISION','REPLACE'), ('SHOULD_REMOVE','DELETE')])
def test_operations_and_untargeted_bytes(setup, kind, operation):
    source = prepared(setup); value = compiled(source, (kind,))
    assert value.plan['edit_units'][0]['operation'] == operation
    raw = None if operation == 'DELETE' else editor_raw(value)
    result = apply_verified_editor(raw, editor_input=value)
    parent = source.payload['parent_skill']
    if operation == 'ADD':
        assert result['candidate_skill'].startswith(parent)
    else:
        rule = next(iter(source.payload['fusion_input']['available_rule_refs'].values()))
        assert result['candidate_skill'] == parent.replace(rule['text'], '' if operation == 'DELETE' else '- Bounded improvement.\n', 1)
    if operation == 'DELETE':
        assert verified_editor_request(value) is None


@pytest.mark.parametrize('mutation', [
    lambda r: r.update(counterevidence_refs=[]),
    lambda r: r.update(evidence_refs=['ATTR/old']),
    lambda r: r['gap'].update(related_rule_refs=['RULE/stale'], kind='NEEDS_REVISION'),
    lambda r: r.update(verdict='NO_EDIT'),
    lambda r: r.update(proposal_id='PISSUE_V20/stale'),
    lambda r: r.update(evidence_refs=[]),
    lambda r: r.update(reason=''),
])
def test_invalid_review_cannot_authorize_edit(setup, mutation):
    request, = review_inputs(prepared(setup, historical=True))
    raw = final(request); mutation(raw)
    with pytest.raises(ValueError):
        validate_evidence_review(encode(raw), request=request)


def test_complete_coverage_conflicts_and_merge(setup):
    source = prepared(setup, historical=True, two=True)
    rs = review_inputs(source)
    one = validate_evidence_review(encode(final(rs[0])), request=rs[0])
    with pytest.raises(ValueError, match='partial compile'):
        compile_verified(source, (one,))
    with pytest.raises(ValueError, match='CONFLICT'):
        compiled(source, ('NEEDS_REVISION', 'SHOULD_REMOVE'))
    value = compiled(source, ('NEEDS_REVISION', 'NEEDS_REVISION'))
    assert len(value.plan['edit_units']) == 1
    assert len(value.plan['edit_units'][0]['proposal_refs']) == 2
    assert len(compiled(source, ('MISSING', 'MISSING')).plan['edit_units']) == 2


def test_no_edit_unable_and_plan_tampering(setup):
    source = prepared(setup); request, = review_inputs(source)
    result = validate_evidence_review(encode(final(request, verdict='NO_EDIT')), request=request)
    value = compile_verified(source, (result,))
    assert apply_verified_editor(None, editor_input=value)['status'] == 'NO_UPDATE'
    assert verified_editor_request(value) is None
    value = compiled(source)
    assert apply_verified_editor(editor_raw(value, 'UNABLE'), editor_input=value)['candidate_skill'] is None
    broken = replace(value, plan_json=encode({**value.plan, 'edit_units': []}))
    with pytest.raises(ValueError, match='plan changed'):
        apply_verified_editor(None, editor_input=broken)


@pytest.mark.parametrize('mutation,match', [
    (lambda p: p['memory']['issues'][0]['attempts'][0].update(source_refs=['MISSING/source']), 'unresolved Memory source'),
    (lambda p: p['archive']['records'].pop('ATTR/failed'), 'unresolved Memory source'),
    (lambda p: p.update(parent_skill='- Stale Parent\n'), 'Parent mismatch'),
    (lambda p: p['archive'].update(run_id='another-run'), 'archive run mismatch'),
])
def test_source_binding_and_missing_originals_fail_closed(setup, mutation, match):
    source = prepared(setup, historical=True)
    p = source.payload; mutation(p)
    if 'Memory source' in match and p['memory'] != source.payload['memory']:
        match = 'Fusion source binding mismatch'
    with pytest.raises(ValueError, match=match):
        review_inputs(GenerationInput(encode(p)))


def test_failed_completion_never_dispatches_editor(setup, tmp_path):
    source = prepared(setup)
    def fail(_):
        return {'finish_reason': 'length', 'raw_response': '{}'}
    def editor(_):
        raise AssertionError('Editor called after incomplete review')
    path = tmp_path/'failed-v20'
    with pytest.raises(ValueError, match='incomplete completion'):
        run_local_generation(source=source, output=path, review_transport=fail, editor_transport=editor)
    assert json.loads((path/'status.json').read_text())['status'] == 'INCOMPLETE'
    assert not (path/'generation-audit.json').exists()
