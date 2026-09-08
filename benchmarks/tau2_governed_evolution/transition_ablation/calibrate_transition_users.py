"""Calibrate Step 4V UserSimulator upfront completeness and procedure neutrality."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.intent_dynamics.calibrate_airline_complex_upfront_user import (
    _run_one,
)
from benchmarks.tau2_governed_evolution.transition_ablation.validate_transition_probe import (
    MANIFEST_PATH,
    PROJECT_ROOT,
    load_suite,
)


DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/transition_ablation_step4v/user_calibration.json"


def run(model: str) -> dict:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    jobs = [
        (spec, tasks[spec["task_id"]], seed, model)
        for spec in manifest["tasks"]
        for seed in (830, 831, 832)
    ]
    samples = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_run_one, *job) for job in jobs]
        for future in as_completed(futures):
            sample = future.result()
            initial = sample["initial"]
            sample["checks"]["no_execution_recipe"] = not re.search(
                r"(?:address|payment|items?).{0,25}(?:must|should|need to).{0,12}(?:first|last)|"
                r"(?:first|last).{0,12}(?:address|payment|items?)|"
                r"before (?:changing|modifying) (?:the )?items",
                initial,
                re.I,
            )
            sample["checks"]["no_transition_disclosure"] = not re.search(
                r"(?:items?|item modification).{0,40}(?:no longer|cannot|close|lock|terminal)",
                initial,
                re.I,
            )
            sample["passed"] = all(sample["checks"].values())
            samples.append(sample)
    samples.sort(key=lambda item: (item["task_id"], item["seed"]))
    return {
        "model": model,
        "seeds": [830, 831, 832],
        "passed": all(item["passed"] for item in samples),
        "task_summary": {
            spec["task_id"]: all(
                item["passed"] for item in samples if item["task_id"] == spec["task_id"]
            )
            for spec in manifest["tasks"]
        },
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="openai/deepseek-v4-flash")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
