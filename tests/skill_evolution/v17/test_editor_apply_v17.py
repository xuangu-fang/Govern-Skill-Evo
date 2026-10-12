import hashlib
import json
from dataclasses import replace
import pytest
from src.skill_evolution.v17.editor_apply_v17 import apply_editor_response
from src.skill_evolution.v17.editor_contract_v17 import EditorInput, EditorRejected
from src.skill_evolution.v17.compiler_v17 import compile_edit_plan
from src.skill_evolution.v17.diagnosis_references_v17 import build_reference_catalogs
from src.skill_evolution.v15.information_boundary_v15 import _seal
from tests.skill_evolution.v17.test_compiler_v17 import case, build, source, batch, valid, diagnosis


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
