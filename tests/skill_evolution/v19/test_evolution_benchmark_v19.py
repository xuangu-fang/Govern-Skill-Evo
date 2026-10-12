import json
from pathlib import Path

import pytest

from src.skill_evolution.v19.evolution_benchmark_v19 import BenchmarkEvolutionV19
from src.skill_evolution.v19.evolution_replay_v19 import ReplayRejected
from src.skill_evolution.v15.information_boundary_v15 import unpack


def test_all_train_environments_preflight_without_model_or_global_policy_patch(tmp_path, monkeypatch):
    from tau2.orchestrator.orchestrator import Orchestrator
    from tau2.environment.environment import Environment
    monkeypatch.setattr(Orchestrator, 'run', lambda _: pytest.fail('preflight must not execute'))
    get_policy = Environment.get_policy
    backend = BenchmarkEvolutionV19()
    manifest = backend.manifest()
    assert len(manifest['task_ids']) == 36 and not any(t.startswith('CTRL-') for t in manifest['task_ids'])
    result = backend.preflight(artifact_dir=tmp_path / 'preflight', skills=(backend._initial_skill, '', '- Added rule.\n'))
    assert result == {'status': 'PREFLIGHT', 'task_count': 36, 'prepared_instances': 108, 'model_calls': 0}
    assert Environment.get_policy is get_policy
    audit = json.loads((tmp_path / 'preflight/preflight.json').read_text())
    assert len(audit['checks']) == 108
    for i in range(0, 108, 3):
        roles = audit['checks'][i:i+3]
        for key in ('initial_db_sha256', 'visible_view_sha256', 'user_prompt_sha256', 'execution_config_sha256'):
            assert len({r[key] for r in roles}) == 1


def test_monitor_task_rejected_before_construction(tmp_path):
    backend = BenchmarkEvolutionV19()
    monitor = backend.registry.task_ids('monitor')[0]
    with pytest.raises(ReplayRejected, match='forbidden'):
        backend.prepare(monitor, '', tmp_path / 'monitor')
    assert not (tmp_path / 'monitor').exists()
    with pytest.raises(ReplayRejected):
        backend.evaluate(monitor, initial_db={}, final_db={}, simulation={})


def test_deployed_skill_mutation_fails_before_run(tmp_path, monkeypatch):
    from tau2.orchestrator.orchestrator import Orchestrator
    monkeypatch.setattr(Orchestrator, 'run', lambda _: pytest.fail('must fail before run'))
    backend = BenchmarkEvolutionV19()
    prepared = backend.prepare(backend.manifest()['task_ids'][0], '- Added rule.\n', tmp_path)
    assert unpack(prepared.visible_view, 'AGENT_VISIBLE_VIEW')['visible_policy']
    (tmp_path / 'deployed_skill.md').write_text('changed')
    with pytest.raises(ReplayRejected, match='Skill changed'): prepared.run()


def test_in_memory_backend_config_cannot_drift():
    backend = BenchmarkEvolutionV19()
    backend._config['seed'] += 1
    with pytest.raises(ReplayRejected, match='changed after construction'): backend.manifest()


def test_preparation_run_and_evaluation_adapter_with_local_stub(tmp_path, monkeypatch):
    from tau2.orchestrator.orchestrator import Orchestrator
    from types import SimpleNamespace
    backend = BenchmarkEvolutionV19()
    task_id = backend.manifest()['task_ids'][0]
    seen = []
    def run(orchestrator):
        seen.append((orchestrator.task.id, orchestrator.seed, orchestrator.agent.__class__.__name__))
        return SimpleNamespace(model_dump=lambda **_: {'task_id': orchestrator.task.id,
                  'seed': orchestrator.seed, 'messages': [{'role': 'user', 'content': 'test'}]})
    monkeypatch.setattr(Orchestrator, 'run', run)
    prepared = backend.prepare(task_id, '- Added rule.\n', tmp_path)
    simulation, final = prepared.run()
    assert seen == [(task_id, 200, 'ManualSkillAgent')]
    assert final == prepared.initial_db
    def evaluate(task_id, **kwargs):
        assert kwargs == {'initial_db': prepared.initial_db, 'final_db': final, 'simulation': simulation}
        return {'success': False, 'compliant': True}
    monkeypatch.setattr(backend.evaluator, 'evaluate', evaluate)
    assert backend.evaluate(task_id, initial_db=prepared.initial_db, final_db=final, simulation=simulation) == {'success': False, 'compliant': True}
