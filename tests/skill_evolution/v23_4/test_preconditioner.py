import json

import pytest

from src.skill_evolution.v23 import editor as old_editor
from src.skill_evolution.v23_3 import preconditioner as old_pc
from src.skill_evolution.v23_3.memory_view import FORMAT, LEGACY
from src.skill_evolution.v23_4 import editor, preconditioner as pc
from src.skill_evolution.v23_4.update_patch import CONTRACT_VERSION
from .helpers import Fake, keep, memory, read, revise, withdraw


@pytest.mark.parametrize("mode", ["keep", "revise", "withdraw"])
def test_archive_reload_and_editor_handoff(upstream, payload, tmp_path, mode):
    gd, dd, saved, pd = upstream
    raw = keep(payload)
    if mode == "revise": raw["adjustments"][0] = revise(payload)
    elif mode == "withdraw":
        raw["adjustments"] = [withdraw(u["id"]) for u in payload["plan"]["updates"]]
        raw["checks"] = []
    fake = Fake(raw)
    result = pc.run_preconditioner(gd, dd, pd, generate=fake, memory=memory(payload))
    assert result["raw_preconditioner"] == raw == read(pd / "parsed.json")
    assert read(pd / "preconditioner.json") == result["preconditioner"]
    assert read(pd / "run.json")["contract_version"] == CONTRACT_VERSION
    assert read(pd / "input.json")["memory"] == memory(payload)
    assert read(pd / "model_input.json")["memory"]["format"] == FORMAT
    assert "Determine the D/S/C change for each Update" in fake.messages[0]["content"]
    assert "{{execution_context}}" not in fake.messages[0]["content"]
    assert pc.model_input(result) == read(pd / "model_input.json")
    assert pc.load_preconditioner(pd) == result
    assert pc.run_preconditioner(gd, dd, pd, generate=fake, memory=memory(payload)) == result
    assert fake.calls == 1
    with pytest.raises(ValueError): old_pc.load_preconditioner(pd)
    ed = tmp_path / "editor"
    parent = payload["parent"]
    candidate = parent + "Offline handoff fixture.\n"
    generated = Fake({"patch": old_editor.actual_diff(parent, candidate), "reason": "Offline interface fixture."})
    if mode == "withdraw":
        assert result["effective_plan"] is None
        with pytest.raises(ValueError): editor.run_editor(pd, ed, generate=generated)
        assert generated.calls == 0 and not ed.exists()
    else:
        output = editor.run_editor(pd, ed, generate=generated)
        assert generated.messages == old_editor.messages_for(result)
        assert json.loads(generated.messages[1]["content"]) == {
            "parent": parent, "plan": result["effective_plan"]}
        assert output["candidate_text"] == candidate
        assert editor.load_editor(ed) == output
        assert editor.run_editor(pd, ed, generate=generated) == output
        assert generated.calls == 1
        # Even a previously valid Editor archive rechecks raw V23.4 lineage.
        raw["adjustments"][0]["reason"] += " tampered"
        (pd / "parsed.json").write_text(json.dumps(raw))
        with pytest.raises(ValueError): editor.load_editor(ed)


@pytest.mark.parametrize("kind", ["json", "duplicate_key", "schema", "reference", "late_patch", "truncated", "exception"])
def test_failure_preserved_without_effective_plan_or_retry(upstream, payload, kind):
    gd, dd, _, pd = upstream
    raw = keep(payload)
    if kind == "schema": raw["adjustments"].pop()
    elif kind == "reference": raw["adjustments"][0]["reason"] = "No need to react to `M99`."
    elif kind == "late_patch":
        raw["adjustments"][0] = revise(payload)
        raw["adjustments"][2] = revise(payload, 2)
        raw["adjustments"][2]["to"]["patch"] = "invalid patch"
    fake = Fake(raw, finish="length" if kind == "truncated" else "stop",
                content={"json": "{", "duplicate_key": '{"adjustments":[],"checks":null,"checks":[]}'}.get(kind))
    if kind == "exception":
        def fake(*args):
            raise RuntimeError("Offline simulated generator failure")
    with pytest.raises((ValueError, RuntimeError)):
        pc.run_preconditioner(gd, dd, pd, generate=fake)
    assert read(pd / "run.json")["status"] == "invalid"
    assert read(pd / "validation.json")["valid"] is False
    assert not (pd / "preconditioner.json").exists()
    assert not (pd / "effective_plan.json").exists()
    retry = Fake(keep(payload))
    with pytest.raises(ValueError): pc.run_preconditioner(gd, dd, pd, generate=retry)
    assert retry.calls == 0


@pytest.mark.parametrize("filename", ["parsed.json", "preconditioner.json", "effective_plan.json",
                                     "model_input.json", "input.json", "messages.json", "response.json",
                                     "validation.json", "prompt.md", "raw_output.txt", "version", "memory_view",
                                     "upstream"])
def test_tampering_is_rejected(upstream, payload, filename):
    gd, dd, _, pd = upstream
    pc.run_preconditioner(gd, dd, pd, generate=Fake(keep(payload)))
    path = pd / filename
    if filename in ("version", "memory_view"):
        path = pd / "run.json"
        value = read(path)
        value["contract_version" if filename == "version" else "memory_view"] = "unsupported"
        path.write_text(json.dumps(value))
    elif filename == "upstream":
        path = dd / "diagnosis.json"
        value = read(path)
        value["plan"]["updates"][0]["text"] += " Changed upstream."
        path.write_text(json.dumps(value))
    elif path.suffix == ".json":
        value = read(path)
        if isinstance(value, dict): value["tampered"] = True
        else: value.append({"tampered": True})
        # validation.json's validity marker is the authoritative field.
        if filename == "validation.json": value["valid"] = False
        path.write_text(json.dumps(value))
    else: path.write_text(path.read_text() + "tampered")
    # Extra provider response metadata is intentionally allowed; alter content.
    if filename == "response.json":
        value["content"] += " tampered"
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError): pc.load_preconditioner(pd)


def test_config_budget_memory_view_and_expected_handoff(upstream, payload):
    gd, dd, saved, pd = upstream
    fake = Fake(keep(payload))
    with pytest.raises(ValueError): pc.run_preconditioner(gd, dd, pd, generate=fake, max_input_chars=1)
    with pytest.raises(ValueError): pc.run_preconditioner(gd, dd, pd, generate=fake, call_config={"different": True})
    assert fake.calls == 0 and not pd.exists()
    output = pc.run_preconditioner(gd, dd, pd, generate=fake, memory_view=LEGACY)
    assert read(pd / "model_input.json")["memory"] == {"entries": [], "sources": {}}
    for kwargs in ({"expected_call_config": {}}, {"expected_memory_view": FORMAT}, {"expected_diagnosis": saved}):
        with pytest.raises(ValueError): pc.load_preconditioner(pd, **kwargs)
    with pytest.raises(ValueError): pc.run_preconditioner(gd, dd, pd, generate=fake)
    assert pc.load_preconditioner(pd, expected_memory_view=LEGACY,
                                  expected_call_config=fake.call_config) == output
    assert fake.calls == 1
