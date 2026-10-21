"""Exactly two factual-reading probes. No generation stage or retry."""
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import requests

from experiments.methods.v23_3.memory_compaction_live_validation_001.run import (
    PROBE_SYSTEM, environment, now, read, save, transport,
)
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from .compact_v3 import explicit_view, validate_explicit
from .offline import HERE, ROOT, V1, V2, OLD_LIVE
from .probes_v3 import adapted_probe, score_answers

LABELS = ("R05", "R06")


def request_for(label, cfg):
    folder = HERE / "cases" / label
    original = read(V1 / "cases" / label / "original_payload.json")
    prior = read(V1 / "cases" / label / "compact_payload.json")
    payload = read(folder / "compact_payload.json")
    view, aliases = explicit_view(prior["memory"])
    assert payload == {**original, "memory": view}
    validate_explicit(view, original["memory"], prior["memory"], aliases)
    questions, expected, changes = adapted_probe(original, prior, payload, case=label)
    assert questions == read(folder / "questions.json")
    assert expected == read(folder / "expected.json")
    assert changes == read(folder / "question_changes.json")
    messages = [
        {"role": "system", "content": PROBE_SYSTEM + "\n" +
         (HERE / "MODEL_FORMAT.md").read_text(encoding="utf-8")},
        {"role": "user", "content": json.dumps({"questions": questions, "payload": payload},
                                             ensure_ascii=False, separators=(",", ":"))},
    ]
    body = {k: v for k, v in cfg.items() if k not in ("endpoint", "timeout_seconds")}
    body.update(max_tokens=16384, messages=messages)
    old_body = read(OLD_LIVE / "config" / label / "request.json")["body"]
    assert {k: v for k, v in body.items() if k != "messages"} == {
        k: v for k, v in old_body.items() if k != "messages"}
    return {"endpoint": cfg["endpoint"], "timeout": [60, 300], "body": body,
            "max_http_requests": 1}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    _, cfg = environment()
    for label in LABELS:
        req = request_for(label, cfg)
        save(HERE / "config" / label / "request.json", req)
        size = len(requests.Request("POST", req["endpoint"], json=req["body"]).prepare().body)
        print("FROZEN", label, "request_bytes", size, "max_tokens", 16384, flush=True)
    files = list(HERE.glob("*.py")) + [HERE / "MODEL_FORMAT.md", HERE / "PROTOCOL.md"]
    files += list((HERE / "cases").rglob("*.json")) + list((HERE / "config").rglob("*.json"))
    files += [V2 / "compact_v2.py", V2 / "probes_v2.py"]
    files += [OLD_LIVE / "run.py", OLD_LIVE / "probes.py", V1 / "compact.py",
              HERE.parent / "p3a_transport_retry_001/run.py",
              HERE.parent / "p3a_first_live_comparison_001/run.py",
              ROOT / "src/skill_evolution/v23/grouping.py",
              ROOT / "src/skill_evolution/v22/diagnosis_editor.py"]
    save(HERE / "config/freeze.json", {
        "at": now(), "route_config": cfg, "max_logical_calls": 2, "max_http_requests": 2,
        "sha256": {str(p.relative_to(ROOT)): digest(p) for p in files},
        "no_generation_editor_replay_or_integration": True,
    })


def verify_frozen():
    frozen = read(HERE / "config/freeze.json")
    key, cfg = environment()
    assert cfg == frozen["route_config"]
    for rel, checksum in frozen["sha256"].items():
        assert digest(ROOT / rel) == checksum, f"Frozen file changed: {rel}"
    for label in LABELS:
        assert read(HERE / "config" / label / "request.json") == request_for(label, cfg)
    return key


def run(label):
    assert label in LABELS
    key = verify_frozen()
    req = read(HERE / "config" / label / "request.json")
    save(HERE / "results" / f"{label}_claim.json", {"at": now(), "max_http_requests": 1})
    out = HERE / "runs" / label
    out.mkdir(parents=True, exist_ok=False)
    dest = out / "http/001"
    dest.mkdir(parents=True)
    started = time.monotonic()
    meta = {"label": label, "started_at": now(), "stage": "transport",
            "status": "started", "http_requests_started": 0}
    try:
        send = transport()
        meta["http_requests_started"] = 1
        response = send(req, key, dest, {"connect_upload_timeout_seconds": 60,
                                      "read_timeout_seconds": 300})
        save(out / "response.json", response)
        (out / "raw_output.txt").write_text(response.get("content", ""), encoding="utf-8")
        meta.update(stage="completion", finish_reason=response.get("finish_reason"),
                    usage=response.get("usage"), response_model=response.get("response_model"),
                    content_chars=len(response.get("content", "")))
        assert response.get("finish_reason") == "stop", "Incomplete response; no retry"
        meta["stage"] = "parse"
        parsed = parse_json_response(response["content"])
        save(out / "parsed.json", parsed)
        meta["stage"] = "factual_checks"
        expected = read(HERE / "cases" / label / "expected.json")
        evaluation = score_answers(parsed, expected)
        save(out / "evaluation.json", evaluation)
        meta.update(status="probe_passed" if evaluation["passed"] else "probe_failed",
                    correct=sum(c["passed"] for c in evaluation["checks"].values()),
                    questions=len(expected))
    except Exception as exc:
        (out / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
        meta.update(status="failed", error_type=type(exc).__name__, error=str(exc))
    finally:
        meta.update(finished_at=now(), elapsed_seconds=time.monotonic() - started)
        save(out / "run.json", meta)
        save(HERE / "results" / f"{label}.json", meta)
    print(json.dumps(meta, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "prepare":
        prepare()
    else:
        run(sys.argv[1])
