from dataclasses import replace
import json

import pytest

from src.skill_evolution.v18.compiler_contract_v18 import CompilerInput
from src.skill_evolution.v18.compiler_v18 import compile_edit_plan
from src.skill_evolution.v18.editor_apply_v18 import apply_editor_response
from src.skill_evolution.v18.editor_contract_v18 import EditorInput
from src.skill_evolution.v19.edit_tracking_v19 import DecidedEdits, TrackingRejected, build_edit_ledger, digest, encode, reconstruct_candidate, trace_edit_history, validate_edit_ledger, validate_history
from src.skill_evolution.v19.edit_tracking_store_v19 import load_edit_history, load_edit_ledger, save_edit_history, save_edit_ledger
from tests.skill_evolution.v18.test_editor_apply_v18 import case, editing_input, indexed_response, mixed, source, diagnosis


def value_for(case, parent, specs, round_id='r1'):
    value = editing_input(case, parent, specs)
    sources = []
    for s in value.compiler_input.diagnoses:
        request = replace(s.request, provenance_json=encode({**s.request.provenance, 'round_id': round_id}))
        sources.append(source(request, json.loads(json.loads(s.validated.payload)['raw_response'])))
    data = CompilerInput(round_id, parent, digest(parent), tuple(sources))
    return EditorInput(data, compile_edit_plan(data))


def ledger_for(value, texts=(), *, history=(), links=(), run_id='test-run'):
    raw = indexed_response(list(texts)) if texts else None
    candidate = apply_editor_response(raw, editor_input=value)['candidate_skill']
    return build_edit_ledger(run_id=run_id, editor_input=value, raw_response=raw,
                             candidate_skill=candidate, history=history, related_history=links)


def link(ledger, index=0, relation='REVISES'):
    edit = ledger.payload['edits'][index]
    return {'edit_unit_index': 0, 'prior_edit_id': edit['edit_id'], 'relation': relation,
            'basis_refs': edit['source_evidence_refs'][:1]}


def test_mixed_records_match_actual_application_and_preserve_bytes(case):
    value = mixed(case)
    ledger = ledger_for(value, [(1, '替换内容'), (3, '新增内容')])
    data = validate_edit_ledger(ledger)
    assert [e['operation'] for e in data['edits']] == ['DELETE', 'REPLACE', 'DELETE', 'ADD']
    assert [e['edit_unit_index'] for e in data['edits']] == [0, 1, 2, 3]
    assert [e['after_text'] for e in data['edits']] == ['', '替换内容\n', '', '新增内容\n']
    assert data['edits'][0]['target_blocks'][0]['text'] == '- A delete\r\n'
    assert '\r\n' in ledger.source['candidate_skill']
    assert reconstruct_candidate(value.compiler_input.parent_skill, data['edits']) == ledger.source['candidate_skill']
    assert data['candidate_skill_ref']['sha256'] == digest(ledger.source['candidate_skill'])
    assert all(e['source_gap_refs'] and e['source_evidence_refs'] for e in data['edits'])
    assert set(r for e in data['edits'] for r in e['source_evidence_refs']) == {e['evidence_id'] for e in data['evidence']}
    assert all(e['resolved']['reference_type'] in ('TRAJECTORY', 'VISIBLE_POLICY') for e in data['evidence'])
    assert 'gate_decision' not in encode(data) and 'effect' not in data


def test_noncontiguous_replace_and_delete_reconstruct(case):
    parent = '# Title\r\n- A\r\n\r\n- B untouched\r\n\r\n- C\r\n\r\n- D'
    value = value_for(case, parent, [('NEEDS_REVISION', [0, 2]), ('SHOULD_REMOVE', [3])])
    ledger = ledger_for(value, [(0, '- replacement')])
    assert ledger.payload['edits'][0]['target_blocks'][1]['text'] == '- C\r\n'
    assert '- B untouched\r\n' in ledger.source['candidate_skill']
    assert '- D' not in ledger.source['candidate_skill']
    validate_edit_ledger(ledger)


@pytest.mark.parametrize('parent', ['', '# Title', '# Title\r\n\r\n'])
def test_add_empty_or_heading_parent(case, parent):
    value = value_for(case, parent, [('MISSING', [])])
    ledger = ledger_for(value, [(0, '  新文本  ')])
    assert ledger.payload['edits'][0]['after_text'] == '  新文本  \n'
    assert ledger.payload['edits'][0]['target_blocks'] == []
    assert reconstruct_candidate(parent, ledger.payload['edits']) == ledger.source['candidate_skill']


