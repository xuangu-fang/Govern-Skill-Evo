"""One authorized format-B completion; reuse the original transport and compiler."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

import requests
from dotenv import dotenv_values
from src.skill_evolution.v23 import grouping, preconditioner as pc, evolution as ev
from src.skill_evolution.v23.prompts import render_prompt
from src.skill_evolution.v22.diagnosis_editor import parse_json_response

E = Path(__file__).resolve().parent
P = E.parent
ROOT = P.parents[3]


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify():
    spec = importlib.util.spec_from_file_location("baseline", P / "p3b_A_retry_001/run_once.py")
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    old.E = E
    frozen, _, cfg = old.preflight()
    req = read(E / "requests/B_UNSENT.json")
    system = render_prompt((E / "config/preconditioner_prompt.md").read_text(),
                           read(P / "config/background.json"))
    assert req["body"]["messages"][0] == {"role": "system", "content": system}
    restored = deepcopy(req)
    restored["body"]["messages"][0] = frozen["B"]["body"]["messages"][0]
    assert restored == frozen["B"]
    assert frozen["A"]["body"]["messages"][0] == frozen["B"]["body"]["messages"][0]
    payload = json.loads(req["body"]["messages"][1]["content"])
    assert payload["memory"] == read(P / "config/memory_B.json")
    assert req["body"]["messages"][0] == read(P / "p3b_A_format_001/runs/A/request.json")["body"]["messages"][0]
    return req, payload, cfg


def freeze():
    req, payload, _ = verify()
    update = payload["plan"]["updates"][0]
    fixture = {"decision": "ready", "reason": "Current evidence P1, P3.",
               "adjustments": [{"from": [update["id"]],
                                "to": [{"id": update["id"], "text": update["text"]}],
                                "basis": ["P1:4"], "reason": "Current evidence P1:4."}],
               "checks": None}
    assert pc.compile_effective_plan(fixture, payload) == payload["plan"]
    bad = deepcopy(fixture)
    bad["adjustments"][0]["to"][0]["basis"] = ["P1:4"]
    try:
        pc.compile_effective_plan(bad, payload)
    except ValueError as exc:
        assert str(exc) == "Replacement Update: unexpected fields"
    else:
        raise AssertionError("Extra replacement field was accepted")
    paths = ["config/preconditioner_prompt.md", "config/prompt.diff",
             "requests/B_UNSENT.json", "reports/DESIGN.md", "run_once.py"]
    record = {"at": ev.now(), "files_sha256": {p: sha(E / p) for p in paths},
              "only_system_changed_from_original_B": True,
              "original_AB_same_system": True, "valid_fixture_compiles": True,
              "invalid_nested_basis_rejected": True, "model_calls": 0,
              "maximum_http_requests": 1, "automatic_retries": 0}
    with (E / "config/freeze.json").open("x") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    print("FROZEN: offline checks passed", flush=True)


def run():
    assert (E / "config/protected_before.json").exists()
    for p, h in read(E / "config/freeze.json")["files_sha256"].items():
        assert sha(E / p) == h, p
    req, payload, cfg = verify()
    with (E / "config/execution_claim.json").open("x") as f:
        json.dump({"at": ev.now(), "maximum_http_requests": 1}, f)
    key = os.environ.get("OPENAI_API_KEY") or dotenv_values(ROOT / ".env").get("OPENAI_API_KEY")
    assert key, "Credential missing; no request sent"
    generate = grouping.live_generator(base_url=cfg["endpoint"].removesuffix("/chat/completions"),
                                      key=key, model=cfg["model"],
                                      max_tokens=cfg["max_tokens"], timeout=cfg["timeout_seconds"])
    assert generate.call_config == cfg
    dest = E / "runs/B"
    dest.mkdir(exist_ok=False)
    count = 0
    original_post = requests.Session.post

    def guarded_post(session, url, **kwargs):
        nonlocal count
        assert count == 0 and url == req["endpoint"] and kwargs["json"] == req["body"]
        assert kwargs["timeout"] == (10, 300) and kwargs["allow_redirects"] is False
        assert not session.trust_env
        assert all(a.max_retries.total == 0 for a in session.adapters.values())
        assert sha(dest / "request.json") == sha(E / "requests/B_UNSENT.json")
        count += 1
        ev.save(dest / "dispatch.json", {"at": ev.now(), "http_attempt": count,
                                        "request_sha256": sha(dest / "request.json")})
        return original_post(session, url, **kwargs)

    meta = {"started_at": ev.now(), "automatic_retries": 0, "experiment": "same-format B completion"}
    start = time.monotonic()
    stage = "transport"
    print("START B same-format", flush=True)
    try:
        with patch.object(requests.Session, "post", guarded_post):
            response = generate(req["body"]["messages"], dest)
        ev.save(dest / "response.json", response)
        (dest / "raw_output.txt").write_text(response["content"])
        ev.save(dest / "usage.json", {k: response.get(k) for k in
                                    ["usage", "response_model", "finish_reason"]})
        meta.update({k: response.get(k) for k in ["usage", "response_model", "finish_reason"]})
        stage = "completion"
        assert response["finish_reason"] == "stop", "Abnormal finish reason"
        stage = "json_parse"
        parsed = parse_json_response(response["content"])
        ev.save(dest / "parsed.json", parsed)
        stage = "schema_compile"
        effective = pc.compile_effective_plan(parsed, payload)
        ev.save(dest / "preconditioner.json", parsed)
        ev.save(dest / "effective_plan.json", effective)
        ev.save(dest / "validation.json", {"valid": True, "decision": parsed["decision"],
                                          "effective_null": effective is None})
        meta.update(status="valid", decision=parsed["decision"])
    except Exception as exc:
        err = {"type": type(exc).__name__, "message": str(exc), "stage": stage}
        ev.save(dest / "error.json", err)
        ev.save(dest / "validation.json", {"valid": False, **err})
        meta.update(status="technical_failure", error=err)
    finally:
        meta.update(finished_at=ev.now(), elapsed_seconds=time.monotonic() - start,
                    http_attempts=count)
        ev.save(dest / "run.json", meta)
        print("FINISH " + meta["status"], flush=True)


if __name__ == "__main__":
    freeze() if "--freeze" in sys.argv else run()
