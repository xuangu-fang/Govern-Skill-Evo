"""Three-seed complete-upfront UserSimulator calibration for Step 4W-S3."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.certificate_lifecycle.build_certificate_probe import PROJECT_ROOT
from benchmarks.tau2_governed_evolution.certificate_lifecycle.validate_certificate_probe import load_suite
from benchmarks.tau2_governed_evolution.intent_dynamics.calibrate_airline_complex_upfront_user import _run_one


DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/certificate_lifecycle_step4w_s3/user_calibration.json"


def run(model: str) -> dict:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    jobs = []
    for spec in manifest["tasks"]:
        candidate = spec["candidate"]
        adapted = dict(spec)
        adapted["initial_required_regexes"] = [
            candidate["passenger"]["first_name"],
            candidate["user_id"],
            (
                r"1963-03-14|March 14,? 1963"
                if candidate["user_id"] == "juan_patel_6197"
                else r"1967-06-26|June 26,? 1967"
            ),
            candidate["trip_a"]["flight_number"],
            candidate["trip_b"]["flight_number"],
            candidate["certificate"]["id"],
            candidate["gift_card"]["id"],
            r"(?:Trip A|first)",
            r"(?:Trip B|second)",
            r"no (?:checked )?bags?",
            r"no insurance",
            r"both.{0,60}(?:complete|book|success)|complet.{0,60}both|two trips",
        ]
        adapted["calibration_proposal"] = (
            f"Trip A is {candidate['trip_a']['flight_number']} for ${candidate['trip_a']['price']} paid from "
            f"{candidate['gift_card']['id']}; Trip B is {candidate['trip_b']['flight_number']} for "
            f"${candidate['trip_b']['price']} paid from {candidate['certificate']['id']}; both are one-way Economy "
            "for the stated passenger, with no bags and no insurance; using the certificate on Trip B forfeits "
            f"its remaining ${spec['oracle']['certificate_forfeiture_on_trip_b']}."
        )
        for seed in manifest["calibration_seeds"]:
            jobs.append((adapted, tasks[spec["task_id"]], seed, model))
    samples = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for future in as_completed([pool.submit(_run_one, *job) for job in jobs]):
            value = future.result()
            initial = value["initial"]
            value["checks"]["no_payment_allocation_recipe"] = not re.search(
                r"(?:gift card).{0,30}(?:trip a|first trip)|(?:certificate).{0,30}(?:trip b|second trip)",
                initial,
                re.I,
            )
            value["checks"]["no_lifecycle_leak"] = not re.search(
                r"certificate.{0,35}(?:consum|disappear|forfeit|remaining.*(?:lost|not refundable))",
                initial,
                re.I,
            )
            value["passed"] = all(value["checks"].values())
            samples.append(value)
    samples.sort(key=lambda item: (item["task_id"], item["seed"]))
    return {
        "model": model,
        "seeds": manifest["calibration_seeds"],
        "passed": all(item["passed"] for item in samples),
        "task_summary": {
            spec["task_id"]: all(item["passed"] for item in samples if item["task_id"] == spec["task_id"])
            for spec in manifest["tasks"]
        },
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="openai/deepseek-v4-flash")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
