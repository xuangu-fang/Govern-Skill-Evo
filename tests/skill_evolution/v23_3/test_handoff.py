"""Versioned Diagnosis → Patch Preconditioner → unchanged Editor contract."""
from copy import deepcopy
import json

import pytest

from src.skill_evolution.v23 import diagnosis as old_diagnosis, editor as old_editor
from src.skill_evolution.v23_3 import diagnosis, editor, preconditioner as pc
from tests.skill_evolution.v23.test_diagnosis import make_grouping
from tests.skill_evolution.v23.test_preconditioner import proposal
from tests.skill_evolution.v23_3.helpers import Fake, keep, patch_result, read, scenario
from tests.skill_evolution.v23_3.test_preconditioner import upstream


def run_pc(upstream, name="single"):
    gd, dd, saved, pd = upstream
    raw = patch_result(saved, scenario("R05", name)["patches"])
    output = pc.run_preconditioner(gd, dd, pd, generate=Fake(raw),
                                  memory=saved["memory"], max_input_chars=4000000)
    return output


def test_multiline_diagnosis_exact_schema_and_single_line_patch(upstream, tmp_path):
    gd, dd, saved, pd = upstream
    loaded = diagnosis.load_diagnosis(dd)
    assert loaded["diagnosis"] == saved["diagnosis"]
    payload = json.loads(diagnosis.messages_for(loaded)[1]["content"])
    assert "memory" not in payload and "sources" not in payload
    assert set(payload) == {"parent", "command_sets", "runs", "grouping"}
    old_diagnosis.validate_diagnosis(loaded["diagnosis"], payload)
    with pytest.raises(ValueError):
        old_diagnosis.load_diagnosis(dd)
    conditioned = run_pc(upstream)
    effective = conditioned["effective_plan"]
    old = saved["diagnosis"]["plan"]["updates"][0]["text"].splitlines(keepends=True)
    new = effective["updates"][0]["text"].splitlines(keepends=True)
    assert sum(a != b for a, b in zip(old, new)) == 1
    assert effective["updates"][1:] == saved["diagnosis"]["plan"]["updates"][1:]
    assert old_editor.editor_input(conditioned) == {"parent": saved["facts"]["parent"], "plan": effective}
    # Deliberately simple human Skill modification exercises the existing interface.
    # It is not an assertion that Editor would implement the Plan correctly.
    parent = saved["facts"]["parent"]
    candidate = parent + "\nOffline mock integration note.\n"
    fake = Fake({"patch": old_editor.actual_diff(parent, candidate),
                 "reason": "Human offline Skill patch, semantic fidelity not evaluated."})
    ed = tmp_path / "editor"
    result = editor.run_editor(pd, ed, generate=fake, max_input_chars=4000000)
    assert fake.calls == 1
    assert fake.messages == old_editor.messages_for(conditioned)
    assert json.loads(fake.messages[1]["content"]) == old_editor.editor_input(conditioned)
    assert result["candidate_text"] == candidate
    assert result["actual_diff"] == old_editor.actual_diff(parent, candidate)
    assert old_editor.validate_editor(read(ed / "editor.json"), parent) == ("candidate", candidate)
    assert editor.load_editor(ed) == result
    assert old_editor.load_editor(ed, expected_preconditioner=conditioned) == result
    assert editor.run_editor(pd, ed, generate=fake, max_input_chars=4000000) == result
    assert fake.calls == 1


@pytest.mark.parametrize("decision", ["revise", "no_change", "need_evidence"])
def test_diagnosis_decisions_and_no_auto_split(tmp_path, decision):
    gd = make_grouping(tmp_path)
    value = proposal() if decision == "revise" else {
        "decision": decision, "reason": "Human stop fixture.", "plan": None}
    fake = Fake(value)
    dd = tmp_path / "diagnosis"
    result = diagnosis.run_diagnosis(gd, dd, generate=fake)
    assert result["diagnosis"] == value
    assert diagnosis.load_diagnosis(dd) == result
    assert diagnosis.run_diagnosis(gd, dd, generate=fake) == result
    assert fake.calls == 1
    if decision == "revise":
        assert all("\n" not in u["text"] for u in result["diagnosis"]["plan"]["updates"])
    else:
        with pytest.raises(ValueError):
            pc.run_preconditioner(gd, dd, tmp_path / "pc", generate=Fake(keep()))
        assert not (tmp_path / "pc").exists()


