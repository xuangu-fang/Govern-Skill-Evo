import json
from pathlib import Path
from unittest.mock import patch
import pytest
from src.skill_evolution import formal_v18_v4 as f


def test_cleanup_only_removes_single_tool_clause():
    policy = 'Before\nYou should only make one tool call at a time, and if you make a tool call, you should not respond to the user simultaneously.\nAfter'
    assert f.clean_policy(policy) == 'Before\nIf you make a tool call, you should not respond to the user simultaneously.\nAfter'
    with pytest.raises(ValueError): f.clean_policy('unrecognized policy')


def test_freeze_detects_drift(tmp_path):
    (tmp_path / 'config.json').write_text('{}')
    f.save(tmp_path / 'manifest.json', {'files': {'config.json': '0'*64}})
    with patch.object(f, 'FREEZE', tmp_path), patch.object(f, 'ROOT', tmp_path):
        with pytest.raises(ValueError, match='Frozen input changed'): f.verify_freeze()


@pytest.mark.parametrize('decisions', [('ACCEPT', 'RETAIN', 'ACCEPT'), ('RETAIN', 'RETAIN', 'RETAIN')])
def test_rounds_only_promote_accepted_candidate(tmp_path, decisions):
    from contextlib import nullcontext
    from src.skill_evolution import monitor_v18, monitor_benchmark_v18_v4
    freeze = tmp_path / 'freeze'; freeze.mkdir()
    (freeze / 'S0.md').write_text('S0'); f.save(freeze / 'manifest.json', {})
    config = {'rounds': 3, 'base_config': {}, 'seed': 200}
    seen = []; calls = iter(decisions)
    def evolve(config, root, round_id, parent):
        seen.append(parent); return parent + '+', 'CANDIDATE'
    class Backend:
        base_config = {}; seed = 200
        def __init__(self, **kwargs): pass
        def monitor_input(self, round_id): return round_id
    with patch.object(f, 'FREEZE', freeze), patch.object(f, 'verify_freeze', return_value=config), patch.object(f, 'frozen_policies', return_value=nullcontext()), patch.object(f, 'evolve_round', side_effect=evolve), patch.object(monitor_benchmark_v18_v4, 'CurrentBenchmarkMonitor', Backend), patch.object(monitor_v18, 'run_monitor', side_effect=lambda *a, **k: {'status': 'COMPLETE', 'decision': next(calls)}):
        f.run_campaign(config, tmp_path / 'out')
    expected = 'S0'
    for parent, decision in zip(seen, decisions):
        assert parent == expected
        if decision == 'ACCEPT': expected += '+'
    assert (tmp_path / 'out/current_skill.md').read_text() == expected
    assert json.loads((tmp_path / 'out/campaign.json').read_text())['status'] == 'COMPLETE'


def test_failure_keeps_parent_and_marks_incomplete(tmp_path):
    from contextlib import nullcontext
    freeze = tmp_path / 'freeze'; freeze.mkdir()
    (freeze / 'S0.md').write_text('S0'); f.save(freeze / 'manifest.json', {})
    config = {'rounds': 3}
    with patch.object(f, 'FREEZE', freeze), patch.object(f, 'verify_freeze', return_value=config), patch.object(f, 'frozen_policies', return_value=nullcontext()), patch.object(f, 'evolve_round', side_effect=RuntimeError('failed')):
        with pytest.raises(RuntimeError): f.run_campaign({'rounds': 3}, tmp_path / 'out')
    assert (tmp_path / 'out/current_skill.md').read_text() == 'S0'
    assert json.loads((tmp_path / 'out/campaign.json').read_text())['status'] == 'INCOMPLETE'


def test_resume_reuses_trajectory_without_model_or_evaluator(tmp_path):
    from unittest.mock import Mock
    orchestrator = Mock()
    orchestrator.environment.tools.db.model_dump.return_value = {'initial': 1}
    evaluator = Mock()
    simulation = {'task_id': 'task', 'seed': 200, 'messages': []}
    for name, data in [('initial_db', {'initial': 1}), ('simulation', simulation), ('final_db', {}), ('evaluation', {'success': False, 'compliant': False})]:
        f.save(tmp_path / f'{name}.json', data)
    result = f.evolution_rollout(tmp_path, orchestrator=orchestrator, evaluator=evaluator, task_id='task', seed=200)
    assert result == (simulation, {'success': False, 'compliant': False})
    orchestrator.run.assert_not_called(); evaluator.evaluate.assert_not_called()
    with pytest.raises(ValueError, match='binding mismatch'):
        f.evolution_rollout(tmp_path, orchestrator=orchestrator, evaluator=evaluator, task_id='other', seed=200)


