"""Bounded live comprehension validation, then one gated production smoke call."""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback

import requests
from dotenv import dotenv_values

from experiments.methods.v23_3.memory_compaction_offline_001.compact import compact_memory, validate_view
from .probes import build_probe, score_answers
from src.skill_evolution.v23 import grouping
from src.skill_evolution.v23.preconditioner import compile_effective_plan
from src.skill_evolution.v23_3.update_patch import normalize_update_patches
from src.skill_evolution.v22.diagnosis_editor import parse_json_response


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OFFLINE = HERE.parent / "memory_compaction_offline_001"
SOURCE_FILES = [HERE / "run.py", HERE / "probes.py", HERE / "PROTOCOL.md",
                OFFLINE / "compact.py", OFFLINE / "MODEL_FORMAT.md",
                HERE.parent / "p3a_transport_retry_001/run.py",
                HERE.parent / "p3a_first_live_comparison_001/run.py",
                ROOT / "src/skill_evolution/v23/grouping.py",
                ROOT / "src/skill_evolution/v23/preconditioner.py",
                ROOT / "src/skill_evolution/v23_3/update_patch.py"]
LABELS = ("R05", "R06", "production_B")
PROBE_SYSTEM = """You are validating comprehension of a historical evidence input format.
This is a factual reading test, not a request to modify a Skill or generate a Plan.
Answer the supplied questions using only the accompanying compact payload. Do not
reconstruct omitted facts from guesses or memory summaries. Return one JSON object:
{"answers": {"question_id": answer_object, ...}}. Use exactly the question IDs and
the fields/types requested in each question. Return original strings exactly when
asked. No extra fields, commentary, explanations or reasoning transcript.
"""


from experiments.methods.v23_3.archive_io import resolve

def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(resolve(Path(path)).read_text(encoding='utf-8'))


