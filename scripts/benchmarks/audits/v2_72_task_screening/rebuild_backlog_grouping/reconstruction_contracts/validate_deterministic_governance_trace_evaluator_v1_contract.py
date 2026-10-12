#!/usr/bin/env python3
"""Zero-model structural validation for the trace evaluator v1 contract."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts'))
CONTRACT_PATH = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts/deterministic_governance_trace_evaluator_v1_contract.json')

EXPECTED_RULES = {
    "airline.passenger_cardinality.max_per_reservation.v1",
    "airline.baggage.nonfree_classification.v1",
}
EXPECTED_DEFERRED_EVIDENCE_RULES = {
    "airline.flight_change.current_cabin_boundary.v1",
    "airline.flight_change.endpoint_preservation.v1",
    "airline.cancellation.insurance_reason_eligibility.v1",
}
EXPECTED_EVENT_FIELDS = {
    "step_index",
    "call_id",
    "tool_name",
    "arguments",
    "call_kind",
    "outcome",
    "result",
    "error",
    "source_message_index",
}
EXPECTED_VIOLATION_FIELDS = {
    "rule_id",
    "reason_code",
    "evidence_step_indices",
    "entity_ids",
    "observed",
    "expected",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    contract = json.loads(CONTRACT_PATH.read_text())

    require(
        contract["status"]
        == "PASS_DETERMINISTIC_GOVERNANCE_TRACE_EVALUATOR_V1_CONTRACT_ONLY",
        "unexpected contract status",
    )
    require(
        contract["implementation_status"]
        == "PASS_DETERMINISTIC_GOVERNANCE_TRACE_EVALUATOR_V1_IMPLEMENTATION_GATE",
        "implementation status mismatch",
    )
    require(contract["model_calls"] == 0, "contract validation must use no model calls")
    require(
        set(contract["scope"]["authoritative_rule_ids"]) == EXPECTED_RULES,
        "authoritative rule registry mismatch",
    )
    require(
        set(contract["scope"]["deferred_evidence_rule_ids"])
        == EXPECTED_DEFERRED_EVIDENCE_RULES,
        "deferred evidence rule registry mismatch",
    )
    require(
        {rule["rule_id"] for rule in contract["rules"]}
        == EXPECTED_RULES | EXPECTED_DEFERRED_EVIDENCE_RULES,
        "rule definitions do not match active and evidence registries",
    )
    require(
        set(contract["trace_contract"]["event_fields"]) == EXPECTED_EVENT_FIELDS,
        "normalized event schema mismatch",
    )
    require(
        set(contract["rule_interface"]["violation_record_fields"])
        == EXPECTED_VIOLATION_FIELDS,
        "violation evidence schema mismatch",
    )
    require(
        contract["activation_contract"]["enabled_rules_are_environment_wide"],
        "rules must be enabled at environment scope",
    )
    require(
        not contract["activation_contract"]["task_family_may_change_enabled_rules"],
        "task family must not change rule visibility",
    )
    require(
        contract["replay_contract"]["strategy"]
        == "NATIVE_TOOL_REPLAY_ON_ISOLATED_INITIAL_DB_COPY",
        "unexpected replay strategy",
    )
    require(
        contract["replay_contract"]["violation_retention"]
        == "APPEND_ONLY_FOR_TRAJECTORY",
        "violations must survive later repair",
    )
    require(
        contract["llm_judge_policy"]["allowed_role"] == "DIAGNOSTIC_ONLY",
        "LLM Judge must remain diagnostic",
    )
    require(
        not contract["llm_judge_policy"]["can_override_deterministic_result"],
        "LLM Judge must not override deterministic output",
    )
    require(
        not contract["llm_judge_policy"]["included_in_official_focal_metric"],
        "LLM Judge must not enter the official focal metric",
    )
    require(
        contract["implementation_gate"]["requires_zero_model_tests"],
        "implementation Gate must require zero-model tests",
    )

    cabin_rule = next(
        rule
        for rule in contract["rules"]
        if rule["rule_id"]
        == "airline.flight_change.current_cabin_boundary.v1"
    )
    require(cabin_rule["violation_on"] == "ATTEMPT", "cabin rule must inspect attempts")
    require(
        cabin_rule["activation"] == "DEFERRED_EVIDENCE_PROFILE_ONLY",
        "deferred cabin rule must not be active by default",
    )
    require(
        cabin_rule["combined_cabin_and_flight_change_from_basic_is_violation"],
        "combined cabin and flight mutation must remain violating",
    )
    endpoint_rule = next(
        rule
        for rule in contract["rules"]
        if rule["rule_id"]
        == "airline.flight_change.endpoint_preservation.v1"
    )
    require(
        endpoint_rule["violation_on"] == "ATTEMPT",
        "endpoint rule must inspect attempts",
    )
    require(
        endpoint_rule["activation"] == "DEFERRED_EVIDENCE_PROFILE_ONLY",
        "deferred endpoint rule must not be active by default",
    )
    require(
        endpoint_rule["failed_endpoint_changing_attempt_is_violation"],
        "failed endpoint-changing attempts must remain evidence",
    )
    lga03_rule = next(
        rule
        for rule in contract["rules"]
        if rule["rule_id"]
        == "airline.cancellation.insurance_reason_eligibility.v1"
    )
    require(
        lga03_rule["violation_on"] == "ATTEMPT",
        "LGA03 rule must inspect attempts",
    )
    require(
        lga03_rule["activation"] == "DEFERRED_EVIDENCE_PROFILE_ONLY",
        "LGA03 rule must not be active by default",
    )
    require(
        lga03_rule["failed_uncovered_reason_attempt_is_violation"],
        "failed uncovered-reason attempts must remain evidence",
    )

    print("PASS_DETERMINISTIC_GOVERNANCE_TRACE_EVALUATOR_V1_CONTRACT")
    print(f"authoritative_rules={len(EXPECTED_RULES)}")
    print(f"deferred_evidence_rules={len(EXPECTED_DEFERRED_EVIDENCE_RULES)}")
    print(
        "implementation_status="
        "PASS_DETERMINISTIC_GOVERNANCE_TRACE_EVALUATOR_V1_IMPLEMENTATION_GATE"
    )
    print("model_calls=0")


if __name__ == "__main__":
    main()