def test_resume_partial_trajectory_restarts_and_preserves_partial(tmp_path):
    from unittest.mock import Mock
    directory = tmp_path / 'T018'
    f.save(directory / 'initial_db.json', {'old': 1})
    orchestrator = Mock(); evaluator = Mock()
    orchestrator.environment.tools.db.model_dump.return_value = {}
    orchestrator.run.return_value.model_dump.return_value = {'task_id': 'task', 'seed': 200}
    evaluator.evaluate.return_value = {'success': True, 'compliant': True}
    f.evolution_rollout(directory, orchestrator=orchestrator, evaluator=evaluator, task_id='task', seed=200)
    orchestrator.run.assert_called_once()
    assert (tmp_path / 'T018.partial-1/initial_db.json').exists()
    assert (directory / 'evaluation.json').exists()


def test_resume_interrupted_grouping_preserves_request_and_restarts(tmp_path):
    from src.skill_evolution import experience_grouping_v17 as grouping
    directory = tmp_path / 'grouping'
    f.save(directory / 'grouping_request.json', {'request': 'fixed'})
    f.save(directory / 'grouping_attempts.json', [{'attempt': 1}])
    with patch.object(grouping, 'prepare_grouping_request', return_value={'request': 'fixed'}), patch.object(grouping, 'run_experience_grouping', return_value={'groups': []}) as run:
        assert f.resume_grouping(None, scope=None, directory=directory) == {'groups': []}
        run.assert_called_once()
    assert (tmp_path / 'grouping.interrupted-1/grouping_attempts.json').exists()


def test_resume_interrupted_grouping_isolates_stale_diagnoses(tmp_path):
    from src.skill_evolution import experience_grouping_v17 as grouping
    directory = tmp_path / 'grouping'
    f.save(directory / 'grouping_request.json', {'request': 'fixed'})
    f.save(tmp_path / 'diagnosis/G1/validation.json', {'status': 'VALID'})
    with patch.object(grouping, 'prepare_grouping_request', return_value={'request': 'fixed'}), patch.object(grouping, 'run_experience_grouping', return_value={'groups': []}):
        f.resume_grouping(None, scope=None, directory=directory)
    assert f.load(tmp_path / 'diagnosis.stale-grouping-1/G1/validation.json')['status'] == 'VALID'
    assert not (tmp_path / 'diagnosis').exists()


def test_campaign_lock_rejects_concurrent_process(tmp_path):
    with f.campaign_lock(tmp_path / 'campaign'):
        with pytest.raises(RuntimeError, match='already running'):
            with f.campaign_lock(tmp_path / 'campaign'):
                pass


def test_resume_completed_grouping_does_not_call_model(tmp_path):
    from src.skill_evolution import experience_grouping_v17 as grouping
    from src.skill_evolution import experience_grouping_contract_v17 as contract
    directory = tmp_path / 'grouping'
    f.save(directory / 'grouping_request.json', {'request': 'fixed'})
    f.save(directory / 'validated_groups.json', {'groups': [], 'round_id': 'r'})
    from types import SimpleNamespace
    with patch.object(grouping, 'prepare_grouping_request', return_value={'request': 'fixed'}), patch.object(grouping, 'run_experience_grouping') as run, patch.object(contract, 'bind_grouping_result', return_value={'groups': [], 'round_id': 'r'}):
        assert f.resume_grouping(SimpleNamespace(payload={}), scope=None, directory=directory)['round_id'] == 'r'
        run.assert_not_called()


@pytest.mark.parametrize('status', ['REJECTED', 'RUNNING'])
def test_resume_diagnosis_retries_only_once_and_preserves_failure(tmp_path, status):
    from src.skill_evolution import diagnosis_v18 as diagnosis
    from src.skill_evolution import diagnosis_prompt_v18 as prompt
    directory = tmp_path / 'g2'
    f.save(directory / 'request.json', {'user_prompt': 'fixed'})
    f.save(directory / 'validation.json', {'status': status})
    with patch.object(prompt, 'build_diagnosis_request', return_value={'user_prompt': 'fixed'}), patch.object(diagnosis, 'run_group_diagnosis', return_value={'status': 'REJECTED'}) as run:
        assert f.resume_diagnosis(None, directory=directory) == {'status': 'REJECTED'}
        run.assert_called_once_with(None, artifact_dir=directory)
    assert f.load(tmp_path / 'g2.attempt-1/validation.json')['status'] == status


