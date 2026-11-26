"""Check the baseline used by each downstream Actor and its request subprocess."""
from importlib import import_module
from pathlib import Path

import pytest

from src.skill_evolution.v25_2.cli import EXPERIMENT
from src.skill_evolution.v25_2.benchmarks.spreadsheetbench import actor, scoring, transport


@pytest.mark.parametrize('version', ['v25_3', 'v25_4', 'v25_5'])
def test_baseline_package_and_inputs(version):
    package = import_module(f'src.skill_evolution.{version}')
    assert package.BASELINE == EXPERIMENT / 'config'
    for maintained in (actor, scoring, transport):
        name = maintained.__name__.replace('v25_2.', version + '.baseline.', 1)
        assert Path(import_module(name).__file__).resolve() == Path(maintained.__file__).resolve()
