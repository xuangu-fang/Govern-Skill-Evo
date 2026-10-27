from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from src.skill_evolution.v23_4 import evolution as historical
from src.skill_evolution.v23_5 import comparison as runner
from src.skill_evolution.v23_5 import comparison_inputs as inputs
from src.skill_evolution.v23_5.comparison_stats import summarize, usage_totals, semantic_material
from tests.skill_evolution.v23_4.test_evolution import Harness, config
from .helpers import keep


@pytest.fixture(scope='module')
def source(tmp_path_factory):
    root = tmp_path_factory.mktemp('comparison_source')/'S1'
    h = Harness()
    historical.run_campaign(root, config=config(6), generate=h.generate, actor_runner=h.actor)
    return root


@pytest.fixture
def spec(source):
    cfg = inputs.read(source/'config.json')
    return {'question': 'Offline fixture question.', 'hypothesis': 'Offline fixture hypothesis.',
            'rounds': list(inputs.ROUNDS), 'call_config': cfg['call_config'], 'max_attempts': 3,
            'max_input_chars': 4000000, 'max_input_bytes': 6000000, 'repetitions': 1, 'retry_delay_seconds': 0}


@pytest.fixture
def frozen(source, tmp_path, spec):
    root = tmp_path/'comparison'
    inputs.prepare(source, root, spec)
    return root


