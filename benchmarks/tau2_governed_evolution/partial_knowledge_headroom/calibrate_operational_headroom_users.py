"""Three-seed UserSimulator calibration for the frozen Step 4W pool."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.intent_dynamics.calibrate_airline_complex_upfront_user import _run_one
from benchmarks.tau2_governed_evolution.partial_knowledge_headroom.validate_operational_headroom_tasks import PROJECT_ROOT, load_suite


DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/partial_knowledge_headroom_step4w/user_calibration.json"
REQUIRED = {
    "retail_pa_o1a_w6779827_items_payment": ["Ethan Lopez", "43275", "W6779827", "Dumbbell", "urethane", "adjustable", "1020"],
    "retail_pa_o1b_w8327915_items_payment": ["Ava Lopez", "92168", "W8327915", "Headphones", "over-ear", "wired", "black", "9677"],
    "airline_pa_o2a_m66qvw_full_replacement": ["lucas_nguyen_6408", "M66QVW", "HAT178", "HAT007", "return"],
    "airline_pa_o2b_1n99u6_full_replacement": ["james_taylor_7043", "1N99U6", "HAT266", "HAT112", "outbound"],
    "airline_pa_o3a_m66qvw_preserved_pricing": ["M66QVW", "HAT281", "50", "HAT178", "HAT007"],
    "airline_pa_o3b_1n99u6_preserved_pricing": ["1N99U6", "HAT131", "no additional|without.*additional", "HAT286", "outbound"],
}
PROPOSALS = {
    "retail_pa_o1a_w6779827_items_payment": "Change Dumbbell Set 7896397433 to 4422467033 and whole-order payment to Mastercard 1020; all unrelated state stays unchanged.",
    "retail_pa_o1b_w8327915_items_payment": "Change Headphones 2025713343 to 3374679624 and whole-order payment to Mastercard 9677; all unrelated state stays unchanged.",
    "airline_pa_o2a_m66qvw_full_replacement": "M66QVW will be Economy outbound HAT007 May 24 and return HAT178 May 30, with both passengers, two bags, route and round-trip type preserved; the result is an $80 refund to gift_card_2684964.",
    "airline_pa_o2b_1n99u6_full_replacement": "1N99U6 will be Economy outbound HAT266 May 19 and return HAT112 May 27, with both passengers, one bag, route and round-trip type preserved; the result is a $414 refund to gift_card_5634230.",
    "airline_pa_o3a_m66qvw_preserved_pricing": "Using preserved HAT007's historical $183 price, HAT281 would charge $68, above the $50 gate, so choose HAT178; the exact result is an $80 refund to gift_card_2684964, with all other state preserved.",
    "airline_pa_o3b_1n99u6_preserved_pricing": "Using the preserved outbound's historical $353 price, HAT131 would charge $28, so choose HAT286; the exact result is a $28 refund to gift_card_5634230, with all other state preserved.",
}


def run(model: str) -> dict:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    registry, tasks = load_suite()
    jobs = []
    for spec in registry["tasks"]:
        adapted = dict(spec)
        adapted["initial_required_regexes"] = REQUIRED[spec["task_id"]]
        adapted["calibration_proposal"] = PROPOSALS[spec["task_id"]]
        for seed in registry["calibration_seeds"]:
            jobs.append((adapted, tasks[spec["task_id"]], seed, model))
    samples = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for future in as_completed([pool.submit(_run_one, *job) for job in jobs]):
            value = future.result()
            initial = value["initial"]
            value["checks"]["procedure_neutral"] = not re.search(r"(?:first|before).{0,25}(?:call|tool|execute)|(?:items?|payment).{0,25}(?:must|should).{0,15}(?:first|last)", initial, re.I)
            value["passed"] = all(value["checks"].values())
            samples.append(value)
    samples.sort(key=lambda item: (item["task_id"], item["seed"]))
    return {"model": model, "seeds": registry["calibration_seeds"], "passed": all(item["passed"] for item in samples), "task_summary": {task_id: all(item["passed"] for item in samples if item["task_id"] == task_id) for task_id in REQUIRED}, "samples": samples}


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