def test_resume_valid_diagnosis_revalidates_without_model(tmp_path):
    from src.skill_evolution import diagnosis_v18 as diagnosis, diagnosis_prompt_v18 as prompt
    from src.skill_evolution import diagnosis_validation_v18 as validation, information_boundary_v15 as boundary
    directory = tmp_path / 'g1'
    for name, data in [('request', {'user_prompt': 'fixed'}), ('validation', {'status': 'VALID'}), ('response', {'raw_response': '{}', 'finish_reason': 'stop'}), ('validated_diagnosis', {'semantic': {}})]:
        f.save(directory / f'{name}.json', data)
    with patch.object(prompt, 'build_diagnosis_request', return_value={'user_prompt': 'fixed'}), patch.object(validation, 'validate_diagnosis_response'), patch.object(boundary, 'unpack', return_value={'semantic': {}}), patch.object(diagnosis, 'run_group_diagnosis') as run:
        assert f.resume_diagnosis(None, directory=directory)['status'] == 'VALID'
        run.assert_not_called()


def test_formal_round_limit_cannot_be_extended(tmp_path):
    with pytest.raises(ValueError, match='extension is forbidden'):
        f.run_campaign({'rounds':4}, tmp_path/'out', resume=True,total_rounds=5)


from tests.skill_evolution.test_editor_apply_v18 import case, editing_input, mixed, indexed_response
from tests.skill_evolution.test_editor_v18 import completion


def test_real_compiler_delete_reaches_gate_with_empty_candidate(case, tmp_path):
    from contextlib import nullcontext
    from src.skill_evolution import editor_v18, monitor_benchmark_v18_v4
    from src.skill_evolution.monitor_v18 import MonitorInput, MonitorTask
    value = editing_input(case, '- A', [('SHOULD_REMOVE', [0])]).compiler_input
    freeze = tmp_path / 'freeze'; freeze.mkdir()
    (freeze / 'S0.md').write_text(value.parent_skill); f.save(freeze / 'manifest.json', {})
    config = {'rounds': 1, 'base_config': {}, 'seed': 200}
    observed = []
    class Backend:
        base_config = {}; seed = 200
        def __init__(self, **kwargs):
            self.parent = kwargs['parent_skill']; self.candidate = kwargs['candidate_skill']
            assert self.candidate == ''
        def monitor_input(self, round_id):
            return MonitorInput(round_id, (MonitorTask('T', 200),), self.parent, self.candidate, 'a'*64)
        def __call__(self, call):
            observed.append(call.role)
            return {'success': call.role == 'CANDIDATE', 'compliant': True, 'initial_state_digest': 'b'*64}
    with patch.object(f, 'FREEZE', freeze), patch.object(f, 'verify_freeze', return_value=config), patch.object(f, 'frozen_policies', return_value=nullcontext()), patch.object(f, 'evolve_round', side_effect=lambda c,r,*a:f.compile_and_edit(value,r)), patch.object(monitor_benchmark_v18_v4, 'CurrentBenchmarkMonitor', Backend), patch.object(editor_v18, '_transport', side_effect=AssertionError('no model')):
        f.run_campaign(config, tmp_path/'out')
    assert sorted(observed) == ['CANDIDATE', 'PARENT']
    assert (tmp_path/'out/current_skill.md').read_bytes() == b''
    assert f.load(tmp_path/'out/round-01/editor/validation.json')['status'] == 'APPLIED_DETERMINISTIC'
    assert f.load(tmp_path/'out/campaign.json')['rounds'][0]['decision'] == 'ACCEPT'


def test_mixed_real_compile_editor_preserves_crlf(case, tmp_path):
    from src.skill_evolution import editor_v18
    value = mixed(case).compiler_input
    with patch.object(editor_v18, '_transport', return_value=completion(indexed_response([(1,'替换'),(3,'追加')]))):
        text, status = f.compile_and_edit(value, tmp_path)
    assert status == 'CANDIDATE' and '\r\n' in text
    assert '- A delete' not in text and '- C delete' not in text
    assert (tmp_path/'editor/candidate_skill.md').read_bytes() == text.encode()


