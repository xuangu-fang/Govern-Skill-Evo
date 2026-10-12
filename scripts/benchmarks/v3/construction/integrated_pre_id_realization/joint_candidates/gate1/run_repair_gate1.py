#!/usr/bin/env python3
"""Run repaired Cardinality and trigger-only Baggage matched Gate 1."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from scripts.benchmarks.v3.construction.integrated_pre_id_realization.joint_candidates.gate1 import run_gate1 as gate1


CONFIG = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/integrated_pre_id_realization/joint_candidates/gate1/repair_config.json')
SUMMARY = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/integrated_pre_id_realization/joint_candidates/gate1/repair_summary.json')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = gate1.load(CONFIG)
    payload = gate1.load(gate1.SPECS)
    base = gate1.load(gate1.BASE_CONFIG)
    gate1.register_airline_domain()
    specs = {
        spec["label"]: (family["family"], spec)
        for family in payload["families"]
        for spec in family["candidates"]
    }
    jobs = []
    selections = (
        (gate1.CARDINALITY, config["cardinality"]),
        (gate1.BAGGAGE, config["baggage"]),
    )
    for expected_family, selection in selections:
        for label in selection["labels"]:
            family, spec = specs[label]
            if family != expected_family:
                raise RuntimeError(f"{label} is not in {expected_family}")
            for seed in selection["seeds"]:
                for condition in config["conditions"]:
                    jobs.append((family, spec, condition, seed, base))
    if len(jobs) != config["planned_trajectories"]:
        raise RuntimeError("Planned trajectory count mismatch")

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(gate1.run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["family"], row["input_label"], row["seed"], row["condition"]))
    families = {
        family: gate1.summarize_family(
            [row for row in rows if row["family"] == family],
            config["family_pass_criteria"],
        )
        for family in (gate1.CARDINALITY, gate1.BAGGAGE)
    }
    passed = all(
        result["verdict"] == "PASS_MATCHED_AXIS_SEPARABILITY_NECESSITY"
        for result in families.values()
    )
    summary = {
        "status": "COMPLETE",
        "verdict": (
            "PASS_NEW_CXG_REPAIRED_MATCHED_NECESSITY"
            if passed else "HOLD_NEW_CXG_REPAIRED_MATCHED_NECESSITY"
        ),
        "experiment": config["experiment"],
        "workspace_status": config["workspace_status"],
        "behavioral_rollouts": len(rows),
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "criteria": config["family_pass_criteria"],
        "families": families,
        "rows": rows,
    }
    gate1.write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