class Generator:
    def __init__(self, mode=None):
        self.calls = []
        self.mode = mode

    def __call__(self, messages, dest):
        self.calls.append(deepcopy(messages))
        payload = json.loads(messages[1]['content'])
        if messages[0]['content'].startswith('# Preconditioner'):
            value = keep(payload)
        else:
            old = payload['memory']['entries']
            value = {'entries': [{'revises': [old[0]['id']], 'knowledge': deepcopy(old[0]['knowledge']) + [
                {'text': 'Synthetic current comparison with uncertain attribution.', 'evidence': ['diff', 'P1:1', 'Q1:1']}]}]}
        response = {'content': json.dumps(value), 'finish_reason': 'stop', 'response_model': 'offline',
                    'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120}}
        if self.mode == 'no_usage': response['usage'] = None
        if self.mode == 'always_invalid' or self.mode == 'once_invalid' and len(self.calls) == 1:
            response['content'] = '{}'
        if self.mode == 'interrupt_with_response' and len(self.calls) == 1:
            inputs.save(dest/'response.json', response)
            raise KeyboardInterrupt()
        if self.mode == 'interrupt_without_response' and len(self.calls) == 1:
            raise KeyboardInterrupt()
        if self.mode == 'non_retryable':
            raise RuntimeError('offline fixture')
        return response


def one(root, gen, **kwargs):
    return runner.run(root, generate=gen, rounds=['R03'], stages=['preconditioner'], arms=['knowledge_only'], **kwargs)


def test_freeze_exact_rounds_sources_and_views(frozen, source):
    manifest = inputs.verify(frozen)
    assert len(manifest['cells']) == 16
    assert not (frozen/'code').exists()
    assert set(manifest) == {'format','created_at','source_campaign','spec','arms','cells'}
    for label in inputs.ROUNDS:
        original=inputs.selected(source/'rounds'/label,'replay')
        assert inputs.read(original/'messages.json') == inputs.messages(frozen,label,'replay','memory_v3')
    assert manifest['cells'][0]['arm'] == 'memory_v3' and manifest['cells'][4]['arm'] == 'knowledge_only'
    for number in range(3,7):
        label = f'R{number:02}'
        state = inputs.read(frozen/'cases'/label/'memory_before/active.json')
        assert state['commits'] == [f'S1_R{i:02}' for i in range(1,number)]
        assert sorted(p.stem for p in (frozen/'cases'/label/'memory_before/archive').glob('*.json')) == state['commits']
        for stage in inputs.STAGES:
            a = inputs.read(inputs.case_path(frozen,label,stage,'memory_v3')/'model_input.json')
            b = inputs.read(inputs.case_path(frozen,label,stage,'knowledge_only')/'model_input.json')
            assert {k:v for k,v in a.items() if k!='memory'} == {k:v for k,v in b.items() if k!='memory'}
            assert a['memory']['entries'] == b['memory']['entries']
            assert set(b['memory']) == {'format','entries'}
    report = summarize(frozen)
    assert report['status'] == 'prepared' and all(v['requests'] == 0 for v in report['arm_totals'].values())
    assert all(c['first_input_token_reduction_pct'] is None for c in report['comparisons'])
    assert not (frozen/'runs').exists()
    with pytest.raises(ValueError,match='new comparison'): inputs.prepare(source,frozen,manifest['spec'])


def test_future_memory_rejected_before_freeze(source,tmp_path,spec):
    clone=tmp_path/'S1';shutil.copytree(source,clone)
    prior=clone/'rounds/R02/memory/active.json'
    state=inputs.read(prior);state['commits'].append('S1_R03');inputs.save(prior,state)
    with pytest.raises(ValueError,match='Future'):
        inputs.prepare(clone,tmp_path/'invalid',spec)
    assert not (tmp_path/'invalid').exists()


@pytest.mark.parametrize('target',['messages.json','material.json','config.json'])
def test_input_content_mismatch_prevents_calls(frozen,target):
    path = (inputs.case_path(frozen,'R03','preconditioner','knowledge_only')/'messages.json' if target=='messages.json'
            else frozen/'cases/R03/preconditioner/material.json' if target=='material.json' else frozen/'config.json')
    value=inputs.read(path)
    if target=='messages.json': value[1]['content']='changed'
    elif target=='material.json': value['diagnosis']['plan']['goal']='Changed goal.'
    else: value['max_attempts']=4
    inputs.save(path,value)
    gen=Generator()
    with pytest.raises(ValueError): one(frozen,gen)
    assert not gen.calls


def test_all_cells_use_isolated_fixed_material_and_resume_without_calls(frozen):
    gen=Generator();result=runner.run(frozen,generate=gen)
    assert len(gen.calls)==16 and all(c['status']=='valid' for c in result)
    report=summarize(frozen)
    assert report['status']=='complete'
    assert report['arm_totals']['knowledge_only']['input_tokens']==800
    assert report['arm_totals']['memory_v3']['retry_requests']==0
    assert all(r['semantic_verdict'] is None for r in report['cells'])
    for row in report['cells']:
        if row['stage']=='replay':
            metrics=row['structural_metrics']
            assert metrics['old_items_requiring_review']==0
            assert metrics['old_items_exact_carryover']>0
    runner.run(frozen,generate=gen,resume=True)
    assert len(gen.calls)==16
    assert not list((frozen/'runs').rglob('active.json'))


def test_invalid_attempt_cost_and_identical_retry(frozen):
    gen=Generator('once_invalid');one(frozen,gen)
    assert len(gen.calls)==2 and gen.calls[0]==gen.calls[1]
    row=next(r for r in summarize(frozen)['cells'] if r['requests'])
    assert row['requests']==2 and row['retry_requests']==1 and row['invalid_attempts']==1
    assert row['input_tokens']==200 and row['first_input_tokens']==100
    assert row['unsuccessful_input_tokens']==100


def test_exhaustion_cannot_reset_budget_on_resume(frozen):
    gen=Generator('always_invalid');assert one(frozen,gen)[0]['status']=='failed'
    assert len(gen.calls)==3
    assert one(frozen,gen,resume=True)[0]['status']=='failed'
    assert len(gen.calls)==3


@pytest.mark.parametrize('mode,expected_calls',[('interrupt_with_response',1),('interrupt_without_response',2)])
def test_interruption_recovery_and_unknown_usage(frozen,mode,expected_calls):
    gen=Generator(mode)
    with pytest.raises(KeyboardInterrupt):one(frozen,gen)
    assert one(frozen,gen,resume=True)[0]['status']=='valid'
    assert len(gen.calls)==expected_calls
    row=next(r for r in summarize(frozen)['cells'] if r['requests'])
    if expected_calls==2:
        assert row['input_tokens'] is None and row['known_input_tokens']==100
        assert row['missing_input_tokens_requests']==1


def test_non_retryable_failure_and_missing_usage(frozen):
    gen=Generator('non_retryable');assert one(frozen,gen)[0]['reason']=='non_retryable'
    assert len(gen.calls)==1
    row=next(r for r in summarize(frozen)['cells'] if r['requests'])
    assert row['input_tokens'] is None and row['total_tokens'] is None
    one(frozen,gen,resume=True);assert len(gen.calls)==1


def test_selected_output_revalidated_on_resume(frozen):
    gen=Generator();one(frozen,gen)
    dest=frozen/'runs/R03/preconditioner/knowledge_only/attempts/001'
    value=inputs.read(dest/'validated.json');value['effective_plan']['goal']='tampered'
    inputs.save(dest/'validated.json',value)
    with pytest.raises(ValueError,match='Saved result differs'):one(frozen,gen,resume=True)
    assert len(gen.calls)==1


def test_invalid_attempt_messages_are_also_verified(frozen):
    gen=Generator('always_invalid');one(frozen,gen)
    dest=frozen/'runs/R03/preconditioner/knowledge_only/attempts/001'
    inputs.save(dest/'messages.json',[])
    with pytest.raises(ValueError,match='messages differ'):summarize(frozen)
    assert len(gen.calls)==3


def test_actual_request_must_match_frozen_parameters(frozen):
    gen=Generator();one(frozen,gen)
    dest=frozen/'runs/R03/preconditioner/knowledge_only/attempts/001'
    cfg=inputs.read(frozen/'config.json')['call_config']
    body={k:v for k,v in cfg.items() if k not in ('endpoint','timeout_seconds')}
    body['messages']=inputs.read(dest/'messages.json')
    request={'endpoint':cfg['endpoint'],'body':body,'timeout_seconds':cfg['timeout_seconds'],'attempts':1}
    inputs.save(dest/'request.json',request);summarize(frozen)
    request['body']['max_tokens']+=1;inputs.save(dest/'request.json',request)
    with pytest.raises(ValueError,match='Actual transport request'):summarize(frozen)


def test_cost_missing_fields_are_not_zero():
    result=usage_totals([{'status':'valid','usage':{'prompt_tokens':7}}, {'status':'invalid','usage':{}}])
    assert result['known_input_tokens']==7 and result['input_tokens'] is None
    assert result['output_tokens'] is None and result['missing_output_tokens_requests']==2
    assert result['unsuccessful_total_tokens'] is None


def test_nonidentical_knowledge_is_review_required_not_automatically_lost():
    old={'id':'M1','knowledge':[{'text':'Old interpretation.','evidence':['R1/diff','R1/P1:1']}]}
    proposal={'revises':['M1'],'knowledge':[{'text':'Refined interpretation.','evidence':['R1/diff','R1/P1:1']}]}
    metrics,review=semantic_material('replay',{'payload':{'memory':{'entries':[old]}}}, {'entries':[proposal]}, {})
    assert metrics['old_items_requiring_review']==1 and review['semantic_verdict'] is None
    assert 'lost' not in metrics


def test_serialization_and_unrelated_files_do_not_block(frozen):
    path=frozen/'config.json'
    path.write_text(json.dumps(inputs.read(path),indent=4)+'\n\n')
    (frozen/'notes.txt').write_text('Ordinary working notes.\n')
    inputs.verify(frozen)


@pytest.mark.parametrize('stage', ['preconditioner', 'replay'])
def test_comparison_crlf_response_does_not_retry(frozen, stage):
    gen = Generator()

    def crlf(messages, dest):
        response = gen(messages, dest)
        response['content'] = json.dumps(json.loads(response['content']), indent=2).replace('\n', '\r\n')
        return response

    args = {'generate': crlf, 'rounds': ['R03'], 'stages': [stage], 'arms': ['knowledge_only']}
    assert runner.run(frozen, **args)[0]['status'] == 'valid'
    assert len(gen.calls) == 1
    dest = frozen/f'runs/R03/{stage}/knowledge_only/attempts/001'
    content = inputs.read(dest/'response.json')['content']
    assert '\r\n' in content and (dest/'raw_output.txt').read_bytes() == content.encode()
    assert runner.run(frozen, resume=True, **args)[0]['status'] == 'valid'
    assert len(gen.calls) == 1
