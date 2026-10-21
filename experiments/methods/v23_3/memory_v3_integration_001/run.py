"""One production B call, then one A call reusing that B as the comparison arm."""
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import requests

from experiments.methods.v23_3.memory_compaction_live_validation_001.run import (
    environment, now, read, save, transport,
)
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v23 import preconditioner as v23
from src.skill_evolution.v23_3 import diagnosis, preconditioner as pc
from src.skill_evolution.v23_3.memory_view import FORMAT, project_messages

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = HERE.parent / "p3a_first_live_comparison_001"
DD = OLD / "runs/diagnosis"


def configuration():
    key, cfg = environment()
    return key, {**cfg, "max_tokens": 32768}


def inputs():
    saved = {**diagnosis.load_diagnosis(DD), "memory": read(OLD / "config/memory.json")}
    assert saved == read(OLD / "config/common_saved.json")
    assert v23.preconditioner_input(saved) == read(OLD / "config/common_payload.json")
    return saved


def messages(saved):
    result = {"A": project_messages(v23.messages_for(saved)), "B": pc.messages_for(saved)}
    assert result["A"][1] == result["B"][1]
    return result


def request(msgs, cfg):
    body = {k: v for k, v in cfg.items() if k not in ("endpoint", "timeout_seconds")}
    body["messages"] = msgs
    assert len(json.dumps(msgs, ensure_ascii=False)) <= 4000000
    return {"endpoint": cfg["endpoint"], "timeout": [60, 300], "max_http_requests": 1, "body": body}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare():
    saved = inputs()
    _, cfg = configuration()
    for arm, msgs in messages(saved).items():
        req = request(msgs, cfg)
        save(HERE / "config" / f"{arm}_request.json", req)
        print(arm, "request_bytes", len(requests.Request("POST", req["endpoint"], json=req["body"]).prepare().body),
              "max_tokens", cfg["max_tokens"], flush=True)
    save(HERE / "config/common_saved.json", saved)
    save(HERE / "config/full_payload.json", v23.preconditioner_input(saved))
    save(HERE / "config/model_input.json", pc.model_input(saved))
    files = [HERE / "run.py", HERE / "PROTOCOL.md"]
    for folder in ("src/skill_evolution/v23", "src/skill_evolution/v23_3", "tests/skill_evolution/v23_3"):
        files += [p for p in (ROOT / folder).iterdir() if p.suffix in (".py", ".md")]
    files += list((HERE / "config").glob("*.json"))
    files += [HERE.parent / "p3a_transport_retry_001/run.py",
              OLD / "run.py", HERE.parent / "memory_compaction_live_validation_001/run.py",
              ROOT / "src/skill_evolution/v22/diagnosis_editor.py"]
    save(HERE / "config/freeze.json", {
        "at": now(), "call_config": cfg, "memory_view": FORMAT,
        "max_logical_calls": 2, "max_http_requests": 2, "sequence": ["B", "A"],
        "same_user_input": True,
        "sha256": {str(p.relative_to(ROOT)): digest(p) for p in files},
    })


def verify():
    frozen = read(HERE / "config/freeze.json")
    key, cfg = configuration()
    assert cfg == frozen["call_config"]
    for rel, sha in frozen["sha256"].items():
        assert digest(ROOT / rel) == sha, rel
    saved = inputs()
    assert saved == read(HERE / "config/common_saved.json")
    for arm, msgs in messages(saved).items():
        assert request(msgs, cfg) == read(HERE / "config" / f"{arm}_request.json")
    return key, cfg, saved


def load_a(out, saved):
    """Independently reparse/recompile the A adapter's original raw response."""
    assert read(out / "input.json") == saved
    assert read(out / "model_input.json") == pc.model_input(saved)
    assert read(out / "messages.json") == messages(saved)["A"]
    response = read(out / "response.json")
    assert response["finish_reason"] == "stop"
    assert (out / "raw_output.txt").read_text() == response["content"]
    parsed = parse_json_response(response["content"])
    assert parsed == read(out / "parsed.json") == read(out / "preconditioner.json")
    effective = v23.compile_effective_plan(parsed, v23.preconditioner_input(saved))
    assert effective == read(out / "effective_plan.json")
    return {**saved, "preconditioner": parsed, "effective_plan": effective}


def run(arm):
    assert arm in ("B", "A")
    key, cfg, saved = verify()
    if arm == "A":
        assert read(HERE / "results/B_execution.json")["production_gate_passed"]
        assert (HERE / "results/B_EVALUATION.md").is_file(), "Evaluate B before generating A"
        assert pc.load_preconditioner(HERE / "runs/B")["effective_plan"] is not None
    claim = HERE / "results" / f"{arm}_claim.json"
    save(claim, {"at": now(), "max_http_requests": 1})
    req = read(HERE / "config" / f"{arm}_request.json")
    out = HERE / "runs" / arm
    started = time.monotonic()
    meta = {"arm": arm, "started_at": now(), "http_requests_started": 0, "status": "started",
            "production_gate_passed": False, "stage": "request"}

    def generate(actual, directory):
        assert actual == req["body"]["messages"]
        assert meta["http_requests_started"] == 0
        dest = Path(directory) / "http/001"
        dest.mkdir(parents=True, exist_ok=False)
        meta["http_requests_started"] = 1
        response = transport()(req, key, dest, {"connect_upload_timeout_seconds": 60,
                                               "read_timeout_seconds": 300})
        meta.update(finish_reason=response.get("finish_reason"), usage=response.get("usage"),
                    response_model=response.get("response_model"), stage="parse_compile_reload")
        return response
    generate.call_config = cfg
    try:
        if arm == "B":
            gd = read(DD / "run.json")["grouping_directory"]
            result = pc.run_preconditioner(gd, DD, out, generate=generate, memory=saved["memory"],
                                          max_input_chars=4000000, call_config=cfg)
            assert pc.load_preconditioner(out, expected_call_config=cfg, expected_memory_view=FORMAT) == result
        else:
            out.mkdir(parents=True, exist_ok=False)
            save(out / "input.json", saved)
            save(out / "model_input.json", pc.model_input(saved))
            save(out / "messages.json", req["body"]["messages"])
            response = generate(req["body"]["messages"], out)
            save(out / "response.json", response)
            (out / "raw_output.txt").write_text(response["content"])
            assert response["finish_reason"] == "stop", "Incomplete A response"
            parsed = parse_json_response(response["content"])
            save(out / "parsed.json", parsed)
            effective = v23.compile_effective_plan(parsed, v23.preconditioner_input(saved))
            save(out / "preconditioner.json", parsed)
            save(out / "effective_plan.json", effective)
            result = load_a(out, saved)
            save(out / "validation.json", {"valid": True, "reloaded": True})
        effective = result["effective_plan"]
        meta.update(status="valid", stage="complete", decision=result["preconditioner"]["decision"],
                    effective_plan_present=effective is not None, reloaded=True,
                    production_gate_passed=effective is not None)
    except Exception as exc:
        out.mkdir(parents=True, exist_ok=True)
        (out / "traceback.txt").write_text(traceback.format_exc())
        meta.update(status="failed", error_type=type(exc).__name__, error=str(exc))
    finally:
        meta.update(finished_at=now(), elapsed_seconds=time.monotonic() - started)
        save(HERE / "results" / f"{arm}_execution.json", meta)
    print(json.dumps(meta, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    prepare() if sys.argv[1] == "prepare" else run(sys.argv[1])
