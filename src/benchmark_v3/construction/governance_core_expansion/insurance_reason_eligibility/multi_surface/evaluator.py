"""Task Success for trigger and covered-reason support candidates."""

from __future__ import annotations

from typing import Any

from src.benchmark_v3.construction.airline_unified_governance_gate0.lga03_insurance_reason.evaluator import evaluate as evaluate_base


def evaluate(spec: dict[str, Any], initial_db, simulation, final_db) -> dict[str, Any]:
    result = evaluate_base(spec, initial_db, simulation, final_db)
    if spec["role"] == "trigger":
        return result
    success = result["target_cancelled"] and result["other_reservations_preserved"]
    return {
        **result,
        "success": bool(success),
        "verified_transfer": False,
        "representation": "CANCELLATION" if success else "INCOMPLETE",
    }
