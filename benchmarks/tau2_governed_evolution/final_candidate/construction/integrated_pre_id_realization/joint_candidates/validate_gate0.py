#!/usr/bin/env python3
"""Run deterministic four-quadrant Gate 0 for selected Joint candidates."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import (  # noqa: E402
    get_environment,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.integrated_pre_id_realization.joint_candidates.evaluator import (  # noqa: E402
    evaluate,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.integrated_pre_id_realization.joint_candidates.fixture import (  # noqa: E402
    build_joint_db,
)


def booking_args(
    spec: dict[str, Any],
    trip: dict[str, Any],
    passengers: list[dict[str, str]],
    payment_id: str,
    nonfree: int,
    total_baggages: int,
) -> dict[str, Any]:
    amount = trip["price"] * len(passengers) + 50 * nonfree
    return {
        "user_id": spec["user_id"],
        "origin": trip["origin"],
        "destination": trip["destination"],
        "flight_type": "one_way",
        "cabin": spec.get("cabin", "economy"),
        "flights": [{"flight_number": trip["flight_number"], "date": trip["date"]}],
        "passengers": deepcopy(passengers),
        "payment_methods": [{"payment_id": payment_id, "amount": amount}],
        "total_baggages": total_baggages,
        "nonfree_baggages": nonfree,
        "insurance": "no",
    }


def run_path(
    spec: dict[str, Any],
    *,
    capability_correct: bool,
    governance_correct: bool,
) -> dict[str, Any]:
    environment = get_environment(db=build_joint_db())
    initial = environment.tools.db.model_dump(mode="json")
    events: list[dict[str, Any]] = []
    native_errors: list[str] = []

    if "group_passengers" in spec:
        passengers = spec["group_passengers"]
        groups = [passengers[:5], passengers[5:]] if governance_correct else [passengers]
        governed_nonfree = [0] * len(groups)
        governed_totals = [0] * len(groups)
    else:
        groups = [[spec["passenger"]]]
        governed_nonfree = [
            spec["true_nonfree"] if governance_correct else spec["competing_nonfree"]
        ]
        governed_totals = [spec["total_baggages"]]

    for index, (group, nonfree, total_baggages) in enumerate(
        zip(groups, governed_nonfree, governed_totals, strict=True)
    ):
        payment_id = (
            spec["certificate_id"]
            if not capability_correct and index == 0
            else spec["gift_card_id"]
        )
        args = booking_args(
            spec,
            spec["governed_trip"],
            group,
            payment_id,
            nonfree,
            total_baggages,
        )
        environment.tools.book_reservation(**args)
        events.append({"tool_name": "book_reservation", "arguments": args})

    certificate_passengers = (
        spec["certificate_passengers"]
        if "certificate_passengers" in spec
        else [spec["passenger"]]
    )
    certificate_args = booking_args(
        spec,
        spec["certificate_trip"],
        certificate_passengers,
        spec["certificate_id"],
        0,
        0,
    )
    try:
        environment.tools.book_reservation(**certificate_args)
        events.append({"tool_name": "book_reservation", "arguments": certificate_args})
    except ValueError as error:
        native_errors.append(str(error))

    final = environment.tools.db.model_dump(mode="json")
    result = evaluate(spec, initial, final, events)
    result["committed_writes"] = len(events)
    result["native_errors"] = native_errors
    return result


def main() -> None:
    payload = json.loads((HERE / "specs.json").read_text(encoding="utf-8"))
    expected = {
        "joint_success": "CS",
        "capability_only_failure": "CF",
        "governance_only_failure": "VS",
        "joint_failure": "VF",
    }
    path_inputs = {
        "joint_success": (True, True),
        "capability_only_failure": (False, True),
        "governance_only_failure": (True, False),
        "joint_failure": (False, False),
    }
    families: dict[str, Any] = {}
    for family in payload["families"]:
        candidate_results = {}
        for spec in family["candidates"]:
            paths = {
                name: run_path(
                    spec,
                    capability_correct=axes[0],
                    governance_correct=axes[1],
                )
                for name, axes in path_inputs.items()
            }
            assert {name: row["quadrant"] for name, row in paths.items()} == expected
            assert paths["joint_success"]["joint_success"] is True
            assert paths["capability_only_failure"]["governance"]["compliant"] is True
            assert paths["governance_only_failure"]["capability"]["success"] is True
            assert paths["joint_failure"]["joint_success"] is False
            candidate_results[spec["label"]] = paths
        families[family["family"]] = candidate_results

    result = {
        "status": "PASS_NEW_CXG_JOINT_ZERO_MODEL_GATE_0",
        "workspace_status": "CONSTRUCTION_ONLY_NOT_AN_EDITION",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "selected_family_count": len(families),
        "candidate_count": sum(len(rows) for rows in families.values()),
        "four_quadrant_paths": sum(
            len(paths) for rows in families.values() for paths in rows.values()
        ),
        "expected_quadrants": expected,
        "families": families,
        "next_gate": "MATCHED_AXIS_SEPARABILITY_NECESSITY",
    }
    (HERE / "gate0_validation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("PASS_NEW_CXG_JOINT_ZERO_MODEL_GATE_0")


if __name__ == "__main__":
    main()
