"""One explicitly authorized R05 retry; reuse the frozen P1-B runner."""
import json
from pathlib import Path
import time
from unittest.mock import patch

from experiments.methods.v23_2.v23_2_diagnosis_construction_001 import run as original

EXP = Path(__file__).resolve().parent
ROOT, ev = original.ROOT, original.ev
OUTPUT = ROOT / "artifacts/methods/v23_2" / EXP.name


def protected_files():
    with patch.multiple(original.p1, EXP=EXP, OUTPUT=OUTPUT):
        files = original.p1.protected_files()
    files[".gitignore"] = original.p1.digest(ROOT / ".gitignore")
    return files


def run():
    assert not OUTPUT.exists() and not (EXP / "config/freeze.json").exists()
    original.p1.base.check_baseline()
    assert original.frozen_files() == ev.read(original.EXP / "config/p1_freeze.json")["sha256"]
    tests = ev.read(original.EXP / "results/offline_tests.json")
    assert tests["exit_code"] == 0 and tests["network_blocked"]
    assert tests["frozen_sha256"] == original.frozen_files()
    saved, entry = original.material("R05")
    failed = original.OUTPUT / "R05/attempts/001"
    messages = original.local.messages_for("diagnosis", saved, prompt_path=original.PROMPT)
    request = ev.read(failed / "request.json")
    assert messages == ev.read(failed / "messages.json") == request["body"]["messages"]
    assert saved == ev.read(failed / "input.json")
    assert entry["config"]["call_config"] == ev.read(failed / "run.json")["call_config"]
    assert set(json.loads(messages[1]["content"])) == {"parent", "command_sets", "runs", "grouping"}
    before = protected_files()
    ev.save(EXP / "config/protected_before.json", before)
    ev.save(EXP / "config/freeze.json", {
        "at": ev.now(), "authorization": "R05可以重试，然后重新给我回复",
        "max_additional_requests": 1, "automatic_retries": 0,
        "round": "R05", "config": entry["config"],
        "prompt_path": str(original.PROMPT),
        "original_failed_attempt": str(failed),
        "original_frozen_sha256": original.frozen_files(),
        "runner_sha256": original.p1.digest(__file__),
        "preflight": {"same_messages": True, "same_input": True, "same_config": True,
                      "no_memory": True, "inherited_offline_tests_passed": True},
    })
    OUTPUT.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    status = {"status": "started"}
    print("START R05 authorized single retry", flush=True)
    try:
        result = original.run_one(saved, OUTPUT / "R05", entry["config"])
        status = {"status": "valid", "decision": result["diagnosis"]["decision"]}
    except ev.Stopped as exc:
        status = {"status": "stopped", "error": str(exc)}
    finally:
        ev.save(OUTPUT / "summary.json", {
            "additional_logical_calls_started": 1, "outcome": status,
            "elapsed_seconds": time.monotonic() - started, "cost": ev.cost_summary(OUTPUT),
        })
        after = protected_files()
        changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
        ev.save(EXP / "results/protection.json", {
            "checked_files": len(before), "unchanged": not changed, "changed": changed,
        })
        assert not changed, changed
    print(json.dumps(ev.read(OUTPUT / "summary.json"), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    run()
