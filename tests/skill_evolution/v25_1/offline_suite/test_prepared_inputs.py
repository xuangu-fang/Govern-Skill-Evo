"""Exercise the standalone training and first-test input layouts."""
from pathlib import Path

import pytest

from src.skill_evolution.v25_1 import cli, evolution
from src.skill_evolution.v25_1.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter


def test_prepare_then_bind_the_approved_test_configuration(tmp_path, monkeypatch):
    experiment = tmp_path / 'experiment'
    result = cli.prepare(experiment)
    training = cli.read_config(result['configuration'])
    evaluation = cli.read_config(experiment / 'config/evaluation/config.json')
    assert training['method']['preconditioner_prompt'] == 'v25_1_current_update_evidence_to_behavior_v1'
    assert training['dataset']['metadata_issues'] and not evaluation['dataset']['metadata_issues']
    assert training['test_tasks'] == evaluation['test_tasks']
    assert all(Path(task['input_path']).is_relative_to(cli.ROOT) for task in training['task_items'].values())
    with pytest.raises(ValueError, match='new directory'):
        cli.prepare(experiment)

    campaign = tmp_path / 'campaign'
    campaign.mkdir()
    evolution.save(campaign / 'config.json', training)
    final = campaign / 'final_skill.md'
    final.write_text('Retained synthetic skill')
    monkeypatch.setattr(evolution, 'final_parent', lambda root: final)
    bundle = SpreadsheetBenchAdapter().prepare_evaluation(experiment, campaign)
    assert bundle['skill_text'] == final.read_text()
    assert bundle['actor_config'] == evaluation
    assert [row['id'] for row in bundle['tasks']] == evaluation['test_tasks']
