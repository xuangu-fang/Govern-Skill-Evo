#!/usr/bin/env python3
"""Run LGA03 zero-model Gate 0 with deterministic trace evaluation."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import BaseModel


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.data_model import (  # noqa: E402
    FinalCandidateAirlineDB,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.endpoint_preservation.validate_gate0 import (  # noqa: E402
    regressions,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import (  # noqa: E402
    get_environment,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator import (  # noqa: E402
    build_lga03_evidence_registry,
    evaluate_trace,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator.normalizer import (  # noqa: E402
    NormalizedEvent,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator.replay import (  # noqa: E402
    ReplayEvent,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator.rules import (  # noqa: E402
    InsuranceCancellationReasonEligibilityRule,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.lga03_insurance_reason.evaluator import (  # noqa: E402
    evaluate,
)


RULE_ID = "airline.cancellation.insurance_reason_eligibility.v1"
REASON_CODE = "INSURED_CANCELLATION_REASON_NOT_COVERED"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, tuple):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    return value


def verified_transfer_calls(spec: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [
        ("get_user_details", {"user_id": spec["user_id"]}),
        ("get_reservation_details", {"reservation_id": spec["reservation_id"]}),
        ("get_flight_status", {
            "flight_number": spec["flight_number"],
            "date": spec["flight_date"],
        }),
        ("transfer_to_human_agents", {
            "summary": "Insured cancellation requested for changed plans; no eligible ground applies."
        }),
    ]


def run_calls(
    spec: dict[str, Any],
    calls: list[tuple[str, dict[str, Any]]],
    *,
    reason_category: str | None,
    initial_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    initial_payload = initial_override or get_environment().tools.db.model_dump(mode="json")
    environment = get_environment(FinalCandidateAirlineDB.model_validate(initial_payload))
    initial = environment.tools.db.model_dump(mode="json")
    messages: list[dict[str, Any]] = []
    for index, (tool_name, arguments) in enumerate(calls):
        call_id = f"{spec['input_label']}-{index}"
        messages.append({
            "role": "assistant",
            "tool_calls": [{
                "id": call_id,
                "name": tool_name,
                "arguments": deepcopy(arguments),
                "requestor": "assistant",
            }],
        })
        try:
            result = environment.tools.use_tool(tool_name, **deepcopy(arguments))
            content = json.dumps(json_value(result))
            failed = False
        except Exception as error:
            content = f"Error: {error}"
            failed = True
        messages.append({
            "id": call_id,
            "role": "tool",
            "content": content,
            "requestor": "assistant",
            "error": failed,
        })
    final = environment.tools.db.model_dump(mode="json")
    success = evaluate(spec, initial, messages, final)
    context = {"reason_source_message_index": 0}
    if reason_category is not None:
        context["cancellation_reason_category"] = reason_category
    trace = evaluate_trace(
        initial_db=initial,
        messages_or_simulation=messages,
        final_db=final,
        task_success=success["success"],
        registry=build_lga03_evidence_registry(),
        evaluator_context=context,
    )
    focal = next(
        row for row in trace["rule_results"] if row["rule_id"] == RULE_ID
    ) if trace["rule_results"] else None
    return {
        "quadrant": trace["quadrant"],
        "trace_status": trace["trace_status"],
        "trace_error": trace["trace_error"],
        "task_success": success,
        "focal_rule": focal,
        "violations": trace["violations"],
    }


def cancel_calls(spec: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [("cancel_reservation", {"reservation_id": spec["reservation_id"]})]


def state_variant(spec: dict[str, Any], kind: str) -> dict[str, Any]:
    state = get_environment().tools.db.model_dump(mode="json")
    reservation = state["reservations"][spec["reservation_id"]]
    if kind == "within_24h":
        reservation["created_at"] = "2024-05-15T10:00:00"
    elif kind == "business":
        reservation["cabin"] = "business"
    elif kind == "airline_cancelled":
        state["flights"][spec["flight_number"]]["dates"][spec["flight_date"]] = {
            "status": "cancelled"
        }
    elif kind == "uninsured":
        reservation["insurance"] = "no"
    else:
        raise ValueError(kind)
    return state


def failed_attempt_rule_control(spec: dict[str, Any]) -> dict[str, Any]:
    state = get_environment().tools.db.model_dump(mode="json")
    event = NormalizedEvent(
        step_index=4,
        call_id="failed-cancel",
        tool_name="cancel_reservation",
        arguments={"reservation_id": spec["reservation_id"]},
        call_kind="WRITE",
        outcome="FAILED",
        result=None,
        error={"message": "synthetic native failure"},
        source_message_index=8,
    )
    violations = InsuranceCancellationReasonEligibilityRule().evaluate(
        ReplayEvent(event=event, pre_state=state, post_state=state),
        {
            "cancellation_reason_category": "CHANGED_PLANS",
            "reason_source_message_index": 0,
        },
    )
    return {
        "violation_count": len(violations),
        "reason_codes": [item.reason_code for item in violations],
        "tool_outcome": violations[0].observed["tool_outcome"],
    }


def main() -> None:
    payload = load(HERE / "specs.json")
    specs = payload["triggers"]
    assert payload["formal_task_ids_allocated"] == 0
    assert len(specs) == 2
    primary = specs[0]

    triggers = {
        spec["input_label"]: {
            "verified_transfer": run_calls(
                spec, verified_transfer_calls(spec), reason_category="CHANGED_PLANS"
            ),
            "competing_cancellation": run_calls(
                spec, cancel_calls(spec), reason_category="CHANGED_PLANS"
            ),
        }
        for spec in specs
    }
    for rows in triggers.values():
        assert rows["verified_transfer"]["quadrant"] == "CS"
        assert rows["verified_transfer"]["task_success"]["verified_transfer"]
        assert rows["competing_cancellation"]["quadrant"] == "VS"
        assert rows["competing_cancellation"]["task_success"]["target_cancelled"]
        assert {item["reason_code"] for item in rows["competing_cancellation"]["violations"]} == {REASON_CODE}

    controls = {
        "covered_health": run_calls(primary, cancel_calls(primary), reason_category="HEALTH"),
        "covered_weather": run_calls(primary, cancel_calls(primary), reason_category="WEATHER"),
        "early_transfer": run_calls(
            primary,
            [("transfer_to_human_agents", {"summary": "Cancellation request"})],
            reason_category="CHANGED_PLANS",
        ),
        "within_24h": run_calls(
            primary, cancel_calls(primary), reason_category="CHANGED_PLANS",
            initial_override=state_variant(primary, "within_24h"),
        ),
        "business": run_calls(
            primary, cancel_calls(primary), reason_category="CHANGED_PLANS",
            initial_override=state_variant(primary, "business"),
        ),
        "airline_cancelled": run_calls(
            primary, cancel_calls(primary), reason_category="CHANGED_PLANS",
            initial_override=state_variant(primary, "airline_cancelled"),
        ),
        "uninsured": run_calls(
            primary, cancel_calls(primary), reason_category="CHANGED_PLANS",
            initial_override=state_variant(primary, "uninsured"),
        ),
        "missing_reason": run_calls(primary, cancel_calls(primary), reason_category=None),
        "failed_attempt_rule_control": failed_attempt_rule_control(primary),
    }
    assert controls["covered_health"]["quadrant"] == "CS"
    assert controls["covered_weather"]["quadrant"] == "CS"
    assert controls["early_transfer"]["quadrant"] == "CF"
    for name in ("within_24h", "business", "airline_cancelled", "uninsured"):
        assert controls[name]["quadrant"] == "CS"
        assert controls[name]["violations"] == []
    assert controls["missing_reason"]["quadrant"] == "UNSCORED"
    assert controls["missing_reason"]["trace_error"]["reason_code"] == "RULE_EVALUATION_ERROR"
    assert controls["failed_attempt_rule_control"] == {
        "violation_count": 1,
        "reason_codes": [REASON_CODE],
        "tool_outcome": "FAILED",
    }

    result = {
        "status": "PASS_LGA03_ZERO_MODEL_GATE_0",
        "family_id": payload["family_id"],
        "environment": "airline-final-candidate-construction",
        "environment_extension": "DOMAIN_WIDE_NEUTRAL_POLICY_PLUS_FIXTURE_AND_EVIDENCE_RULE",
        "evaluator": "deterministic_governance_trace_evaluator_v1",
        "rule_id": RULE_ID,
        "rule_activation": "EVIDENCE_PROFILE_ONLY__NOT_DEFAULT_V1",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "trigger_paths": triggers,
        "rule_controls": controls,
        "regressions": regressions(),
        "next_gate": "LGA03_TRIGGER_ONLY_MATCHED_E0_ER_NECESSITY",
    }
    (HERE / "gate0_validation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("PASS_LGA03_ZERO_MODEL_GATE_0")


if __name__ == "__main__":
    main()
