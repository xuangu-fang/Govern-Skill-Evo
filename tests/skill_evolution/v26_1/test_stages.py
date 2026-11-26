from copy import deepcopy
import json
import pytest
from .support import make, batch, MethodProvider
from src.skill_evolution.v26_1 import stages, diagnosis, facts, output_feedback as feedback
from src.skill_evolution.v26.transport import RequestFailure, http_failure


def setup(tmp):
    method,actor,cfg=make(tmp/'fixture')
    return method,actor,cfg


def options(cfg):
    return dict(call_config=cfg['module_calls']['diagnosis'],max_attempts=6,
                max_input_chars=4000000,max_message_utf8_bytes=6000000,retry_delay_seconds=2)


def test_feedback_budget_hidden_data_and_readonly_recovery(tmp_path,monkeypatch):
    method,actor,cfg=setup(tmp_path); waits=[]; monkeypatch.setattr(stages.time,'sleep',waits.append)
    good=MethodProvider(); seen=[]
    def generate(name,messages,path,config):
        seen.append(deepcopy(messages))
        if len(seen)==1:return {'content':'{"groups":[]}','finish_reason':'stop','reasoning_content':'HIDDEN_SENTINEL'}
        if len(seen)==2:raise RequestFailure('temporary')
        if len(seen)==3:return {'content':'not json','finish_reason':'stop'}
        return good(name,messages,path,config)
    with method.using():
        call=diagnosis.diagnosis_call(facts.build_parent_bundle(batch(method,tmp_path/'parent'),'R1'))
        path,result=stages.run_stage(tmp_path/'stage',call,generate=generate,**options(cfg))
        assert path.name=='004' and [len(m) for m in seen]==[2,4,4,4]
        assert waits==[2,4,6] and seen[1]==seen[2] and seen[3][-2]['content']=='not json'
        assert 'HIDDEN_SENTINEL' not in json.dumps(seen) and 'GOLD_ONLY_SENTINEL' not in json.dumps(seen)
        assert stages.read(tmp_path/'stage/identity.json')['execution_view'] == 'v26_officeqa_formal_evidence_v1'
        for context in (tmp_path/'stage/attempts').glob('*/request_context.json'):
            assert stages.read(context)['execution_view'] == 'v26_officeqa_formal_evidence_v1'
        assert stages.run_stage(tmp_path/'stage',call,resume=True,read_only=True,**options(cfg))[1]==result
        assert len(seen)==4


def test_feedback_view_is_officeqa_and_rejects_docvqa():
    from src.skill_evolution.v29 import output_feedback as legacy
    base = [{'role': 'user', 'content': 'OfficeQA formal runs'}]
    context = {'policy': feedback.POLICY, 'feedback_from': None,
               'execution_view': 'v26_officeqa_formal_evidence_v1'}
    assert feedback.TIMELINE == context['execution_view']
    assert feedback.request_messages(base, context) == base
    with pytest.raises(ValueError, match='execution input view'):
        feedback.request_messages(base, {**context, 'execution_view': legacy.TIMELINE})
    assert legacy.TIMELINE == 'v29_docvqa_facts_v1'
    assert legacy.request_messages(base, {**context, 'execution_view': legacy.TIMELINE}) == base


def test_shared_six_attempts_never_reset(tmp_path):
    method,actor,cfg=setup(tmp_path); calls=[]
    def generate(name,messages,path,config):
        calls.append(path.name)
        return {'content':'{}','finish_reason':'length' if len(calls)%2 else 'stop'}
    with method.using():
        call=diagnosis.diagnosis_call(facts.build_parent_bundle(batch(method,tmp_path/'parent'),'R1'))
        for resume in (False,True):
            with pytest.raises(stages.Stopped,match='exhausted'):
                stages.run_stage(tmp_path/'stage',call,generate=generate,resume=resume,**options(cfg))
        assert calls==['001','002','003','004','005','006']


@pytest.mark.parametrize('slot',[1,6])
def test_saved_response_recovers_without_seventh_request(tmp_path,monkeypatch,slot):
    method,actor,cfg=setup(tmp_path); good=MethodProvider(); calls=[]
    save=stages.save
    def crash(path,value):
        save(path,value)
        if path.name=='response.json' and path.parent.name==f'{slot:03}':raise KeyboardInterrupt('after durable response')
    def generate(name,messages,path,config):
        calls.append(path.name)
        if int(path.name)<slot:raise RequestFailure('temporary')
        return good(name,messages,path,config)
    with method.using():
        call=diagnosis.diagnosis_call(facts.build_parent_bundle(batch(method,tmp_path/'parent'),'R1'))
        monkeypatch.setattr(stages,'save',crash)
        with pytest.raises(KeyboardInterrupt):stages.run_stage(tmp_path/'stage',call,generate=generate,**options(cfg))
        monkeypatch.setattr(stages,'save',save)
        path,_=stages.run_stage(tmp_path/'stage',call,resume=True,generate=None,**options(cfg))
        assert len(calls)==slot and path.name==f'{slot:03}'
        assert stages.read(path/'recovery.json')=={'additional_requests':0}


@pytest.mark.parametrize('limit,value',[('max_input_chars',1),('max_message_utf8_bytes',1)])
def test_capacity_blocks_before_reserving_request(tmp_path,limit,value):
    method,actor,cfg=setup(tmp_path); good=MethodProvider()
    with method.using():
        call=diagnosis.diagnosis_call(facts.build_parent_bundle(batch(method,tmp_path/'parent'),'R1'))
        with pytest.raises(ValueError):
            stages.run_stage(tmp_path/'stage',call,generate=good,**{**options(cfg),limit:value})
        assert not good.calls
        assert not list((tmp_path/'stage').rglob('request_started.json'))


@pytest.mark.parametrize('status,retry',[(401,True),(408,False),(409,False),(429,True),(500,True),(502,True),(503,True),(504,True),(403,False)])
def test_method_http_classification_is_original_officeqa(status,retry):
    assert http_failure(status,'temporary').retryable is retry
    if status in (429,500,502,503,504):assert not http_failure(status,'quota_exceeded').retryable


def test_source_failure_has_no_output_feedback_or_extra_request(tmp_path):
    method,actor,cfg=setup(tmp_path); calls=[]
    with method.using():
        records=batch(method,tmp_path/'parent')
        call=diagnosis.diagnosis_call(facts.build_parent_bundle(records,'R1'))
        def generate(*args):
            calls.append(1)
            (tmp_path/'parent/runs/records.json').write_text('[]')
            return {'content':'{}','finish_reason':'stop'}
        with pytest.raises((ValueError,stages.Stopped)):
            stages.run_stage(tmp_path/'stage',call,generate=generate,**options(cfg))
        assert len(calls)==1
        errors=list((tmp_path/'stage').rglob('error.json'))
        assert not errors or all(stages.read(path)['kind']=='technical' for path in errors)
