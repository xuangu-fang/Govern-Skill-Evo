import json
from pathlib import Path
from unittest.mock import patch
import pytest
from src.skill_evolution import formal_v17 as f


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
    from src.skill_evolution import monitor_v17, monitor_benchmark_v17
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
