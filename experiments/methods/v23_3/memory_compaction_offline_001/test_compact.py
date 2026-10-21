from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from experiments.methods.v23_3.memory_compaction_offline_001.compact import (
    compact_memory, restore_complete_memory, validate_view,
)
from src.skill_evolution.v23.memory import validate_memory


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline tests must not access the network")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def memory_with(refs=("P1:4",), n=10):
    initial = {"observation": "initial state", "commands_ref": "C1"}
    steps, before = [], initial
    for i in range(1, n + 1):
        after = {"observation": f"state after {i}", "commands_ref": "C1"}
        steps.append({"step": f"P1:{i}", "before": deepcopy(before),
                      "action": f"action {i}", "after": after,
                      "feedback": {"reward": 0.0, "done": False, "won": False,
                                   "action_in_admissible_commands": False, "fallback": None}})
        before = after
    return {
        "entries": [{"id": "M1", "knowledge": "Conditional observation, not a proven causal law.",
                     "evidence": ["R1/diff", *[f"R1/{ref}" for ref in refs]]}],
        "sources": {
            "R1/diff": {"parent": "original guidance", "diff": "actual edit",
                        "execution_context": {"history_window": 2}},
            "R1/P1": {
                "run": {"ref": "P1", "task": "original task", "initial": initial,
                        "steps": steps, "outcome": {"status": "step_limit", "success": False,
                                                  "end_reason": "step_limit"}},
                "command_sets": {"C1": ["look", "go to cabinet 1"]},
            },
        },
    }


def test_exact_window_and_all_actions_without_mutation():
    original = memory_with()
    before = deepcopy(original)
    view = compact_memory(original)
    source = view["sources"]["R1/P1"]
    assert [(w["start"], w["end"]) for w in source["windows"]] == [(2, 6)]
    assert source["windows"][0]["before"] == original["sources"]["R1/P1"]["run"]["steps"][1]["before"]
    assert len(source["run"]["trace"]) == 10
    assert source["omitted_detail_ranges"] == [[1, 1], [7, 10]]
    assert source["detail_coverage"] == "partial"
    assert validate_view(view, original)["detailed_steps"] == 5
    assert original == before
    with pytest.raises(ValueError, match="Cannot restore"):
        restore_complete_memory(view)
    with pytest.raises(ValueError):
        validate_memory(view)  # Deliberately distinct from the full archive contract.


@pytest.mark.parametrize("refs,expected", [
    (("P1:1",), [(1, 3)]),
    (("P1:10",), [(8, 10)]),
    (("P1:0",), [(1, 2)]),
    (("P1:3", "P1:6"), [(1, 8)]),
    (("P1:1", "P1:10"), [(1, 3), (8, 10)]),
    (("P1:4", "P1:outcome"), [(2, 6)]),
    (("P1",), [(1, 10)]),
    (("P1:outcome",), [(1, 10)]),
])
def test_boundaries_merging_and_unlocalized_fallback(refs, expected):
    original = memory_with(refs)
    view = compact_memory(original)
    source = view["sources"]["R1/P1"]
    assert [(w["start"], w["end"]) for w in source["windows"]] == expected
    validate_view(view, original)
    if refs in (("P1",), ("P1:outcome",)):
        assert source["detail_reason"] == "unlocalized_reference"
        assert restore_complete_memory(view) == original


def test_shared_references_union_and_same_c_id_different_contexts():
    original = memory_with(("P1:2",))
    original["entries"].append({"id": "M2", "knowledge": "Another observation",
                               "evidence": ["R1/diff", "R1/P1:9", "R2/diff", "R2/P1:2"]})
    original["sources"]["R2/diff"] = deepcopy(original["sources"]["R1/diff"])
    original["sources"]["R2/P1"] = deepcopy(original["sources"]["R1/P1"])
    original["sources"]["R2/P1"]["command_sets"]["C1"] = ["open cabinet 1"]
    view = compact_memory(original)
    assert len(view["sources"]) == 4
    assert len(view["command_pool"]) == 2
    one, two = view["sources"]["R1/P1"], view["sources"]["R2/P1"]
    assert one["command_sets"]["C1"] != two["command_sets"]["C1"]
    assert [(w["start"], w["end"]) for w in one["windows"]] == [(1, 4), (7, 10)]
    validate_view(view, original)