@pytest.mark.parametrize('reply,expected', [('unable','UNABLE'), ('invalid','REJECTED')])
def test_mixed_failed_editor_keeps_parent(case,tmp_path,reply,expected):
    from src.skill_evolution import editor_v18
    value = mixed(case).compiler_input
    raw = json.dumps({'status':'UNABLE','reason':'conflict','edits':[]}) if reply=='unable' else '{}'
    with patch.object(editor_v18, '_transport', return_value=completion(raw)):
        if expected == 'REJECTED':
            with pytest.raises(ValueError,match='Editor rejected'):f.compile_and_edit(value,tmp_path)
        else:assert f.compile_and_edit(value,tmp_path) == (None,'UNABLE')
    assert not (tmp_path/'editor/candidate_skill.md').exists()


def test_interrupted_compiler_and_editor_archived(case,tmp_path):
    value = editing_input(case, '- A', [('SHOULD_REMOVE',[0])]).compiler_input
    for name in ('compiler','editor'):f.save(tmp_path/name/'validation.json',{'status':'RUNNING'})
    assert f.compile_and_edit(value,tmp_path) == ('','CANDIDATE')
    for name in ('compiler','editor'):
        assert f.load(tmp_path/(name+'.attempt-1')/'validation.json')['status']=='RUNNING'


def test_resume_deterministic_candidate_without_learner(case,tmp_path):
    from contextlib import nullcontext
    from src.skill_evolution import monitor_benchmark_v18_v4, monitor_v18
    value = editing_input(case,'- A',[('SHOULD_REMOVE',[0])]).compiler_input
    freeze=tmp_path/'freeze';freeze.mkdir();(freeze/'S0.md').write_text('- A');f.save(freeze/'manifest.json',{})
    out=tmp_path/'out';root=out/'round-01';root.mkdir(parents=True)
    (root/'parent_skill.md').write_text('- A')
    f.compile_and_edit(value,root)
    config={'rounds':1,'base_config':{},'seed':200}
    f.save(out/'config.json',config);f.save(out/'frozen_manifest.json',{});f.save(out/'execution.json',{'mode':'FORMAL','round_limit':1})
    f.save(out/'campaign.json',{'status':'INCOMPLETE','rounds':[]})
    class Backend:
        base_config={};seed=200
        def __init__(self,**kw):assert kw['candidate_skill']==''
        def monitor_input(self,r):return r
    with patch.object(f,'FREEZE',freeze),patch.object(f,'verify_freeze',return_value=config),patch.object(f,'frozen_policies',return_value=nullcontext()),patch.object(f,'evolve_round',side_effect=AssertionError('no learner')),patch.object(monitor_benchmark_v18_v4,'CurrentBenchmarkMonitor',Backend),patch.object(monitor_v18,'run_monitor',return_value={'status':'COMPLETE','decision':'RETAIN'}):
        f.run_campaign(config,out,resume=True)
    assert (out/'current_skill.md').read_text()=='- A'


def test_resume_rejects_changed_freeze(tmp_path):
    freeze=tmp_path/'freeze';freeze.mkdir();(freeze/'S0.md').write_text('S0');f.save(freeze/'manifest.json',{'new':1})
    out=tmp_path/'out';out.mkdir();config={'rounds':1}
    f.save(out/'config.json',config);f.save(out/'frozen_manifest.json',{});f.save(out/'execution.json',{'mode':'FORMAL','round_limit':1})
    with patch.object(f,'FREEZE',freeze),patch.object(f,'verify_freeze',return_value=config):
        with pytest.raises(ValueError,match='Resume freeze'):f.run_campaign(config,out,resume=True)


