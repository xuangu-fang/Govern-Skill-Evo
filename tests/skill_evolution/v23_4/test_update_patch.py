from copy import deepcopy
import json
import re

import pytest

from src.skill_evolution.v23.editor import actual_diff
from src.skill_evolution.v23_3.memory_view import FORMAT, LEGACY
from src.skill_evolution.v23_4.update_patch import normalize_update_patches as normalize
from src.skill_evolution.v23_4.preconditioner import PROMPT_PATH
from .helpers import keep, memory, revise, withdraw


def test_keep_is_original_plan_and_deep_copy(payload):
    raw = keep(payload)
    before = deepcopy((raw, payload))
    legacy, effective = normalize(raw, payload)
    assert legacy["decision"] == "ready" and legacy["adjustments"] == []
    assert effective == payload["plan"]
    effective["updates"][0]["basis"].append("local mutation")
    legacy["checks"].clear()
    assert (raw, payload) == before


@pytest.mark.parametrize("view", [FORMAT, LEGACY])
def test_history_basis_order_and_simultaneous_patches(payload, view):
    payload["memory"] = memory(payload)
    raw = keep(payload)
    raw["adjustments"][0] = revise(payload)
    raw["adjustments"][0]["reason"] = "`M1` with `R1/diff` and `R1/P1:1` motivates `P2:1` exploration alongside `u2`; `M1` is not causal proof."
    raw["adjustments"][2] = revise(payload, 2, "Keep productive alternatives available.")
    raw["adjustments"][2]["focus"] = ["D", "C"]
    raw["adjustments"].reverse()
    before = deepcopy((raw, payload))
    legacy, effective = normalize(raw, payload, memory_view=view)
    assert [a["from"] for a in legacy["adjustments"]] == [["u1"], ["u3"]]
    assert legacy["adjustments"][0]["basis"] == ["G1", "P1:1", "M1", "P2:1"]
    assert "R1/P1:1" in legacy["adjustments"][0]["reason"]
    assert "change=" in legacy["adjustments"][0]["reason"]
    assert [u["id"] for u in effective["updates"]] == ["u1", "u2", "u3"]
    assert effective["updates"][0]["basis"] == payload["plan"]["updates"][0]["basis"]
    assert effective["updates"][1] == payload["plan"]["updates"][1]
    assert effective["updates"][2]["text"] == "Keep productive alternatives available."
    assert (raw, payload) == before
    raw["adjustments"].reverse()
    assert normalize(raw, payload, memory_view=view) == (legacy, effective)


@pytest.mark.parametrize("all_withdrawn", [False, True])
def test_withdrawal_checks_must_be_resolved(payload, all_withdrawn):
    raw = keep(payload)
    raw["adjustments"][0] = withdraw("u1")
    if all_withdrawn:
        raw["adjustments"] = [withdraw(u["id"]) for u in payload["plan"]["updates"]]
    with pytest.raises(ValueError):
        normalize(raw, payload)
    raw["checks"] = []
    legacy, effective = normalize(raw, payload)
    assert legacy["decision"] == ("no_change" if all_withdrawn else "ready")
    assert effective is None if all_withdrawn else [u["id"] for u in effective["updates"]] == ["u2", "u3"]
    payload["plan"]["checks"] = []
    raw["checks"] = None
    assert normalize(raw, payload) == (legacy, effective)