def test_pure_delete_empty_candidate_and_deleted_subject(case):
    ledger = ledger_for(value_for(case, '- A', [('SHOULD_REMOVE', [0])]))
    assert ledger.source['candidate_skill'] == ''
    assert ledger.payload['edits'][0]['after_text'] == ''
    history = (DecidedEdits(ledger, 'ACCEPT'),)
    view = trace_edit_history(history)
    assert view['current_skill'] == '' and view['current_rules'] == []
    assert view['edits'][0]['binding_subject'] == 'DELETED_TARGETS'
    assert view['edits'][0]['binding_status'] == 'ABSENT'
    assert trace_edit_history((DecidedEdits(ledger, 'RETAIN'),))['edits'][0]['binding_status'] == 'EXACT'


def test_edit_id_binds_run_round_plan_and_candidate_text(case):
    value = value_for(case, '', [('MISSING', [])])
    a = ledger_for(value, [(0, 'a')]); same = ledger_for(value, [(0, 'a')])
    changed = ledger_for(value, [(0, 'b')])
    other_run = ledger_for(value, [(0, 'a')], run_id='other')
    other_round = ledger_for(value_for(case, '', [('MISSING', [])], 'r2'), [(0, 'a')])
    assert a == same
    assert len({x.payload['edits'][0]['edit_id'] for x in (a, changed, other_run, other_round)}) == 4
    assert a.payload['plan_ref'] == changed.payload['plan_ref']


def test_refuses_candidate_mismatch_and_incomplete_application(case):
    value = value_for(case, '', [('MISSING', [])])
    with pytest.raises(TrackingRejected, match='Candidate differs'):
        build_edit_ledger(run_id='run', editor_input=value, raw_response=indexed_response([(0, 'a')]), candidate_skill='b')
    with pytest.raises(TrackingRejected, match='completed Candidate'):
        build_edit_ledger(run_id='run', editor_input=value, raw_response=json.dumps({
            'status': 'UNABLE', 'reason': 'No evidence', 'edits': []}), candidate_skill=None)
    request = value.compiler_input.diagnoses[0].request
    data = replace(value.compiler_input, diagnoses=(source(request, diagnosis('NOT_ADDRESSABLE')),))
    with pytest.raises(TrackingRejected, match='completed Candidate'):
        build_edit_ledger(run_id='run', editor_input=EditorInput(data, compile_edit_plan(data)),
                          raw_response=None, candidate_skill=None)


@pytest.mark.parametrize('change', [
    lambda d: d['edits'][0].update(after_text='changed\n'),
    lambda d: d['edits'].pop(),
    lambda d: d['edits'][0].update(edit_unit_index=True),
    lambda d: d['edits'][0].update(operation='DELETE'),
    lambda d: d['edits'][0].update(source_evidence_refs=[]),
    lambda d: d['evidence'][0]['resolved'].update(event={'text': 'fabricated'}),
    lambda d: d.update(monitor_private={'reason': 'hidden'}),
    lambda d: d['edits'][0]['candidate_skill_ref'].update(sha256='a' * 64),
])
def test_rejects_tampered_ledger_even_when_json_is_valid(case, change):
    ledger = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, '- New')])
    data = ledger.payload; change(data)
    with pytest.raises(TrackingRejected):
        validate_edit_ledger(replace(ledger, output_json=encode(data)))


def test_ledger_payload_cannot_mutate_saved_record(case):
    ledger = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, '- New')])
    data = ledger.payload; data['edits'].clear()
    assert len(ledger.payload['edits']) == 1
    validate_edit_ledger(ledger)


def test_accepted_revision_partial_content_and_structural_provenance(case):
    a = ledger_for(value_for(case, '# Skill\n', [('MISSING', [])]), [(0, '- Keep\n\n- Harmful')])
    h = (DecidedEdits(a, 'ACCEPT'),)
    b = ledger_for(value_for(case, a.source['candidate_skill'], [('NEEDS_REVISION', [1])], 'r2'),
                   [(0, '- Narrowed')], history=h, links=[link(a)])
    h += (DecidedEdits(b, 'ACCEPT'),)
    view = trace_edit_history(h)
    old, new = view['edits']
    assert old['binding_status'] == 'PARTIAL'
    assert len(old['current_rule_refs']) == 1
    assert old['structural_changes'][0]['operation'] == 'REPLACE'
    assert old['related_followups'][0]['relation'] == 'REVISES'
    assert new['binding_status'] == 'EXACT'
    assert view['current_rules'][0]['writer_edit_ids'] == [a.payload['edits'][0]['edit_id']]
    assert view['current_rules'][1]['writer_edit_ids'] == [b.payload['edits'][0]['edit_id']]
    assert view['current_rules'][1]['ancestor_edit_ids'] == [a.payload['edits'][0]['edit_id']]
    assert a.payload['edits'][0]['after_text'] == '- Keep\n\n- Harmful\n'


