from copy import deepcopy
import socket

import pytest

from experiments.methods.v23_3.memory_compaction_v2_validation_001.compact_v2 import explicit_view, validate_explicit
from experiments.methods.v23_3.memory_compaction_v2_validation_001.offline import V1, OLD_LIVE, read
from experiments.methods.v23_3.memory_compaction_v2_validation_001.probes_v2 import adapted_probe, score_answers


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline tests must not access the network")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def source(case):
    folder = V1 / "cases" / case
    return read(folder / "original_payload.json"), read(folder / "compact_payload.json")


@pytest.mark.parametrize("case", ["R04", "R05", "R06", "P3A_A", "P3A_B"])
def test_same_delivered_facts_and_selection_with_direct_addresses(case):
    original, prior = source(case)
    untouched = deepcopy((original, prior))
    view, aliases = explicit_view(prior["memory"])
    result = validate_explicit(view, original["memory"], prior["memory"], aliases)
    assert result["same_raw_facts_and_resolved_menus_as_v1"]
    assert (original, prior) == untouched
    for key, item in view["sources"].items():
        if "run" not in item:
            continue
        assert "command_sets" not in item
        for detail in item["detailed_steps"]:
            assert detail["step"].startswith(key + ":")
            for state in (detail["before"], detail["after"]):
                assert state["commands_ref"] is None or state["commands_ref"] in view["command_pool"]


def test_failed_v1_state_is_explicit_and_ambiguous_c1_alias_is_removed():
    original, prior = source("R05")
    view, aliases = explicit_view(prior["memory"])
    target = next(s for s in view["sources"]["S1_R03/Q4"]["detailed_steps"]
                  if s["step"] == "S1_R03/Q4:13")
    assert target["before"]["observation"].startswith("You arrive at diningtable 1.")
    assert target["before"]["commands_ref"] == aliases["S1_R03/Q4"]["C136"]
    first = view["sources"]["S1_R01/P1"]["run"]["initial"]["commands_ref"]
    second = view["sources"]["S1_R02/P1"]["run"]["initial"]["commands_ref"]
    assert first != second
    assert len(view["command_pool"][first]) == 13
    assert len(view["command_pool"][second]) == 12


@pytest.mark.parametrize("case,count", [("R05", 11), ("R06", 14)])
def test_same_questions_facts_and_only_address_adaptation(case, count):
    original, prior = source(case)
    view, _ = explicit_view(prior["memory"])
    payload = {**original, "memory": view}
    questions, answers, changes = adapted_probe(original, prior, payload, case=case)
    old = read(OLD_LIVE / "config" / case / "expected.json")
    normalized = deepcopy(answers)
    for qid in ("window_start", "inside_window", "operation_precondition"):
        normalized[qid]["commands_ref"] = old[qid]["commands_ref"]
    assert normalized == old
    assert len(questions) == count
    assert {c["id"] for c in changes if c["question_changed"]} == {
        "menu_namespaces", "operation_precondition"}
    assert score_answers({"answers": answers}, answers)["passed"]
    assert "local command table" not in next(q["question"] for q in questions if q["id"] == "menu_namespaces")
    assert answers["omitted_precondition"]["exact_before_observation"] is None
    assert answers["omitted_after"]["exact_after_observation"] is None
    assert answers["coverage"]["detailed_step_count"] == 13


@pytest.mark.parametrize("corruption", [
    "before", "cross_source_menu", "missing_step", "step_id", "action", "coverage", "pool", "trace",
])
def test_reject_changed_or_misaddressed_facts(corruption):
    original, prior = source("R05")
    view, aliases = explicit_view(prior["memory"])
    item = view["sources"]["S1_R03/Q4"]
    if corruption == "before": item["detailed_steps"][0]["before"]["observation"] = "invented"
    if corruption == "cross_source_menu":
        item["detailed_steps"][0]["before"]["commands_ref"] = aliases["S1_R02/P1"]["C1"]
    if corruption == "missing_step": item["detailed_steps"].pop()
    if corruption == "step_id": item["detailed_steps"][0]["step"] = "S1_R01/Q4:10"
    if corruption == "action": item["detailed_steps"][0]["action"] = "invented action"
    if corruption == "coverage": item["windows"][0]["end"] -= 1
    if corruption == "pool": view["command_pool"]["menu_1"].append("invented action")
    if corruption == "trace": item["run"]["trace"].reverse()
    with pytest.raises(AssertionError):
        validate_explicit(view, original["memory"], prior["memory"], aliases)


@pytest.mark.parametrize("case", ["R05", "R06"])
def test_frozen_probe_parameters_and_no_answer_leak(case):
    from experiments.methods.v23_3.memory_compaction_v2_validation_001.run import request_for
    import json
    prior = read(OLD_LIVE / "config" / case / "request.json")
    cfg = {k: v for k, v in prior["body"].items() if k != "messages"}
    cfg.update(endpoint=prior["endpoint"], timeout_seconds=300)
    req = request_for(case, cfg)
    assert req["timeout"] == [60, 300] and req["max_http_requests"] == 1
    sent = json.loads(req["body"]["messages"][1]["content"])
    assert set(sent) == {"questions", "payload"}
    assert all("command_sets" not in source for source in sent["payload"]["memory"]["sources"].values()
               if "run" in source)
