"""Run fixed-seed Upfront-Stability calibration for Step 4T."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.intent_dynamics.calibrate_airline_complex_upfront_user import _run_one
from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import PROJECT_ROOT, load_suite


def _hidden_oracle_ids(spec: dict) -> set[str]:
    hidden: set[str] = set()
    for action in spec["oracle"]["actions"]:
        arguments = action["arguments"]
        hidden.update(str(value) for value in arguments.get("new_item_ids", []))
        hidden.update(
            str(value["flight_number"])
            for value in arguments.get("flights", [])
        )
    return hidden


def run(model: str, task_ids: tuple[str, ...] | None = None) -> dict:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    selected_ids = set(task_ids) if task_ids else {spec["task_id"] for spec in manifest["tasks"]}
    if not selected_ids <= {spec["task_id"] for spec in manifest["tasks"]}:
        raise ValueError("Unknown --tasks value")
    jobs = [
        (spec, tasks[spec["task_id"]], seed, model)
        for spec in manifest["tasks"]
        if spec["task_id"] in selected_ids
        for seed in manifest["calibration_seeds"]
    ]
    samples = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_run_one, *job) for job in jobs]
        for future in as_completed(futures):
            sample = future.result()
            spec = next(
                item for item in manifest["tasks"]
                if item["task_id"] == sample["task_id"]
            )
            initial = sample["initial"]
            confirmation = sample["confirmation"]
            sample["checks"]["no_oracle_id_leakage"] = not any(
                value in initial for value in _hidden_oracle_ids(spec)
            )
            sample["checks"]["confirmation_is_explicit_yes"] = bool(
                re.search(r"\b(?:yes|I explicitly confirm|I confirm)\b", confirmation, re.I)
                and not re.search(
                    r"don.t confirm|do not confirm|before I confirm|cannot confirm|need to (?:see|review|verify)",
                    confirmation,
                    re.I,
                )
            )
            sample["passed"] = all(sample["checks"].values())
            samples.append(sample)
    samples.sort(key=lambda item: (item["task_id"], item["seed"]))
    return {
        "model": model,
        "seeds": manifest["calibration_seeds"],
        "passed": all(item["passed"] for item in samples),
        "task_summary": {
            spec["task_id"]: all(
                item["passed"] for item in samples
                if item["task_id"] == spec["task_id"]
            )
            for spec in manifest["tasks"]
            if spec["task_id"] in selected_ids
        },
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="openai/deepseek-v4-flash")
    parser.add_argument("--tasks", nargs="+")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "artifacts/phase_a_capability_step4t/user_calibration.json",
    )
    args = parser.parse_args()
    result = run(args.model, tuple(args.tasks) if args.tasks else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
