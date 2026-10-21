"""Offline timeout/byte/traceback checks; never sends a network request."""
import importlib.util
from pathlib import Path
import json

import pytest
import requests


def module():
    spec = importlib.util.spec_from_file_location("timeout_retry_fixture", Path(__file__).with_name("run.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize("fail", [False, True])
def test_prepared_bytes_and_actual_timeout(tmp_path, monkeypatch, fail):
    m = module()
    req = {"endpoint": "http://example.invalid", "body": {"messages": [{"content": "中文\n"}]}}

    def fake_send(session, prepared, **kwargs):
        assert kwargs == {"timeout": (60, 300), "allow_redirects": False}
        assert session.trust_env is False
        assert json.loads(prepared.body) == req["body"]
        if fail: raise requests.ConnectionError("offline transport failure")
        r = requests.Response()
        r.status_code = 200
        r._content = b'{"choices":[{"message":{"content":"{}"},"finish_reason":"stop"}],"model":"offline"}'
        return r

    monkeypatch.setattr(requests.Session, "send", fake_send)
    transport = {"connect_upload_timeout_seconds": 60, "read_timeout_seconds": 300}
    if fail:
        with pytest.raises(requests.ConnectionError): m.send_once(req, "fake", tmp_path, transport)
    else:
        assert m.send_once(req, "fake", tmp_path, transport)["finish_reason"] == "stop"
    record = m.read(tmp_path / "request.json")
    expected_bytes = len(requests.Request("POST", req["endpoint"], json=req["body"]).prepare().body)
    assert record["actual_body_bytes"] == record["content_length"] == expected_bytes
    assert record["timeout"] == [60, 300]
    assert "fake" not in (tmp_path / "request.json").read_text()
    assert (tmp_path / "send_events.json").exists()


def test_three_attempt_limit_and_tracebacks(tmp_path, monkeypatch):
    m = module()
    original = m.E
    for name in ["transport.json", "freeze.json", "A_request.json", "original_protocol.md"]:
        (tmp_path / "config").mkdir(exist_ok=True)
        (tmp_path / "config" / name).write_bytes((original / "config" / name).read_bytes())
    (tmp_path / "P3A_RETRY_PROTOCOL.md").write_bytes((original / "P3A_RETRY_PROTOCOL.md").read_bytes())
    monkeypatch.setattr(m, "E", tmp_path)
    cfg = m.read(tmp_path / "config/freeze.json")["call_config"]
    monkeypatch.setattr(m.base, "env_config", lambda: ("unused", "fake", cfg))
    monkeypatch.setattr(m.base, "verify_frozen", lambda: None)
    monkeypatch.setattr(m.time, "sleep", lambda _: None)
    calls = []

    def fail(*args):
        calls.append(1)
        raise requests.ConnectionError("offline failed body send")

    monkeypatch.setattr(m, "send_once", fail)
    with pytest.raises(requests.ConnectionError): m.generate("A", tmp_path / "out")
    assert len(calls) == 3
    assert len(list((tmp_path / "out/http").glob("*/traceback.txt"))) == 3
    assert "ConnectionError" in (tmp_path / "out/http/001/traceback.txt").read_text()
    with pytest.raises(FileExistsError): m.generate("A", tmp_path / "out")
    assert len(calls) == 3
