"""Exact text edits and saved handoffs; no LLM or environment execution."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23 import diagnosis, preconditioner as pc, editor
from src.skill_evolution.v23.prompts import execution_context
from tests.skill_evolution.v23.test_diagnosis import make_grouping
from tests.skill_evolution.v23.test_preconditioner import proposal, keep, answer

HEADER = '--- a/SKILL.md\n+++ b/SKILL.md\n'
CREATE = '--- /dev/null\n+++ b/SKILL.md\n'
MARK = '\\ No newline at end of file\n'
REAL = Path('artifacts/methods/v23/v23_preconditioner_001/live')


def result(patch):
    return {'patch': patch, 'reason': 'Implement the effective requirements.'}


def setup_case(root, parent=None, stop=False):
    grouping = make_grouping(root, parent)
    diagnosis.run_diagnosis(grouping, root/'diagnosis', generate=lambda *_: answer(proposal()))
    value = {**keep(), 'decision': 'need_evidence'} if stop else keep()
    pc.run_preconditioner(grouping, root/'diagnosis', root/'preconditioner', generate=lambda *_: answer(value))
    return root/'preconditioner', root/'editor'


@pytest.fixture
def setup(tmp_path):
    return setup_case(tmp_path)


@pytest.mark.parametrize('parent,patch,expected', [
    (None, CREATE+'@@ -0,0 +1,2 @@\n+## Skill\n+Inspect visible locations.\n', '## Skill\nInspect visible locations.\n'),
    ('', HEADER+'@@ -0,0 +1 @@\n+New\n', 'New\n'),
    ('A\n', HEADER+'@@ -1 +1,2 @@\n A\n+B\n', 'A\nB\n'),
    ('A\n', HEADER+'@@ -0,0 +1 @@\n+B\n', 'B\nA\n'),
    ('A\n', HEADER+'@@ -1,0 +2 @@\n+B\n', 'A\nB\n'),
    ('A\nB\n', HEADER+'@@ -1,0 +2 @@\n+X\n', 'A\nX\nB\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-A\n+B\n', 'B\n'),
    ('A\nB\nC\n', HEADER+'@@ -2 +1,0 @@\n-B\n', 'A\nC\n'),
    ('A\nB\n', HEADER+'@@ -1 +0,0 @@\n-A\n', 'B\n'),
    ('A\nB\nC\nD\nE\n', HEADER+'@@ -1 +1,2 @@\n-A\n+X\n+Y\n@@ -4,2 +5 @@\n-D\n E\n', 'X\nY\nB\nC\nE\n'),
    ('same\nX\nsame\n', HEADER+'@@ -3 +3 @@\n-same\n+last\n', 'same\nX\nlast\n'),
    ('A\nB', HEADER+'@@ -1 +1 @@\n-A\n+X\n', 'X\nB'),
    ('A', HEADER+'@@ -1 +1 @@\n-A\n'+MARK+'+B\n'+MARK, 'B'),
    ('A', HEADER+'@@ -1 +1 @@\n-A\n'+MARK+'+A\n', 'A\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-A\n+A\n'+MARK, 'A'),
    (None, CREATE+'@@ -0,0 +1 @@\n+A\n'+MARK, 'A'),
    ('A\nB', HEADER+'@@ -1,2 +1,2 @@\n-A\n+X\n B\n'+MARK, 'X\nB'),
    (' A \r\nB\r\n', HEADER+'@@ -1,2 +1,2 @@\n- A \r\n+ X \r\n B\r\n', ' X \r\nB\r\n'),
    ('A\u2028B\nC\n', HEADER+'@@ -2 +2 @@ context\n-C\n+D\n', 'A\u2028B\nD\n'),
    ('a\r', HEADER+'@@ -1 +1 @@\n-a\r\n'+MARK+'+b\r\n'+MARK, 'b\r'),
])
def test_exact_patch_examples(parent, patch, expected):
    assert editor.apply_patch(parent, patch) == expected
    # Independent expected texts above also exercise the persisted actual Diff.
    assert editor.apply_patch(parent, editor.actual_diff(parent, expected)) == expected


@pytest.mark.parametrize('parent,patch', [
    ('A\n', CREATE+'@@ -0,0 +1 @@\n+B\n'),
    (None, HEADER+'@@ -0,0 +1 @@\n+B\n'),
    ('A\n', HEADER.replace('a/SKILL.md','a/OTHER.md')+'@@ -1 +1 @@\n-A\n+B\n'),
    ('A\n', HEADER.replace('b/SKILL.md','b/../SKILL.md')+'@@ -1 +1 @@\n-A\n+B\n'),
    ('A\n', HEADER+'@@ invalid @@\n-A\n+B\n'),
    ('A\n', HEADER+'@@ -0 +1 @@\n-A\n+B\n'),
    ('A\n', HEADER+'@@ -1 +0 @@\n-A\n+B\n'),
    ('A\n', HEADER+'@@ -1,0 +1,0 @@\n'),
    ('A\n', HEADER+'@@ -2 +2 @@\n-A\n+B\n'),
    ('X\nA\n', HEADER+'@@ -1 +1 @@\n-A\n+B\n'),
    ('A\n', HEADER+'@@ -1 +2 @@\n-A\n+B\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-X\n+B\n'),
    ('A \n', HEADER+'@@ -1 +1 @@\n-A\n+B\n'),
    ('A\r\n', HEADER+'@@ -1 +1 @@\n-A\n+B\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n A\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-A\n+A\n'),
    ('A\n', HEADER+'@@ -1 +0,0 @@\n-A\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-A\n+  \n'),
    ('A\n', HEADER+'@@ -1,2 +1 @@\n-A\n+B\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-A\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-A\n+B'),
    ('A', HEADER+'@@ -1 +1 @@\n-A\n+B\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-A\n'+MARK+'+B\n'),
    ('A\nB\n', HEADER+'@@ -1 +1 @@\n-A\n+X\n'+MARK),
    ('A\nB\n', HEADER+'@@ -1 +1 @@\n-A\n+X\n@@ -2 +2 @@\n-WRONG\n+Y\n'),
    ('A\nB\n', HEADER+'@@ -1 +1 @@\n-A\n+X\n@@ -1 +1 @@\n-A\n+Y\n'),
    ('A\nB\n', HEADER+'@@ -2 +2 @@\n-B\n+X\n@@ -1 +1 @@\n-A\n+Y\n'),
    ('A\nB\n', HEADER+'@@ -1 +1,2 @@\n-A\n+X\n+Y\n@@ -2 +2 @@\n-B\n+Z\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-A\n+B\n'+HEADER+'@@ -1 +1 @@\n-B\n+C\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-A\n+B\n\n'),
    ('A\n', HEADER+'@@ -1 +1 @@\n-A\n+B\n'+MARK+MARK),
    (None, CREATE+'@@ -0,0 +1 @@\n+\0\n'),
])
def test_invalid_patch_is_rejected_without_repairs(parent, patch):
    with pytest.raises(ValueError): editor.apply_patch(parent, patch)


@pytest.mark.parametrize('patch,status', [('', 'no_change'), (None, 'needs_revision'),
    (CREATE+'@@ -0,0 +1 @@\n+New guidance.\n', 'candidate')])
def test_three_outcomes_persist_and_reuse(setup, patch, status):
    calls=[]
    def generate(*_): calls.append(1); return answer(result(patch))
    saved=editor.run_editor(*setup, generate=generate, call_config={'model':'offline'})
    assert saved['editor_status']==status
    assert (setup[1]/'candidate.md').exists() == (status=='candidate')
    assert (setup[1]/'actual.diff').exists() == (status=='candidate')
    assert (setup[1]/'patch.diff').exists() == (patch is not None)
    before={p.name:p.read_bytes() for p in setup[1].iterdir()}
    assert editor.run_editor(*setup, generate=generate, call_config={'model':'offline'})==saved
    assert before=={p.name:p.read_bytes() for p in setup[1].iterdir()}
    assert len(calls)==1
    with pytest.raises(ValueError): editor.run_editor(*setup, generate=generate, call_config={'model':'changed'})
    assert len(calls)==1


@pytest.mark.parametrize('bad', [
    {'patch':' ', 'reason':'Reason'}, {'patch':'\n', 'reason':'Reason'},
    {'patch':None, 'reason':''}, {'patch':'', 'reason':'  '}, {'patch':'', 'reason':None},
    {'patch':0, 'reason':'Reason'}, {'patch':False, 'reason':'Reason'}, {'patch':[], 'reason':'Reason'},
    {'patch':'', 'reason':'Reason', 'decision':'no_change'}, {'patch':None}, [],
])
def test_output_contract(bad):
    with pytest.raises(ValueError): editor.validate_editor(bad,None)


@pytest.mark.parametrize('parent', [None,'A\r\nB'])
def test_input_exact_parent_plan_context_and_checks(tmp_path,parent):
    pre,_=setup_case(tmp_path,parent)
    saved=pc.load_preconditioner(pre); before=deepcopy(saved)
    payload=editor.editor_input(saved)
    assert set(payload)=={'parent','plan'} and payload['parent']==parent
    assert payload['plan']==saved['effective_plan']
    messages=editor.messages_for(saved)
    assert json.loads(messages[1]['content'])==payload
    assert messages[0]['content'].count(execution_context(saved['background']))==1
    assert '{{execution_context}}' not in messages[0]['content']
    assert saved==before
    payload['plan']['checks']=[]
    assert saved==before


def test_existing_parent_byte_preservation_and_no_auto_checks(tmp_path):
    pre,out=setup_case(tmp_path,'A\r\nB')
    patch=HEADER+'@@ -1 +1 @@\n-A\r\n+X\r\n'
    saved=editor.run_editor(pre,out,generate=lambda *_:answer(result(patch)))
    assert saved['candidate_text']=='X\r\nB'
    assert (out/'candidate.md').read_bytes()==b'X\r\nB'
    assert editor.load_editor(out)==saved
    assert 'Are inspections productive?' not in saved['candidate_text']


def test_upstream_stop_and_budget_never_call(tmp_path):
    pre,out=setup_case(tmp_path,stop=True)
    with pytest.raises(ValueError): editor.run_editor(pre,out,generate=None)
    assert not out.exists()


def test_budget_config_prompt_and_snapshot_checks(setup,tmp_path,monkeypatch):
    with pytest.raises(ValueError): editor.run_editor(*setup,generate=None,max_input_chars=1)
    assert not setup[1].exists()
    def generate(*_):return answer(result(''))
    generate.call_config={'model':'offline'}
    with pytest.raises(ValueError): editor.run_editor(*setup,generate=generate,call_config={'model':'other'})
    saved=editor.run_editor(*setup,generate=generate)
    changed=pc.load_preconditioner(setup[0]);changed['background']['max_steps']=99
    with pytest.raises(ValueError):editor.load_editor(setup[1],expected_preconditioner=changed)
    template=tmp_path/'prompt.md';template.write_text(editor.PROMPT_PATH.read_text()+'\nChanged task.\n')
    monkeypatch.setattr(editor,'PROMPT_PATH',template)
    with pytest.raises(ValueError):editor.load_editor(setup[1])
    assert saved['candidate_text'] is None


@pytest.mark.parametrize('kind',['json','truncated','patch','contract','network','interrupt'])
def test_failures_preserve_original_without_retry(setup,kind):
    raw=answer(result(CREATE+'@@ -0,0 +1 @@\n+Guidance.\n'))
    if kind=='json':raw['content']='{not JSON'
    if kind=='truncated':raw['finish_reason']='length'
    if kind=='patch':raw=answer(result(CREATE+'@@ -0,0 +2 @@\n+Incomplete\n'))
    if kind=='contract':raw=answer({**result(''), 'decision':'no_change'})
    calls=[]
    def generate(*_):
        calls.append(1)
        if kind=='network':raise ConnectionError('unavailable')
        if kind=='interrupt':raise KeyboardInterrupt()
        return raw
    with pytest.raises((ValueError,ConnectionError,KeyboardInterrupt)):
        editor.run_editor(*setup,generate=generate)
    assert not json.loads((setup[1]/'validation.json').read_text())['valid']
    assert not (setup[1]/'candidate.md').exists() and not (setup[1]/'editor.json').exists()
    if kind not in ('network','interrupt'):
        assert (setup[1]/'raw_output.txt').read_bytes()==raw['content'].encode()
        assert json.loads((setup[1]/'response.json').read_text())==raw
    if kind=='patch':assert (setup[1]/'patch.diff').read_text()==json.loads(raw['content'])['patch']
    with pytest.raises(ValueError):editor.run_editor(*setup,generate=generate)
    assert len(calls)==1


@pytest.mark.parametrize('name',['input.json','background.json','upstream.json','messages.json','prompt.md',
    'raw_output.txt','response.json','parsed.json','editor.json','patch.diff','candidate.md','actual.diff','run.json','validation.json'])
def test_artifact_tampering_refuses_reuse(setup,name):
    editor.run_editor(*setup,generate=lambda *_:answer(result(CREATE+'@@ -0,0 +1 @@\n+Guidance.\n')))
    path=setup[1]/name
    if not name.endswith('.json'):path.write_bytes(path.read_bytes()+b'changed')
    else:
        data=json.loads(path.read_text())
        if name=='input.json':data['parent']='changed'
        elif name=='background.json':data['max_steps']=99
        elif name=='upstream.json':data['effective_plan']['goal']='changed'
        elif name=='messages.json':data[0]['content']+='changed'
        elif name=='response.json':data['content']=json.dumps(result(''))
        elif name=='run.json':data['outcome']='no_change'
        elif name=='validation.json':data['valid']=False
        else:data['reason']+='changed'
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError):editor.load_editor(setup[1])


def test_http_failure_preserved(setup,monkeypatch):
    import requests
    class HTTP:
        status_code=503
        content=b'unavailable'
    calls=[]
    def post(*args,**kwargs):calls.append(1);return HTTP()
    monkeypatch.setattr(requests.Session,'post',post)
    generate=editor.live_generator(base_url='https://example.test',key='private',model='offline')
    with pytest.raises(ValueError):editor.run_editor(*setup,generate=generate)
    assert (setup[1]/'http_response.txt').read_bytes()==b'unavailable'
    assert len(calls)==1


def test_real_archives_handoff_readonly():
    if not REAL.exists():pytest.skip('Local saved Preconditioner unavailable')
    directories=[REAL, Path('artifacts/methods/v23/v23_prompt_alignment_001/grouping'),Path('artifacts/methods/v23/v23_prompt_alignment_001/diagnosis')]
    before={str(p):p.read_bytes() for d in directories for p in d.rglob('*') if p.is_file()}
    saved=pc.load_preconditioner(REAL)
    payload=editor.editor_input(saved)
    assert payload['parent'] is None and len(payload['plan']['updates'])==len(payload['plan']['checks'])==3
    assert saved['preconditioner']['adjustments']==[]
    assert [s['task_id'] for s in saved['sources']]==[f'train:{i:04}' for i in range(12,16)]
    assert len(saved['facts']['runs'])==4 and sum(len(r['steps']) for r in saved['facts']['runs'])==93
    assert json.loads(editor.messages_for(saved)[1]['content'])==payload
    assert before=={str(p):p.read_bytes() for d in directories for p in d.rglob('*') if p.is_file()}


def test_eof_marker_without_final_framing_newline():
    patch=CREATE+'@@ -0,0 +1 @@\n+No final newline\n'+MARK.rstrip('\n')
    assert editor.apply_patch(None,patch)=='No final newline'


@pytest.mark.parametrize('patch',['',None])
def test_semantic_stop_cannot_have_fabricated_candidate(setup,patch):
    editor.run_editor(*setup,generate=lambda *_:answer(result(patch)))
    (setup[1]/'candidate.md').write_text('Fabricated')
    with pytest.raises(ValueError):editor.load_editor(setup[1])


def test_duplicate_json_keys_preserved_as_failure(setup):
    raw='{"patch":null,"patch":"","reason":"Cannot silently choose a branch."}'
    with pytest.raises(ValueError):editor.run_editor(*setup,generate=lambda *_:{'content':raw,'finish_reason':'stop'})
    assert (setup[1]/'raw_output.txt').read_text()==raw
    assert not (setup[1]/'editor.json').exists()


def test_partial_hunk_failure_publishes_no_candidate(tmp_path):
    pre,out=setup_case(tmp_path,'A\nB\n')
    patch=HEADER+'@@ -1 +1 @@\n-A\n+X\n@@ -2 +2 @@\n-Wrong\n+Y\n'
    with pytest.raises(ValueError):editor.run_editor(pre,out,generate=lambda *_:answer(result(patch)))
    assert (out/'patch.diff').read_text()==patch
    assert not (out/'candidate.md').exists()


def test_no_semantic_validation_or_automatic_revision():
    patch=CREATE+'@@ -0,0 +1 @@\n+Remember the complete execution history forever.\n'
    status,candidate=editor.validate_editor(result(patch),None)
    assert status=='candidate' and candidate=='Remember the complete execution history forever.\n'
    assert editor.validate_editor({'patch':'','reason':'The explanation says unable.'},None)==('no_change',None)


def test_changed_upstream_prevents_reuse(setup,monkeypatch):
    editor.run_editor(*setup,generate=lambda *_:answer(result('')))
    saved=pc.load_preconditioner(setup[0]);saved['sources'][0]['run_id']='another execution'
    monkeypatch.setattr(editor,'load_preconditioner',lambda *_:saved)
    with pytest.raises(ValueError):editor.run_editor(*setup,generate=None)