@pytest.mark.parametrize("kind", ["json", "schema", "basis", "checks", "truncated", "exception"])
def test_diagnosis_failure_no_partial_plan(tmp_path, kind):
    gd = make_grouping(tmp_path)
    value = proposal()
    if kind == "schema": value["extra"] = True
    if kind == "basis": value["plan"]["updates"][0]["basis"] = ["unknown"]
    if kind == "checks": value["plan"]["checks"][0]["update_ids"] = ["unknown"]
    fake = Fake(value, content="{" if kind == "json" else None,
                finish="length" if kind == "truncated" else "stop")
    if kind == "exception":
        def fake(*args):
            raise RuntimeError("Offline simulated failure")
    dd = tmp_path / "diagnosis"
    with pytest.raises((ValueError, RuntimeError)):
        diagnosis.run_diagnosis(gd, dd, generate=fake)
    assert read(dd / "validation.json")["valid"] is False
    assert not (dd / "diagnosis.json").exists()
    with pytest.raises(ValueError):
        diagnosis.run_diagnosis(gd, dd, generate=Fake(proposal()))


@pytest.mark.parametrize("filename", [
    "input.json", "messages.json", "prompt.md", "raw_output.txt", "parsed.json",
    "diagnosis.json", "response.json", "run.json", "validation.json",
])
def test_diagnosis_archive_mutation_detected(upstream, filename):
    path = upstream[1] / filename
    if filename.endswith(".json"):
        value = read(path)
        if filename == "input.json": value["facts"]["parent"] += "\naltered"
        elif filename == "messages.json": value[0]["content"] += "altered"
        elif filename == "response.json": value["content"] += "altered"
        elif filename == "run.json": value["grouping_round_id"] = "altered"
        elif filename == "validation.json": value["valid"] = False
        else: value["reason"] += "altered"
        path.write_text(json.dumps(value))
    else: path.write_bytes(path.read_bytes() + b"altered")
    with pytest.raises(ValueError):
        diagnosis.load_diagnosis(upstream[1])


@pytest.mark.parametrize("outcome", ["candidate", "no_change", "needs_revision", "json", "diff", "schema", "truncated"])
def test_editor_outcomes_and_failure(upstream, tmp_path, outcome):
    saved = run_pc(upstream)
    parent = saved["facts"]["parent"]
    patch = old_editor.actual_diff(parent, parent + "\nHuman fixture.\n")
    if outcome == "no_change": patch = ""
    elif outcome == "needs_revision": patch = None
    elif outcome == "diff": patch = "invalid"
    value = {"patch": patch, "reason": "Human offline fixture."}
    if outcome == "schema": value["extra"] = True
    fake = Fake(value, content="{" if outcome == "json" else None,
                finish="length" if outcome == "truncated" else "stop")
    ed = tmp_path / "editor"
    if outcome in ("json", "diff", "schema", "truncated"):
        with pytest.raises(ValueError):
            editor.run_editor(upstream[3], ed, generate=fake, max_input_chars=4000000)
        assert read(ed / "validation.json")["valid"] is False
        assert not (ed / "candidate.md").exists()
        with pytest.raises(ValueError):
            editor.run_editor(upstream[3], ed, generate=Fake(value), max_input_chars=4000000)
    else:
        result = editor.run_editor(upstream[3], ed, generate=fake, max_input_chars=4000000)
        assert result["editor_status"] == outcome
        assert (ed / "candidate.md").exists() == (outcome == "candidate")
        assert editor.load_editor(ed) == result
    assert fake.calls == 1


@pytest.mark.parametrize("stage", ["diagnosis", "raw_patch", "normalized", "upstream", "candidate"])
def test_cross_stage_recovery_rechecks_lineage(upstream, tmp_path, stage):
    saved = run_pc(upstream)
    ed = tmp_path / "editor"
    parent = saved["facts"]["parent"]
    editor.run_editor(upstream[3], ed, generate=Fake({
        "patch": old_editor.actual_diff(parent, parent + "\nHuman fixture.\n"),
        "reason": "Offline fixture."}), max_input_chars=4000000)
    path = {
        "diagnosis": upstream[1] / "diagnosis.json",
        "raw_patch": upstream[3] / "parsed.json",
        "normalized": upstream[3] / "preconditioner.json",
        "upstream": ed / "upstream.json",
        "candidate": ed / "candidate.md",
    }[stage]
    if stage == "candidate": path.write_bytes(path.read_bytes() + b"altered")
    else:
        value = read(path)
        if stage == "upstream": value["diagnosis"]["plan"]["goal"] += "altered"
        else: value["reason"] += "altered"
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        editor.load_editor(ed)


def test_diagnosis_call_limits_and_expected_input(tmp_path):
    gd = make_grouping(tmp_path)
    dd = tmp_path / "diagnosis"
    fake = Fake(proposal())
    with pytest.raises(ValueError):
        diagnosis.run_diagnosis(gd, dd, generate=fake, max_input_chars=1)
    with pytest.raises(ValueError):
        diagnosis.run_diagnosis(gd, dd, generate=fake, call_config={"wrong": True})
    assert fake.calls == 0 and not dd.exists()
    diagnosis.run_diagnosis(gd, dd, generate=fake)
    with pytest.raises(ValueError):
        diagnosis.load_diagnosis(dd, expected_grouping={})
    with pytest.raises(ValueError):
        diagnosis.load_diagnosis(dd, expected_call_config={})
