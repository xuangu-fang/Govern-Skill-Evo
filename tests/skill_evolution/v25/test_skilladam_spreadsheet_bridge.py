"""Offline checks of the controlled comparison boundary, not model quality."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import requests

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/runs'))
import run_skilladam_spreadsheetbench_aligned as app
from skilladam.execution.contracts import GenerationRequest, GenerationResult, RawRollout
from skilladam.core.momentum import MomentumTracker, build_momentum_tools


def configs():
    return app.read(app.EXPERIMENT / 'shared_config.json'), app.read(app.EXPERIMENT / 'skilladam.json')


def response(text, finish='stop', tools=None):
    return {'choices': [{'finish_reason': finish, 'message': {'content': text, 'tool_calls': tools}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}


def request(shared, cfg, stage='iteration_patch', metadata=None):
    return GenerationRequest(stage, ({'role': 'system', 'content': 'contract'},
                                     {'role': 'user', 'content': 'evidence'}),
                             app.context_for(shared, cfg), metadata or {})


VALID = json.dumps({'reasoning': 'test', 'patch': '--- a/skill.md\n+++ b/skill.md\n@@ -1 +1 @@\n-Original\n+Updated\n'})


def test_plan_exact_initial_and_environment():
    shared, cfg = configs()
    ref = ROOT / cfg['reference_campaign']
    assert shared == app.read(ref / 'config.json')
    assert (app.EXPERIMENT / 'initial_skill.md').read_bytes() == (ref / 'initial_skill.md').read_bytes()
    native = app.native_config(cfg)
    runner = app.AlignedRunner(config=native, adapter=app.AlignedAdapter(app.EXPERIMENT), backend=None,
                               context=app.context_for(shared, cfg), output_dir=Path('/unused'))
    cases = runner._validate_cases(app.cases_for(shared, cfg))
    batches = list(runner._build_sampler(cases))
    assert [list(b.training_case_ids) for b in batches] == shared['batches']
    assert all(b.training_case_ids == b.validation_case_ids for b in batches)
    assert set(c.case_id for c in cases).isdisjoint(shared['test_tasks'])
    assert len(cases) == 120 and len(batches) == 8
    assert all('answer_path' not in c.payload for c in cases)
    assert native.trajectory_compression == 'llm' and native.optimizer_context_limit == 96000
    assert cfg['optimizer_transport']['max_tokens'] == 16384
    assert shared['actor_profile']['actor_max_output_tokens'] == 32768


def test_one_retry_budget_feedback_and_unchanged_technical_requests(tmp_path):
    shared, cfg = configs()
    calls = []
    def send(body, path):
        calls.append(deepcopy(body))
        if len(calls) == 1:
            return response('invalid JSON')
        if len(calls) == 2:
            raise requests.Timeout()
        if len(calls) == 3:
            return response('truncated', 'length')
        return response(VALID)
    backend = app.SharedBackend(shared, cfg, tmp_path, sender=send)
    backend.patch_context = SimpleNamespace(current_skill='Original\n')
    with patch.object(app.time, 'sleep') as sleep:
        result = backend.generate(request(shared, cfg))
    assert len(calls) == 4 and sum(u.requests for u in result.usage) == 4
    assert calls[0]['max_tokens'] == 16384
    assert calls[0]['thinking'] == shared['call_config']['thinking']
    assert calls[1]['messages'][:2] == calls[0]['messages']
    assert calls[1]['messages'][-2]['content'] == 'invalid JSON'
    assert 'Validation Error' in calls[1]['messages'][-1]['content']
    assert calls[1] == calls[2] == calls[3]
    assert [c.args[0] for c in sleep.call_args_list] == [2, 4, 6]
    backend.generate(request(shared, cfg))
    assert len(calls) == 4


def test_six_attempts_persist_across_resume_without_budget_reset(tmp_path):
    shared, cfg = configs()
    count = 0
    def send(body, path):
        nonlocal count
        count += 1
        return response('invalid JSON')
    backend = app.SharedBackend(shared, cfg, tmp_path, sender=send)
    backend.patch_context = SimpleNamespace(current_skill='Original\n')
    with patch.object(app.time, 'sleep'), pytest.raises(RuntimeError, match='budget exhausted'):
        backend.generate(request(shared, cfg))
    assert count == 6
    backend.resume = True
    with pytest.raises(RuntimeError, match='budget exhausted'):
        backend.generate(request(shared, cfg))
    assert count == 6


def test_momentum_tools_retry_without_mutating_memory(tmp_path):
    shared, cfg = configs()
    calls = []
    def send(body, path):
        calls.append(deepcopy(body))
        args = {'label': 'format', 'description': 'bad format', 'evidence': 'execution failed'}
        if len(calls) == 1:
            del args['description']
        tool = {'id': 'call_1', 'type': 'function', 'function': {
            'name': 'report_problem', 'arguments': json.dumps(args)}}
        return response(None, 'tool_calls', [tool])
    backend = app.SharedBackend(shared, cfg, tmp_path, sender=send)
    backend.momentum = MomentumTracker()
    with patch.object(app.time, 'sleep'):
        result = backend.generate(request(shared, cfg, 'momentum_update', {'tools': build_momentum_tools()}))
    assert len(calls) == 2 and len(result.tool_calls) == 1
    assert calls[0]['tools'] == calls[1]['tools']
    assert 'report_problem' in calls[1]['messages'][-2]['content']
    assert 'missing required' in calls[1]['messages'][-1]['content']
    assert not backend.momentum.problems


@pytest.mark.parametrize('kind', ['disk', 'forbidden'])
def test_non_retryable_failure_stops_immediately(tmp_path, kind):
    shared, cfg = configs()
    calls = []
    def send(body, path):
        calls.append(body)
        if kind == 'disk':
            raise OSError('local disk failure')
        app.write(path / 'http_status.json', {'status_code': 403})
        (path / 'http_response.txt').write_text('forbidden')
        raise ValueError('HTTP 403')
    backend = app.SharedBackend(shared, cfg, tmp_path, sender=send)
    with pytest.raises((OSError, app.RequestFailure)):
        backend.generate(request(shared, cfg, 'trajectory_compression'))
    assert len(calls) == 1


def test_shared_actor_feedback_and_score_stay_separate(tmp_path):
    import openpyxl
    shared, cfg = configs()
    book = tmp_path / 'input.xlsx'
    wb = openpyxl.Workbook(); wb.save(book); wb.close()
    task = dict(shared['task_items'][shared['batches'][0][0]], input_path=str(book))
    calls, executions = [], []
    def generate(messages, directory, timeout, config):
        calls.append(messages)
        return {'content': '```python\nprint("test")\n```', 'finish_reason': 'stop'}
    def execute(code, snapshot, directory, timeout, config):
        executions.append(code)
        if len(executions) == 1:
            return {'status': 'error', 'error_category': 'execution_error', 'error_detail': 'runtime failure',
                    'exit_status': 1, 'output_openable': False, 'stderr': 'runtime failure'}
        return {'status': 'success', 'exit_status': 0, 'output_openable': True, 'output_path': str(book)}
    score = {'hard': 0, 'per_cell_pass_rate': .5, 'correct_cells': 1, 'total_cells': 2,
             'mismatched_cells': ['GOLD_ONLY_COORDINATE']}
    path = app.actor.run(task, 'Original\n', tmp_path / 'actor', shared,
                         generate=generate, execute=execute, score=lambda *args: score)
    record = app.read(path)
    assert len(calls) == 2 and calls[1][-1] == record['attempts'][0]['feedback_to_actor']
    assert 'runtime failure' in calls[1][-1]['content']
    assert 'GOLD_ONLY_COORDINATE' not in json.dumps(calls)
    raw = app.convert_record(record)
    assert raw['hard'] == 0 and raw['per_cell_pass_rate'] == .5
    assert record['attempts'][-1]['feedback_to_actor'] is None
    assert 'GOLD_ONLY_COORDINATE' not in json.dumps(raw['messages'])
    names = [m.get('name') for m in raw['messages'] if m['role'] == 'tool']
    assert names == ['harness_execution_not_actor_feedback', 'actual_feedback_to_actor'] * 2


def test_native_loop_skips_stage0_runs_gate_and_momentum(tmp_path):
    shared, cfg = configs()
    cfg['native']['optimization_case_ids'] = shared['batches'][0][:1]
    cfg['native'].update(train_size=1, validation_size=1, stage0_size=1)
    cfg['native']['feedback_loop'].update(max_iterations=1, min_iterations=1)
    class Backend(app.SharedBackend):
        def __init__(self):
            super().__init__(shared, cfg, tmp_path)
            self.rollouts, self.stages = [], []
        def execute_batch(self, execution):
            self.rollouts.append(execution.stage)
            value = int(len(self.rollouts) == 3)
            result = []
            for r in execution.requests:
                self.queries[r.case.case_id] = 'Original user task'
                result.append(RawRollout(r.case.case_id, {'hard': value, 'per_cell_pass_rate': value,
                    'exec_pass': 1, 'n_turns': 1, 'code': 'print(1)', 'messages': []}))
            return tuple(result)
        def generate(self, req):
            self.stages.append(req.stage)
            return GenerationResult(VALID if req.stage == 'iteration_patch' else 'No additional issues.')
    backend = Backend()
    runner = app.AlignedRunner(config=app.native_config(cfg), adapter=app.AlignedAdapter(tmp_path), backend=backend,
                               context=app.context_for(shared, cfg), output_dir=tmp_path / 'native')
    result = runner.run(cases=app.cases_for(shared, cfg), initial_skill='Original\n')
    assert backend.rollouts == ['training_rollout', 'validation_rollout', 'validation_rollout']
    assert backend.stages == ['trajectory_compression', 'iteration_patch', 'momentum_update']
    assert result.final_skill == 'Updated\n'
    assert result.feedback_loop.iterations[0].accepted


def execution_configs(tmp_path):
    from .test_execution_history import setup
    shared,task=setup(tmp_path)
    _,cfg=configs()
    cfg['actor_evidence_view']=app.protocol.EXECUTION_HISTORY
    cfg['native']['optimization_case_ids']=[task['id']]
    cfg['native'].update(train_size=1,validation_size=1,stage0_size=1)
    cfg['native']['feedback_loop'].update(max_iterations=1,min_iterations=1)
    assert shared['actor_profile']['actor_max_output_tokens']==49152
    return shared,cfg,task


def test_conversion_reuses_v25_audit_and_preserves_all_request_costs(tmp_path):
    from .test_execution_history import good,runtime_error
    from .support import response as actor_response,fast_execute,PARENT
    from src.skill_evolution.v25.benchmarks.spreadsheetbench import transport
    shared,cfg,task=execution_configs(tmp_path);calls=[];executions=[]
    def generate(messages,*args):
        calls.append(deepcopy(messages));n=len(calls)
        if n in (1,6):return actor_response('PRIVATE_FORMAT_'+str(n))
        if n==2:raise transport.RequestError('PRIVATE_NETWORK')
        if n==3:return {**actor_response('PRIVATE_TRUNCATION'),'finish_reason':'length'}
        if n==4:return actor_response('')
        return good()
    def execute(*args):
        executions.append(1)
        return runtime_error() if len(executions)==1 else fast_execute(*args)
    record=app.read(app.actor.run(task,PARENT,tmp_path/'actor',shared,generate=generate,execute=execute))
    original=deepcopy(record);raw=app.convert_record(record)
    assert record==original and len(calls)==7 and len(executions)==2
    assert 'PRIVATE_' not in json.dumps(raw['messages'])
    assert 'Previous Program Validation Error' not in json.dumps(raw['messages'])
    assert 'FULL_RUNTIME_LOG' in json.dumps(raw['messages']) and 'VISIBLE_RUNTIME' in json.dumps(raw['messages'])
    assert sum(u['requests'] for u in raw['usage_records'])==7
    assert sum(u['total_tokens'] or 0 for u in raw['usage_records'])==12
    assert raw['usage_records'][1]['total_tokens'] is None  # Failed transport usage is unknown, not free.
    v25=app.facts.build_facts([record])['facts']['runs'][0]
    tools=[json.loads(m['content']) for m in raw['messages'] if m.get('name')=='harness_execution_not_actor_feedback']
    assert [e['ref'] for e in tools]==['P1:4','P1:6']
    for source,event in zip(v25['attempts'],tools):
        assert all(event[k]==source[k] for k in ('ref','execution','executed_code','code_attempt','request_context'))
    assert json.loads(raw['messages'][-1]['content'])==v25['outcome']
    assert 'api_requests' not in json.dumps(raw['messages']) and 'generation_responses' not in json.dumps(raw['messages'])
    parsed=app.AlignedAdapter(tmp_path).parse_result(app.cases_for(shared,cfg)[0],raw)
    assert sum(u.requests for u in parsed.usage)==7 and parsed.metadata['n_turns']==2
    record['requests'][1]['messages']=[]
    with pytest.raises(ValueError,match='Archived API request differs'):app.convert_record(record)


@pytest.mark.parametrize('change',['missing_view','unknown_view','old_actor','task_timeout','request_budget','sdk_retry','outer_retry'])
def test_actor_and_evidence_protocol_mismatch_is_rejected(tmp_path,change):
    shared,cfg,_=execution_configs(tmp_path)
    assert app.validate_actor_protocol(shared,cfg)=={'actor_history_policy':'execution_only_v1','actor_evidence_view':'execution_only_v1'}
    if change=='missing_view':cfg.pop('actor_evidence_view')
    elif change=='unknown_view':cfg['actor_evidence_view']='unknown'
    elif change=='old_actor':shared['actor_profile'].pop('actor_history_policy')
    elif change=='task_timeout':shared['actor_profile']['actor_task_timeout_seconds']=600
    elif change=='request_budget':shared['actor_profile']['request_attempts_total']=7
    elif change=='sdk_retry':cfg['optimizer_transport']['sdk_max_retries']=1
    else:cfg['native']['feedback_loop']['patch_attempts']=2
    with pytest.raises(ValueError):app.SharedBackend(shared,cfg,tmp_path/'unused')
    assert not (tmp_path/'unused').exists()


def test_preflight_reports_and_requires_frozen_new_protocol(tmp_path,monkeypatch):
    shared,cfg,_=execution_configs(tmp_path)
    experiment=tmp_path/'comparison';reference=tmp_path/'reference'
    cfg['reference_campaign']='reference'
    app.write(experiment/'shared_config.json',shared);app.write(experiment/'skilladam.json',cfg)
    (experiment/'initial_skill.md').write_text(shared['initial_skill']['text'])
    app.write(reference/'config.json',shared);app.write(reference/'contract.json',{});app.write(reference/'runtime.json',{})
    manifest=dict(python_version=sys.version,python_executable=sys.executable,packages={},docker_image_id='fake-image',
        files={str((experiment/name).relative_to(tmp_path)):app.sha(experiment/name) for name in ('shared_config.json','skilladam.json')})
    app.write(experiment/'manifest.json',manifest)
    monkeypatch.setattr(app,'ROOT',tmp_path);monkeypatch.setattr(app,'EXPERIMENT',experiment)
    monkeypatch.setattr(app.executor,'runtime_snapshot',lambda cfg:{})
    monkeypatch.setattr(app.subprocess,'check_output',lambda *a,**kw:'fake-image\n')
    report=app.check()
    assert report['actor_history_policy']==report['actor_evidence_view']=='execution_only_v1'
    assert report['model_requests']==0 and report['optimizer_max_tokens']==16384
    assert report['actor_max_tokens']==49152
    manifest['files'].pop('comparison/skilladam.json');app.write(experiment/'manifest.json',manifest)
    with pytest.raises(ValueError,match='not frozen: skilladam.json'):app.check()


def test_new_protocol_reaches_native_compression_gate_and_momentum_without_leaks(tmp_path):
    from .support import response as actor_response,fast_execute,CODE
    shared,cfg,task=execution_configs(tmp_path);seen=set();calls=[];requests=[]
    native_before=deepcopy(cfg['native']);original_run=app.actor.run
    def generate(messages,directory,*args):
        calls.append(deepcopy(messages));slot=Path(directory).parent
        if slot not in seen:
            seen.add(slot);return actor_response('PRIVATE_FORMAT_SENTINEL')
        return actor_response('```python\n'+CODE%(' + 1' if 'Updated' in messages[0]['content'] else '')+'```')
    def run(*args,**kwargs):return original_run(*args,**kwargs,generate=generate,execute=fast_execute)
    class Backend(app.SharedBackend):
        def generate(self,req):
            requests.append(req)
            return GenerationResult(VALID if req.stage=='iteration_patch' else 'Observed execution only.')
    backend=Backend(shared,cfg,tmp_path/'native')
    runner=app.AlignedRunner(config=app.native_config(cfg),adapter=app.AlignedAdapter(tmp_path),backend=backend,
        context=app.context_for(shared,cfg),output_dir=tmp_path/'native')
    with patch.object(app.actor,'run',side_effect=run):
        result=runner.run(cases=app.cases_for(shared,cfg),initial_skill='Original\n')
    assert [r.stage for r in requests]==['trajectory_compression','iteration_patch','momentum_update']
    for req in requests:
        text=json.dumps([dict(m) for m in req.messages])
        assert 'PRIVATE_FORMAT_SENTINEL' not in text
        assert 'Previous Program Validation Error' not in text
        assert 'usage_records' not in text
    compression=requests[0].messages[-1]['content']
    assert 'execution_only_v1' in compression and 'post_execution_outcome_not_actor_feedback' in compression
    assert len(calls)==6 and len(seen)==3
    assert result.final_skill=='Updated\n' and result.feedback_loop.iterations[0].accepted
    assert cfg['native']==native_before
    assert runner.config.trajectory_compression=='llm' and runner.config.optimizer_context_limit==96000
    assert cfg['optimizer_transport']['max_tokens']==16384
    assert all('49152' in messages[0]['content'] for messages in calls)
    for file in (tmp_path/'native').rglob('trajectory.json'):
        assert 'PRIVATE_FORMAT_SENTINEL' in file.read_text()
    for file in (tmp_path/'native').rglob('batch.json'):
        assert app.read(file)['actor_evidence_view']=='execution_only_v1'
