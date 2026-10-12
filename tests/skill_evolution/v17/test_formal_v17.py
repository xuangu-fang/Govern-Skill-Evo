import json
from pathlib import Path
from unittest.mock import patch
import pytest
from src.skill_evolution.v17 import formal_v17 as f


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
    from src.skill_evolution.v17 import monitor_v17, monitor_benchmark_v17
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
    with patch.object(f, 'FREEZE', freeze), patch.object(f, 'verify_freeze'), patch.object(f, 'frozen_policies', return_value=nullcontext()), patch.object(f, 'evolve_round', side_effect=evolve), patch.object(monitor_benchmark_v17, 'CurrentBenchmarkMonitor', Backend), patch.object(monitor_v17, 'run_monitor', side_effect=lambda *a, **k: {'status': 'COMPLETE', 'decision': next(calls)}):
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
    with patch.object(f, 'FREEZE', freeze), patch.object(f, 'verify_freeze'), patch.object(f, 'frozen_policies', return_value=nullcontext()), patch.object(f, 'evolve_round', side_effect=RuntimeError('failed')):
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
    from src.skill_evolution.v17 import experience_grouping_v17 as grouping
    directory = tmp_path / 'grouping'
    f.save(directory / 'grouping_request.json', {'request': 'fixed'})
    f.save(directory / 'grouping_attempts.json', [{'attempt': 1}])
    with patch.object(grouping, 'prepare_grouping_request', return_value={'request': 'fixed'}), patch.object(grouping, 'run_experience_grouping', return_value={'groups': []}) as run:
        assert f.resume_grouping(None, scope=None, directory=directory) == {'groups': []}
        run.assert_called_once()
    assert (tmp_path / 'grouping.interrupted-1/grouping_attempts.json').exists()


def test_resume_completed_grouping_does_not_call_model(tmp_path):
    from src.skill_evolution.v17 import experience_grouping_v17 as grouping
    from src.skill_evolution.v17 import experience_grouping_contract_v17 as contract
    directory = tmp_path / 'grouping'
    f.save(directory / 'grouping_request.json', {'request': 'fixed'})
    f.save(directory / 'validated_groups.json', {'groups': [], 'round_id': 'r'})
    from types import SimpleNamespace
    with patch.object(grouping, 'prepare_grouping_request', return_value={'request': 'fixed'}), patch.object(grouping, 'run_experience_grouping') as run, patch.object(contract, 'bind_grouping_result', return_value={'groups': [], 'round_id': 'r'}):
        assert f.resume_grouping(SimpleNamespace(payload={}), scope=None, directory=directory)['round_id'] == 'r'
        run.assert_not_called()


@pytest.mark.parametrize('status', ['REJECTED', 'RUNNING'])
def test_resume_diagnosis_retries_only_once_and_preserves_failure(tmp_path, status):
    from src.skill_evolution.v17 import diagnosis_v17 as diagnosis
    from src.skill_evolution.v17 import diagnosis_prompt_v17 as prompt
    directory = tmp_path / 'g2'
    f.save(directory / 'request.json', {'user_prompt': 'fixed'})
    f.save(directory / 'validation.json', {'status': status})
    with patch.object(prompt, 'build_diagnosis_request', return_value={'user_prompt': 'fixed'}), patch.object(diagnosis, 'run_group_diagnosis', return_value={'status': 'REJECTED'}) as run:
        assert f.resume_diagnosis(None, directory=directory) == {'status': 'REJECTED'}
        run.assert_called_once_with(None, artifact_dir=directory)
    assert f.load(tmp_path / 'g2.attempt-1/validation.json')['status'] == status


def test_resume_valid_diagnosis_revalidates_without_model(tmp_path):
    from src.skill_evolution.v17 import diagnosis_v17 as diagnosis, diagnosis_prompt_v17 as prompt
    from src.skill_evolution.v17 import diagnosis_validation_v17 as validation
    from src.skill_evolution.v15 import information_boundary_v15 as boundary
    directory = tmp_path / 'g1'
    for name, data in [('request', {'user_prompt': 'fixed'}), ('validation', {'status': 'VALID'}), ('response', {'raw_response': '{}', 'finish_reason': 'stop'}), ('validated_diagnosis', {'semantic': {}})]:
        f.save(directory / f'{name}.json', data)
    with patch.object(prompt, 'build_diagnosis_request', return_value={'user_prompt': 'fixed'}), patch.object(validation, 'validate_diagnosis_response'), patch.object(boundary, 'unpack', return_value={'semantic': {}}), patch.object(diagnosis, 'run_group_diagnosis') as run:
        assert f.resume_diagnosis(None, directory=directory)['status'] == 'VALID'
        run.assert_not_called()


def test_extend_completed_campaign_uses_last_accepted_skill(tmp_path):
    from contextlib import nullcontext
    freeze = tmp_path / 'freeze'; freeze.mkdir()
    (freeze / 'S0.md').write_text('S0'); f.save(freeze / 'manifest.json', {})
    output = tmp_path / 'out'; output.mkdir()
    config = {'rounds': 3}
    f.save(output / 'config.json', config)
    (output / 'current_skill.md').write_text('accepted-Skill')
    rounds = [{'round': f'round-{i:02d}', 'retained_skill_sha256': f.digest(b'accepted-Skill'), 'decision': 'ACCEPT'} for i in range(1,4)]
    f.save(output / 'campaign.json', {'status': 'COMPLETE', 'stop_reason': 'ROUND_LIMIT', 'rounds': rounds})
    with patch.object(f, 'FREEZE', freeze), patch.object(f, 'verify_freeze'), patch.object(f, 'frozen_policies', return_value=nullcontext()), patch.object(f, 'evolve_round', return_value=(None, 'NO_UPDATE')) as evolve:
        f.run_campaign(config, output, resume=True, total_rounds=4)
        evolve.assert_called_once_with(config, output/'round-04', 'round-04', 'accepted-Skill')
    assert f.load(output/'config.json') == config
    assert f.load(output/'campaign.json')['rounds'][:3] == rounds
    assert f.load(output/'resume_history.json')[0]['previous_campaign']['status'] == 'COMPLETE'
