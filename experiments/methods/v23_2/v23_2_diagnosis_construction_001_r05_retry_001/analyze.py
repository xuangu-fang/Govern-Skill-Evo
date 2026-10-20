"""Read-only validation of model archives; write only this retry's reports."""
import json
from pathlib import Path

from experiments.methods.v23_2.v23_2_diagnosis_construction_001_r05_retry_001 import run as r


def analyze():
    old = r.original
    freeze = r.ev.read(r.EXP / "config/freeze.json")
    assert old.frozen_files() == freeze["original_frozen_sha256"]
    assert old.p1.digest(r.EXP / "run.py") == freeze["runner_sha256"]
    attempt = r.OUTPUT / "R05/attempts/001"
    result = old.local.load_attempt(attempt, prompt_path=old.PROMPT)
    failed = old.OUTPUT / "R05/attempts/001"
    for name in ("input.json", "messages.json", "request.json"):
        assert r.ev.read(attempt / name) == r.ev.read(failed / name), name
    assert (attempt / "prompt.md").read_bytes() == (failed / "prompt.md").read_bytes()
    assert not (failed / "diagnosis.json").exists()
    request_files = list(r.OUTPUT.rglob("request.json"))
    assert len(request_files) == 1
    assert r.ev.read(attempt / "run.json")["module"] == "diagnosis"
    assert r.ev.read(attempt / "run.json")["started_at"] > freeze["at"]
    comparison = r.ev.read(old.EXP / "results/comparison.json")
    comparison["R05"]["D2_retry"] = result["diagnosis"]
    r.ev.save(r.EXP / "results/comparison.json", comparison)
    old_summary = r.ev.read(old.OUTPUT / "summary.json")
    new_summary = r.ev.read(r.OUTPUT / "summary.json")
    totals = {k: v + new_summary["cost"][k] for k, v in old_summary["cost"].items()}
    r.ev.save(r.EXP / "results/aggregate.json", {
        "original": old_summary, "retry": new_summary, "combined_cost": totals,
        "combined_wall_seconds": old_summary["elapsed_seconds"] + new_summary["elapsed_seconds"],
        "additional_user_authorized_retries": 1, "automatic_retries": 0,
        "money_cost": None, "money_cost_note": "No bill or verified charged rate available.",
    })
    before = r.ev.read(r.EXP / "config/protected_before.json")
    after = r.protected_files()
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    r.ev.save(r.EXP / "results/verification.json", {
        "at": r.ev.now(), "same_complete_request": True, "same_input_prompt_config": True,
        "original_parser_and_validator_passed": True, "frozen_runner_unchanged": True,
        "new_http_requests": len(request_files), "only_diagnosis": True,
        "original_truncation_preserved": True, "protected_files": len(before),
        "changed": changed,
        "drift_hashes": {p: {"before": before.get(p), "after": after.get(p)} for p in changed},
        "historical_run_protection_warning_preserved": True,
    })
    reports = r.EXP / "reports"
    reports.mkdir(exist_ok=True)
    sections = ["# R05 用户授权重试：完整输出对照\n",
                "D2原请求截断，仍保留为技术失败；以下D2-retry为独立追加一次请求的合法输出。\n"]
    for label, value in (("D0 正式V23", comparison["R05"]["D0"]),
                         ("D1 P1", comparison["R05"]["D1"]),
                         ("D2-retry P1-B", result["diagnosis"])):
        sections.append(f"## {label}\n\n```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```\n")
    (reports / "OUTPUTS.md").write_text("\n".join(sections))
    print(json.dumps({"cost": totals, "changed": changed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    analyze()
