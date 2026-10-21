"""Human P1-R fixtures against existing V23 pure functions; no stage runners."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23 import editor, preconditioner as pc

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FIXTURES = HERE / "fixtures"
HEADER = "--- a/SKILL.md\n+++ b/SKILL.md\n"
MARK = "\\ No newline at end of file\n"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=["R04", "R05", "R06"])
def case(request):
    name = request.param
    sources = read(FIXTURES / "sources.json")["sources"][name]
    original = read(FIXTURES / f"{name}.original.json")
    multiline = read(FIXTURES / f"{name}.multiline.json")
    saved = read(ROOT / sources["facts"])
    saved["diagnosis"] = multiline
    saved["memory"] = read(ROOT / sources["memory"])["memory"]
    return name, original, saved, pc.preconditioner_input(saved)


def formal(payload, updates, checks=None):
    """Build an already-existing Adjustment test input, not the P2 adapter."""
    originals = {u["id"]: u for u in payload["plan"]["updates"]}
    return {
        "decision": "ready",
        "reason": "Human compatibility fixture; semantic effectiveness is not evaluated.",
        "adjustments": [
            {"from": [uid], "to": [{"id": uid, "text": text}],
             "basis": originals[uid]["basis"],
             "reason": "Human-selected change for pure-function compatibility only."}
            for uid, text in updates.items()
        ],
        "checks": checks,
    }


def test_representation_only_changes_text(case):
    name, original, saved, payload = case
    source = read(FIXTURES / "sources.json")["sources"][name]["diagnosis"]
    assert (FIXTURES / f"{name}.original.json").read_bytes() == (ROOT / source).read_bytes()
    restored = deepcopy(saved["diagnosis"])
    for represented, old in zip(restored["plan"]["updates"], original["plan"]["updates"]):
        assert set(represented) == {"id", "text", "basis"}
        assert "\n" not in old["text"]
        assert represented["text"].endswith("\n")
        assert all(line.startswith("- ") for line in represented["text"].splitlines())
        represented["text"] = old["text"]
    assert restored == original
    keep = formal(payload, {})
    assert pc.compile_effective_plan(keep, payload) == saved["diagnosis"]["plan"]


@pytest.mark.parametrize("scenario_name", ["single", "linked", "add", "delete", "broad", "cross"])
def test_patch_compile_and_editor_handoff(case, scenario_name, request):
    name, _, saved, payload = case
    scenario = next(s for s in read(FIXTURES / f"{name}.scenarios.json")["scenarios"]
                    if s["name"] == scenario_name)
    before = deepcopy(payload)
    originals = {u["id"]: u for u in payload["plan"]["updates"]}
    applied = {}
    for uid, patch in scenario["patches"].items():
        applied[uid] = editor.apply_patch(originals[uid]["text"], patch)
        assert applied[uid] == scenario["expected"][uid]
        old_lines = originals[uid]["text"].splitlines(keepends=True)
        new_lines = applied[uid].splitlines(keepends=True)
        for old, new in scenario["preserved_line_pairs"][uid]:
            assert old_lines[old - 1].encode("utf-8") == new_lines[new - 1].encode("utf-8")
        if scenario_name == "linked":
            assert patch.count("@@ -") == 2
        if name == "R05":
            assert "every receptacle type has been sampled once" not in applied[uid]
    result = formal(payload, applied)
    effective = pc.compile_effective_plan(result, payload)
    assert effective["goal"] == payload["plan"]["goal"]
    assert effective["checks"] == payload["plan"]["checks"]
    for update in effective["updates"]:
        assert update == (dict(originals[update["id"]], text=applied[update["id"]])
                          if update["id"] in applied else originals[update["id"]])
    handoff = {**saved, "preconditioner": result, "effective_plan": effective}
    assert editor.editor_input(handoff) == {"parent": payload["parent"], "plan": effective}
    assert json.loads(editor.messages_for(handoff)[1]["content"])["plan"] == effective
    assert payload == before
    request.node.user_properties.append(("compatibility", {
        "kind": "human_design_fixture_not_model_output", "case": name, "scenario": scenario_name,
        "applied_updates": applied, "preserved_line_pairs": scenario["preserved_line_pairs"],
        "goal_preserved": True, "checks_preserved": True, "other_updates_preserved": True,
        "formal_compiler": "passed", "editor_pure_input": "passed",
        "semantic_validity": "not_evaluated", "p2_loader_runner": "not_implemented",
    }))


@pytest.mark.parametrize("failure", [
    "wrong_context", "old_outside", "new_position", "overlap", "truncated", "late_failure"
])
def test_patch_errors_return_no_partial_text(case, failure, request):
    _, _, _, payload = case
    source = payload["plan"]["updates"][0]["text"]
    lines = source.splitlines(keepends=True)
    first = "@@ -1 +1 @@\n-" + lines[0] + "+Human replacement.\n"
    patch = {
        "wrong_context": HEADER + "@@ -1 +1 @@\n-Wrong original.\n+Replacement.\n",
        "old_outside": HEADER + "@@ -999 +999 @@\n-Wrong original.\n+Replacement.\n",
        "new_position": HEADER + first.replace("@@ -1 +1 @@", "@@ -1 +2 @@"),
        "overlap": HEADER + first + first,
        "truncated": HEADER + "@@ -1 +1 @@\n-" + lines[0],
        "late_failure": HEADER + first + "@@ -2 +2 @@\n-Wrong second line.\n+Replacement.\n",
    }[failure]
    returned = None
    with pytest.raises(ValueError) as error:
        returned = editor.apply_patch(source, patch)
    assert returned is None
    assert payload["plan"]["updates"][0]["text"] == source
    request.node.user_properties.append(("expected_rejection", {
        "failure": failure, "error": str(error.value), "partial_return": False
    }))


@pytest.mark.parametrize("format_name", ["lf", "no_final_lf", "crlf", "unicode_spaces"])
def test_case_text_format_preservation(case, format_name):
    _, _, _, payload = case
    text = payload["plan"]["updates"][0]["text"]
    if format_name == "no_final_lf":
        text = text[:-1]
    elif format_name == "crlf":
        text = text.replace("\n", "\r\n")
    elif format_name == "unicode_spaces":
        text += "- 人工 Unicode 检查 🧪  \n"
    # Explicit last-line hunk, exercising EOF framing separately from content.
    lines = editor._lines(text)
    old = lines[-1]
    ending = "\r\n" if old.endswith("\r\n") else "\n" if old.endswith("\n") else ""
    new = "- Human final requirement.  " + ending
    frame = lambda value: value if value.endswith("\n") else value + "\n" + MARK
    patch = HEADER + f"@@ -{len(lines)} +{len(lines)} @@\n-" + frame(old) + "+" + frame(new)
    result = editor.apply_patch(text, patch)
    assert result == "".join(lines[:-1]) + new
    assert result.encode("utf-8").startswith("".join(lines[:-1]).encode("utf-8"))


def test_withdrawal_and_checks_contract(case):
    _, _, saved, payload = case
    uid = payload["plan"]["updates"][0]["id"]
    result = formal(payload, {uid: "unused"})
    result["adjustments"][0]["to"] = []
    with pytest.raises(ValueError, match="check.update_ids"):
        pc.compile_effective_plan(result, payload)
    result["checks"] = [c for c in payload["plan"]["checks"] if uid not in c["update_ids"]]
    effective = pc.compile_effective_plan(result, payload)
    assert effective["goal"] == payload["plan"]["goal"]
    assert effective["updates"] == payload["plan"]["updates"][1:]
    assert editor.editor_input({**saved, "preconditioner": result, "effective_plan": effective})["plan"] == effective
    all_withdrawn = formal(payload, {u["id"]: "unused" for u in payload["plan"]["updates"]}, checks=[])
    for adjustment in all_withdrawn["adjustments"]:
        adjustment["to"] = []
    all_withdrawn["decision"] = "no_change"
    assert pc.compile_effective_plan(all_withdrawn, payload) is None


def test_updated_checks_and_invalid_handoff(case):
    _, _, saved, payload = case
    checks = deepcopy(payload["plan"]["checks"])
    checks[0]["question"] = "Are the changed conditions executable while necessary completion behavior is preserved?"
    result = formal(payload, {}, checks=checks)
    effective = pc.compile_effective_plan(result, payload)
    assert effective["checks"] == checks
    handoff = {**saved, "preconditioner": result, "effective_plan": effective}
    assert editor.editor_input(handoff)["plan"] == effective
    handoff["effective_plan"] = {**effective, "goal": "Unauthorized different Goal"}
    with pytest.raises(ValueError, match="Effective Plan differs"):
        editor.editor_input(handoff)


def test_raw_patch_is_not_a_formal_adjustment(case):
    _, _, _, payload = case
    uid = payload["plan"]["updates"][0]["id"]
    result = formal(payload, {uid: "unused"})
    result["adjustments"][0]["to"] = [{"id": uid, "patch": HEADER}]
    with pytest.raises(ValueError, match="Replacement Update: unexpected fields"):
        pc.compile_effective_plan(result, payload)


def test_insert_replace_delete_in_one_patch(case, request):
    name, _, saved, payload = case
    source = payload["plan"]["updates"][0]["text"]
    lines = source.splitlines(keepends=True)
    added = "- Human independent insertion; semantic approval is not implied.\n"
    replacement = "- Human replacement for mixed-hunk coordinate testing.\n"
    patch = (HEADER + "@@ -1,0 +2 @@\n+" + added
             + "@@ -3 +4 @@\n-" + lines[2] + "+" + replacement
             + "@@ -5 +5,0 @@\n-" + lines[4])
    updated = editor.apply_patch(source, patch)
    assert updated == lines[0] + added + lines[1] + replacement + lines[3] + "".join(lines[5:])
    result = formal(payload, {"u1": updated})
    effective = pc.compile_effective_plan(result, payload)
    assert effective["goal"] == payload["plan"]["goal"]
    assert effective["checks"] == payload["plan"]["checks"]
    assert effective["updates"][1:] == payload["plan"]["updates"][1:]
    assert editor.editor_input({**saved, "preconditioner": result, "effective_plan": effective})["plan"] == effective
    request.node.user_properties.append(("mixed_hunks", {
        "case": name, "patch": patch, "applied_text": updated,
        "kind": "human_coordinate_fixture_not_behavioral_proposal",
    }))


@pytest.mark.parametrize("placement", ["new_line", "inside_replaced_line"])
def test_r05_unsupported_exit_can_still_pass_structure(request, placement):
    # Deliberate negative semantic fixture: the original program must not be
    # credited with understanding whether the inserted requirement is justified.
    sources = read(FIXTURES / "sources.json")["sources"]["R05"]
    saved = read(ROOT / sources["facts"])
    saved["diagnosis"] = read(FIXTURES / "R05.multiline.json")
    payload = pc.preconditioner_input(saved)
    source = payload["plan"]["updates"][0]["text"]
    n = len(source.splitlines())
    added = "- Stop searching when every receptacle type has been sampled once.\n"
    if placement == "new_line":
        patch = HEADER + f"@@ -{n},0 +{n+1} @@\n+" + added
        expected = source + added
    else:
        lines = source.splitlines(keepends=True)
        replacement = lines[4][:-1] + " Stop searching when every receptacle type has been sampled once.\n"
        patch = HEADER + "@@ -5 +5 @@\n-" + lines[4] + "+" + replacement
        expected = "".join(lines[:4]) + replacement + "".join(lines[5:])
    updated = editor.apply_patch(source, patch)
    result = formal(payload, {"u1": updated})
    effective = pc.compile_effective_plan(result, payload)
    assert editor.editor_input({**saved, "preconditioner": result, "effective_plan": effective})["plan"] == effective
    assert updated == expected
    request.node.user_properties.append(("semantic_counterexample", {
        "kind": "deliberately_unsupported_human_fixture", "patch": patch,
        "structurally_accepted": True, "semantically_approved": False,
    }))