def test_rejected_good_direction_retry_keeps_original_decision(case):
    a = ledger_for(value_for(case, '', [('MISSING', []), ('MISSING', [])]), [(0, '- Good'), (1, '- Bad')])
    h = (DecidedEdits(a, 'RETAIN'),)
    assert all(e['binding_status'] == 'ABSENT' for e in trace_edit_history(h)['edits'])
    b = ledger_for(value_for(case, '', [('MISSING', [])], 'r2'), [(0, '- Good')],
                   history=h, links=[link(a, relation='RETRIES')])
    view = trace_edit_history(h + (DecidedEdits(b, 'ACCEPT'),))
    old, bad, new = view['edits']
    assert old['gate_decision'] == 'RETAIN' and old['binding_status'] == 'EXACT'
    assert bad['binding_status'] == 'ABSENT'
    assert old['related_followups'][0]['relation'] == 'RETRIES'
    assert view['current_rules'][0]['writer_edit_ids'] == [new['edit_id']]
    assert view['current_rules'][0]['ancestor_edit_ids'] == []  # intent is not structural origin


def test_accepted_removal_and_rejected_removal_are_distinct(case):
    a = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, '- Bad')])
    h = (DecidedEdits(a, 'ACCEPT'),)
    b = ledger_for(value_for(case, a.source['candidate_skill'], [('SHOULD_REMOVE', [0])], 'r2'),
                   history=h, links=[link(a, relation='REVERTS')])
    rejected = trace_edit_history(h + (DecidedEdits(b, 'RETAIN'),))
    assert rejected['edits'][0]['binding_status'] == 'EXACT'
    assert rejected['edits'][0]['structural_changes'] == []
    accepted = trace_edit_history(h + (DecidedEdits(b, 'ACCEPT'),))
    assert accepted['edits'][0]['binding_status'] == 'ABSENT'
    assert accepted['edits'][0]['structural_changes'][0]['operation'] == 'DELETE'
    assert accepted['current_rules'] == []


def test_rewritten_single_block_is_unresolved_not_silently_absent(case):
    a = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, 'Keep useful part and bad part.')])
    h = (DecidedEdits(a, 'ACCEPT'),)
    b = ledger_for(value_for(case, a.source['candidate_skill'], [('NEEDS_REVISION', [0])], 'r2'),
                   [(0, 'Keep useful part with a narrower condition.')], history=h)
    old = trace_edit_history(h + (DecidedEdits(b, 'ACCEPT'),))['edits'][0]
    assert old['binding_status'] == 'UNRESOLVED' and old['current_rule_refs'] == []
    assert len(old['descendant_rule_refs']) == 1


def test_duplicate_text_never_guesses_a_location(case):
    a = ledger_for(value_for(case, '- Same\n', [('MISSING', [])]), [(0, '- Same')])
    result = trace_edit_history((DecidedEdits(a, 'ACCEPT'),))
    assert result['edits'][0]['binding_status'] == 'UNRESOLVED'
    assert result['edits'][0]['current_rule_refs'] == []
    assert len(result['edits'][0]['possible_rule_refs']) == 2
    assert result['current_rules'][0]['writer_edit_ids'] == []
    assert result['current_rules'][1]['writer_edit_ids'] == [a.payload['edits'][0]['edit_id']]


def test_deleted_content_reintroduced_is_reported_as_present(case):
    a = ledger_for(value_for(case, '- Old\n', [('SHOULD_REMOVE', [0])]))
    h = (DecidedEdits(a, 'ACCEPT'),)
    b = ledger_for(value_for(case, '', [('MISSING', [])], 'r2'), [(0, '- Old')],
                   history=h, links=[link(a, relation='REVERTS')])
    old = trace_edit_history(h + (DecidedEdits(b, 'ACCEPT'),))['edits'][0]
    assert old['operation'] == 'DELETE' and old['binding_status'] == 'EXACT'


