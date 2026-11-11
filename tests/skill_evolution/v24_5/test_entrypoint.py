import sys

import pytest

from scripts.runs.v24_5 import run_v24_5 as runner
from src.skill_evolution.v24_2.storage import save


@pytest.mark.parametrize('validate_only', [True, False])
def test_archived_or_validate_only_routes_to_v24_4_without_training(tmp_path, monkeypatch, validate_only):
    training, evaluation = tmp_path / 'training', tmp_path / 'test'
    config = training / 'config.json'
    save(config, {'prompt_revision': 'v24.5', 'method': runner.campaign.VERSION})
    if not validate_only:
        save(evaluation / 'summary.json', {'status': 'complete'})
    args = ['run_v24_5', '--config', str(config), '--campaign', str(training), '--evaluation', str(evaluation)]
    if validate_only:
        args.append('--validate-only')
    monkeypatch.setattr(sys, 'argv', args)
    commands = []
    monkeypatch.setattr(runner.subprocess, 'run', lambda cmd, *, check: commands.append(cmd))
    monkeypatch.setattr(runner.campaign, 'prepare', lambda *_: pytest.fail('Unexpected training'))

    runner.main()

    assert commands == [[sys.executable, str(runner.TEST), '--campaign', str(training),
                         '--evaluation', str(evaluation), '--validate-only' if validate_only else '--resume']]
    assert not (training / 'launch').exists()
