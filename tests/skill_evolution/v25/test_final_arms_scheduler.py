from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/runs'))
import run_spreadsheetbench_final_arms as app


@pytest.mark.parametrize('arm,dependency', [('v25', 'no_skill'), ('skilladam', 'initial_skill')])
def test_each_arm_waits_for_its_own_baseline_and_uses_new_validation(tmp_path, arm, dependency):
    skill = tmp_path / 'final.md'; skill.write_text('final retained skill')
    app.ev.save(tmp_path / f'{arm}.json', {'arm': arm, 'actor_skill': str(skill)})
    calls = []; cfg = {'task_items': {'test:a': {'id': 'test:a'}}}
    def verify(root, name, config): calls.append(('verify', name))
    def run_arm(root, shared, row, config, *, resume, runner):
        calls.append(('start', row['arm']))
        runner('test:a', skill, tmp_path / 'task', config)
        return {'completed': 280, 'success': 200}
    with patch.object(app, 'verify_complete', side_effect=verify), \
         patch.object(app, 'prerequisite_state', side_effect=['waiting', 'complete']) as ready, \
         patch.object(app.time, 'sleep') as sleep, \
         patch.object(app.queue, 'run_arm', side_effect=run_arm), \
         patch.object(app.validation.actor, 'run') as actor:
        app.lane(tmp_path, tmp_path, cfg, arm, False)
        assert calls == [('verify', dependency), ('start', arm)]
        assert actor.call_args.args[1] == 'final retained skill'
        assert actor.call_args.kwargs['execute'] is app.validation.execute_checked
        assert ready.call_count == (2 if arm == 'skilladam' else 0)
        assert sleep.call_count == (1 if arm == 'skilladam' else 0)


def test_interrupted_initial_blocks_skilladam(tmp_path):
    with patch.object(app, 'prerequisite_state', return_value='blocked'), \
         patch.object(app.queue, 'run_arm') as run_arm:
        with pytest.raises(ValueError, match='Initial Skill stopped'):
            app.lane(tmp_path, tmp_path, {}, 'skilladam', False)
        run_arm.assert_not_called()
        assert app.ev.read(tmp_path / 'skilladam_progress.json')['status'] == 'stopped'
