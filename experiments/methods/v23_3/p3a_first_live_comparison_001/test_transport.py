"""Experiment-wrapper tests only; no live transport and no research outputs."""
import importlib.util
from pathlib import Path

import pytest
import requests


@pytest.mark.parametrize("failures,expected,success", [
    ([], 1, True),
    ([503], 2, True),
    ([429, "timeout"], 3, True),
    ([503, 503, 503], 3, False),
    ([400], 1, False),
    (["ssl"], 1, False),
    (["decode"], 1, False),
])
def test_retry_budget_and_identical_requests(tmp_path, monkeypatch, failures, expected, success):
    spec = importlib.util.spec_from_file_location("p3a_transport_fixture", Path(__file__).with_name("run.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cfg = {"endpoint": "http://example.invalid/chat/completions", "model": "offline",
           "max_tokens": 16384, "timeout_seconds": 300}
    messages = [{"role": "user", "content": "fixed"}]
    req = module.request(messages, cfg)
    monkeypatch.setattr(module, "E", tmp_path)
    monkeypatch.setattr(module, "verify_frozen", lambda: None)
    monkeypatch.setattr(module, "env_config", lambda: ("http://example.invalid", "not-a-key", cfg))
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    module.save(tmp_path / "requests/A.json", req)
    module.save(tmp_path / "config/call_config.json", cfg)
    calls = []

    def fake_inner(actual, dest):
        assert actual == messages
        calls.append(1)
        module.save(dest / "request.json", req)
        failure = failures[len(calls)-1] if len(calls) <= len(failures) else None
        if isinstance(failure, int):
            module.save(dest / "http_status.json", {"status_code": failure})
            raise ValueError(f"Model API returned HTTP {failure}")
        if failure == "timeout": raise requests.ReadTimeout("offline timeout")
        if failure == "ssl": raise requests.exceptions.SSLError("offline SSL failure")
        if failure == "decode": raise ValueError("offline malformed HTTP JSON")
        # Even malformed model JSON is a completed response, not a transport retry.
        return {"content": "{", "finish_reason": "stop"}

    fake_inner.call_config = cfg
    monkeypatch.setattr(module.grouping, "live_generator", lambda **kwargs: fake_inner)
    generate = module.generator("A")
    if success:
        assert generate(messages, tmp_path / "out")["content"] == "{"
    else:
        with pytest.raises((ValueError, requests.RequestException)):
            generate(messages, tmp_path / "out")
    assert len(calls) == expected
    assert len(list((tmp_path / "out/http").glob("*/attempt.json"))) == expected
    # The one-shot claim prevents resampling even after failure.
    with pytest.raises(FileExistsError):
        generate(messages, tmp_path / "out")
    assert len(calls) == expected
