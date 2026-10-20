"""Deterministic P1-B checks; no live requests or semantic keyword scoring."""
import json
import pytest
import requests

from experiments.methods.v23_2.v23_2_diagnosis_construction_001 import run as r
from src.skill_evolution.v23 import diagnosis, preconditioner
from tests.skill_evolution.v23_2.test_local_validation import saved, config
from tests.skill_evolution.v23.test_diagnosis import answer


def test_frozen_sources_and_defaults():
    r.check()
    assert r.frozen_files() == r.ev.read(r.EXP / "config/p1_freeze.json")["sha256"]
    expected = (r.P1_EXP / "config/diagnosis_prompt.md").read_text()
    for change in r.ev.read(r.EXP / "config/replacements.json"):
        assert expected.count(change["before"]) == 1
        expected = expected.replace(change["before"], change["after"])
    assert r.PROMPT.read_text() == expected
    assert r.local.PROMPTS["diagnosis"] == diagnosis.PROMPT_PATH


@pytest.mark.parametrize("rnd", r.ROUNDS)
def test_fixed_upstream_input_and_config(rnd):
    saved, entry = r.material(rnd)
    original = r.ev.read(r.Path(entry["diagnosis_path"]) / "messages.json")
    messages = r.local.messages_for("diagnosis", saved, prompt_path=r.PROMPT)
    assert messages[1:] == original[1:]
    assert set(json.loads(messages[1]["content"])) == {"parent", "command_sets", "runs", "grouping"}
    assert "memory" not in saved and "diagnosis" not in saved
    diagnosis.validate_diagnosis(entry["original_output"], diagnosis.diagnosis_input(saved))
    assert entry["config"] == r.ev.read(r.P1_EXP / "config/cases.json")[rnd]["config"]


def test_existing_parser_and_downstream_fields(saved, config, tmp_path):
    upstream = {k: v for k, v in saved.items() if k not in ("diagnosis", "memory")}
    result = r.run_one(upstream, tmp_path / "d", config, generate=lambda *_: answer())
    assert set(result) == set(upstream) | {"diagnosis"}
    assert r.local.load_attempt(tmp_path / "d/attempts/001", prompt_path=r.PROMPT) == result
    payload = preconditioner.preconditioner_input(result)
    assert payload["plan"] == result["diagnosis"]["plan"]
    compiled = preconditioner.compile_effective_plan(
        {"decision": "ready", "reason": "Keep.", "adjustments": [], "checks": None}, payload)
    assert compiled == payload["plan"]


@pytest.mark.parametrize("kind", ("timeout", "truncated", "contract"))
def test_one_request_even_on_failure(saved, config, tmp_path, kind):
    calls = []
    def generate(*_):
        calls.append(1)
        if kind == "timeout":
            raise requests.Timeout("offline simulated failure")
        value = answer()
        if kind == "truncated":
            value["finish_reason"] = "length"
        else:
            value["content"] = '{"unexpected":true}'
        return value
    upstream = {k: v for k, v in saved.items() if k not in ("diagnosis", "memory")}
    with pytest.raises(r.ev.Stopped):
        r.run_one(upstream, tmp_path / "d", config, generate=generate)
    assert len(calls) == 1
    assert (tmp_path / "d/stop.json").exists()
    assert (tmp_path / "d/attempts/001/error.json").exists()
    assert not (tmp_path / "d/attempts/002").exists()