@pytest.mark.parametrize("shared", [False, True])
def test_full_roundtrip_including_unused_menu_and_null_command_reference(shared):
    original = memory_with()
    original["sources"]["R1/P1"]["command_sets"]["unused"] = ["inspect something"]
    original["sources"]["R1/P1"]["run"]["initial"]["commands_ref"] = None
    original["sources"]["R1/P1"]["run"]["steps"][0]["before"]["commands_ref"] = None
    view = compact_memory(original, full=True, shared_menus=shared)
    validate_view(view, original)
    assert restore_complete_memory(view) == original


def test_empty_and_zero_step_memory():
    empty = {"entries": [], "sources": {}}
    view = compact_memory(empty)
    assert validate_view(view, empty)["runs"] == 0
    assert restore_complete_memory(view) == empty
    original = memory_with(("P1:0",), n=0)
    view = compact_memory(original)
    assert validate_view(view, original)["detailed_steps"] == 0
    assert restore_complete_memory(view) == original


@pytest.mark.parametrize("mutation", [
    "action", "feedback", "outcome", "boundary", "after", "menu", "knowledge",
    "source_missing", "window_missing", "false_complete", "omission", "duplicate_step",
])
def test_reject_corrupted_projection(mutation):
    original = memory_with()
    view = compact_memory(original)
    source = view["sources"]["R1/P1"]
    if mutation == "action": source["run"]["trace"][0]["action"] = "invented action"
    if mutation == "feedback": source["run"]["trace"][0]["feedback"]["won"] = True
    if mutation == "outcome": source["run"]["outcome"]["success"] = True
    if mutation == "boundary": source["windows"][0]["before"]["observation"] = "invented state"
    if mutation == "after": source["windows"][0]["after"][0]["observation"] = "invented state"
    if mutation == "menu": view["command_pool"]["menu_1"].append("invented action")
    if mutation == "knowledge": view["entries"][0]["knowledge"] = "rewritten summary"
    if mutation == "source_missing": del view["sources"]["R1/diff"]
    if mutation == "window_missing": source["windows"] = []
    if mutation == "false_complete": source["detail_coverage"] = "complete"
    if mutation == "omission": source["omitted_detail_ranges"] = []
    if mutation == "duplicate_step": source["run"]["trace"].append(source["run"]["trace"][0])
    with pytest.raises(ValueError):
        validate_view(view, original)


def test_reject_invalid_input_before_conversion():
    original = memory_with()
    original["sources"]["R1/P1"]["run"]["steps"][2]["before"]["observation"] = "broken chain"
    with pytest.raises(ValueError, match="continuity"):
        compact_memory(original)
    with pytest.raises(ValueError, match="radius"):
        compact_memory(memory_with(), radius=-1)


@pytest.mark.parametrize("round_id,attempt", [("R04", "002"), ("R05", "001"), ("R06", "001")])
def test_real_archives_lossless_roundtrip_and_projection(round_id, attempt):
    root = Path(__file__).resolve().parents[4]
    path = root / "artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds" / round_id
    request = json.loads((path / "preconditioner/attempts" / attempt / "request.json").read_text())
    original = json.loads(request["body"]["messages"][1]["content"])["memory"]
    before = deepcopy(original)
    full = compact_memory(original, full=True)
    assert restore_complete_memory(full) == original
    validate_view(full, original)
    compact = compact_memory(original)
    metrics = validate_view(compact, original)
    assert metrics["detailed_steps"] < metrics["steps"]
    assert original == before
