"""Synthetic offline cases; real history is checked separately without environment execution."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.adapters.alfworld.actor_prompt import render_messages, visible_commands
from src.adapters.alfworld.run_task_upstream import build_messages, protocol_metadata
from src.adapters.alfworld.skill_runtime import execution_protocol
from src.skill_evolution.v23.facts import build_facts
from src.skill_evolution.v23.grouping import (
    PROMPT_PATH, candidate_groups, live_generator, load_grouping, messages_for,
    run_grouping, validate_grouping,
)
from src.skill_evolution.v22.diagnosis_editor import parse_json_response


def record(number=1, *, status="success", parent=None, menus=None):
    menus = menus or [["help", "look", "look"], ["look", "open cabinet 1"]]
    protocol = execution_protocol(2)
    initial = "A room. Your task is to: inspect the cabinet."
    r = {"run_id": f"synthetic-{number}", "task": {"id": f"train:{number:04}"},
         "skill": {"mode": "none" if parent is None else "fixed", "text": parent},
         "protocol": protocol, "initial_observation": initial,
         "initial_admissible_commands": menus[0], "goal": "inspect the cabinet.",
         "steps": [], "status": status, "won": status == "success"}
    history, observation = [], initial
    for i, menu in enumerate(menus, 1):
        messages = render_messages(observation, menu, r["goal"], history,
                                   **{k: protocol[k] for k in ("system_prompt", "initial_template", "history_template")})
        if parent is not None:
            messages[0]["content"] += protocol["skill_prefix"] + parent + protocol["skill_suffix"]
        action = "look"
        event = {"step": i, "phase": "executed", "messages": messages,
                 "admissible_commands": menu, "action": action,
                 "action_in_admissible_commands": action in menu,
                 "observation": "A closed cabinet.", "reward": float(i == len(menus) and status == "success"),
                 "done": i == len(menus) and status in {"success", "environment_ended"},
                 "won": i == len(menus) and status == "success"}
        r["steps"].append(event)
        history.append({"observation": observation, "action": action})
        observation = event["observation"]
    return r


def result(facts):
    refs = [r["ref"] for r in facts["runs"]]
    return {"groups": [{"group_id": "G1", "members": refs,
                        "decision_problem": "Whether to inspect a closed cabinet before proceeding.",
                        "shared_basis": "Comparable inspection opportunities at " + ", ".join(f"{p}:1" for p in refs),
                        "important_differences": []}]}


def response(facts):
    return {"content": json.dumps(result(facts)), "finish_reason": "stop", "usage": {"total_tokens": 1}}


def test_exact_filter_preserves_content_order_and_duplicates():
    values = ["help", "Help", " help", "help ", "look", "look", "HELP", ""]
    assert visible_commands(values) == values[1:]
    assert values[0] == "help"


def test_actor_uses_shared_renderer_without_behavior_change():
    history = [{"observation": f"obs{i}", "action": "look"} for i in range(4)]
    p = protocol_metadata()
    for h in ([], history):
        expected = render_messages("obs", ["help", "Help", "look", "look"], "goal", h,
                                   **{k: p[k] for k in ("system_prompt", "initial_template", "history_template")})
        assert build_messages("obs", ["help", "Help", "look", "look"], "goal", h) == expected


def test_filtered_menus_share_reference_but_keep_internal_duplicates():
    b = build_facts([record(menus=[["help", "look", "look"], ["look", "look"]])])
    f = b["facts"]
    assert f["command_sets"] == {"C1": ["look", "look"]}
    assert f["runs"][0]["steps"][0]["before"]["commands_ref"] == "C1"
    assert f["runs"][0]["steps"][0]["after"]["commands_ref"] == "C1"


def test_identical_content_has_separate_events_and_no_mutation():
    records = [record(1), record(2)]
    before = deepcopy(records)
    b = build_facts(records)
    assert records == before
    assert [e["step"] for r in b["facts"]["runs"] for e in r["steps"]] == ["P1:1", "P1:2", "P2:1", "P2:2"]
    assert b["sources"][0]["run_id"] != b["sources"][1]["run_id"]


def test_initial_continuity_and_last_missing_menu():
    b = build_facts([record()])
    r = b["facts"]["runs"][0]
    assert r["initial"] == r["steps"][0]["before"]
    assert r["steps"][0]["after"] == r["steps"][1]["before"]
    assert r["steps"][-1]["after"]["commands_ref"] is None
    assert b["sources"][0]["events"][0]["after_menu_source"] == "P1:2:before"


def test_empty_list_is_not_missing_and_legality_uses_environment_menu():
    r = record(menus=[["help"], []])
    r["steps"][0]["action"] = "help"
    r["steps"][0]["action_in_admissible_commands"] = True
    history = [{"observation": r["initial_observation"], "action": "help"}]
    r["steps"][1]["messages"] = build_messages("A closed cabinet.", [], r["goal"], history)
    b = build_facts([r])
    assert b["facts"]["command_sets"] == {"C1": []}
    e = b["facts"]["runs"][0]["steps"][0]
    assert e["before"]["commands_ref"] == "C1"
    assert e["feedback"]["action_in_admissible_commands"] is True
    assert b["sources"][0]["events"][0]["actor_candidate_contains_action"] is False


@pytest.mark.parametrize("status,success", [("success", True), ("environment_ended", False),
    ("step_limit", False), ("interrupted", None), ("error", None), ("unknown", None), ("running", None)])
def test_outcome_distinctions(status, success):
    outcome = build_facts([record(status=status)])["facts"]["runs"][0]["outcome"]
    assert outcome == {"status": status, "success": success, "end_reason": status}


@pytest.mark.parametrize("phase", ["requesting", "responded"])
def test_pending_request_is_not_fabricated_execution(phase):
    r = record(status="error")
    tail = r["steps"][-1]
    tail["phase"] = phase
    for key in ("observation", "reward", "done", "won"):
        tail.pop(key)
    b = build_facts([r])
    assert len(b["facts"]["runs"][0]["steps"]) == 1
    assert b["sources"][0]["pending_step"] == {"step": "P1:2", "phase": phase}
    assert b["facts"]["runs"][0]["steps"][0]["after"]["commands_ref"] is not None


@pytest.mark.parametrize("parent", [None, "Preserve the observed task goal."])
def test_parent_and_background(parent):
    b = build_facts([record(parent=parent)])
    assert b["facts"]["parent"] == parent
    assert set(b["facts"]) == {"parent", "command_sets", "runs"}
    messages = messages_for(b)
    assert '{{max_steps}}' not in messages[0]["content"]
    assert "at most 2 steps" in messages[0]["content"]
    assert "capabilities" not in b["facts"]


@pytest.mark.parametrize("mutation", [
    lambda r: r["initial_admissible_commands"].append("different"),
    lambda r: r["steps"][0]["messages"][1].update(content="changed prompt"),
    lambda r: r["steps"][0].update(observation="different state"),
    lambda r: r["steps"][1].update(step=3),
    lambda r: r["steps"][0].update(done=True),
    lambda r: r["steps"][0].update(action_in_admissible_commands=False),
    lambda r: r["steps"][-1].update(won=False),
    lambda r: r["protocol"].update(history_length=5),
    lambda r: r.update(goal="different goal"),
])
def test_inconsistent_records_rejected(mutation):
    r = record()
    # Separate initially shared fixture lists before testing independent recorded fields.
    r["initial_admissible_commands"] = list(r["initial_admissible_commands"])
    mutation(r)
    with pytest.raises(ValueError):
        build_facts([r])


def test_mixed_parent_and_duplicate_run_rejected():
    for records in ([record(), record()], [record(1), record(2, parent="new")]):
        with pytest.raises(ValueError):
            build_facts(records)


@pytest.mark.parametrize("kind", ["extra_top", "extra_group", "missing_field", "type", "empty", "duplicate_id",
    "duplicate_member", "missing_member", "unknown_member", "unknown_step", "unknown_execution", "missing_step",
    "unknown_menu", "bad_difference"])
def test_invalid_output_is_rejected(kind):
    facts = build_facts([record(1), record(2)])["facts"]
    value = result(facts)
    g = value["groups"][0]
    if kind == "extra_top": value["extra"] = 1
    elif kind == "extra_group": g["extra"] = 1
    elif kind == "missing_field": del g["shared_basis"]
    elif kind == "type": g["members"] = "P1"
    elif kind == "empty": value["groups"] = []
    elif kind == "duplicate_id": value["groups"].append(deepcopy(g))
    elif kind == "duplicate_member": g["members"].append("P1")
    elif kind == "missing_member": g["members"].remove("P2")
    elif kind == "unknown_member": g["members"].append("P9")
    elif kind == "unknown_step": g["shared_basis"] += " P1:99"
    elif kind == "unknown_execution": g["shared_basis"] += " P9:1"
    elif kind == "missing_step": g["shared_basis"] = "P1 and P2 both inspect."
    elif kind == "unknown_menu": g["shared_basis"] += " C999"
    elif kind == "bad_difference": g["important_differences"] = [None]
    with pytest.raises(ValueError):
        validate_grouping(value, facts)


def test_singletons_and_range_citations():
    facts = build_facts([record(1), record(2)])["facts"]
    groups = []
    for i in (1, 2):
        g = result(facts)["groups"][0]
        g.update(group_id=f"G{i}", members=[f"P{i}"], shared_basis=f"P{i}:1–2 show inspection.")
        groups.append(g)
    assert validate_grouping({"groups": groups}, facts)["groups"] == groups
    groups[0]["shared_basis"] = "P1:1–99"
    with pytest.raises(ValueError): validate_grouping({"groups": groups}, facts)


@pytest.mark.parametrize("raw", ['{"groups": [], "groups": []}', 'prefix {"groups": []}', '{"groups": NaN}'])
def test_existing_parser_rejects_bad_json(raw):
    with pytest.raises(ValueError): parse_json_response(raw)


def test_prompt_exactly_matches_approved_document():
    doc = Path("docs/methods/v23/AUTOMATIC_GROUPING_DESIGN.md").read_text()
    approved = "# Grouping" + doc.split("```text\n# Grouping", 1)[1].split("\n```", 1)[0] + "\n"
    assert PROMPT_PATH.read_text() == approved


def test_valid_result_reuse_and_diagnosis_handoff(tmp_path):
    records = [record(1), record(2)]
    expected = response(build_facts(records)["facts"])
    calls = []
    def generate(messages, directory):
        calls.append(messages)
        return expected
    out = tmp_path / "round"
    saved = run_grouping(records, out, round_id="r1", generate=generate)
    assert run_grouping(records, out, round_id="r1", generate=generate) == saved
    assert len(calls) == 1
    assert load_grouping(out) == saved
    assert candidate_groups(saved, ["train:0002", "train:0001"]) == {"train:0002": "G1", "train:0001": "G1"}
    with pytest.raises(ValueError): candidate_groups(saved, ["train:9999"])
    with pytest.raises(ValueError): run_grouping(records, out, round_id="r2", generate=generate)
    changed = deepcopy(records)
    changed[0]["run_id"] = "different-execution"
    with pytest.raises(ValueError): run_grouping(changed, out, round_id="r1", generate=generate)
    assert len(calls) == 1


@pytest.mark.parametrize("kind", ["invalid_json", "invalid_refs", "truncated", "network"])
def test_invalid_response_preserved_and_never_silently_retried(tmp_path, kind):
    records = [record()]
    raw = response(build_facts(records)["facts"])
    if kind == "invalid_json": raw["content"] = "not JSON"
    if kind == "invalid_refs": raw["content"] = raw["content"].replace("P1:1", "P9:1")
    if kind == "truncated": raw["finish_reason"] = "length"
    calls = []
    def generate(messages, directory):
        calls.append(1)
        if kind == "network": raise RuntimeError("private network details")
        return raw
    out = tmp_path / kind
    with pytest.raises((ValueError, RuntimeError)):
        run_grouping(records, out, round_id="r1", generate=generate)
    assert json.loads((out / "validation.json").read_text())["valid"] is False
    if kind != "network":
        assert json.loads((out / "response.json").read_text()) == raw
        assert (out / "raw_output.txt").read_text() == raw["content"]
    assert not (out / "grouping.json").exists()
    with pytest.raises(ValueError): run_grouping(records, out, round_id="r1", generate=generate)
    assert len(calls) == 1


def test_budget_stops_before_request(tmp_path):
    with pytest.raises(ValueError):
        run_grouping([record()], tmp_path / "budget", round_id="r1", generate=None, max_input_chars=10)
    assert not (tmp_path / "budget").exists()


def test_reuse_detects_result_and_prompt_changes(tmp_path):
    records = [record()]
    out = tmp_path / "valid"
    run_grouping(records, out, round_id="r1", generate=lambda *args: response(build_facts(records)["facts"]))
    p = out / "grouping.json"
    value = json.loads(p.read_text()); value["groups"][0]["decision_problem"] = "Altered decision"
    p.write_text(json.dumps(value))
    with pytest.raises(ValueError): load_grouping(out)


def test_single_http_call_archives_raw_response_without_credentials(tmp_path, monkeypatch):
    import requests
    raw = response(build_facts([record()])["facts"])
    payload = {"model": "test-model", "usage": {}, "choices": [{"message": {"content": raw["content"]}, "finish_reason": "stop"}]}
    class HTTP:
        status_code = 200
        content = json.dumps(payload).encode()
        def json(self): return payload
    calls = []
    def post(self, endpoint, **kwargs):
        calls.append(kwargs)
        return HTTP()
    monkeypatch.setattr(requests.Session, "post", post)
    generator = live_generator(base_url="https://example.test/v1", key="private-key", model="test-model")
    out = tmp_path / "live"
    run_grouping([record()], out, round_id="r1", generate=generator)
    assert len(calls) == 1 and calls[0]["allow_redirects"] is False
    assert (out / "http_response.txt").read_bytes() == HTTP.content
    assert all("private-key" not in p.read_text() for p in out.iterdir())


def test_unknown_group_reference_rejected():
    facts = build_facts([record()])["facts"]
    value = result(facts)
    value["groups"][0]["important_differences"] = ["Unlike G99, this case has a cabinet."]
    with pytest.raises(ValueError): validate_grouping(value, facts)


def test_zero_executed_steps_preserve_unknown_outcome():
    r = record(status="interrupted")
    r["steps"] = []
    b = build_facts([r])
    assert b["facts"]["runs"][0]["steps"] == []
    assert b["facts"]["runs"][0]["outcome"]["success"] is None
    value = result(b["facts"])
    value["groups"][0]["shared_basis"] = "P1:0 exposes an initial inspection choice; execution was interrupted."
    validate_grouping(value, b["facts"])


def test_changed_saved_messages_cannot_be_reused(tmp_path):
    records = [record()]
    out = tmp_path / "saved"
    run_grouping(records, out, round_id="r1", generate=lambda *args: response(build_facts(records)["facts"]))
    p = out / "messages.json"
    messages = json.loads(p.read_text()); messages[0]["content"] += "changed"
    p.write_text(json.dumps(messages))
    with pytest.raises(ValueError): load_grouping(out)


def test_http_failure_preserves_body_and_does_not_retry(tmp_path, monkeypatch):
    import requests
    class HTTP:
        status_code = 503
        content = b'provider unavailable'
    calls = []
    def post(self, endpoint, **kwargs):
        calls.append(1)
        return HTTP()
    monkeypatch.setattr(requests.Session, "post", post)
    out = tmp_path / "http_error"
    generator = live_generator(base_url="https://example.test/v1", key="private-key", model="test-model")
    with pytest.raises(ValueError): run_grouping([record()], out, round_id="r1", generate=generator)
    assert len(calls) == 1
    assert (out / "http_response.txt").read_bytes() == HTTP.content
    assert json.loads((out / "validation.json").read_text())["valid"] is False
