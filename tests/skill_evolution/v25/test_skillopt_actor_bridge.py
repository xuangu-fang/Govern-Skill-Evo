"""Synthetic Docker integration; no benchmark rollout or live model request."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/runs'))
import skillopt_spreadsheetbench_actor as worker
from .support import config, response, CODE, PARENT


def test_shared_actor_docker_scoring_and_native_evidence(tmp_path):
    cfg = config(tmp_path / 'data', n=1)
    key = next(iter(cfg['task_items']))
    directory = tmp_path / 'run'
    worker.ev.save(directory / 'input.json', {'shared': cfg, 'task': key, 'skill': PARENT})
    calls = []
    def generate(messages, *args):
        calls.append(messages)
        return response('FORMAT_REPAIR_SENTINEL') if len(calls) == 1 else response('```python\n' + CODE % ' + 1' + '```')
    row = worker.run_task(directory, generate=generate)
    assert row['hard'] == row['soft'] == 1 and row['n_turns'] == 1
    assert row['id'] == key and row['n_cells_match'] == row['n_cells_total'] == 2
    conversation = (directory / 'conversation.json').read_text()
    assert 'FORMAT_REPAIR_SENTINEL' not in conversation
    assert 'post_execution_outcome_not_actor_feedback' in conversation
    assert cfg['task_items'][key]['instruction'] in conversation
    assert cfg['task_items'][key]['answer_path'] not in row['target_user_prompt']
    def forbidden(*args):
        pytest.fail('Completed task was requested again')
    assert worker.run_task(directory, generate=forbidden) == row


def test_generation_exhaustion_does_not_become_a_failed_training_example(tmp_path):
    cfg = config(tmp_path / 'data', n=1)
    cfg['retry_delay_seconds'] = 0
    directory = tmp_path / 'run'
    worker.ev.save(directory / 'input.json', {'shared': cfg, 'task': next(iter(cfg['task_items'])), 'skill': PARENT})
    with pytest.raises(Exception):
        worker.run_task(directory, generate=lambda *args: response('INVALID'))
    assert not (directory / 'native_result.json').exists()
    assert not (directory / 'conversation.json').exists()
