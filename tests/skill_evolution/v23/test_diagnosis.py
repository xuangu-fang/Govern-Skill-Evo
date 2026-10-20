"""Diagnosis contract and recorded handoff tests; no real model requests."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23 import diagnosis
from src.skill_evolution.v23.grouping import load_grouping, messages_for as grouping_messages, run_grouping
from tests.skill_evolution.v23.test_grouping import record
from src.skill_evolution.v23.prompts import execution_context


REAL_GROUPING = Path("artifacts/methods/v23/v23_grouping_001/live")


def make_grouping(root, parent=None):
    directory = root / "grouping"
    result = {"groups": [
        {"group_id": f"G{i}", "members": [f"P{i}"], "decision_problem": "Which location to inspect?",
         "shared_basis": f"P{i}:1 shows an inspection choice.", "important_differences": []}
        for i in (1, 2)]}
    run_grouping([record(1, parent=parent), record(2, parent=parent)], directory, round_id="test_round",
                 generate=lambda *args: {"content": json.dumps(result), "finish_reason": "stop"})
    return directory


def proposal():
    return {"decision": "revise", "reason": "P1:1 and P2:1 expose a concrete inspection choice.",
            "plan": {"goal": "Improve inspection choices while retaining valid completion behavior.",
                     "updates": [{"id": "u1", "text": "When the current observation exposes a closed container relevant to the goal, inspect its contents before treating that location as exhausted.",
                                  "basis": ["G1", "G2", "P1:1", "P2:1"]}],
                     "checks": [{"id": "c1", "update_ids": ["u1"], "question": "Does the relevant container get inspected without abandoning a visible target?"}]}}


def answer(value=None, finish="stop"):
    return {"content": json.dumps(proposal() if value is None else value), "finish_reason": finish,
            "response_model": "offline", "usage": {"total_tokens": 12, "completion_tokens_details": {"reasoning_tokens": 4}}}


@pytest.fixture
def setup(tmp_path):
    path = make_grouping(tmp_path)
    return path, load_grouping(path), tmp_path / "diagnosis"


@pytest.mark.parametrize("decision", ["revise", "no_change", "need_evidence"])
def test_decisions_and_stop_shapes(setup, decision):
    _, saved, _ = setup
    value = proposal() if decision == "revise" else {"decision": decision, "reason": "Specific reason grounded in P1:1.", "plan": None}
    assert diagnosis.validate_diagnosis(value, diagnosis.diagnosis_input(saved)) == value


@pytest.mark.parametrize("parent", [None, "Retain the goal while inspecting available locations."])
def test_exact_shared_input_and_background(tmp_path, parent):
    path = make_grouping(tmp_path, parent)
    saved = load_grouping(path)
    previous = deepcopy(saved)
    payload = diagnosis.diagnosis_input(saved)
    assert set(payload) == {"parent", "command_sets", "runs", "grouping"}
    assert payload["parent"] == parent
    assert {k: payload[k] for k in saved["facts"]} == saved["facts"]
    assert payload["grouping"] == saved["grouping"]
    messages = diagnosis.messages_for(saved)
    assert json.loads(messages[1]["content"]) == payload
    context = execution_context(saved["background"])
    assert context in grouping_messages(saved)[0]["content"]
    assert context.rstrip() in messages[0]["content"]
    assert "{{execution_context}}" not in messages[0]["content"]
    assert "sources" not in payload and "memory" not in payload
    assert saved == previous
    payload["runs"][0]["task"] = "local mutation"
    assert saved == previous


def test_wrong_grouping_analysis_does_not_replace_facts(setup):
    _, saved, _ = setup
    saved["grouping"]["groups"][0]["shared_basis"] = "P1:2 happened before P1:1 and revealed a red dragon."
    payload = json.loads(diagnosis.messages_for(saved)[1]["content"])
    assert "red dragon" in payload["grouping"]["groups"][0]["shared_basis"]
    assert [s["step"] for s in payload["runs"][0]["steps"]] == ["P1:1", "P1:2"]
    assert "red dragon" not in json.dumps(payload["runs"])
    assert "follow the actual events and their order" in diagnosis.messages_for(saved)[0]["content"]


@pytest.mark.parametrize("basis", [["P1:1"], ["P1:0"], ["P1:outcome"], ["P1"],
                                    ["G1", "G2", "P1:1", "P2:1"]])
def test_execution_sources_and_multiple_groups(setup, basis):
    value = proposal()
    value["plan"]["updates"][0]["basis"] = basis
    diagnosis.validate_diagnosis(value, diagnosis.diagnosis_input(setup[1]))


def test_empty_checks_and_partial_coverage_are_allowed(setup):
    value = proposal()
    value["plan"]["checks"] = []
    second = deepcopy(value["plan"]["updates"][0]); second["id"] = "u2"
    value["plan"]["updates"].append(second)
    diagnosis.validate_diagnosis(value, diagnosis.diagnosis_input(setup[1]))
    value["plan"]["checks"] = proposal()["plan"]["checks"]
    diagnosis.validate_diagnosis(value, diagnosis.diagnosis_input(setup[1]))
    value["plan"]["checks"][0]["update_ids"] = ["u1", "u2"]
    diagnosis.validate_diagnosis(value, diagnosis.diagnosis_input(setup[1]))


@pytest.mark.parametrize("kind", [
    "extra_top", "unknown_decision", "empty_reason", "reason_type", "revise_null", "stop_plan",
    "empty_updates", "extra_plan", "empty_goal", "goal_type", "updates_type", "extra_update",
    "duplicate_update", "empty_update_id", "source_id_collision", "empty_text", "text_type",
    "basis_type", "basis_empty", "group_only", "unknown_group", "unknown_event", "range_in_basis",
    "mismatched_group", "unbacked_second_group", "duplicate_basis", "checks_type", "extra_check",
    "duplicate_check", "check_update_collision", "update_ids_unknown", "update_ids_group", "update_ids_empty",
    "update_ids_duplicate", "question_empty", "unknown_text_ref", "unknown_text_group",
])
def test_contract_errors(setup, kind):
    value = proposal(); plan = value["plan"]; update = plan["updates"][0]; check = plan["checks"][0]
    if kind == "extra_top": value["findings"] = []
    elif kind == "unknown_decision": value["decision"] = "maybe"
    elif kind == "empty_reason": value["reason"] = " "
    elif kind == "reason_type": value["reason"] = []
    elif kind == "revise_null": value["plan"] = None
    elif kind == "stop_plan": value["decision"] = "no_change"
    elif kind == "empty_updates": plan["updates"] = []
    elif kind == "extra_plan": plan["issues"] = []
    elif kind == "empty_goal": plan["goal"] = ""
    elif kind == "goal_type": plan["goal"] = None
    elif kind == "updates_type": plan["updates"] = {}
    elif kind == "extra_update": update["direction"] = "D"
    elif kind == "duplicate_update": plan["updates"].append(deepcopy(update))
    elif kind == "empty_update_id": update["id"] = " "
    elif kind == "source_id_collision": update["id"] = "P1"
    elif kind == "empty_text": update["text"] = ""
    elif kind == "text_type": update["text"] = []
    elif kind == "basis_type": update["basis"] = "P1:1"
    elif kind == "basis_empty": update["basis"] = []
    elif kind == "group_only": update["basis"] = ["G1"]
    elif kind == "unknown_group": update["basis"] = ["G9", "P1:1"]
    elif kind == "unknown_event": update["basis"] = ["P1:999"]
    elif kind == "range_in_basis": update["basis"] = ["P1:1-2"]
    elif kind == "mismatched_group": update["basis"] = ["G1", "P2:1"]
    elif kind == "unbacked_second_group": update["basis"] = ["G1", "G2", "P1:1"]
    elif kind == "duplicate_basis": update["basis"] = ["P1:1", "P1:1"]
    elif kind == "checks_type": plan["checks"] = None
    elif kind == "extra_check": check["score"] = 1
    elif kind == "duplicate_check": plan["checks"].append(deepcopy(check))
    elif kind == "check_update_collision": check["id"] = "u1"
    elif kind == "update_ids_unknown": check["update_ids"] = ["u99"]
    elif kind == "update_ids_group": check["update_ids"] = ["G1"]
    elif kind == "update_ids_empty": check["update_ids"] = []
    elif kind == "update_ids_duplicate": check["update_ids"] = ["u1", "u1"]
    elif kind == "question_empty": check["question"] = ""
    elif kind == "unknown_text_ref": value["reason"] += " P99:1"
    elif kind == "unknown_text_group": check["question"] += " G99"
    with pytest.raises(ValueError): diagnosis.validate_diagnosis(value, diagnosis.diagnosis_input(setup[1]))


@pytest.mark.parametrize("decision", ["revise", "no_change", "need_evidence"])
def test_persistence_reuse_and_preconditioner_handoff(setup, decision):
    grouping, saved, output = setup
    original = {p.name: p.read_bytes() for p in grouping.iterdir()}
    calls = []
    value = proposal() if decision == "revise" else {"decision": decision, "reason": "A concrete current-evidence reason.", "plan": None}
    def generate(messages, directory):
        calls.append(messages)
        return answer(value)
    first = diagnosis.run_diagnosis(grouping, output, generate=generate)
    assert diagnosis.run_diagnosis(grouping, output, generate=generate) == first
    assert diagnosis.load_diagnosis(output, expected_grouping=saved) == first
    assert first["diagnosis"] == value
    assert first["facts"] == saved["facts"] and first["sources"] == saved["sources"]
    assert len(calls) == 1
    assert original == {p.name: p.read_bytes() for p in grouping.iterdir()}


@pytest.mark.parametrize("kind", ["malformed", "contract", "truncated", "duplicate_keys", "network", "interrupt"])
def test_failed_attempt_is_archived_without_semantic_stop_or_retry(setup, kind):
    grouping, _, output = setup
    response = answer()
    if kind == "malformed": response["content"] = "not JSON"
    if kind == "contract": response["content"] = json.dumps({"decision": "revise"})
    if kind == "truncated": response["finish_reason"] = "length"
    if kind == "duplicate_keys": response["content"] = '{"decision":"no_change","decision":"revise"}'
    calls = []
    def generate(*args):
        calls.append(1)
        if kind == "network": raise RuntimeError("private network details")
        if kind == "interrupt": raise KeyboardInterrupt()
        return response
    with pytest.raises((ValueError, RuntimeError, KeyboardInterrupt)):
        diagnosis.run_diagnosis(grouping, output, generate=generate)
    assert not (output / "diagnosis.json").exists()
    assert json.loads((output / "validation.json").read_text())["valid"] is False
    assert json.loads((output / "run.json").read_text())["status"] == "invalid"
    if kind not in ("network", "interrupt"):
        assert json.loads((output / "response.json").read_text()) == response
        assert (output / "raw_output.txt").read_text() == response["content"]
    if kind == "contract": assert json.loads((output / "parsed.json").read_text()) == {"decision": "revise"}
    with pytest.raises(ValueError): diagnosis.run_diagnosis(grouping, output, generate=generate)
    assert len(calls) == 1


@pytest.mark.parametrize("change", ["grouping", "facts", "background", "sources", "round_id"])
def test_changed_handoff_prevents_reuse(setup, change):
    grouping, saved, output = setup
    diagnosis.run_diagnosis(grouping, output, generate=lambda *args: answer())
    changed = deepcopy(saved)
    if change == "grouping": changed["grouping"]["groups"][0]["decision_problem"] = "Different choice"
    elif change == "facts": changed["facts"]["parent"] = "Changed Skill"
    elif change == "background": changed["background"]["max_steps"] = 99
    elif change == "sources": changed["sources"][0]["run_id"] = "Different execution"
    else: changed["round_id"] = "r9"
    with pytest.raises(ValueError): diagnosis.load_diagnosis(output, expected_grouping=changed)


@pytest.mark.parametrize("name", ["messages.json", "prompt.md", "diagnosis.json", "parsed.json", "response.json", "run.json"])
def test_saved_artifact_mismatch_rejected(setup, name):
    grouping, _, output = setup
    diagnosis.run_diagnosis(grouping, output, generate=lambda *args: answer())
    p = output / name
    if name == "prompt.md": p.write_text(p.read_text() + "changed")
    else:
        data = json.loads(p.read_text())
        if name == "messages.json": data[0]["content"] += "changed"
        elif name == "response.json": data["content"] = data["content"].replace("inspection choice", "another choice")
        elif name == "run.json": data["grouping_round_id"] = "other"
        else: data["reason"] += "changed"
        p.write_text(json.dumps(data))
    with pytest.raises(ValueError): diagnosis.load_diagnosis(output)


def test_budget_checked_before_call(setup):
    grouping, _, output = setup
    with pytest.raises(ValueError): diagnosis.run_diagnosis(grouping, output, generate=None, max_input_chars=10)
    assert not output.exists()


def test_valid_but_semantically_dubious_text_is_not_heuristically_rewritten(setup):
    value = proposal()
    value["plan"]["updates"][0]["text"] = "Use an impossible persistent memory to remember every room."
    assert diagnosis.validate_diagnosis(value, diagnosis.diagnosis_input(setup[1])) == value


def test_live_generator_http_failure_is_preserved(setup, monkeypatch):
    import requests
    class HTTP:
        status_code = 503
        content = b"service unavailable"
    calls = []
    def post(*args, **kwargs):
        calls.append(1)
        return HTTP()
    monkeypatch.setattr(requests.Session, "post", post)
    generate = diagnosis.live_generator(base_url="https://example.test", key="private", model="test")
    with pytest.raises(ValueError): diagnosis.run_diagnosis(setup[0], setup[2], generate=generate)
    assert (setup[2] / "http_response.txt").read_bytes() == HTTP.content
    assert len(calls) == 1


def test_real_saved_grouping_handoff_without_model_call():
    if not REAL_GROUPING.exists(): pytest.skip("Local historical Grouping artifact is not available")
    legacy = Path("experiments/methods/v23/v23_prompt_alignment_001/config/before/grouping_prompt.md").read_text()
    saved = load_grouping(REAL_GROUPING, legacy_template=legacy)
    payload = diagnosis.diagnosis_input(saved)
    assert len(payload["runs"]) == 4
    assert sum(len(r["steps"]) for r in payload["runs"]) == 93
    assert {g["group_id"] for g in payload["grouping"]["groups"]} == {"G1", "G2"}
    assert {s["task_id"] for s in saved["sources"]} == {f"train:{i:04}" for i in range(12, 16)}
    assert payload["runs"][2]["steps"][9]["step"] == "P3:10"
    assert payload["runs"][2]["steps"][9]["action"] == "go to shelf 4"
    assert "P3:1-P3:17), then extends" in payload["grouping"]["groups"][1]["shared_basis"]
    assert json.loads(diagnosis.messages_for(saved)[1]["content"]) == payload
