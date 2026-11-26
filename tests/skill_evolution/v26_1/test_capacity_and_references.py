import json
import pytest
from src.skill_evolution.v27.capacity import account
from src.skill_evolution.v26_1 import protocol, diagnosis, facts, preconditioner, execution_input_view as codec
from src.skill_evolution.v29_2.execution_references import references
from .support import make,batch,response,diagnosed


def test_actual_large_utf8_boundaries_are_exact_and_lossless():
    messages=[{'role':'user','content':'界'*1500000}]
    encoded=json.dumps(messages,ensure_ascii=False,allow_nan=False)
    chars,size=len(encoded),len(encoded.encode('utf-8'))
    result=account(messages,protocol.PLAN['module_calls']['diagnosis'],max_input_chars=4000000,max_message_utf8_bytes=6000000)
    assert result['input_chars']==chars and result['input_utf8_bytes']==size and size>4500000
    for char_limit,byte_limit in ((chars-1,size),(chars,size-1)):
        with pytest.raises(ValueError):account(messages,protocol.PLAN['module_calls']['diagnosis'],max_input_chars=char_limit,max_message_utf8_bytes=byte_limit)
    assert messages[0]['content']=='界'*1500000


def test_large_memory_and_skill_are_not_truncated(tmp_path):
    method,actor,_=make(tmp_path/'fixture')
    with method.using():
        _,saved=diagnosed(method,tmp_path/'parent')
        knowledge='完整保留\r\n'*100000
        memory={'rounds':[{'round_id':'old','source_updates':[{'id':'old_u','text':'Old','gate_decision':'Defer'}],
                          'entries':[{'id':'M1','knowledge':{'task_id':'old_t','update_id':None,'text':knowledge}}]}]}
        encoded=preconditioner.model_input(saved,memory)
        restored=codec.restore_model_input(encoded,module='preconditioner')
        assert restored['memory']==memory
        assert len(restored['memory']['rounds'][0]['entries'][0]['knowledge']['text'])==len(knowledge)
        from src.skill_evolution.v26_1 import editor
        parent='始\r\n'+'x'*300000+'\n末'
        result=editor.construct_candidate({'edits':[{'update_id':'u1','patch':'','reason':'Already satisfied'}]},
                                          {'parent':parent,'plan':{'goal':'Keep','updates':[{'id':'u1','text':'Preserve'}]}})
        assert result['candidate_text'] is None and result['editor_status']=='no_change'
        selected=editor.construct_selected({'edits':[{'update_id':'u1','patch':'','reason':'Already satisfied'}]},
            {'parent':parent,'plan':{'goal':'Keep','updates':[{'id':'u1','text':'Preserve'}]}},[])
        assert selected['selected_text']==parent


def test_tool_ids_and_ranges_have_exact_authority(tmp_path):
    method,actor,_=make(tmp_path/'fixture')
    actor.scripts['UID0007']=[response(calls=[('glob',{'pattern':'*'})]),response()]
    with method.using():
        call=diagnosis.diagnosis_call(facts.build_parent_bundle(batch(method,tmp_path/'parent',tasks=['UID0007']),'R1'))
        for reason in ('P1:1-2','P1:1_t1/P1:outcome','`Evidence:P1:1_t1`'):
            call.complete({'decision':'no_change','reason':reason,'plan':None})
        for reason in ('P1:1-3','P1:1_t2','P1:1_t1/P99','R1/P1:1_t1','`Check:c1`'):
            with pytest.raises(ValueError):call.complete({'decision':'no_change','reason':reason,'plan':None})
        assert references('P1:1_t1/Q1:2_t3')=={'P1:1_t1','Q1:2_t3'}