@pytest.mark.parametrize('change', [
    lambda l: l.update(prior_edit_id='unknown'),
    lambda l: l.update(relation='ACCEPT'),
    lambda l: l.update(basis_refs=[]),
    lambda l: l.update(basis_refs=['MONITOR/private']),
    lambda l: l.update(edit_unit_index=True),
    lambda l: l.update(extra='untrusted'),
])
def test_bad_links_rejected(case, change):
    a = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, '- Old')])
    history = (DecidedEdits(a, 'RETAIN'),)
    bad = link(a); change(bad)
    with pytest.raises(TrackingRejected):
        ledger_for(value_for(case, '', [('MISSING', [])], 'r2'), [(0, '- New')], history=history, links=[bad])


def test_wrong_history_run_round_parent_and_decision_rejected(case):
    a = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, '- Old')])
    h = (DecidedEdits(a, 'RETAIN'),)
    with pytest.raises(TrackingRejected, match='another run'):
        ledger_for(value_for(case, '', [('MISSING', [])], 'r2'), [(0, 'new')], history=h, run_id='other')
    with pytest.raises(TrackingRejected, match='already tracked'):
        ledger_for(value_for(case, '', [('MISSING', [])]), [(0, 'new')], history=h)
    with pytest.raises(TrackingRejected, match='Parent does not match'):
        ledger_for(value_for(case, '- wrong', [('MISSING', [])], 'r2'), [(0, 'new')], history=h)
    with pytest.raises(TrackingRejected, match='completed'):
        validate_history((DecidedEdits(a, 'PENDING'),))
    b = ledger_for(value_for(case, '', [('MISSING', [])], 'r2'), [(0, 'new')], history=h)
    with pytest.raises(TrackingRejected, match='history binding'):
        validate_edit_ledger(b, history=(DecidedEdits(a, 'ACCEPT'),))
    with pytest.raises(TrackingRejected):
        validate_history((DecidedEdits(b, 'ACCEPT'), DecidedEdits(a, 'RETAIN')))


def test_conflicting_links_rejected(case):
    a = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, 'old')])
    with pytest.raises(TrackingRejected, match='conflicting'):
        ledger_for(value_for(case, '', [('MISSING', [])], 'r2'), [(0, 'new')],
                   history=(DecidedEdits(a, 'RETAIN'),), links=[link(a), link(a, relation='RETRIES')])


def test_persistence_reload_and_history_binding(case, tmp_path):
    a = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, 'old')])
    save_edit_ledger(a, artifact_dir=tmp_path / 'r1')
    loaded = load_edit_ledger(tmp_path / 'r1')
    assert loaded == a
    h = (DecidedEdits(loaded, 'RETAIN'),)
    b = ledger_for(value_for(case, '', [('MISSING', [])], 'r2'), [(0, 'new')], history=h, links=[link(a)])
    save_edit_ledger(b, artifact_dir=tmp_path / 'r2', history=h)
    assert load_edit_ledger(tmp_path / 'r2', history=h) == b
    with pytest.raises(TrackingRejected, match='history binding'):
        load_edit_ledger(tmp_path / 'r2')
    with pytest.raises(FileExistsError):
        save_edit_ledger(a, artifact_dir=tmp_path / 'r1')


def test_storage_corruption_and_incomplete_publication(case, tmp_path, monkeypatch):
    from pathlib import Path
    a = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, 'old')])
    out = tmp_path / 'valid'
    save_edit_ledger(a, artifact_dir=out)
    output = a.payload; output['edits'][0]['after_text'] = 'forged\n'
    (out / 'ledger.json').write_text(encode(output))
    with pytest.raises(TrackingRejected, match='digest mismatch'):
        load_edit_ledger(out)
    manifest = json.loads((out / 'validation.json').read_text())
    manifest['artifact_sha256']['ledger.json'] = digest(encode(output))
    (out / 'validation.json').write_text(encode(manifest))
    with pytest.raises(TrackingRejected, match='revalidated sources'):
        load_edit_ledger(out)

    original = Path.replace
    def fail(self, target):
        if Path(target).name == 'ledger.json':
            raise OSError('simulated interruption')
        return original(self, target)
    monkeypatch.setattr(Path, 'replace', fail)
    with pytest.raises(OSError):
        save_edit_ledger(a, artifact_dir=tmp_path / 'interrupted')
    with pytest.raises(TrackingRejected, match='incomplete'):
        load_edit_ledger(tmp_path / 'interrupted')


