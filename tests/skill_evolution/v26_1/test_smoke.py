from .support import make, MethodProvider
from src.skill_evolution.v26_1 import evolution, config
from scripts.runs.run_v26_1_campaign import run_training
from src.skill_evolution.v26_1.evaluation import run_test


def test_train_and_test_are_separate(tmp_path):
    method, actor, cfg = make(tmp_path / 'fixture')
    provider = MethodProvider()
    with method.using():
        config.validate_config(cfg, executable=True)
        summary = run_training(tmp_path / 'campaign', cfg, generate=provider)
        assert summary['test_started'] is False
        assert len(actor.requests) == 4
        result = run_test(tmp_path / 'campaign', tmp_path / 'evaluation')
        assert result['completed'] == 2 and result['em'] == 1
