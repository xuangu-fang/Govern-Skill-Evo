"""Ensure runtime routing cannot escape the canonical tree or change run flags."""
from pathlib import Path

import pytest

from scripts import run_method
from src.skill_evolution.shared.experiment_paths import ROOT, resolve_experiment_path


def test_older_flat_identity_resolves_to_same_run():
    old = ROOT / 'experiments/v18_v4_formal_002'
    expected = ROOT / 'artifacts/methods/v18/formal/v18_v4_formal_002'
    assert resolve_experiment_path(old) == expected
    assert expected.exists()
    assert not old.exists()


def test_navigation_has_priority_over_runtime_directory_mapping():
    assert resolve_experiment_path('experiments/v17/INDEX.md') == (
        ROOT / 'experiments/methods/v17/runtime-history/INDEX.md')


@pytest.mark.parametrize('name', ['../escape', '/tmp/run', '.', '..', 'a/b', ''])
def test_run_id_cannot_escape_runtime_directory(name):
    with pytest.raises(ValueError, match='single directory'):
        run_method.command_for('v19', name, None, ['run'])


def test_resume_preserves_command_and_selects_existing_stage(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    args = ['resume', '--config', 'relative-config.json']
    command = run_method.command_for('v20', 'v20_test', 'pilot', args)
    assert command[2:-2] == args
    assert command[-2] == '--output'
    assert Path(command[-1]) == run_method.ROOT / 'artifacts/methods/v20/pilot/v20_test'
    assert not (run_method.ROOT / 'artifacts/methods/v20/pilot/v20_test').exists()


@pytest.mark.parametrize('output', [['--output', '/tmp/other'], ['--output=/tmp/other']])
def test_output_override_is_rejected(output):
    with pytest.raises(ValueError, match='run-id'):
        run_method.command_for('v18-v4', 'test', None, output)


def test_print_command_does_not_execute_runner(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError('runner executed')
    monkeypatch.setattr(run_method.subprocess, 'call', forbidden)
    assert run_method.main(['v18-v4', '--run-id', 'test', '--print-command', '--', '--run']) == 0
    assert '--run --output' in capsys.readouterr().out


def test_execution_forwards_exit_status_without_changing_cwd(monkeypatch):
    seen = []
    monkeypatch.setattr(run_method.subprocess, 'call', lambda command: seen.append(command) or 7)
    assert run_method.main(['v19', '--run-id', 'test', '--', 'resume']) == 7
    assert seen[0][2] == 'resume'
