import hashlib
import json
from dataclasses import replace
import pytest
from src.skill_evolution.v18.editor_apply_v18 import apply_editor_response
from src.skill_evolution.v18.editor_contract_v18 import EditorInput, EditorRejected
from src.skill_evolution.v18.compiler_v18 import compile_edit_plan
from src.skill_evolution.v18.diagnosis_references_v18 import build_reference_catalogs
from src.skill_evolution.v15.information_boundary_v15 import _seal
from tests.skill_evolution.v18.test_compiler_v18 import case, build, source, batch, valid, diagnosis


def setup(case, parent=None, targets=None):
    a=build(case)[0]
    if parent is not None:
        payload=a.learner_payload; payload['current_skill']=parent
        payload.update(build_reference_catalogs(payload))
        provenance=a.provenance;provenance['parent_skill_digest']=hashlib.sha256(parent.encode()).hexdigest()
        a=replace(a,learner_view=_seal('V17_GROUP_DIAGNOSIS_INPUT',payload),provenance_json=json.dumps(provenance))
    output=valid(a)
    if targets is not None:
        rules=list(a.learner_payload['available_rule_refs'])
        output['parent_skill_gaps'][0].update(kind='NEEDS_REVISION',related_rule_refs=[rules[i] for i in targets])
        output['parent_skill_gaps'].append({**valid(a)['parent_skill_gaps'][0], 'gap':'Also add guidance'})
    data=batch(a,[source(a,output)])
    return EditorInput(data,compile_edit_plan(data))


def response(texts):
    return json.dumps({'status':'EDITED','reason':'Done','edits':[{'edit_unit_index':i,'text':t} for i,t in enumerate(texts)]})


@pytest.mark.parametrize('parent',['', '# Title', '# Title\r\n\r\n', '# Title\n'])
def test_append_exact_and_deterministic(case,parent):
    value=setup(case,parent)
    raw=response(['  新规则  '])
    result=apply_editor_response(raw,editor_input=value)
    prefix=parent + (('' if parent.endswith('\n') else '\n')+'\n' if parent else '')
    assert result['candidate_skill']==prefix+'  新规则  \n'
    assert result==apply_editor_response(raw,editor_input=value)
    assert result['raw_response']==raw


def test_noncontiguous_replace_preserves_untargeted_bytes(case):
    parent='# Title\r\n- A\r\n\r\n## Middle\r\n- B untouched  \r\n\r\n- C\r\n\r\n# Tail'
    value=setup(case,parent,[0,2])
    result=apply_editor_response(response(['Replacement','Added']),editor_input=value)
    assert result['candidate_skill']=='# Title\r\nReplacement\n\r\n## Middle\r\n- B untouched  \r\n\r\n\r\n# Tail\n\nAdded\n'
    assert value.compiler_input.parent_skill==parent


@pytest.mark.parametrize('raw',[None,'{}','```json\n{}\n```','{"status":"EDITED","status":"UNABLE"}', '{"x":NaN}',response(['']),response(['a','b']), '{"status":"EDITED","reason":"ok","edits":[{"edit_unit_index":true,"text":"x"}]}'])
def test_invalid_response_has_no_candidate(case,raw):
    with pytest.raises(EditorRejected):apply_editor_response(raw,editor_input=setup(case))


def test_unable_and_noop(case):
    value=setup(case)
    raw=json.dumps({'status':'UNABLE','reason':'Conflict','edits':[]})
    assert apply_editor_response(raw,editor_input=value)['candidate_skill'] is None
    a=build(case)[0]; data=batch(a,[source(a,diagnosis('NOT_ADDRESSABLE'))])
    noop=EditorInput(data,compile_edit_plan(data))
    assert apply_editor_response(None,editor_input=noop)['status']=='NO_UPDATE'
    with pytest.raises(EditorRejected):apply_editor_response(raw,editor_input=noop)


def test_stale_parent_rejected(case):
    value=setup(case)
    value=replace(value,compiler_input=replace(value.compiler_input,parent_skill='changed'))
    with pytest.raises(EditorRejected):apply_editor_response(response(['x']),editor_input=value)


