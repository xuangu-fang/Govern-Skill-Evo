"""Bounded task concurrency, ordered evidence and failure draining; no real Actor."""
from pathlib import Path
from threading import Barrier, Event, Lock
import time

import pytest
from src.skill_evolution.v23 import evolution as ev
from tests.skill_evolution.v23.test_evolution import config, Harness


def setup(tmp_path, count, workers):
    cfg=config(1);cfg['batches']=[[f'train:{i:04}' for i in range(count)]]
    cfg['actor_max_workers']=workers
    ev.initialize(tmp_path,cfg)
    rd=tmp_path/'rounds/R01';rd.mkdir(parents=True)
    return cfg,rd


@pytest.mark.parametrize('count,workers,peak_expected',[(10,8,8),(10,1,1),(7,8,7)])
def test_bound_order_and_independent_task_files(tmp_path,count,workers,peak_expected):
    cfg,rd=setup(tmp_path,count,workers);h=Harness();lock=Lock()
    first=Barrier(peak_expected);active=0;peak=0;finished=[];directories=[]
    def runner(task,skill,dest,c):
        nonlocal active,peak
        n=int(task.split(':')[1])
        with lock:
            active+=1;peak=max(peak,active);directories.append(dest)
        try:
            if n<peak_expected:first.wait(timeout=5)
            time.sleep((peak_expected-(n%peak_expected))*.01)
            p=h.actor(task,skill,dest,c)
            with lock:finished.append(task)
            return p
        finally:
            with lock:active-=1
    paths,records=ev._actors(tmp_path,rd,'parent_runs',cfg['batches'][0],None,cfg,runner,False)
    assert peak==peak_expected and len(set(directories))==count
    assert [r['task']['id'] for r in records]==cfg['batches'][0]
    assert [ev.read(p)['task']['id'] for p in paths]==cfg['batches'][0]
    if workers>1:assert finished!=cfg['batches'][0]
    assert all((rd/'parent_runs'/t.replace(':','_')/'result.json').is_file() for t in cfg['batches'][0])
    assert len({str(p.parent) for p in directories})==count


def test_failure_stops_submission_drains_results_and_resume_reuses(tmp_path):
    cfg,rd=setup(tmp_path,10,8);h=Harness();barrier=Barrier(8);calls=[];lock=Lock()
    def runner(task,skill,dest,c):
        with lock:calls.append(task)
        barrier.wait(timeout=5)
        if task=='train:0000':
            # Adapter already exhausted its step budget; orchestrator does not retry HTTP.
            ev.save(dest/'request_failures.json',{'attempts':3})
            raise RuntimeError('Actor step attempts exhausted')
        time.sleep(.05)
        return h.actor(task,skill,dest,c)
    before=(tmp_path/'state.json').read_bytes()
    with pytest.raises(RuntimeError,match='exhausted'):
        ev.run_round(tmp_path,actor_runner=runner,generate=lambda *a:pytest.fail('Downstream called'))
    assert len(calls)==8 and set(calls)==set(cfg['batches'][0][:8])
    assert (tmp_path/'state.json').read_bytes()==before
    assert ev.read(tmp_path/'stop.json')['stage']=='parent_runs'
    saved={t:(rd/'parent_runs'/t.replace(':','_')/'result.json').read_bytes() for t in cfg['batches'][0][1:8]}
    resumed=[]
    def recovery(task,skill,dest,c):
        resumed.append(task);return h.actor(task,skill,dest,c)
    paths,records=ev._actors(tmp_path,rd,'parent_runs',cfg['batches'][0],None,cfg,recovery,True)
    assert set(resumed)=={'train:0000','train:0008','train:0009'}
    assert (rd/'parent_runs/train_0000/attempts/001/request_failures.json').is_file()
    assert (rd/'parent_runs/train_0000/attempts/002/trajectory.json').is_file()
    assert saved=={t:(rd/'parent_runs'/t.replace(':','_')/'result.json').read_bytes() for t in saved}
    assert [r['task']['id'] for r in records]==cfg['batches'][0]


@pytest.mark.parametrize('side',['parent_runs','candidate_runs'])
def test_successes_saved_while_another_task_is_running(tmp_path,side):
    from concurrent.futures import ThreadPoolExecutor
    cfg,rd=setup(tmp_path,2,2);h=Harness();release=Event();waiting=Event()
    def runner(task,skill,dest,c):
        if task=='train:0001':
            waiting.set();assert release.wait(timeout=5)
        return h.actor(task,skill,dest,c)
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(ev._actors,tmp_path,rd,side,cfg['batches'][0],None,cfg,runner,False)
        assert waiting.wait(timeout=5)
        marker=rd/side/'train_0000/result.json'
        try:
            deadline=time.monotonic()+5
            while not marker.exists() and time.monotonic()<deadline:time.sleep(.01)
            assert marker.exists() and not future.done()
        finally:release.set()
        future.result()


@pytest.mark.parametrize('value',[0,-1,True,1.5,'8'])
def test_invalid_worker_count_rejected(value):
    cfg=config();cfg['actor_max_workers']=value
    with pytest.raises(ValueError,match='actor_max_workers'):ev.validate_config(cfg)
