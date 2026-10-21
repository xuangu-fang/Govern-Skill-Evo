from copy import deepcopy

import pytest

from src.skill_evolution.v23.editor import actual_diff
from src.skill_evolution.v23.preconditioner import compile_effective_plan, preconditioner_input
from src.skill_evolution.v23_3.update_patch import normalize_update_patches
from tests.skill_evolution.v23_3.helpers import frozen, keep, patch_result, scenario


@pytest.mark.parametrize("case", ["R04", "R05", "R06"])
@pytest.mark.parametrize("name", ["single", "linked", "add", "delete", "broad", "cross"])
def test_human_scenarios(case, name):
    saved = frozen(case)
    example = scenario(case, name)
    raw = patch_result(saved, example["patches"])
    payload = preconditioner_input(saved)
    before = deepcopy((raw, payload))
    normalized, effective = normalize_update_patches(raw, payload)
    assert compile_effective_plan(normalized, payload) == effective
    assert (raw, payload) == before
    assert effective["goal"] == payload["plan"]["goal"]
    assert effective["checks"] == payload["plan"]["checks"]
    for old, new in zip(payload["plan"]["updates"], effective["updates"]):
        uid = old["id"]
        assert new == {**old, "text": example["expected"].get(uid, old["text"])}
        for a, b in example["preserved_line_pairs"].get(uid, []):
            assert old["text"].splitlines(keepends=True)[a-1] == new["text"].splitlines(keepends=True)[b-1]


@pytest.mark.parametrize("kind", ["keep", "withdraw", "no_change", "need_evidence"])
def test_decisions(kind):
    saved = frozen()
    raw = keep()
    if kind in ("withdraw", "no_change"):
        updates = saved["diagnosis"]["plan"]["updates"]
        chosen = updates[:1] if kind == "withdraw" else updates
        raw["adjustments"] = [{"from": [u["id"]], "to": [], "basis": u["basis"],
                               "reason": "Human withdrawal fixture."} for u in chosen]
        raw["checks"] = []
    if kind in ("no_change", "need_evidence"):
        raw["decision"] = kind
    normalized, effective = normalize_update_patches(raw, preconditioner_input(saved))
    assert normalized == raw
    if kind in ("no_change", "need_evidence"):
        assert effective is None
    elif kind == "keep":
        assert effective == saved["diagnosis"]["plan"]
    else:
        assert effective["updates"] == saved["diagnosis"]["plan"]["updates"][1:]


@pytest.mark.parametrize("kind", [
    "unknown", "repeat", "merge", "split", "new_id", "text", "both", "null",
    "empty", "diff", "late_failure", "checks", "blank", "no_change_keep",
    "need_evidence_changes", "extra", "basis",
])
def test_reject_without_mutation(kind):
    saved = frozen()
    raw = patch_result(saved, scenario("R05", "single")["patches"])
    a = raw["adjustments"][0]
    if kind == "unknown": a["from"] = ["missing"]
    elif kind == "repeat": raw["adjustments"].append(deepcopy(a))
    elif kind == "merge": a["from"].append("u2")
    elif kind == "split": a["to"].append(deepcopy(a["to"][0]))
    elif kind == "new_id": a["to"][0]["id"] = "new"
    elif kind == "text": a["to"][0] = {"id": "u1", "text": "free rewrite"}
    elif kind == "both": a["to"][0]["text"] = "free rewrite"
    elif kind in ("null", "empty", "diff"): a["to"][0]["patch"] = {"null": None, "empty": "", "diff": "bad"}[kind]
    elif kind == "late_failure":
        raw["adjustments"].append({"from": ["u2"], "to": [{"id": "u2", "patch": "bad"}],
                                   "basis": a["basis"], "reason": a["reason"]})
    elif kind == "checks": raw["checks"] = [{"id": "c99", "update_ids": ["gone"], "question": "Valid?"}]
    elif kind == "blank": a["to"][0]["patch"] = actual_diff(saved["diagnosis"]["plan"]["updates"][0]["text"], "")
    elif kind == "no_change_keep": raw = {**keep(), "decision": "no_change", "checks": []}
    elif kind == "need_evidence_changes": raw["decision"] = "need_evidence"
    elif kind == "extra": raw["role"] = "target"
    elif kind == "basis": a["basis"] = ["M99999"]
    payload = preconditioner_input(saved)
    before = deepcopy((raw, payload))
    with pytest.raises(ValueError):
        normalize_update_patches(raw, payload)
    assert (raw, payload) == before


@pytest.mark.parametrize("source", ["old one line", "a\nb\n", "a\r\nb\r\n", "中文  \n尾行"])
def test_exact_text_formats(source):
    saved = frozen()
    saved["diagnosis"]["plan"]["updates"][0]["text"] = source
    target = source.replace(source[0], "X", 1)
    raw = patch_result(saved, {"u1": actual_diff(source, target)})
    _, effective = normalize_update_patches(raw, preconditioner_input(saved))
    assert effective["updates"][0]["text"] == target


def test_semantic_risk_is_structurally_accepted_not_validated(request):
    saved = frozen()
    old = saved["diagnosis"]["plan"]["updates"][0]["text"]
    target = old + "- Stop after sampling every receptacle category once.\n"
    _, effective = normalize_update_patches(
        patch_result(saved, {"u1": actual_diff(old, target)}), preconditioner_input(saved))
    assert effective["updates"][0]["text"] == target
    request.node.user_properties.append(("semantic_validity", "NOT_VERIFIED: intentionally unsupported exit"))
