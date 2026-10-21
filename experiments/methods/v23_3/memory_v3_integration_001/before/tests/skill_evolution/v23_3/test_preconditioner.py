"""Mock calls and raw-to-derived archive verification, with frozen research evidence."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23 import grouping
from src.skill_evolution.v23_3 import diagnosis
from src.skill_evolution.v23_3 import preconditioner as pc
from tests.skill_evolution.v23_3.helpers import Fake, frozen, keep, patch_result, read, scenario


@pytest.fixture
def upstream(tmp_path):
    saved = frozen()
    # Read the valid frozen formal Grouping; only the downstream responses are mocks.
    grouped = {k: v for k, v in saved.items() if k not in ("diagnosis", "memory")}
    gd = Path("artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/grouping/attempts/002")
    assert grouping.load_grouping(gd) == grouped
    dd = tmp_path / "diagnosis"
    fake = Fake(saved["diagnosis"])
    diagnosis.run_diagnosis(gd, dd, generate=fake, max_input_chars=4000000)
    return gd, dd, saved, tmp_path / "preconditioner"


def run(upstream, raw=None, fake=None, **kwargs):
    gd, dd, saved, out = upstream
    fake = fake or Fake(keep() if raw is None else raw)
    kwargs.setdefault("max_input_chars", 4000000)
    result = pc.run_preconditioner(gd, dd, out, generate=fake, memory=saved["memory"], **kwargs)
    return result, fake


@pytest.mark.parametrize("kind", ["single", "cross", "keep", "withdraw", "no_change", "need_evidence"])
def test_one_call_and_reload(upstream, kind):
    _, _, saved, out = upstream
    raw = keep()
    if kind in ("single", "cross"):
        raw = patch_result(saved, scenario("R05", kind)["patches"])
    elif kind in ("withdraw", "no_change"):
        chosen = saved["diagnosis"]["plan"]["updates"]
        if kind == "withdraw": chosen = chosen[:1]
        raw["adjustments"] = [{"from": [u["id"]], "to": [], "basis": u["basis"],
                               "reason": "Human offline withdrawal."} for u in chosen]
        raw["checks"] = []
    if kind in ("no_change", "need_evidence"): raw["decision"] = kind
    result, fake = run(upstream, raw)
    assert fake.calls == 1
    assert read(out / "parsed.json") == raw
    assert read(out / "response.json") == fake.response
    assert (out / "raw_output.txt").read_bytes().decode() == fake.response["content"]
    assert json.loads(fake.messages[1]["content"]) == pc.preconditioner_input(saved)
    assert pc.load_preconditioner(out) == result
    # Existing output reloads with matching config; no second generation.
    assert pc.run_preconditioner(upstream[0], upstream[1], out, generate=fake,
                                memory=saved["memory"], max_input_chars=4000000) == result
    assert fake.calls == 1
    if kind in ("single", "cross"):
        assert read(out / "preconditioner.json") != raw
        assert "text" in result["preconditioner"]["adjustments"][0]["to"][0]
    assert result["diagnosis"] == saved["diagnosis"]


@pytest.mark.parametrize("kind", ["json", "schema", "patch", "reference", "truncated", "exception", "late_patch"])
def test_failure_preserves_raw_no_derived_no_retry(upstream, kind):
    raw = patch_result(upstream[2], scenario("R05", "single")["patches"])
    if kind == "schema": raw["unexpected"] = True
    if kind == "patch": raw["adjustments"][0]["to"][0]["patch"] = "invalid diff"
    if kind == "reference": raw["adjustments"][0]["basis"] = ["M9999"]
    if kind == "late_patch":
        raw["adjustments"].append({"from": ["u2"], "to": [{"id": "u2", "patch": "bad"}],
                                   "basis": ["P1"], "reason": "Bad later patch."})
    fake = Fake(raw, content="{" if kind == "json" else None,
                finish="length" if kind == "truncated" else "stop")
    if kind == "exception":
        def fake(*args):
            raise RuntimeError("Offline simulated request failure")
    with pytest.raises((ValueError, RuntimeError)):
        run(upstream, fake=fake)
    out = upstream[3]
    assert read(out / "validation.json")["valid"] is False
    assert read(out / "run.json")["status"] == "invalid"
    for name in ("preconditioner.json", "effective_plan.json", "candidate.md"):
        assert not (out / name).exists()
    if kind != "exception":
        assert read(out / "response.json") == fake.response
        assert fake.calls == 1
    with pytest.raises(ValueError):
        pc.run_preconditioner(upstream[0], upstream[1], out, generate=Fake(keep()),
                              memory=upstream[2]["memory"], max_input_chars=4000000)


@pytest.mark.parametrize("filename", [
    "input.json", "messages.json", "prompt.md", "response.json", "raw_output.txt",
    "parsed.json", "preconditioner.json", "effective_plan.json", "validation.json", "run.json",
])
@pytest.mark.parametrize("mutation", ["missing", "tamper"])
def test_archive_corruption_rejected(upstream, filename, mutation):
    run(upstream, patch_result(upstream[2], scenario("R05", "single")["patches"]))
    target = upstream[3] / filename
    if mutation == "missing": target.unlink()
    elif filename.endswith(".json"):
        value = read(target)
        if filename == "validation.json": value["valid"] = False
        elif filename == "run.json": value["round_id"] = "other"
        elif filename == "input.json": value["diagnosis"]["plan"]["goal"] += " altered"
        elif filename == "effective_plan.json": value["goal"] += " altered"
        elif filename == "messages.json": value[0]["content"] += " altered"
        elif filename == "response.json": value["content"] += " altered"
        else: value["reason"] = "altered"
        target.write_text(json.dumps(value))
    else: target.write_bytes(target.read_bytes() + b" altered")
    with pytest.raises((ValueError, FileNotFoundError)):
        pc.load_preconditioner(upstream[3])


def test_budget_configuration_and_expected_handoff(upstream):
    fake = Fake(keep())
    with pytest.raises(ValueError):
        run(upstream, fake=fake, max_input_chars=1)
    with pytest.raises(ValueError):
        run(upstream, fake=fake, call_config={"other": True})
    assert fake.calls == 0 and not upstream[3].exists()
    result, _ = run(upstream)
    with pytest.raises(ValueError):
        pc.load_preconditioner(upstream[3], expected_call_config={"other": True})
    altered = deepcopy(upstream[2])
    altered["diagnosis"]["plan"]["goal"] += " changed"
    with pytest.raises(ValueError):
        pc.load_preconditioner(upstream[3], expected_diagnosis=altered)
    assert result["effective_plan"] == upstream[2]["diagnosis"]["plan"]


def test_prompt_contract_is_versioned_not_case_answer_key(upstream):
    prompt = pc.messages_for(upstream[2])[0]["content"]
    assert "{{execution_context}}" not in prompt
    prose = " ".join(prompt.split())
    for token in ("**Keep**", "**Narrow**", "**Widen**", "**Replace**", "**Withdraw**",
                  "actual Diff", "counterexample", "same", "not automatically authorize",
                  "one decision and one JSON response"):
        assert token in prose
    for forbidden in ("R04", "R05", "R06", "M6", "M10", "P3-C1"):
        assert forbidden not in prompt
