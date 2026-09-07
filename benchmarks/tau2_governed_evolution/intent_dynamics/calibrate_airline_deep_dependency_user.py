"""Calibrate first-turn stability and exact confirmation for Step 4R."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.intent_dynamics.calibrate_airline_complex_upfront_user import _run_one
from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_deep_dependency import MANIFEST_PATH, PROJECT_ROOT, load_suite


def run(model: str) -> dict:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    jobs = [(spec, tasks[spec["task_id"]], seed, model) for spec in manifest["tasks"] for seed in manifest["calibration_seeds"]]
    samples = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_run_one, *job) for job in jobs]
        for future in as_completed(futures):
            sample = future.result()
            confirmation = sample["confirmation"]
            sample["checks"]["confirmation_is_explicit_yes"] = bool(
                re.search(r"\b(?:yes|I explicitly confirm|I confirm)\b", confirmation, re.I)
                and not re.search(r"don.t confirm|do not confirm|before I confirm|can.t confirm|cannot confirm|need to (?:see|review|verify)", confirmation, re.I)
            )
            sample["passed"] = all(sample["checks"].values())
            samples.append(sample)
    samples.sort(key=lambda x: (x["task_id"], x["seed"]))
    return {"model": model, "seeds": manifest["calibration_seeds"], "passed": all(x["passed"] for x in samples), "task_summary": {spec["task_id"]: all(x["passed"] for x in samples if x["task_id"] == spec["task_id"]) for spec in manifest["tasks"]}, "samples": samples}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="openai/deepseek-v4-flash")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "artifacts/airline_deep_dependency_step4r/user_calibration.json")
    args = parser.parse_args()
    result = run(args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