@pytest.mark.parametrize("kind", [
    "top_decision", "top_reason", "from", "nested", "basis", "extra", "missing", "duplicate", "unknown_target",
    "target_object", "focus_string", "focus_duplicate", "focus_unknown", "focus_object", "keep_focus",
    "keep_array", "keep_patch", "nonkeep_null", "nonkeep_empty_focus", "to_false", "to_empty_string",
    "to_empty_object", "to_nonempty_array", "to_id", "to_text", "reason_empty", "change_empty",
    "checks_object", "check_extra", "check_unknown", "check_duplicate", "check_empty_links",
])
def test_contract_rejections(payload, kind):
    raw = keep(payload)
    a = raw["adjustments"][0]
    if kind == "top_decision": raw["decision"] = "ready"
    elif kind == "top_reason": raw["reason"] = "redundant"
    elif kind in ("from", "nested", "basis", "extra"):
        a[{"nested": "transformations"}.get(kind, kind)] = []
    elif kind == "missing": raw["adjustments"].pop()
    elif kind == "duplicate": raw["adjustments"].append(deepcopy(a))
    elif kind == "unknown_target": a["target"] = "u99"
    elif kind == "target_object": a["target"] = {"id": "u1", "start_line": 1}
    elif kind.startswith("focus_"):
        a["focus"] = {"focus_string": "D", "focus_duplicate": ["D", "D"],
                      "focus_unknown": ["X"], "focus_object": [{}]}[kind]
    elif kind == "keep_focus": a["focus"] = ["D"]
    elif kind == "keep_array": a["to"] = []
    elif kind == "keep_patch": a["to"] = revise(payload)["to"]
    elif kind == "nonkeep_null": a.update(change="Revise.", focus=["D"])
    elif kind == "nonkeep_empty_focus": a.update(change="Revise.", to=[])
    elif kind.startswith("to_"):
        a.update(revise(payload))
        a["to"] = {"to_false": False, "to_empty_string": "", "to_empty_object": {},
                   "to_nonempty_array": [{"patch": "..."}], "to_id": {"id": "u1", **a["to"]},
                   "to_text": {"text": "new text"}}[kind]
    elif kind == "reason_empty": a["reason"] = " "
    elif kind == "change_empty": a["change"] = " "
    elif kind == "checks_object": raw["checks"] = {}
    else:
        raw["checks"] = deepcopy(payload["plan"]["checks"])
        check = raw["checks"][0]
        if kind == "check_extra": check["extra"] = True
        elif kind == "check_unknown": check["update_ids"] = ["u99"]
        elif kind == "check_duplicate": raw["checks"].append(deepcopy(check))
        elif kind == "check_empty_links": check["update_ids"] = []
    with pytest.raises(ValueError):
        normalize(raw, payload)


@pytest.mark.parametrize("citation", ["`M99`", "`R1/P1:10`", "`R1/P1:1-2`", "`P1:1 P2:1`", "`u99`",
                                       "`made_up`", "`P1:1", "``P1:1``", "M99", "R9/diff", "Q99:1",
                                       "M1", "P1:1", "R1/P1:1"])
def test_keep_reasons_cannot_bypass_reference_validation(payload, citation):
    payload["memory"] = memory(payload)
    raw = keep(payload)
    raw["adjustments"][0]["reason"] = "Preserve because " + citation
    with pytest.raises(ValueError):
        normalize(raw, payload)


@pytest.mark.parametrize("mode", ["keep", "revise", "replace", "remove"])
def test_reason_can_discuss_original_and_replacement_checks_without_evidence_basis(payload, mode):
    raw = keep(payload)
    original_id = payload["plan"]["checks"][0]["id"]
    if mode != "keep":
        raw["adjustments"][0] = revise(payload)
    raw["adjustments"][0]["reason"] = f"Current `P1:1` motivates this decision; retain Check `{original_id}`."
    if mode == "replace":
        raw["checks"] = [{"id": "c_new", "update_ids": ["u1"], "question": "Is exact target identification preserved?"}]
        raw["adjustments"][0]["reason"] = f"Current `P1:1` motivates replacing `{original_id}` with `c_new`."
    elif mode == "remove":
        raw["checks"] = []
        raw["adjustments"][0]["reason"] = f"Current `P1:1` motivates removing Check `{original_id}`."
    before = deepcopy((raw, payload))
    legacy, effective = normalize(raw, payload)
    assert effective["updates"][0]["basis"] == payload["plan"]["updates"][0]["basis"]
    assert all(a["basis"] == payload["plan"]["updates"][0]["basis"] for a in legacy["adjustments"])
    assert (raw, payload) == before


@pytest.mark.parametrize("kind", ["undeclared", "duplicate", "dangling", "collision"])
def test_check_citations_do_not_bypass_check_validation(payload, kind):
    raw = keep(payload)
    raw["adjustments"][0]["reason"] = "Retain `c_new` for observation; current `P1:1` motivates the proposal."
    if kind != "undeclared":
        raw["checks"] = [{"id": "c_new", "update_ids": ["u1"], "question": "Does task progress improve?"}]
        if kind == "duplicate": raw["checks"] *= 2
        elif kind == "dangling": raw["checks"][0]["update_ids"] = ["u99"]
        else: raw["checks"].append({**raw["checks"][0], "id": "u1"})
    with pytest.raises(ValueError): normalize(raw, payload)


@pytest.mark.parametrize("old_lf", [False, True])
@pytest.mark.parametrize("new_lf", [False, True])
def test_update_patch_preserves_exact_eof_boundary(payload, old_lf, new_lf):
    payload["plan"]["updates"][0]["text"] = "Old rule." + ("\n" if old_lf else "")
    replacement = "New rule." + ("\n" if new_lf else "")
    raw = keep(payload)
    raw["adjustments"][0] = revise(payload, replacement=replacement)
    assert normalize(raw, payload)[1]["updates"][0]["text"] == replacement
    if not old_lf:
        raw["adjustments"][0]["to"]["patch"] = raw["adjustments"][0]["to"]["patch"].replace(
            "\\ No newline at end of file\n", "", 1)
        with pytest.raises(ValueError, match="Parent context/deletion text differs"):
            normalize(raw, payload)


