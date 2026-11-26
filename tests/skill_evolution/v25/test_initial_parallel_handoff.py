from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch, Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/runs'))
import run_spreadsheetbench_initial_parallel as app


def test_reserved_tasks_stop_old_queue_then_are_reused_without_calls(tmp_path):
    folder = tmp_path / 'results/initial_skill'
    tasks = ['test:a', 'test:b']
    for task in tasks:
        (folder / 'episodes' / task.replace(':', '_') / 'attempts/001').mkdir(parents=True)
    adapter = SimpleNamespace(check_record=lambda r, *args: r, is_complete=lambda r: r['complete'])
    runner = Mock()
    with patch.object(app.ev, '_check_contract'), patch.object(app.ev, 'benchmark_current', return_value=adapter):
        with pytest.raises(app.ev.Stopped, match='explicit resume needed'):
            app.ev._actors(tmp_path, folder, 'episodes', tasks, None, {'actor_max_workers': 2}, runner, False)
        runner.assert_not_called()
        def execute(task, skill, dest, config):
            path = dest / 'trajectory.json'; app.ev.save(path, {'complete': True, 'task': task})
            return path
        runner.side_effect = execute
        first = app.ev._actors(tmp_path, folder, 'episodes', tasks, None, {'actor_max_workers': 2}, runner, True)
        assert runner.call_count == 2
        runner.reset_mock()
        second = app.ev._actors(tmp_path, folder, 'episodes', tasks, None, {'actor_max_workers': 2}, runner, False)
        assert second == first
        runner.assert_not_called()


@pytest.mark.parametrize('progress,expected', [
    ({'status': 'running', 'active_arm': 'no_skill'}, 'wait'),
    ({'status': 'running', 'active_arm': 'skilladam'}, 'original_queue_continues'),
    ({'status': 'completed', 'active_arm': None}, 'original_queue_continues'),
    ({'status': 'stopped', 'active_arm': 'initial_skill', 'error_type': 'Stopped'}, 'resume_after_handoff'),
    ({'status': 'stopped', 'active_arm': 'no_skill', 'error_type': 'Stopped'}, 'blocked'),
    ({'status': 'stopped', 'active_arm': 'initial_skill', 'error_type': 'ValueError'}, 'blocked'),
])
def test_resume_only_recognized_queue_handoff(progress, expected):
    assert app.continuation_action(progress) == expected
