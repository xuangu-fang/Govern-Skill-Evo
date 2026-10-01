from copy import deepcopy
import pytest
from src.skill_evolution.memory_consumption_v19 import state_view,select_originals,tokens


def experience(n,text='observed behavior'):
    return {'trajectory_ref':str(n),'events':[
        {'evidence_ref':f'PAIR/{n}/PARENT/E1','event_type':'message','step':1,'content':text},
        {'evidence_ref':f'PAIR/{n}/CANDIDATE/E1','event_type':'message','step':1,'content':text}]}


def test_repeated_history_is_not_repeated_state():
    observation={'behavior':'same claim','uncertainty':'not causal proof'}
    one,_=state_view({'observations':[observation]})
    many,receipt=state_view({'observations':[observation]*10000})
    assert one==many
    assert receipt['summary_tokens']<=receipt['summary_limit']


def test_distinct_claim_growth_fails_closed_without_truncation():
    source={'observations':[{'claim':str(i)} for i in range(100)]}
    before=deepcopy(source)
    with pytest.raises(ValueError,match='summary exceeds'):
        state_view(source,limit=20)
    assert source==before


def test_raw_growth_is_bounded_and_counterevidence_prioritized():
    for count in (2,20,200):
        archive=[experience(i) for i in range(count)]
        refs={e['evidence_ref'] for x in archive for e in x['events']}
        counter={f'PAIR/{count-1}/PARENT/E1'}
        selected,receipt=select_originals(archive,refs,counter,limit=150)
        assert counter<=selected
        assert receipt['raw_tokens']<=150
        assert receipt['omitted_count']+len(selected)==len(refs)
        for i in range(count):
            pair={f'PAIR/{i}/PARENT/E1',f'PAIR/{i}/CANDIDATE/E1'}
            assert not pair&selected or pair<=selected


def test_oversized_counter_is_explicit_and_not_sliced():
    archive=[experience(1,'long evidence '*1000)]
    ref='PAIR/1/PARENT/E1';before=deepcopy(archive)
    selected,receipt=select_originals(archive,{ref},{ref},limit=100)
    assert not selected and receipt['omitted_counterevidence_count']==1
    assert archive==before


def test_summary_observation_threshold_does_not_reject(monkeypatch):
    import src.skill_evolution.memory_consumption_v19 as module
    source={'claim':'preserve evidence and uncertainty'}
    for size in (9999,10000,10001,10353,40000):
        monkeypatch.setattr(module,'tokens',lambda value,n=size:n)
        result,receipt=module.state_view(source)
        assert result==source and receipt['summary_tokens']==size
        assert receipt['summary_limit']==64000
    monkeypatch.setattr(module,'tokens',lambda value:64001)
    with pytest.raises(ValueError,match='summary exceeds'):
        module.state_view(source)
