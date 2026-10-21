from copy import deepcopy
import socket

import pytest

from experiments.methods.v23_3.memory_compaction_live_validation_001.probes import (
    build_probe, score_answers,
)
from experiments.methods.v23_3.memory_compaction_live_validation_001.run import (
    OFFLINE, read, production_gate,
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Preflight tests must not access the network")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.mark.parametrize("case,count", [("R05", 11), ("R06", 14)])
def test_questions_and_oracles_from_archived_states(case, count):
    folder = OFFLINE / "cases" / case
    original, compact = read(folder / "original_payload.json"), read(folder / "compact_payload.json")
    before = deepcopy((original, compact))
    questions, answers = build_probe(original, compact, case=case)
    assert len(questions) == len(answers) == count
    assert {q["id"] for q in questions} == set(answers)
    assert score_answers({"answers": answers}, answers)["passed"]
    assert answers["whole_trace"]["countertop2_steps"] == ["Q2:25", "Q2:30", "Q2:36"]
    assert answers["whole_trace"]["countertop3_steps"] == []
    assert answers["coverage"]["detailed_step_count"] == 13
    assert answers["omitted_precondition"]["exact_before_observation"] is None
    assert answers["omitted_precondition"]["recorded_action_in_admissible_commands"] is False
    assert answers["operation_precondition"]["heat_is_listed"] is True
    assert answers["menu_namespaces"]["same_contents"] is False
    assert answers["mixed_response"] == {
        "parent_success": True, "parent_steps": 20, "candidate_success": False, "candidate_steps": 50}
    if case == "R06":
        assert answers["instance_vs_category"] == {
            "parent_location": "countertop 1", "candidate_location": "countertop 2",
            "same_receptacle_type": True}
        assert answers["actual_edit"]["continuation"] == "rather than exhausting or looping over one type"
        assert answers["absence_boundary"]["global_absence_proven"] is False
    assert (original, compact) == before


@pytest.mark.parametrize("value", [
    {"answers": {"q": {"known": 0}}},
    {"answers": {"q": {"known": "false"}}},
    {"answers": {}},
    {"answers": {"q": {"known": False}, "extra": {}}},
    {"answers": {"q": {"known": False}}, "reasoning": "unrequested"},
    {"q": {"known": False}},
])
def test_strict_grading_does_not_accept_wrong_types_missing_or_extra_answers(value):
    assert not score_answers(value, {"q": {"known": False}})["passed"]


@pytest.mark.parametrize("a,b,expected", [
    ("probe_passed", "probe_passed", True),
    ("probe_passed", "probe_failed", False),
    ("failed", "probe_passed", False),
    ("probe_passed", "compiled", False),
])
def test_production_gate(a, b, expected):
    assert production_gate({"R05": {"status": a}, "R06": {"status": b}}) is expected
    assert production_gate({}) is False
