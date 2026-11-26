import json
import pytest
from .support import make,batch,response
from src.skill_evolution.v26_1 import facts,diagnosis,reporting
from src.adapters.officeqa import retry, runtime as runtime_module
from src.adapters.officeqa.retry import GenerationExhausted
from skilladam.benchmarks.officeqa.rollout import extract_answer


def test_original_messages_and_exact_crlf_skill(tmp_path):
    method,actor,_=make(tmp_path/'fixture')
    skill='α\r\nβ\nno final newline'
    with method.using():
        records=batch(method,tmp_path/'parent',skill=skill,tasks=['UID0007'])
        assert records[0]['execution']['skill']==skill
        initial,_=method.runtime.prepare(method.dataset.case('UID0007'),skill)
        assert actor.requests[0]['messages']==list(initial)
        assert len(actor.requests[0]['tools'])==3
        assert actor.requests[0]['max_tokens']==65536
        assert diagnosis.diagnosis_input(facts.build_parent_bundle(records,'R1'))['parent']==skill


@pytest.mark.parametrize('slot',[1,6])
def test_actor_saved_response_recovery_through_new_binding(tmp_path,monkeypatch,slot):
    method,actor,_=make(tmp_path/'fixture')
    actor.scripts['UID0007']=[response('')]*(slot-1)+[response('1000')]
    real=retry.parse_turn
    def crash(value,**kwargs):
        if value['choices'][0]['message']['content']=='1000':raise KeyboardInterrupt('saved response')
        return real(value,**kwargs)
    with method.using():
        monkeypatch.setattr(retry,'parse_turn',crash)
        with pytest.raises(KeyboardInterrupt):batch(method,tmp_path/'parent',tasks=['UID0007'])
        monkeypatch.setattr(retry,'parse_turn',real)
        records=batch(method,tmp_path/'parent',tasks=['UID0007'])
        assert len(actor.requests)==slot and records[0]['execution']['raw_result']['api_requests']==slot
        assert reporting.costs(tmp_path/'parent')['actor_reserved_http_attempts']==slot


def test_exhaustion_incomplete_not_zero_score(tmp_path):
    method,actor,_=make(tmp_path/'fixture')
    actor.scripts['UID0007']=[response('')]*6
    with method.using():
        for _ in range(2):
            with pytest.raises(GenerationExhausted):batch(method,tmp_path/'parent',tasks=['UID0007'])
    assert len(actor.requests)==6 and not (tmp_path/'parent/runs/records.json').exists()
    assert reporting.costs(tmp_path/'parent')['actor_tasks_completed']==0


@pytest.mark.parametrize('text,expected', [('<ANSWER>first</ANSWER><answer>second</answer>','first'),
    ('thinking\nlast line\n','last line'),('<answer>\n-1.25%\n</answer>','-1.25%')])
def test_native_answer_parse(text,expected):
    assert extract_answer({'response':text})[0]==expected


def test_original_scoring_not_numeric_tolerance_and_f1_only(tmp_path):
    from dataclasses import replace
    method,_,_=make(tmp_path/'fixture');scorer=method.runtime.scorer
    case=replace(method.dataset.case('UID0007'),reference=['12 34'])
    assert dict(scorer.evaluate(scorer.parse_result(case,{'response':'34 12'})).metrics)=={'em':0.0,'f1':1.0}
    for prediction,ref,expected in [('1,000 million dollars','1000',1),('1.0','1',0),('-1','1',0),('1%','1',0)]:
        scored=scorer.evaluate(scorer.parse_result(replace(case,reference=[ref]),{'response':prediction}))
        assert scored.metrics['em']==expected
