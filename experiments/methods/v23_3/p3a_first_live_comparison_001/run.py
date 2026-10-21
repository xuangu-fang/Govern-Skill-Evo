"""One R05 live experiment: immutable inputs, bounded transport retries, no rollout."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
E = Path(__file__).resolve().parent
ROOT = E.parents[3]
sys.path.insert(0, str(ROOT))

import requests
from dotenv import dotenv_values
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v23 import grouping, memory, preconditioner as v23
from src.skill_evolution.v23_3 import diagnosis, preconditioner as v233
from src.skill_evolution.v23_3.update_patch import normalize_update_patches

S = ROOT / "artifacts/methods/v23/v23_alfworld_formal_001/S1"
GD = S / "rounds/R05/grouping/attempts/002"


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def env_config():
    env = dotenv_values(ROOT / ".env")
    base = os.environ.get("OPENAI_BASE_URL") or env.get("OPENAI_BASE_URL")
    key = os.environ.get("OPENAI_API_KEY") or env.get("OPENAI_API_KEY")
    assert base and key, "Configured route/credential required"
    return base, key, grouping.call_configuration(
        base_url=base, model="deepseek-v4.1-flash", max_tokens=16384, timeout=300)


def request(messages, cfg):
    return {"endpoint": cfg["endpoint"], "timeout_seconds": cfg["timeout_seconds"], "attempts": 1,
            "body": {**{k: v for k, v in cfg.items() if k not in ("endpoint", "timeout_seconds")},
                     "messages": messages}}


def budget(messages):
    encoded = json.dumps(messages, ensure_ascii=False)
    assert len(encoded) <= 4000000 and len(encoded.encode()) <= 6000000
    return {"message_chars": len(encoded), "message_utf8_bytes": len(encoded.encode())}


def prepare():
    assert (E / "P3A_EXPERIMENT_PROTOCOL.md").exists()
    grouped = grouping.load_grouping(GD)
    olddir = S / "rounds/R05/preconditioner/attempts/001"
    old, ri = read(olddir / "input.json"), read(S / "rounds/R05/round_input.json")
    mem = memory.load_memory(S / ri["state"]["active_memory"])
    assert mem == ri["memory"] == old["memory"]
    assert mem == json.loads(read(olddir / "request.json")["body"]["messages"][1]["content"])["memory"]
    assert [x["id"] for x in mem["entries"]] == ["M1", "M2", "M3", "M6", "M7", "M8", "M9"]
    assert grouped == {k: v for k, v in old.items() if k not in ("diagnosis", "memory")}
    base, key, cfg = env_config()
    assert cfg["model"] == "deepseek-v4.1-flash"
    save(E / "config/grouping.json", grouped)
    save(E / "config/memory.json", mem)
    save(E / "config/call_config.json", cfg)
    save(E / "config/sources.json", {
        "grouping_directory": str(GD), "round_input": str(S / "rounds/R05/round_input.json"),
        "active_memory": str(S / ri["state"]["active_memory"]), "formal_preconditioner": str(olddir),
        "historical_call_config": read(olddir / "run.json")["call_config"],
        "memory_ids": [x["id"] for x in mem["entries"]], "credential_present": bool(key)})
    for name, path in [("diagnosis_prompt.md", diagnosis.PROMPT_PATH),
                       ("A_preconditioner_prompt.md", v23.PROMPT_PATH),
                       ("B_preconditioner_prompt.md", v233.PROMPT_PATH)]:
        (E / "config" / name).write_bytes(path.read_bytes())
    messages = diagnosis.messages_for(grouped)
    assert "memory" not in json.loads(messages[1]["content"])
    save(E / "requests/diagnosis.json", request(messages, cfg))
    save(E / "config/preflight.json", {
        "frozen_at": now(), "diagnosis_budget": budget(messages), "memory_exact": True,
        "grouping_exact": True, "max_logical_calls": 3, "max_http_per_logical": 3,
        "protocol": (E / "P3A_EXPERIMENT_PROTOCOL.md").read_text(),
        "diagnosis_prompt_equals_versioned_source": True, "capacity_probe": False})
    print("FROZEN", json.dumps(budget(messages)), flush=True)


def verify_frozen():
    assert read(E / "config/preflight.json")["protocol"] == (E / "P3A_EXPERIMENT_PROTOCOL.md").read_text()
    for name, path in [("diagnosis_prompt.md", diagnosis.PROMPT_PATH),
                       ("A_preconditioner_prompt.md", v23.PROMPT_PATH),
                       ("B_preconditioner_prompt.md", v233.PROMPT_PATH)]:
        assert (E / "config" / name).read_bytes() == path.read_bytes()
    assert read(E / "config/grouping.json") == grouping.load_grouping(GD)
    assert read(E / "config/memory.json") == memory.load_memory(Path(read(E / "config/sources.json")["active_memory"]))


def generator(label):
    """Existing single-HTTP generator; only the preregistered transport failures retry."""
    verify_frozen()
    base, key, cfg = env_config()
    assert cfg == read(E / "config/call_config.json")
    expected = read(E / f"requests/{label}.json")
    inner = grouping.live_generator(base_url=base, key=key, model=cfg["model"],
                                   max_tokens=cfg["max_tokens"], timeout=cfg["timeout_seconds"])
    assert inner.call_config == cfg

    def generate(messages, directory):
        assert request(messages, cfg) == expected
        budget(messages)
        save(E / f"results/{label}_claim.json", {"started_at": now(), "max_http": 3})
        for attempt in range(1, 4):
            dest = Path(directory) / "http" / f"{attempt:03}"
            dest.mkdir(parents=True, exist_ok=False)
            started = time.monotonic()
            meta = {"label": label, "attempt": attempt, "started_at": now()}
            failure = None
            try:
                response = inner(messages, dest)
                save(dest / "response.json", response)
                meta["status"] = "response_received"
            except Exception as exc:
                failure = exc
                code = read(dest / "http_status.json")["status_code"] if (dest / "http_status.json").exists() else None
                transient = code in (408, 429, 500, 502, 503, 504) or (
                    isinstance(exc, (requests.Timeout, requests.ConnectionError))
                    and not isinstance(exc, requests.exceptions.SSLError))
                meta.update(status="technical_failure", http_status=code, transient=transient,
                            error_type=type(exc).__name__, error=str(exc))
            finally:
                meta.update(finished_at=now(), elapsed_seconds=time.monotonic() - started)
                if (dest / "request.json").exists():
                    assert read(dest / "request.json") == expected
                save(dest / "attempt.json", meta)
                print(label, attempt, meta["status"], round(meta["elapsed_seconds"], 2), flush=True)
            if failure is None:
                return response
            if not meta["transient"] or attempt == 3:
                raise failure
            time.sleep(5 if attempt == 1 else 10)
    generate.call_config = cfg
    return generate


def run_diagnosis():
    out = E / "runs/diagnosis"
    assert not out.exists(), "Logical call already started; only inspect/reload"
    started = time.monotonic()
    result = {"started_at": now()}
    try:
        saved = diagnosis.run_diagnosis(GD, out, generate=generator("diagnosis"),
                                        max_input_chars=4000000,
                                        call_config=read(E / "config/call_config.json"))
        result.update(status="valid", decision=saved["diagnosis"]["decision"])
    except Exception as exc:
        result.update(status="technical_failure", error_type=type(exc).__name__, error=str(exc))
    result.update(finished_at=now(), elapsed_seconds=time.monotonic() - started)
    save(E / "results/diagnosis_execution.json", result)
    print(json.dumps(result), flush=True)


def freeze_common():
    verify_frozen()
    assert read(E / "results/diagnosis_gate.json")["passed"] is True
    saved = diagnosis.load_diagnosis(E / "runs/diagnosis")
    saved["memory"] = read(E / "config/memory.json")
    messages = {"A": v23.messages_for(saved), "B": v233.messages_for(saved)}
    payload = v23.preconditioner_input(saved)
    assert messages["A"][1] == messages["B"][1]
    assert json.loads(messages["A"][1]["content"]) == payload
    keep = {"decision": "ready", "reason": "Offline input compatibility only.", "adjustments": [], "checks": None}
    assert v23.compile_effective_plan(keep, payload) == normalize_update_patches(keep, payload)[1] == payload["plan"]
    save(E / "config/common_saved.json", saved)
    save(E / "config/common_payload.json", payload)
    save(E / "config/original_plan.json", payload["plan"])
    cfg = read(E / "config/call_config.json")
    for arm in ("A", "B"):
        save(E / f"requests/{arm}.json", request(messages[arm], cfg))
    save(E / "results/common_input_checks.json", {
        "frozen_at": now(), "same_user_content": True, "same_background": True,
        "same_memory": True, "keep_compiles_both": True,
        "runs": [r["ref"] for r in payload["runs"]],
        "groups": [g["group_id"] for g in payload["grouping"]["groups"]],
        "command_sets": len(payload["command_sets"]),
        "budgets": {arm: budget(messages[arm]) for arm in messages}})


def run_arm(arm):
    assert arm in ("A", "B")
    assert read(E / "results/diagnosis_gate.json")["passed"] is True
    if arm == "B":
        assert (E / "results/A_execution.json").exists(), "A must finish first"
    verify_frozen()
    saved = read(E / "config/common_saved.json")
    loaded = diagnosis.load_diagnosis(E / "runs/diagnosis")
    assert saved == {**loaded, "memory": read(E / "config/memory.json")}
    payload = v23.preconditioner_input(saved)
    assert payload == read(E / "config/common_payload.json")
    req = read(E / f"requests/{arm}.json")
    assert read(E / "requests/A.json")["body"]["messages"][1] == read(E / "requests/B.json")["body"]["messages"][1]
    expected_messages = (v23 if arm == "A" else v233).messages_for(saved)
    assert req["body"]["messages"] == expected_messages
    out = E / "runs" / arm
    out.mkdir(exist_ok=False)
    save(out / "input.json", saved)
    save(out / "messages.json", expected_messages)
    (out / "prompt.md").write_text(expected_messages[0]["content"], encoding="utf-8")
    started = time.monotonic()
    meta = {"arm": arm, "started_at": now(), "stage": "transport"}
    try:
        response = generator(arm)(expected_messages, out)
        save(out / "response.json", response)
        (out / "raw_output.txt").write_bytes(response["content"].encode())
        meta.update(stage="completion", finish_reason=response.get("finish_reason"),
                    response_model=response.get("response_model"), usage=response.get("usage"))
        assert response.get("finish_reason") == "stop", "Model response did not finish normally"
        meta["stage"] = "parse"
        parsed = parse_json_response(response["content"])
        save(out / "parsed.json", parsed)
        meta["stage"] = "schema_patch_compile"
        normalized, effective = ((parsed, v23.compile_effective_plan(parsed, payload))
                                 if arm == "A" else normalize_update_patches(parsed, payload))
        save(out / "preconditioner.json", normalized)
        save(out / "effective_plan.json", effective)
        assert v23.compile_effective_plan(normalized, payload) == effective
        meta.update(status="valid", decision=parsed["decision"], stage="complete")
        save(out / "validation.json", {"valid": True, "effective_null": effective is None})
    except Exception as exc:
        meta.update(status="technical_failure", error_type=type(exc).__name__, error=str(exc))
        save(out / "validation.json", {"valid": False, "stage": meta["stage"],
                                      "error_type": type(exc).__name__, "error": str(exc)})
    meta.update(finished_at=now(), elapsed_seconds=time.monotonic() - started)
    save(out / "run.json", meta)
    save(E / f"results/{arm}_execution.json", meta)
    print(json.dumps(meta, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "prepare": prepare()
    elif action == "diagnosis": run_diagnosis()
    elif action == "freeze_common": freeze_common()
    elif action in ("A", "B"): run_arm(action)
    else: raise ValueError("Unknown stage")