def editing_input(case, parent, specs):
    request = setup(case, parent).compiler_input.diagnoses[0].request
    rules = list(request.learner_payload['available_rule_refs'])
    output = valid(request)
    gap = output['parent_skill_gaps'][0]
    output['parent_skill_gaps'] = [
        {**gap, 'kind': kind, 'related_rule_refs': [rules[i] for i in targets]}
        for kind, targets in specs]
    data = batch(request, [source(request, output)])
    return EditorInput(data, compile_edit_plan(data))


def mixed(case):
    parent = '# Title\r\n- A delete\r\n\r\n- B replace\r\n\r\n- C delete\r\n\r\n## 留下\r\n- 原样  '
    return editing_input(case, parent, [
        ('SHOULD_REMOVE', [0]), ('NEEDS_REVISION', [1]),
        ('SHOULD_REMOVE', [2]), ('MISSING', [])])


def indexed_response(edits):
    return json.dumps({'status': 'EDITED', 'reason': 'Done', 'edits': [
        {'edit_unit_index': i, 'text': text} for i, text in edits]})


def test_mixed_delete_replace_add_preserves_original_slices(case):
    value = mixed(case)
    raw = indexed_response([(1, '新替换'), (3, '新追加')])
    result = apply_editor_response(raw, editor_input=value)
    assert result['candidate_skill'] == '# Title\r\n\r\n新替换\n\r\n\r\n## 留下\r\n- 原样  \n\n新追加\n'
    assert result == apply_editor_response(raw, editor_input=value)
    assert result['model_edit_unit_indices'] == [1, 3]
    assert [d['edit_unit_index'] for d in result['deterministic_deletions']] == [0, 2]
    assert result['deterministic_deletions'][0]['target_rules'][0]['text'] == '- A delete\r\n'
    assert result['candidate_sha256'] == hashlib.sha256(result['candidate_skill'].encode()).hexdigest()
    assert '- A delete' in value.compiler_input.parent_skill


@pytest.mark.parametrize('parent,expected', [
    ('- A\n- B', ''), ('# 标题\r\n- A\r\n- B\r\n', '# 标题\r\n'),
    ('# 标题\n\n- A\n\n- B\n\n', '# 标题\n\n\n\n'),
])
def test_pure_delete_including_empty_and_heading_only_candidates(case, parent, expected):
    value = editing_input(case, parent, [('SHOULD_REMOVE', [0, 1])])
    result = apply_editor_response(None, editor_input=value)
    assert result['status'] == 'APPLIED_DETERMINISTIC'
    assert result['candidate_skill'] == expected
    assert result['output'] is None and result['raw_response'] is None
    assert result['model_edit_unit_indices'] == []
    with pytest.raises(EditorRejected, match='pure DELETE'):
        apply_editor_response(response(['']), editor_input=value)


def test_noncontiguous_deletion_does_not_delete_between_targets(case):
    value = editing_input(case, '- A\r\n\r\n## Keep\r\n- B  \r\n\r\n- C', [('SHOULD_REMOVE', [0, 2])])
    assert apply_editor_response(None, editor_input=value)['candidate_skill'] == '\r\n## Keep\r\n- B  \r\n\r\n'


@pytest.mark.parametrize('edits', [
    [(0, 'unauthorized deletion text'), (1, 'B'), (3, 'D')],
    [(0, 'renumbered'), (1, 'renumbered')], [(1, 'B')],
    [(3, 'D'), (1, 'B')], [(1, 'B'), (1, 'B'), (3, 'D')],
    [(1, ''), (3, 'D')], [(1, ' \n'), (3, 'D')],
    [(True, 'B'), (3, 'D')], [(1, '\ud800'), (3, 'D')],
])
def test_mixed_rejects_incomplete_or_unauthorized_text_without_applying_delete(case, edits):
    value = mixed(case)
    before = value.compiler_input.parent_skill
    with pytest.raises(EditorRejected):
        apply_editor_response(indexed_response(edits), editor_input=value)
    assert value.compiler_input.parent_skill == before


def test_mixed_unable_produces_no_partial_candidate(case):
    value = mixed(case)
    result = apply_editor_response(json.dumps({'status': 'UNABLE', 'reason': 'Conflicting basis', 'edits': []}), editor_input=value)
    assert result['status'] == 'UNABLE' and result['candidate_skill'] is None
    assert 'deterministic_deletions' not in result
