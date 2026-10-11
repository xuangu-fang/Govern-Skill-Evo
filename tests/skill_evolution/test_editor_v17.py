import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace
import sys

import pytest
from src.skill_evolution.editor_v17 import run_editor, _transport
from src.skill_evolution.editor_contract_v17 import EditorInput
from src.skill_evolution.compiler_v17 import compile_edit_plan
from tests.skill_evolution.test_editor_apply_v17 import case, setup, response, build, source, batch, diagnosis


def completion(raw, finish='stop', refusal=None):
    return {'raw_response':raw,'finish_reason':finish,'refusal':refusal,'usage':{},'response_model':'test','response_id':'id'}


def test_success_and_overwrite(case,tmp_path):
    value=setup(case);calls=[];raw=' \n'+response(['新规则'])+'\n'
    def transport(p):
        calls.append(p)
        assert (tmp_path/'run'/'request.json').exists()
        return completion(raw)
    result=run_editor(value,artifact_dir=tmp_path/'run',transport=transport)
    assert result['status']=='VALID' and len(calls)==1
    assert json.loads((tmp_path/'run'/'response.json').read_text())['raw_response']==raw
    for name,digest in result['artifact_sha256'].items():
        assert hashlib.sha256((tmp_path/'run'/name).read_bytes()).hexdigest()==digest
    assert result['candidate_sha256']==result['artifact_sha256']['candidate_skill.md']
    assert (tmp_path/'run'/'parent_skill.md').read_bytes()==value.compiler_input.parent_skill.encode()
    with pytest.raises(FileExistsError):run_editor(value,artifact_dir=tmp_path/'run',transport=transport)
    assert len(calls)==1


@pytest.mark.parametrize('raw,finish,refusal,status',[
    ('{}','stop',None,'REJECTED'),
    (response(['x']),'length',None,'REJECTED'),
    (response(['x']),'stop','refused','REJECTED'),
    (json.dumps({'status':'UNABLE','reason':'conflict','edits':[]}),'stop',None,'UNABLE')])
def test_single_call_no_candidate(case,tmp_path,raw,finish,refusal,status):
    calls=[]
    def transport(p):calls.append(p);return completion(raw,finish,refusal)
    result=run_editor(setup(case),artifact_dir=tmp_path/'run',transport=transport)
    assert result['status']==status and len(calls)==1
    assert not (tmp_path/'run'/'candidate_skill.md').exists()


def test_transport_and_invalid_input(case,tmp_path):
    def transport(p):raise RuntimeError('SECRET CONNECTION DETAIL')
    result=run_editor(setup(case),artifact_dir=tmp_path/'transport',transport=transport)
    assert result['stage']=='TRANSPORT' and 'SECRET' not in str(result)
    invalid=setup(case);invalid=replace(invalid,plan=replace(invalid.plan,edit_units=()))
    result=run_editor(invalid,artifact_dir=tmp_path/'invalid',transport=lambda p:pytest.fail('called'))
    assert result['status']=='REJECTED' and result['model_calls']==0


def test_noop_skips_call(case,tmp_path):
    a=build(case)[0];data=batch(a,[source(a,diagnosis('NOT_ADDRESSABLE'))])
    result=run_editor(EditorInput(data,compile_edit_plan(data)),artifact_dir=tmp_path/'noop',transport=lambda p:pytest.fail('called'))
    assert result['status']=='NO_UPDATE' and result['model_calls']==0
    assert not (tmp_path/'noop'/'request.json').exists()


def test_sdk_no_retries(monkeypatch):
    seen={}
    class Client:
        def __init__(self,**kwargs):
            seen.update(kwargs);self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def create(self,**kwargs):
            seen['call']=kwargs
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=' {} ',refusal=None),finish_reason='stop')],model='fixed',id='id',usage=None)
    monkeypatch.setitem(sys.modules,'openai',SimpleNamespace(OpenAI=Client))
    monkeypatch.setenv('OPENAI_API_KEY','test');monkeypatch.setenv('OPENAI_BASE_URL','https://example.invalid')
    prepared={'model':'fixed','temperature':0,'reasoning_effort':'high','max_completion_tokens':24000,'system_prompt':'s','user_prompt':'u','response_format':{}}
    assert _transport(prepared)['raw_response']==' {} '
    assert seen['max_retries']==0 and seen['call']['temperature']==0
