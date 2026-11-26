from copy import deepcopy
import json
import pytest
from .support import make, MethodProvider, response, batch
from src.skill_evolution.v26_1 import evolution as ev, memory, facts, diagnosis, config
from scripts.runs.run_v26_1_campaign import run_training
from src.skill_evolution.v26_1.evaluation import run_test


@pytest.mark.parametrize('changed', ['runtime_version', 'sources'])
def test_round_boundary_identity_change_blocks_new_requests(tmp_path, monkeypatch, changed):
    method, actor, _ = make(tmp_path / 'fixture')
    tasks = method.dataset.splits['train']
    method.dataset.batches = [tasks[:2], tasks[2:]]
    cfg = config.campaign_config(method)
    provider = MethodProvider()
    root = tmp_path / 'campaign'
    with method.using():
        ev.run_round(root, config=cfg, generate=provider)
        before = (len(actor.requests), len(provider.calls))
        state = ev.read(root / 'state.json')
        identity = (root / 'implementation.json').read_bytes()
        assert before == (2, 1) and state['next_round'] == 2
        with monkeypatch.context() as patch:
            if changed == 'runtime_version':
                patch.setattr(ev, 'RUNTIME_VERSION', ev.RUNTIME_VERSION + '_changed')
            else:
                sources = {**ev.stages._source_hashes(), ev.__file__: '0' * 64}
                patch.setattr(ev.stages, '_source_hashes', lambda: sources)
            with pytest.raises(ValueError, match='implementation.json'):
                ev.run_campaign(root, generate=provider, resume=True)
        assert (len(actor.requests), len(provider.calls)) == before
        assert ev.read(root / 'state.json') == state
        assert (root / 'implementation.json').read_bytes() == identity
        assert not (root / 'rounds/R02').exists()
        assert ev.run_campaign(root, generate=provider, resume=True)['status'] == 'complete'
        assert (len(actor.requests), len(provider.calls)) == (4, 2)


@pytest.mark.parametrize('mode,outcome,commits,requests', [
    ('no_change','diagnosis_no_change',0,4), ('withdraw','preconditioner_withdrawn',0,4),
    ('empty','editor_no_change',1,4), ('candidate','gate_completed',1,8)])
def test_short_circuits(tmp_path, mode, outcome, commits, requests):
    method, actor, cfg = make(tmp_path / 'fixture'); provider=MethodProvider(mode)
    with method.using():
        result=ev.run_round(tmp_path/'campaign',config=cfg,generate=provider)
        assert result['outcome']==outcome and len(actor.requests)==requests
        assert len(memory.load_memory(tmp_path/'campaign/memory')['memory']['rounds'])==commits
        if mode=='candidate':
            assert [n for n,_ in provider.calls]==['diagnosis','preconditioner','editor']
            assert ev.read(tmp_path/'campaign/rounds/R01/replay/completed.json')['status']=='skipped'
            assert not (tmp_path/'campaign/rounds/R01/replay/attempts').exists()


def test_null_editor_stops_without_resampling(tmp_path):
    method, actor, cfg=make(tmp_path/'fixture'); provider=MethodProvider('null')
    with method.using():
        for resume in (False,True):
            with pytest.raises((ev.Stopped, ValueError),match='null'):
                ev.run_campaign(tmp_path/'campaign',config=cfg,generate=provider,resume=resume)
        assert len(actor.requests)==4 and len(provider.calls)==3
        assert memory.load_memory(tmp_path/'campaign/memory')['head'] is None
        assert ev.read(tmp_path/'campaign/state.json')['next_round']==1


@pytest.mark.parametrize('point',['memory_prepared','before_memory_commit','after_memory_commit','before_publish','after_publish'])
def test_publication_interrupt_resume_zero_requests(tmp_path, point):
    method,actor,cfg=make(tmp_path/'fixture'); provider=MethodProvider('candidate')
    actor.scripts={tid:[response('0'),response('1000')] for tid in method.dataset.splits['train']}
    def hook(name):
        if name==point: raise KeyboardInterrupt('injected')
    with method.using():
        with pytest.raises(KeyboardInterrupt):
            ev.run_campaign(tmp_path/'campaign',config=cfg,generate=provider,hook=hook)
        before=(len(actor.requests),len(provider.calls))
        result=ev.run_campaign(tmp_path/'campaign',generate=None,resume=True)
        assert result['status']=='complete'
        assert (len(actor.requests),len(provider.calls))==before
        state=memory.load_memory(tmp_path/'campaign/memory')
        assert len(state['memory']['rounds'])==1
        assert state['selection']['selected_text']==ev.final_parent(tmp_path/'campaign').read_text()


