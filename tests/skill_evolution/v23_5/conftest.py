import pytest

from src.skill_evolution.v23.preconditioner import preconditioner_input
from src.skill_evolution.v23_5 import diagnosis
from tests.skill_evolution.v23.test_diagnosis import make_grouping
from tests.skill_evolution.v23.test_preconditioner import proposal
from .helpers import Fake


@pytest.fixture
def upstream(tmp_path):
    gd, dd = make_grouping(tmp_path, parent="Preserve the task goal.\n"), tmp_path / "diagnosis"
    value = proposal()
    value["plan"]["updates"][0]["text"] = "Inspect relevant containers.\nPreserve exact target identification.\n"
    saved = diagnosis.run_diagnosis(gd, dd, generate=Fake(value))
    return gd, dd, saved, tmp_path / "preconditioner"


@pytest.fixture
def payload(upstream):
    return preconditioner_input(upstream[2])
