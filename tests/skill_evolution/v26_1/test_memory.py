from copy import deepcopy
import pytest
from .support import make
from .test_contracts import prepare_replay
from src.skill_evolution.v26_1 import replay, gate, memory


def prepare(method,actor,tmp):
    bundle,_=prepare_replay(method,actor,tmp,parent_answers=['0']*4,candidate_answers=['1000']*4)
    receipt=replay.replay_call(bundle).complete({'entries':[{'knowledge':[
        {'task_id':p['task_id'],'update_id':None,'text':'Unattributed transition'} for p in replay.replay_input(bundle)['pairs']]}]})
    result=gate.evaluate_gate(receipt)
    return receipt,result,memory.prepare_append(memory.load_memory(tmp/'memory'),replayed=receipt,gate_result=result)


def test_stale_head_duplicate_id_and_light_history(tmp_path):
    method,actor,_=make(tmp_path/'fixture')
    with method.using():
        receipt,result,prepared=prepare(method,actor,tmp_path)
        root=tmp_path/'memory'
        first=memory.commit_memory(root,prepared,expected_head=None)
        stale=deepcopy(receipt);stale['audit']['editor']['round_id']='R2'
        p2=memory.prepare_append(prepared['previous'],replayed=stale,gate_result=result)
        with pytest.raises(ValueError,match='Stale'):memory.commit_memory(root,p2,expected_head=None)
        stale['audit']['editor']['memory']=first['memory']
        p2=memory.prepare_append(first,replayed=stale,gate_result=result)
        second=memory.commit_memory(root,p2,expected_head=first['head'])
        assert memory.commit_memory(root,prepared,expected_head=None)==first
        assert memory.load_memory(root)==second
        assert [e['id'] for r in second['memory']['rounds'] for e in r['entries']]==[f'M{i}' for i in range(1,9)]
        # Historical raw sources are an audit facility, not required for ordinary reads.
        for path in (root/'sources').glob('*.json'):path.unlink()
        assert memory.load_memory(root)==second
        (root/'commits'/f"{second['head']}.json").write_text('{}')
        with pytest.raises(ValueError):memory.load_memory(root)


@pytest.mark.parametrize('point',['source','commit','head'])
def test_atomic_prepublication_interrupt(tmp_path,monkeypatch,point):
    method,actor,_=make(tmp_path/'fixture')
    with method.using():
        _,_,prepared=prepare(method,actor,tmp_path);root=tmp_path/'memory'
        original=memory._atomic_write
        def crash(path,data):
            original(path,data)
            hit=path.parent.name=={'source':'sources','commit':'commits'}.get(point)
            if point=='head':hit=path.name=='HEAD.json' and b'000001-' in data
            if hit:raise KeyboardInterrupt('publication injection')
        monkeypatch.setattr(memory,'_atomic_write',crash)
        with pytest.raises(KeyboardInterrupt):memory.commit_memory(root,prepared,expected_head=None)
        monkeypatch.setattr(memory,'_atomic_write',original)
        before=memory.load_memory(root)
        assert bool(before['head'])==(point=='head')
        after=memory.commit_memory(root,prepared,expected_head=None)
        assert len(after['memory']['rounds'])==1
        assert memory.load_memory(root)==after
        (root/'HEAD.json').unlink()
        with pytest.raises(ValueError,match='Missing HEAD'):memory.load_memory(root)