def test_history_snapshot_roundtrip_preserves_rejected_attempts_and_gate(case, tmp_path):
    a = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, '- Old')])
    h = (DecidedEdits(a, 'RETAIN'),)
    b = ledger_for(value_for(case, '', [('MISSING', [])], 'r2'), [(0, '- Retry')],
                   history=h, links=[link(a, relation='RETRIES')])
    h += (DecidedEdits(b, 'ACCEPT'),)
    out = tmp_path / 'history'
    save_edit_history(h, artifact_dir=out)
    assert load_edit_history(out) == h
    assert trace_edit_history(load_edit_history(out)) == trace_edit_history(h)
    assert trace_edit_history(h)['edits'][0]['binding_status'] == 'UNRESOLVED'
    with pytest.raises(FileExistsError):
        save_edit_history(h, artifact_dir=out)
    snapshot = json.loads((out / 'history.json').read_text())
    snapshot['rounds'][0]['gate_decision'] = 'ACCEPT'
    (out / 'history.json').write_text(encode(snapshot))
    manifest = json.loads((out / 'validation.json').read_text())
    manifest['artifact_sha256']['history.json'] = digest(encode(snapshot))
    (out / 'validation.json').write_text(encode(manifest))
    with pytest.raises(TrackingRejected, match='history binding'):
        load_edit_history(out)


def test_future_and_cross_edit_basis_links_rejected(case):
    a = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, '- Old')])
    h = (DecidedEdits(a, 'RETAIN'),)
    value = value_for(case, '', [('MISSING', [])], 'r2')
    future = ledger_for(value, [(0, '- New')], history=h)
    bad = link(future)
    with pytest.raises(TrackingRejected, match='earlier edit'):
        ledger_for(value, [(0, '- New')], history=h, links=[bad])


def test_text_matching_respects_line_boundaries(case):
    # A deleted unterminated block must not bind to a prefix of a longer block.
    a = ledger_for(value_for(case, '- A', [('SHOULD_REMOVE', [0])]))
    h = (DecidedEdits(a, 'ACCEPT'),)
    b = ledger_for(value_for(case, '', [('MISSING', [])], 'r2'), [(0, '- ABC')], history=h)
    assert trace_edit_history(h + (DecidedEdits(b, 'ACCEPT'),))['edits'][0]['binding_status'] == 'ABSENT'


def test_multi_target_delete_partial_reintroduction(case):
    a = ledger_for(value_for(case, '- A\n\n- B\n', [('SHOULD_REMOVE', [0, 1])]))
    h = (DecidedEdits(a, 'ACCEPT'),)
    b = ledger_for(value_for(case, a.source['candidate_skill'], [('MISSING', [])], 'r2'),
                   [(0, '- A')], history=h)
    result = trace_edit_history(h + (DecidedEdits(b, 'ACCEPT'),))
    assert result['edits'][0]['binding_status'] == 'PARTIAL'
    assert len(result['edits'][0]['current_rule_refs']) == 1


def test_rejects_tampered_source_and_ambiguous_json(case):
    a = ledger_for(value_for(case, '', [('MISSING', [])]), [(0, '- Old')])
    data = a.source
    data['editor']['sources'][0]['diagnosis_ref'] = 'DIAGNOSIS/forged'
    with pytest.raises(TrackingRejected):
        validate_edit_ledger(replace(a, input_json=encode(data)))
    with pytest.raises(TrackingRejected, match='JSON'):
        validate_edit_ledger(replace(a, output_json='{"edits": [], "edits": []}'))


def test_history_reload_in_a_fresh_process(case, tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    a = ledger_for(value_for(case, '# 标题\r\n', [('MISSING', [])]), [(0, '- 规则')])
    history = (DecidedEdits(a, 'ACCEPT'),)
    out = tmp_path / 'history'
    save_edit_history(history, artifact_dir=out)
    code = '''
import sys
from src.skill_evolution.v19.edit_tracking_store_v19 import load_edit_history
from src.skill_evolution.v19.edit_tracking_v19 import trace_edit_history
print(trace_edit_history(load_edit_history(sys.argv[1]))['history_sha256'])
'''
    result = subprocess.run([sys.executable, '-c', code, str(out)],
                            cwd=Path(__file__).resolve().parents[3],
                            capture_output=True, text=True, check=True)
    assert result.stdout.strip() == trace_edit_history(history)['history_sha256']