def test_published_history_is_light_and_current_evidence_is_strict(tmp_path):
    method,actor,cfg=make(tmp_path/'fixture'); provider=MethodProvider('empty')
    with method.using():
        original_summary=run_training(tmp_path/'campaign',cfg,generate=provider)
        old=tmp_path/'campaign/rounds/R01/parent_runs/records.json'
        original=old.read_bytes(); old.write_text('{}')
        # Already published history requires no old raw execution audit.
        assert ev.final_parent(tmp_path/'campaign').is_file()
        assert run_training(tmp_path/'campaign',cfg,generate=None,resume=True)==original_summary
        assert memory.load_memory(tmp_path/'campaign/memory')['head']
        old.write_bytes(original)
        records=batch(method,tmp_path/'current')
        saved=facts.build_parent_bundle(records,'R2')
        target=tmp_path/'current/runs/records.json'
        changed=json.loads(target.read_text()); changed[0]['execution']['answer']='tampered'
        target.write_text(json.dumps(changed))
        with pytest.raises(ValueError): diagnosis.diagnosis_call(saved)


def test_unobserved_source_changes_do_not_block_diagnosis(tmp_path):
    method, actor, cfg = make(tmp_path / 'fixture')
    provider = MethodProvider('no_change')
    def generate(name, messages, directory, config):
        source = method.runtime.parsed_root / 'jsons/treasury_bulletin_2011_03.json'
        source.write_bytes(source.read_bytes() + b'\n')
        return provider(name, messages, directory, config)

    with method.using():
        result = ev.run_campaign(tmp_path / 'campaign', config=cfg, generate=generate)
    assert result['status'] == 'complete'
    assert len(actor.requests) == 4 and len(provider.calls) == 1


def test_complete_synthetic74_and172(tmp_path):
    method,actor,cfg=make(tmp_path/'fixture',full=True); provider=MethodProvider('candidate')
    actor.scripts={tid:[response('0'),response('1000')] for tid in method.dataset.splits['train']}
    with method.using():
        summary=run_training(tmp_path/'campaign',cfg,generate=provider)
        assert summary['rounds_completed']==8 and summary['optimization_count']==74
        assert [len(b) for b in cfg['batches']]==[10]*7+[4]
        assert len(actor.requests)==148 and len(provider.calls)==32
        assert summary['cost']['actor_reserved_http_attempts'] == 148
        assert summary['cost']['method_reserved_http_attempts'] == 32
        assert summary['cost']['tokens']['input_tokens'] == {'known_sum':14800,'unknown_requests':32}
        assert summary['new_combinations'] == 0 and len(summary['rounds']) == 8
        assert {n for n,_ in provider.calls}=={'diagnosis','preconditioner','editor','replay'}
        assert not summary['test_started']
        before=memory.load_memory(tmp_path/'campaign/memory')
        assert len(before['memory']['rounds'])==8
        assert sum(len(r['entries']) for r in before['memory']['rounds'])==74
        report=run_test(tmp_path/'campaign',tmp_path/'evaluation')
        assert report['count']==172 and report['correct']==172 and len(actor.requests)==320
        assert all(r['max_tokens']==32768 for r in actor.requests[148:])
        for request in actor.requests[:148]:
            is_override='Question for UID0007?' in json.dumps(request['messages'])
            assert request['max_tokens']==(65536 if is_override else 32768)
        assert memory.load_memory(tmp_path/'campaign/memory')==before
        assert (tmp_path/'campaign/final_skill.md').read_bytes()==(tmp_path/'evaluation/skill.md').read_bytes()
        assert all('GOLD_ONLY_SENTINEL' not in json.dumps(messages) for _,messages in provider.calls)
        request_count=len(actor.requests)
        assert run_test(tmp_path/'campaign',tmp_path/'evaluation',resume=True)==report
        assert len(actor.requests)==request_count


def test_incomplete_test_null_metrics_and_same_budget_resume(tmp_path):
    method,actor,cfg=make(tmp_path/'fixture'); provider=MethodProvider()
    with method.using():
        run_training(tmp_path/'campaign',cfg,generate=provider)
        # A crash after the provider response but before local persistence consumes
        # the reserved slot; explicit recovery may use the remaining original slots.
        actor.scripts['t']=[KeyboardInterrupt('response unavailable')]
        with pytest.raises(KeyboardInterrupt): run_test(tmp_path/'campaign',tmp_path/'evaluation')
        incomplete=ev.read(tmp_path/'evaluation/incomplete.json')
        assert incomplete['em'] is None and not (tmp_path/'evaluation/summary.json').exists()
        report=run_test(tmp_path/'campaign',tmp_path/'evaluation',resume=True)
        assert report['completed']==2 and report['cost']['http_attempts']==3
        assert not (tmp_path/'evaluation/incomplete.json').exists()


def test_data_and_configuration_drift_rejected(tmp_path):
    method,actor,cfg=make(tmp_path/'fixture')
    with method.using():
        for key,value in [('actor_task_output_limits',{}),('initial_skill','new'),('train_workers',5),('batches',[['UID0007']])]:
            bad=deepcopy(cfg);bad[key]=value
            with pytest.raises(ValueError):config.validate_config(bad,executable=True)
        method.dataset.rows['UID0007']['question'] = 'changed same ID'
        with pytest.raises(ValueError):config.validate_config(cfg,executable=True)
    assert not actor.requests
