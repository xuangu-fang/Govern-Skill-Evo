from copy import deepcopy
import json
import socket

import pytest

from experiments.methods.v23_3.memory_compaction_v3_validation_001.compact_v3 import (
    explicit_view, validate_explicit,
)
from experiments.methods.v23_3.memory_compaction_v3_validation_001.offline import V1, V2, read
from experiments.methods.v23_3.memory_compaction_v3_validation_001.probes_v3 import adapted_probe, score_answers, STEP_FIELDS


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("Offline tests cannot access network")
    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(socket.socket, "connect", reject)


def inputs(case):
    return (read(V1 / "cases" / case / "original_payload.json"),
            read(V1 / "cases" / case / "compact_payload.json"))


@pytest.mark.parametrize("case", ["R04", "R05", "R06", "P3A_A", "P3A_B"])
def test_all_original_facts_and_global_step_identity(case):
    original, prior = inputs(case)
    untouched = deepcopy(prior)
    view, aliases = explicit_view(prior["memory"])
    result = validate_explicit(view, original["memory"], prior["memory"], aliases)
    assert result["unique_qualified_trace_ids"] == result["steps"]
    assert prior == untouched
    normalized = deepcopy(view)
    normalized["format"] = "memory_evidence_view_v2"
    for source in normalized["sources"].values():
        if "run" in source:
            for row in source["run"]["trace"]:
                row["step"] = row["step"].split("/", 1)[1]
    assert normalized == read(V2 / "cases" / case / "compact_payload.json")["memory"]


def test_cross_source_q6_26_regression():
    _, prior = inputs("R05")
    view, _ = explicit_view(prior["memory"])
    expected = {
        "S1_R02/Q6": ("examine cabinet 4", True),
        "S1_R03/Q6": ("go to cabinet 3", False),
        "S1_R04/Q6": ("examine drawer 8", True),
    }
    for source, (action, legal) in expected.items():
        row = next(r for r in view["sources"][source]["run"]["trace"] if r["step"] == source + ":26")
        assert row["action"] == action
        assert row["feedback"]["action_in_admissible_commands"] is legal


@pytest.mark.parametrize("case,count", [("R05", 11), ("R06", 14)])
def test_same_facts_explicit_contract_and_strict_source_scoring(case, count):
    original, prior = inputs(case)
    view, _ = explicit_view(prior["memory"])
    questions, answers, changes = adapted_probe(original, prior, {**original, "memory": view}, case=case)
    old = read(V2 / "cases" / case / "expected.json")
    normalized = deepcopy(answers)
    assert len(questions) == count
    for qid, (_, fields) in STEP_FIELDS.items():
        for field in fields:
            normalized[qid][field] = [s.split("/", 1)[1] for s in normalized[qid][field]]
        assert "fully qualified" in next(q["question"] for q in questions if q["id"] == qid)
    assert normalized == old
    assert {c["id"] for c in changes if c["answer_changed"]} == set(STEP_FIELDS)
    assert score_answers({"answers": answers}, answers)["passed"]
    for bad_id in ("Q2:25", "S1_R02/Q2:25"):
        bad = deepcopy(answers)
        bad["whole_trace"]["countertop2_steps"][0] = bad_id
        assert not score_answers({"answers": bad}, answers)["passed"]
    bad = deepcopy(answers)
    bad["omitted_precondition"].update(action="examine cabinet 4",
                                      recorded_action_in_admissible_commands=True)
    assert not score_answers({"answers": bad}, answers)["passed"]


@pytest.mark.parametrize("mutation", ["wrong_source", "local", "duplicate", "action", "feedback", "detail"])
def test_reject_wrong_identity_and_changed_facts(mutation):
    original, prior = inputs("R05")
    view, aliases = explicit_view(prior["memory"])
    source = view["sources"]["S1_R03/Q6"]
    row = source["run"]["trace"][25]
    if mutation == "wrong_source": row["step"] = "S1_R02/Q6:26"
    if mutation == "local": row["step"] = "Q6:26"
    if mutation == "duplicate": row["step"] = source["run"]["trace"][24]["step"]
    if mutation == "action": row["action"] = "examine cabinet 4"
    if mutation == "feedback": row["feedback"]["action_in_admissible_commands"] = True
    if mutation == "detail": source["detailed_steps"][0]["step"] = "S1_R02/Q6:2"
    with pytest.raises(AssertionError):
        validate_explicit(view, original["memory"], prior["memory"], aliases)
