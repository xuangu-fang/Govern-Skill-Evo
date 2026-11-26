"""Control selection, sequential launch, and fixed Skill isolation."""
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/runs'))
import run_spreadsheetbench_controls as app


def config():
    return app.ev.read(ROOT / 'experiments/methods/v25/v25_full120_timeline_actor32k_w4_20261026_002/config/config.json')


def test_common_test_subset_keeps_original_order_and_pending_tasks():
    cfg = config()
    plan = app.test_plan(cfg)
    assert len(plan['tasks']) == plan['metrics_denominator'] == 277
    assert plan['full_test_count'] == 280
    pending = {row['task_id'] for row in plan['pending_tasks']}
    assert pending == {'test:60-7', 'test:283-32', 'test:73-45'}
    assert plan['tasks'] == [key for key in cfg['test_tasks'] if key not in pending]
    assert set(plan['tasks']).isdisjoint(key for batch in cfg['batches'] for key in batch)


def test_initial_starts_only_after_no_skill_completes(tmp_path):
    cfg = config(); plan = app.test_plan(cfg); events = []
    def arm(root, name, *args, **kwargs):
        events.extend([name + ':start', name + ':complete'])
        return {'completed': 277}
    with patch.object(app, 'check', return_value=(cfg, plan)), patch.object(app, 'run_arm', side_effect=arm):
        result = app.run(tmp_path, runner=object())
    assert events == ['no_skill:start', 'no_skill:complete', 'initial_skill:start', 'initial_skill:complete']
    assert result['status'] == 'selected_subset_complete'
    assert app.ev.read(tmp_path / 'comparison.json')['metrics_denominator'] == 277


def test_interruption_does_not_start_initial_skill(tmp_path):
    cfg = config(); plan = app.test_plan(cfg); arms = []
    def arm(root, name, *args, **kwargs):
        arms.append(name)
        raise RuntimeError('technical interruption')
    with patch.object(app, 'check', return_value=(cfg, plan)), patch.object(app, 'run_arm', side_effect=arm):
        with pytest.raises(RuntimeError):
            app.run(tmp_path, runner=object())
    assert arms == ['no_skill']
    assert app.ev.read(tmp_path / 'progress.json')['status'] == 'stopped'


@pytest.mark.parametrize('arm', ['no_skill', 'initial_skill'])
def test_fixed_skill_passed_to_shared_scheduler(tmp_path, arm):
    cfg = config(); plan = app.test_plan(cfg)
    (tmp_path / 'initial_skill.md').write_text(cfg['initial_skill']['text'])
    rows = [{'task': {'id': key}, 'score': {'hard': 0, 'per_cell_pass_rate': 0},
             'termination': 'valid_workbook_submitted', 'code_attempts': 1} for key in plan['tasks']]
    with patch.object(app.ev, '_actors', return_value=(['/fake'] * 277, rows)) as actors:
        summary = app.run_arm(tmp_path, arm, cfg, plan)
    passed_skill = actors.call_args.args[4]
    assert passed_skill == (tmp_path / 'initial_skill.md' if arm == 'initial_skill' else None)
    assert actors.call_args.args[3] == plan['tasks']
    assert actors.call_args.args[5] == cfg
    assert summary['completed'] == 277 and summary['full_test_count'] == 280


def test_full_test_prepare_freezes_explicit_config_without_campaign(tmp_path):
    from src.skill_evolution.v25 import baseline
    prepared=tmp_path/'prepared';baseline.prepare(prepared)
    cfg=app.ev.read(prepared/'config/campaign.json')
    assert cfg['dataset']['metadata_issues']==[]
    assert cfg['task_items']['test:60-7']['answer_region']=="'Consolidated Tracker'!A3:E11"
    assert cfg['dataset']['scoring_compatibility']['metadata_corrections'][0]['task_id']=='test:60-7'
    root=tmp_path/'controls'
    with patch.object(app.executor,'runtime_snapshot',return_value={'test':'runtime'}),patch.object(app.subprocess,'check_output',return_value='test-image\n'):
        result=app.prepare(root,config_file=prepared/'config/campaign.json')
        checked,plan=app.check(root)
        assert result['tasks_per_arm']==280 and result['pending']==0
        assert plan['scope']=='full_test' and plan['tasks']==cfg['test_tasks']
        assert plan['simultaneous_arms']==1 and checked==cfg
        assert not (root/'progress.json').exists() and not (root/'no_skill').exists()
        modified=dict(cfg,actor_max_workers=1);app.ev.save(root/'config.json',modified)
        with pytest.raises(ValueError,match='Frozen file changed'):app.check(root)
