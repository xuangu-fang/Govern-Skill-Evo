"""Route new calls consistently, without sending requests to either provider."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
import requests

from src.skill_evolution.v23 import evolution as ev, grouping
from src.skill_evolution.v23.model_routing import model_for_endpoint
from tests.skill_evolution.v23.test_evolution import config


ROUTES = [
    ("http://llm-proxy.intra.xiaojukeji.com", "deepseek-v4.1-flash"),
    ("https://api.deepseek.com", "deepseek-flash"),
]


@pytest.mark.parametrize("base,model", ROUTES)
@pytest.mark.parametrize("suffix", ["", "/", "/v1", "/v1/"])
def test_endpoint_selects_model(base, model, suffix):
    for old in [None, "deepseek-v4-flash", "deepseek-v4-pro", "deepseek-flash"]:
        assert model_for_endpoint(base + suffix, old) == model


def test_unknown_endpoint_does_not_match_known_host_prefix():
    assert model_for_endpoint("https://api.deepseek.com.example.invalid", "custom") == "custom"
    with pytest.raises(ValueError, match="--model"):
        model_for_endpoint("https://example.invalid")
    with pytest.raises(ValueError, match="Invalid API base URL"):
        model_for_endpoint("https://user:secret@api.deepseek.com", "custom")


@pytest.mark.parametrize("base,model", ROUTES)
def test_actual_request_and_archive_use_routed_model(tmp_path, monkeypatch, base, model):
    calls = []
    payload = {"model": model, "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]}

    def post(session, endpoint, **kwargs):
        calls.append((endpoint, kwargs, session.trust_env))
        return SimpleNamespace(status_code=200, content=json.dumps(payload).encode(), json=lambda: payload)

    monkeypatch.setattr(requests.Session, "post", post)
    generate = grouping.live_generator(base_url=base, key="synthetic", model="deepseek-v4-pro")
    generate([{"role": "user", "content": "test"}], tmp_path)
    request = ev.read(tmp_path/"request.json")
    assert request["endpoint"] == calls[0][0] == base + "/chat/completions"
    assert request["body"] == calls[0][1]["json"]
    assert request["body"]["model"] == generate.call_config["model"] == model
    assert calls[0][2] is (".intra." not in base)
    assert len(calls) == 1
    assert all("synthetic" not in p.read_text() for p in tmp_path.iterdir())


@pytest.mark.parametrize("base,model", ROUTES)
def test_dotenv_routes_actor_modules_and_overrides_without_mutating_input(tmp_path, monkeypatch, base, model):
    monkeypatch.setattr(ev, "ROOT", tmp_path)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path/".env").write_text(f"OPENAI_BASE_URL={base}\nOPENAI_API_KEY=synthetic\n")
    original = config(1)
    original["stage_configs"] = {"editor": {**original["call_config"], "max_tokens": 20000}}
    before = deepcopy(original)
    routed = ev.configuration_from_environment(original)
    assert original == before
    assert routed["actor_model"] == routed["call_config"]["model"] == model
    assert routed["actor_base_url"] == base
    assert routed["stage_configs"]["editor"]["model"] == model
    assert routed["stage_configs"]["editor"]["max_tokens"] == 20000
    assert ev._generator(routed).call_config == routed["call_config"]


@pytest.mark.parametrize("base,model", ROUTES)
def test_new_campaign_freezes_route_before_actor_and_module_execution(tmp_path, monkeypatch, base, model):
    monkeypatch.setenv("OPENAI_BASE_URL", base)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic")
    original = config(1)
    observed = []

    def round_(root, **kwargs):
        frozen = ev.read(root/"config.json")
        observed.append(frozen)
        assert frozen["actor_model"] == frozen["call_config"]["model"] == model
        state = ev.read(root/"state.json"); state["next_round"] = 2
        ev.save(root/"state.json", state)
        return {"outcome": "no_change"}

    monkeypatch.setattr(ev, "run_round", round_)
    ev.run_campaign(tmp_path, config=original)
    assert len(observed) == 1
    assert ev.read(tmp_path/"initial_config.json") == observed[0]
    assert original["actor_model"] == "offline"


@pytest.mark.parametrize("base,model", ROUTES)
def test_actor_subprocess_receives_same_route(tmp_path, monkeypatch, base, model):
    monkeypatch.setenv("OPENAI_BASE_URL", base)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic")
    routed = ev.configuration_from_environment(config(1))
    calls = []

    def run(cmd, **kwargs):
        calls.append((cmd, kwargs["env"]))
        ev.save(tmp_path/"trajectory.json", {})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ev.subprocess, "run", run)
    ev.actor_task("train:0010", None, tmp_path, routed)
    cmd, env = calls[0]
    assert cmd[cmd.index("--model") + 1] == model
    assert env["OPENAI_BASE_URL"] == base
    assert env["OPENAI_API_KEY"] == "synthetic"


def test_changed_endpoint_stops_before_actor_or_module_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", ROUTES[0][0])
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic")
    routed = ev.configuration_from_environment(config(1))
    ev.initialize(tmp_path, routed)
    before = (tmp_path/"config.json").read_bytes()
    monkeypatch.setenv("OPENAI_BASE_URL", ROUTES[1][0])
    monkeypatch.setattr(ev.subprocess, "run", lambda *a, **kw: pytest.fail("actor started"))
    monkeypatch.setattr(requests.Session, "post", lambda *a, **kw: pytest.fail("request sent"))
    with pytest.raises(ValueError, match="use a new Campaign"):
        ev.run_campaign(tmp_path, resume=True)
    assert (tmp_path/"config.json").read_bytes() == before
    assert not (tmp_path/"rounds").exists()
