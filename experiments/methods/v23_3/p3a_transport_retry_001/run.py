"""Authorized A/B rerun: same frozen bodies; explicit (60, 300) transport."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
E = Path(__file__).resolve().parent
OLD = E.parent / "p3a_first_live_comparison_001"
spec = importlib.util.spec_from_file_location("p3a_frozen_source", OLD / "run.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
import requests
from src.skill_evolution.v23 import grouping, preconditioner as v23
from src.skill_evolution.v23_3 import diagnosis, preconditioner as v233
from src.skill_evolution.v23_3.update_patch import normalize_update_patches
from src.skill_evolution.v22.diagnosis_editor import parse_json_response

read, save, now = base.read, base.save, base.now
active_send = None


def audit(event, args):
    if event == "http.client.send" and active_send is not None:
        conn, data = args
        # Never serialize data or headers; lengths and socket state suffice.
        active_send["events"].append({
            "at": now(), "bytes": len(data), "is_body": len(data) == active_send["body_bytes"],
            "socket_timeout_seconds": conn.sock.gettimeout() if conn.sock is not None else None})


sys.addaudithook(audit)


def prepare():
    base.verify_frozen()
    _, _, cfg = base.env_config()
    assert cfg == read(OLD / "config/call_config.json")
    save(E / "config/transport.json", {"connect_upload_timeout_seconds": 60,
                                     "read_timeout_seconds": 300, "max_http_per_arm": 3})
    save(E / "config/freeze.json", {
        "at": now(), "source_experiment": str(OLD), "same_request_bodies": True,
        "diagnosis_reused": str(OLD / "runs/diagnosis"),
        "call_config": cfg, "protocol": (E / "P3A_RETRY_PROTOCOL.md").read_text()})
    for arm in ("A", "B"):
        save(E / f"config/{arm}_request.json", read(OLD / f"requests/{arm}.json"))
    print("Frozen rerun; no Diagnosis call", flush=True)


def send_once(req, key, dest, transport):
    global active_send
    timeout = (transport["connect_upload_timeout_seconds"], transport["read_timeout_seconds"])
    assert timeout == (60, 300)
    with requests.Session() as session:
        session.trust_env = False
        assert all(a.max_retries.total == 0 for a in session.adapters.values())
        prepared = session.prepare_request(requests.Request(
            "POST", req["endpoint"], json=req["body"], headers={"Authorization": f"Bearer {key}"}))
        body = prepared.body
        assert isinstance(body, bytes)
        assert json.loads(body) == req["body"]
        active_send = {"body_bytes": len(body), "events": []}
        save(dest / "request.json", {"endpoint": req["endpoint"], "body": req["body"],
                                    "timeout": list(timeout), "actual_body_bytes": len(body),
                                    "content_length": int(prepared.headers["Content-Length"]),
                                    "allow_redirects": False, "transport_retries": 0})
        try:
            raw = session.send(prepared, timeout=timeout, allow_redirects=False)
            (dest / "http_response.txt").write_bytes(raw.content)
            save(dest / "http_status.json", {"status_code": raw.status_code, "received_at": now()})
            if not 200 <= raw.status_code < 300:
                raise ValueError(f"Model API returned HTTP {raw.status_code}")
            return grouping.response_value(raw.json())
        finally:
            save(dest / "send_events.json", active_send)
            active_send = None


def generate(arm, out):
    base.verify_frozen()
    _, key, cfg = base.env_config()
    freeze = read(E / "config/freeze.json")
    assert cfg == freeze["call_config"]
    assert freeze["protocol"] == (E / "P3A_RETRY_PROTOCOL.md").read_text()
    assert (E / "config/original_protocol.md").read_bytes() == (OLD / "P3A_EXPERIMENT_PROTOCOL.md").read_bytes()
    req = read(E / f"config/{arm}_request.json")
    assert req == read(OLD / f"requests/{arm}.json")
    transport = read(E / "config/transport.json")
    assert transport == {"connect_upload_timeout_seconds": 60, "read_timeout_seconds": 300, "max_http_per_arm": 3}
    save(E / f"results/{arm}_claim.json", {"at": now(), "max_http": 3})
    for attempt in range(1, 4):
        dest = out / "http" / f"{attempt:03}"
        dest.mkdir(parents=True, exist_ok=False)
        started = time.monotonic()
        meta = {"arm": arm, "attempt": attempt, "started_at": now(), "timeout": [60, 300]}
        error = None
        try:
            response = send_once(req, key, dest, transport)
            save(dest / "response.json", response)
            meta["status"] = "response_received"
        except Exception as exc:
            error = exc
            (dest / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
            code = read(dest / "http_status.json")["status_code"] if (dest / "http_status.json").exists() else None
            transient = code in (408, 429, 500, 502, 503, 504) or (
                isinstance(exc, (requests.Timeout, requests.ConnectionError))
                and not isinstance(exc, requests.exceptions.SSLError))
            meta.update(status="technical_failure", transient=transient,
                        error_type=type(exc).__name__, error=str(exc))
        finally:
            meta.update(finished_at=now(), elapsed_seconds=time.monotonic() - started)
            save(dest / "attempt.json", meta)
            print(arm, attempt, meta["status"], round(meta["elapsed_seconds"], 2), flush=True)
        if error is None: return response
        if not meta["transient"] or attempt == 3: raise error
        time.sleep(5 if attempt == 1 else 10)


def run(arm):
    assert arm in ("A", "B")
    if arm == "B": assert (E / "results/A_execution.json").exists()
    original = diagnosis.load_diagnosis(OLD / "runs/diagnosis")
    saved = read(OLD / "config/common_saved.json")
    assert saved == {**original, "memory": read(OLD / "config/memory.json")}
    payload = v23.preconditioner_input(saved)
    assert payload == read(OLD / "config/common_payload.json")
    req = read(E / f"config/{arm}_request.json")
    assert req["body"]["messages"] == (v23 if arm == "A" else v233).messages_for(saved)
    assert read(E / "config/A_request.json")["body"]["messages"][1] == read(E / "config/B_request.json")["body"]["messages"][1]
    out = E / "runs" / arm
    out.mkdir(exist_ok=False)
    save(out / "input.json", saved)
    save(out / "messages.json", req["body"]["messages"])
    started = time.monotonic()
    meta = {"arm": arm, "started_at": now(), "stage": "transport"}
    try:
        response = generate(arm, out)
        save(out / "response.json", response)
        (out / "raw_output.txt").write_bytes(response["content"].encode())
        meta.update(stage="completion", finish_reason=response.get("finish_reason"),
                    response_model=response.get("response_model"), usage=response.get("usage"))
        assert response.get("finish_reason") == "stop", "Model response did not finish normally"
        meta["stage"] = "parse"
        parsed = parse_json_response(response["content"])
        save(out / "parsed.json", parsed)
        meta["stage"] = "schema_patch_compile"
        normalized, effective = ((parsed, v23.compile_effective_plan(parsed, payload)) if arm == "A"
                                 else normalize_update_patches(parsed, payload))
        save(out / "preconditioner.json", normalized)
        save(out / "effective_plan.json", effective)
        assert v23.compile_effective_plan(normalized, payload) == effective
        meta.update(status="valid", decision=parsed["decision"], stage="complete")
        save(out / "validation.json", {"valid": True, "effective_null": effective is None})
    except Exception as exc:
        (out / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
        meta.update(status="technical_failure", error_type=type(exc).__name__, error=str(exc))
        save(out / "validation.json", {"valid": False, "stage": meta["stage"],
                                      "error_type": type(exc).__name__, "error": str(exc)})
    meta.update(finished_at=now(), elapsed_seconds=time.monotonic() - started)
    save(out / "run.json", meta)
    save(E / f"results/{arm}_execution.json", meta)
    print(json.dumps(meta, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "prepare": prepare()
    else: run(sys.argv[1])