def test_pilot_runs_exactly_one_round_and_records_mode(tmp_path):
    from contextlib import nullcontext
    from src.skill_evolution import monitor_benchmark_v18_v4, monitor_v18
    freeze=tmp_path/'freeze';freeze.mkdir();(freeze/'S0.md').write_text('S0');f.save(freeze/'manifest.json',{})
    config={'rounds':4,'base_config':{},'seed':200}
    seen=[]
    class Backend:
        base_config={};seed=200
        def __init__(self,**kwargs):pass
        def monitor_input(self,round_id):return round_id
    def evolve(config,root,round_id,parent):
        seen.append(round_id);return 'candidate','CANDIDATE'
    with patch.object(f,'FREEZE',freeze),patch.object(f,'verify_freeze',return_value=config),patch.object(f,'frozen_policies',return_value=nullcontext()),patch.object(f,'evolve_round',side_effect=evolve),patch.object(monitor_benchmark_v18_v4,'CurrentBenchmarkMonitor',Backend),patch.object(monitor_v18,'run_monitor',return_value={'status':'COMPLETE','decision':'RETAIN'}):
        f.run_campaign(config,tmp_path/'out',pilot=True)
    assert seen == ['round-01']
    assert f.load(tmp_path/'out/execution.json') == {'mode':'PILOT','round_limit':1}
    assert f.load(tmp_path/'out/campaign.json')['stop_reason'] == 'ROUND_LIMIT'


def test_pilot_resume_requires_same_mode(tmp_path):
    freeze=tmp_path/'freeze';freeze.mkdir();(freeze/'S0.md').write_text('S0');f.save(freeze/'manifest.json',{})
    out=tmp_path/'out';out.mkdir();config={'rounds':4}
    f.save(out/'config.json',config);f.save(out/'execution.json',{'mode':'FORMAL','round_limit':4});f.save(out/'frozen_manifest.json',{})
    with patch.object(f,'FREEZE',freeze),patch.object(f,'verify_freeze',return_value=config):
        with pytest.raises(ValueError,match='execution mode'):f.run_campaign(config,out,resume=True,pilot=True)


def test_evolve_round_wires_grouping_diagnosis_compiler_editor(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from src.skill_evolution import experience_grouping_v17 as grouping, diagnosis_v18, editor_v18
    from src.skill_evolution import autonomous_gse_v15_benchmark_runtime as normalization
    from src.skill_evolution.experience_grouping_contract_v17 import EvolutionExperienceRef, bind_grouping_result
    from src.skill_evolution.information_boundary_v15 import unpack
    from tests.skill_evolution.test_experience_cards_v17 import captured
    from tests.skill_evolution.test_compiler_v18 import valid
    from tests.skill_evolution.test_editor_apply_v18 import response
    sample=captured(EvolutionExperienceRef('T001','C001','R001'))
    freeze=tmp_path/'freeze';freeze.mkdir();(freeze/'S0.md').write_text('# Skill\n');f.save(freeze/'user_prompts.json',{})
    root=tmp_path/'round';root.mkdir()
    adapter=Mock();adapter.build_orchestrator.return_value=(Mock(),sample.visible_view)
    runtime=SimpleNamespace(BenchmarkRegistry=Mock(),UnifiedEnvironmentAdapter=Mock(return_value=adapter),DeterministicEvaluatorDispatcher=Mock())
    def group(batch,scope,artifact_dir):
        return bind_grouping_result(batch.payload,{'groups':[{'group_id':'G1','decision_problem':'When to act?', 'members':['T001'],'shared_basis':'Observed behavior','important_differences':[]}]},scope=scope)
    original=diagnosis_v18.run_group_diagnosis
    def diagnose(request,**kwargs):return original(request,transport=lambda _:completion(json.dumps(valid(request))),**kwargs)
    events=[{k:v for k,v in e.items() if k!='step'} for e in unpack(sample.experience,'TRAJECTORY_DERIVED')['trajectory']]
    with patch.object(f,'FREEZE',freeze),patch.object(f,'runtime',return_value=runtime),patch.object(f,'evolution_rollout',return_value=({}, {'success':False,'compliant':True})),patch.object(normalization,'normalize_stored_simulation',return_value=events),patch.object(grouping,'run_experience_grouping',side_effect=group),patch.object(diagnosis_v18,'run_group_diagnosis',side_effect=diagnose),patch.object(editor_v18,'_transport',return_value=completion(response(['Learned rule']))):
        text,status=f.evolve_round({'tasks':{'train':['task']},'base_config':{},'seed':200},root,'round-01','# Skill\n')
    assert status=='CANDIDATE' and 'Learned rule' in text
    assert f.load(root/'compiler/validation.json')['status']=='VALID'
    assert f.load(root/'editor/validation.json')['status']=='VALID'
    assert f.load(root/'diagnosis/G1/validation.json')['status']=='VALID'
    assert runtime.UnifiedEnvironmentAdapter.call_args.kwargs == {'frozen_user_prompts':{}}
