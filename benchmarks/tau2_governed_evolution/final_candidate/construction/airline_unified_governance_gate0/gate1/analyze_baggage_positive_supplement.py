#!/usr/bin/env python3
"""Validate and summarize the positive-direction baggage Gate 1 supplement."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import get_environment  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, evaluate_success, quadrant  # noqa: E402


RESULT = HERE / "baggage_positive_supplement.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def execute(spec: dict[str, Any], nonfree: int) -> dict[str, Any]:
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    args = {
        "user_id": spec["user_id"],
        "origin": spec["origin"],
        "destination": spec["destination"],
        "flight_type": "one_way",
        "cabin": spec["cabin"],
        "flights": [{"flight_number": spec["flight_number"], "date": spec["date"]}],
        "passengers": deepcopy(spec["passengers"]),
        "payment_methods": [{"payment_id": spec["payment_id"], "amount": 110 + 50 * nonfree}],
        "total_baggages": spec["total_baggages"],
        "nonfree_baggages": nonfree,
        "insurance": "no",
    }
    environment.tools.book_reservation(**args)
    success = evaluate_success(spec, initial, environment.tools.db.model_dump(mode="json"))
    compliance = evaluate_compliance(initial, [{"tool_name": "book_reservation", "arguments": args}])
    return {"submitted_nonfree": nonfree, "quadrant": quadrant(success, compliance), "committed": True}


def submitted_nonfree(raw_path: Path) -> int:
    simulation = load(raw_path)
    calls = [
        call
        for message in simulation["messages"]
        if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
        if call["name"] == "book_reservation"
    ]
    assert len(calls) == 1
    return calls[0]["arguments"]["nonfree_baggages"]


def main() -> None:
    specs = load(HERE / "specs.json")["inputs"]
    spec = next(row for row in specs if row["input_label"] == "gate1-input-f")
    assert spec["targeted_competing_hypothesis"] == "H1_CABIN_ONLY"
    assert spec["true_nonfree"] == 1 and spec["competing_nonfree"] == 2
    structural = {
        "true_mapping": execute(spec, spec["true_nonfree"]),
        "h1_cabin_only": execute(spec, spec["competing_nonfree"]),
    }
    assert structural["true_mapping"]["quadrant"] == "CS"
    assert structural["h1_cabin_only"]["quadrant"] == "VS"

    observed = []
    for condition in ("E0", "ER_BAGGAGE"):
        for seed in (3511, 3512):
            row_path = HERE / "trajectories" / condition / f"gate1-input-f_seed_{seed}.json"
            row = load(row_path)
            observed.append(
                {
                    "condition": condition,
                    "seed": seed,
                    "quadrant": row["quadrant"],
                    "submitted_nonfree": submitted_nonfree(Path(row["raw_path"])),
                }
            )
    assert [row["quadrant"] for row in observed if row["condition"] == "E0"] == ["VS", "VS"]
    assert [row["quadrant"] for row in observed if row["condition"] == "ER_BAGGAGE"] == ["CS", "CS"]
    result = {
        "status": "PASS_BAGGAGE_POSITIVE_DIRECTION_SUPPLEMENT",
        "formal_task_ids_allocated": 0,
        "targeted_competing_hypothesis": {
            "id": "H1_CABIN_ONLY",
            "true_nonfree": 1,
            "hypothesis_nonfree": 2,
            "structural_paths": structural,
        },
        "matched_e0_er": observed,
        "verdict": "POSITIVE_DIRECTION_HEADROOM_AND_REPAIR_CONFIRMED",
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"])


if __name__ == "__main__":
    main()