def save(path, value):
    resolve(path.parent).mkdir(parents=True, exist_ok=True)
    with resolve(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def environment():
    env = dotenv_values(ROOT / ".env")
    base = os.environ.get("OPENAI_BASE_URL") or env.get("OPENAI_BASE_URL")
    key = os.environ.get("OPENAI_API_KEY") or env.get("OPENAI_API_KEY")
    assert base and key, "Existing model route and credential required"
    cfg = grouping.call_configuration(base_url=base, model="deepseek-v4.1-flash",
                                      max_tokens=16384, timeout=300)
    assert cfg["endpoint"] == "http://llm-proxy.intra.xiaojukeji.com/chat/completions"
    assert cfg["model"] == "deepseek-v4.1-flash"
    return key, cfg


def prepare():
    _, cfg = environment()
    for label in LABELS:
        case = "P3A_B" if label == "production_B" else label
        folder = OFFLINE / "cases" / case
        full, payload = read(folder / "original_payload.json"), read(folder / "compact_payload.json")
        assert payload["memory"] == compact_memory(full["memory"])
        validate_view(payload["memory"], full["memory"])
        assert {k: v for k, v in payload.items() if k != "memory"} == {
            k: v for k, v in full.items() if k != "memory"}
        save(HERE / "config" / label / "full_payload.json", full)
        save(HERE / "config" / label / "compact_payload.json", payload)
        if label == "production_B":
            messages = read(folder / "compact_messages.json")
            assert json.loads(messages[1]["content"]) == payload
            max_tokens = 32768
        else:
            questions, expected = build_probe(full, payload, case=label)
            save(HERE / "config" / label / "questions.json", questions)
            save(HERE / "config" / label / "expected.json", expected)
            messages = [
                {"role": "system", "content": PROBE_SYSTEM + "\n" +
                 resolve(OFFLINE / 'MODEL_FORMAT.md').read_text(encoding='utf-8')},
                {"role": "user", "content": json.dumps({"questions": questions, "payload": payload},
                                                     ensure_ascii=False, separators=(",", ":"))},
            ]
            max_tokens = 16384
        body = {k: v for k, v in cfg.items() if k not in ("endpoint", "timeout_seconds")}
        body.update(max_tokens=max_tokens, messages=messages)
        req = {"endpoint": cfg["endpoint"], "timeout": [60, 300], "body": body,
               "max_http_requests": 1}
        save(HERE / "config" / label / "request.json", req)
        size = len(requests.Request("POST", req["endpoint"], json=body).prepare().body)
        print("FROZEN", label, "request_bytes", size, "max_tokens", max_tokens, flush=True)
    save(HERE / "config/freeze.json", {
        "at": now(), "route_config": cfg, "max_logical_calls": 3, "max_http_requests": 3,
        "sources": {str(p.relative_to(ROOT)): resolve(p).read_text(encoding='utf-8') for p in SOURCE_FILES},
        "no_editor_replay_or_memory_write": True,
    })


def verify_frozen():
    frozen = read(HERE / "config/freeze.json")
    key, cfg = environment()
    assert cfg == frozen["route_config"]
    for rel, content in frozen["sources"].items():
        assert resolve(ROOT / rel).read_text(encoding='utf-8') == content, f"Frozen source changed: {rel}"
    for label in LABELS:
        case = "P3A_B" if label == "production_B" else label
        folder, dest = OFFLINE / "cases" / case, HERE / "config" / label
        full, compact = read(dest / "full_payload.json"), read(dest / "compact_payload.json")
        assert full == read(folder / "original_payload.json")
        assert compact == read(folder / "compact_payload.json")
        req = read(dest / "request.json")
        if label == "production_B":
            expected_messages = read(folder / "compact_messages.json")
        else:
            questions, expected = build_probe(full, compact, case=label)
            assert questions == read(dest / "questions.json") and expected == read(dest / "expected.json")
            expected_messages = [
                {"role": "system", "content": PROBE_SYSTEM + "\n" +
                 resolve(OFFLINE / 'MODEL_FORMAT.md').read_text(encoding='utf-8')},
                {"role": "user", "content": json.dumps({"questions": questions, "payload": compact},
                                                     ensure_ascii=False, separators=(",", ":"))}]
        expected_body = {k: v for k, v in cfg.items() if k not in ("endpoint", "timeout_seconds")}
        expected_body.update(max_tokens=32768 if label == "production_B" else 16384,
                             messages=expected_messages)
        assert req == {"endpoint": cfg["endpoint"], "timeout": [60, 300], "body": expected_body,
                       "max_http_requests": 1}
    return key


def production_gate(results):
    return all(results.get(label, {}).get("status") == "probe_passed" for label in ("R05", "R06"))


def transport():
    # Reuse the already exercised single-request transport and non-secret send audit.
    path = HERE.parent / "p3a_transport_retry_001/run.py"
    spec = importlib.util.spec_from_file_location("compact_live_transport", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.send_once


def run(label):
    assert label in LABELS
    key = verify_frozen()
    if label == "production_B":
        results = {case: read(HERE / "results" / f"{case}.json") for case in ("R05", "R06")}
        assert production_gate(results), "Both factual probes must pass before production generation"
    req = read(HERE / "config" / label / "request.json")
    save(HERE / "results" / f"{label}_claim.json", {"at": now(), "max_http_requests": 1})
    out = HERE / "runs" / label
    resolve(out).mkdir(parents=True, exist_ok=False)
    save(out / "messages.json", req["body"]["messages"])
    dest = out / "http/001"
    resolve(dest).mkdir(parents=True)
    started = time.monotonic()
    meta = {"label": label, "started_at": now(), "stage": "transport",
            "status": "started", "http_requests_started": 0}
    try:
        send = transport()
        meta["http_requests_started"] = 1
        response = send(req, key, dest, {"connect_upload_timeout_seconds": 60,
                                      "read_timeout_seconds": 300})
        save(out / "response.json", response)
        (resolve(out / "raw_output.txt")).write_text(response.get("content", ""), encoding="utf-8")
        meta.update(stage="completion", finish_reason=response.get("finish_reason"),
                    usage=response.get("usage"), response_model=response.get("response_model"),
                    content_chars=len(response.get("content", "")))
        assert response.get("finish_reason") == "stop", "Incomplete model response; no resampling"
        meta["stage"] = "parse"
        parsed = parse_json_response(response["content"])
        save(out / "parsed.json", parsed)
        if label != "production_B":
            meta["stage"] = "factual_checks"
            evaluation = score_answers(parsed, read(HERE / "config" / label / "expected.json"))
            save(out / "evaluation.json", evaluation)
            meta.update(status="probe_passed" if evaluation["passed"] else "probe_failed",
                        correct=sum(c["passed"] for c in evaluation["checks"].values()),
                        questions=len(read(HERE / "config" / label / "expected.json")))
        else:
            meta["stage"] = "patch_compile"
            full = read(HERE / "config" / label / "full_payload.json")
            normalized, effective = normalize_update_patches(parsed, full)
            assert compile_effective_plan(normalized, full) == effective
            save(out / "preconditioner.json", normalized)
            save(out / "effective_plan.json", effective)
            meta.update(status="compiled", decision=parsed["decision"],
                        patch_count=sum(bool(a["to"]) for a in parsed["adjustments"]),
                        adjustment_count=len(parsed["adjustments"]),
                        manual_evidence_review_required=True)
    except Exception as exc:
        (resolve(out / "traceback.txt")).write_text(traceback.format_exc(), encoding="utf-8")
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
