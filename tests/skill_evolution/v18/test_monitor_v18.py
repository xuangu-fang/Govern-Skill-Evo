from dataclasses import asdict, replace
import json
import pytest
from src.skill_evolution.v18.monitor_v18 import MonitorInput, MonitorTask, MonitorRejected, expected_calls, summarize_monitor, run_monitor


def config(n=1):
    return MonitorInput('round-1', tuple(MonitorTask(str(i),200) for i in range(n)), 'parent','candidate','a'*64)


def rows(value, pairs):
    result=[]
    for call in expected_calls(value):
        q=pairs[int(call.task_id)][call.role=='CANDIDATE']
        row=asdict(call);row.pop('skill')
        row.update(status='COMPLETE',success=q[1]=='S',compliant=q[0]=='C',initial_state_digest='b'*64,error=None)
        result.append(row)
    return result


@pytest.mark.parametrize('a,b,accept',[(a,b,(a,b) in {('VF','CF'),('VF','VS'),('VF','CS'),('CF','CS'),('VS','CS')}) for a in ['CS','CF','VS','VF'] for b in ['CS','CF','VS','VF']])
def test_all_transitions(a,b,accept):
    c=config(); s=summarize_monitor(c,rows(c,[(a,b)]))
    assert (s['decision']=='ACCEPT')==accept
    assert s['transition_counts'][a][b]==1


def test_joint_distribution_protection_and_order():
    c=config(2)
    # Marginals unchanged, but best and worst both grow: reject VF growth.
    data=rows(c,[('CF','CS'),('VS','VF')])
    s=summarize_monitor(c,data)
    assert s['delta_counts']=={'S':0,'C':0,'CS':1,'VF':1} and s['decision']=='RETAIN'
    assert s==summarize_monitor(replace(c,tasks=c.tasks[::-1]),data[::-1])


@pytest.mark.parametrize('mutation',[
    lambda r:r.pop(), lambda r:r.append(r[0].copy()),
    lambda r:r[0].update(seed=201),lambda r:r[0].update(success=1),
    lambda r:r[0].update(skill_digest='bad'),lambda r:r[0].update(rollout_index=True)])
def test_strict_binding(mutation):
    c=config();data=rows(c,[('VF','CS')]);mutation(data)
    with pytest.raises(MonitorRejected):summarize_monitor(c,data)


def test_state_mismatch_incomplete():
    c=config();data=rows(c,[('VF','CS')]);data[0]['initial_state_digest']='c'*64
    assert summarize_monitor(c,data)['decision'] is None


def test_run_fresh_calls_and_audit(tmp_path):
    calls=[]
    def backend(call):
        calls.append(call)
        return {'success':call.role=='CANDIDATE','compliant':True,'initial_state_digest':'b'*64}
    c=config(2);out=run_monitor(c,backend=backend,artifact_dir=tmp_path/'run')
    assert out=={'status':'COMPLETE','decision':'ACCEPT'} and len(calls)==4
    assert all(call.rollout_index==1 and call.seed==200 for call in calls)
    summary=json.loads((tmp_path/'run'/'summary.json').read_text())
    assert summary['transition_counts']['CF']['CS']==2
    with pytest.raises(FileExistsError):run_monitor(c,backend=backend,artifact_dir=tmp_path/'run')


def test_error_is_not_failure_or_retain(tmp_path):
    calls=[]
    def backend(call):
        calls.append(call)
        if call.role=='PARENT':raise RuntimeError('private detail')
        return {'success':True,'compliant':True,'initial_state_digest':'b'*64}
    out=run_monitor(config(),backend=backend,artifact_dir=tmp_path/'run')
    assert out=={'status':'INCOMPLETE','decision':None} and len(calls)==2
    assert 'private detail' not in (tmp_path/'run'/'results.json').read_text()


def test_empty_duplicate_tasks_rejected():
    for c in [replace(config(),tasks=()), replace(config(),tasks=(MonitorTask('a',200),)*2)]:
        with pytest.raises(MonitorRejected):list(expected_calls(c))


def test_parallel_monitor_preserves_serial_statistics_and_order(tmp_path):
    from threading import Barrier
    barrier = Barrier(4)
    def observation(call):
        return {'success': call.role == 'CANDIDATE', 'compliant': True, 'initial_state_digest': 'b'*64}
    def concurrent_backend(call):
        barrier.wait(timeout=5)  # Fails if calls are accidentally serial.
        return observation(call)
    value = config(2)
    run_monitor(value, backend=concurrent_backend, artifact_dir=tmp_path/'parallel', max_workers=4)
    run_monitor(value, backend=observation, artifact_dir=tmp_path/'serial')
    for name in ('results.json', 'summary.json'):
        assert json.loads((tmp_path/'parallel'/name).read_text()) == json.loads((tmp_path/'serial'/name).read_text())


def test_resume_rejects_different_bound_input(tmp_path):
    value=config()
    backend=lambda c: {'success':True,'compliant':True,'initial_state_digest':'b'*64}
    run_monitor(value,backend=backend,artifact_dir=tmp_path/'m')
    with pytest.raises(MonitorRejected,match='Resume Monitor input'):
        run_monitor(replace(value,candidate_skill='different'),backend=backend,artifact_dir=tmp_path/'m',resume=True)