def test_prompt_eof_json_example_applies_exactly(payload):
    examples = [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", PROMPT_PATH.read_text(), re.S)]
    patch, = [example for example in examples if isinstance(example, str)]
    payload["plan"]["updates"][0]["text"] = "Old rule."
    raw = keep(payload)
    raw["adjustments"][0] = revise(payload, replacement="New rule.")
    raw["adjustments"][0]["to"]["patch"] = patch
    assert normalize(raw, payload)[1]["updates"][0]["text"] == "New rule."


@pytest.mark.parametrize("field", ["change", "patch", "check"])
def test_unavailable_refs_outside_reason(payload, field):
    raw = keep(payload)
    raw["adjustments"][0] = revise(payload)
    if field == "change": raw["adjustments"][0]["change"] += " R9/Q1:1"
    elif field == "patch": raw["adjustments"][0] = revise(payload, replacement="Based on M99, inspect everything.")
    else:
        raw["checks"] = [{"id": "c2", "update_ids": ["u1"], "question": "Does R9/diff support it?"}]
    with pytest.raises(ValueError):
        normalize(raw, payload)


@pytest.mark.parametrize("kind", ["wrong_context", "wrong_header", "empty", "unchanged", "blank_result", "truncated"])
def test_patch_errors_are_not_keep_and_do_not_mutate(payload, kind):
    raw = keep(payload)
    raw["adjustments"][0] = revise(payload)  # A valid earlier patch must not escape.
    a = revise(payload, 2)
    raw["adjustments"][2] = a
    patch = a["to"]["patch"]
    if kind == "wrong_context": patch = patch.replace("Use visible available alternatives.", "Different original.")
    elif kind == "wrong_header": patch = patch.replace("a/SKILL.md", "a/OTHER.md")
    elif kind == "empty": patch = ""
    elif kind == "unchanged": patch = "--- a/SKILL.md\n+++ b/SKILL.md\n"
    elif kind == "blank_result": patch = actual_diff(payload["plan"]["updates"][2]["text"], " \n")
    elif kind == "truncated": patch = patch[:-10]
    a["to"]["patch"] = patch
    before = deepcopy((raw, payload))
    with pytest.raises(ValueError):
        normalize(raw, payload)
    assert (raw, payload) == before


def test_checks_only_and_semantic_limit(payload):
    raw = keep(payload)
    raw["checks"] = [{"id": "c2", "update_ids": ["u2"], "question": "Is target information retained?"}]
    _, effective = normalize(raw, payload)
    assert effective["updates"] == payload["plan"]["updates"]
    assert effective["checks"] == raw["checks"]
    # This deliberately mismatched content is structurally valid. Passing is NOT
    # a claim that the new stopping restriction was authorized by change/reason.
    raw["adjustments"][0] = revise(payload, replacement="Search every category before stopping.\n")
    _, effective = normalize(raw, payload)
    assert effective["updates"][0]["text"] == "Search every category before stopping.\n"


def test_trace_citation_is_visible_without_implying_detailed_state_support(payload):
    payload["memory"] = memory(payload)
    run = payload["memory"]["sources"]["R1/P1"]["run"]
    step = deepcopy(run["steps"][0])
    state = deepcopy(run["initial"])
    # Extend a synthetic nonterminal run beyond the citation window at step 1.
    run["steps"] = [{**deepcopy(step), "step": f"P1:{i}", "before": deepcopy(state),
                     "after": deepcopy(state), "feedback": {"done": False, "won": False}}
                    for i in range(1, 9)]
    run["outcome"] = {"status": "step_limit", "success": False, "end_reason": "step_limit"}
    from src.skill_evolution.v23_3.memory_view import project_payload
    visible = project_payload(payload)["memory"]["sources"]["R1/P1"]
    assert "R1/P1:8" in {s["step"] for s in visible["run"]["trace"]}
    assert "R1/P1:8" not in {s["step"] for s in visible["detailed_steps"]}
    raw = keep(payload)
    raw["adjustments"][0]["reason"] = "`M1` and `R1/P1:8` supply trace feedback, not detailed state; retain pending validation."
    assert normalize(raw, payload)[1] == payload["plan"]
    raw["adjustments"][0]["reason"] = "Unknown step `R1/P1:9`."
    with pytest.raises(ValueError): normalize(raw, payload)
