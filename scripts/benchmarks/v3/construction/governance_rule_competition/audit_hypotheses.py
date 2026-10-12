#!/usr/bin/env python3
"""Static preflight for the open Governance-rule competition."""

import json
import sys
from collections import Counter
from pathlib import Path


HERE = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/governance_rule_competition')
REPO = HERE.parents[4]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from src.benchmark_v3.construction.airline_unified_governance_gate0.fixture import build_gate0_db
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator import build_endpoint_preservation_evidence_registry, build_lga01_evidence_registry, build_lgv16b_003_evidence_registry, build_profile_payment_evidence_registry


payload = json.loads((HERE / "hypotheses.json").read_text(encoding="utf-8"))
hypotheses = payload["hypotheses"]
surfaces = [(hypothesis, surface) for hypothesis in hypotheses for surface in hypothesis["surfaces"]]
assert payload["formal_task_ids_allocated"] == 0
assert len(hypotheses) == 4 and len(surfaces) == 8
assert all(len(hypothesis["surfaces"]) == 2 for hypothesis in hypotheses)
assert len({surface["label"] for _, surface in surfaces}) == 8
assert len({surface["user_id"] for _, surface in surfaces}) == 8
assert len({surface["reservation_id"] for _, surface in surfaces}) == 8
assert Counter(hypothesis["source"] for hypothesis in hypotheses) == {
    "DEFERRED_FAMILY": 3,
    "V2_UNUSED_RULE": 1,
}

forbidden = (
    "policy", "rule", "violation", "human agent", "transfer me",
    "separate reservation", "update_reservation", "cancel_reservation",
    "first change the cabin", "before changing the date", "not in my profile",
)
assert all(
    not any(term in surface["reason_for_call"].lower() for term in forbidden)
    for _, surface in surfaces
)

registries = {
    "airline.cancellation.flown_segment_boundary.v1": build_lga01_evidence_registry(),
    "airline.flight_change.current_cabin_boundary.v1": build_lgv16b_003_evidence_registry(),
    "airline.flight_change.endpoint_preservation.v1": build_endpoint_preservation_evidence_registry(),
    "airline.payment.current_profile_membership.v1": build_profile_payment_evidence_registry(),
}
for hypothesis in hypotheses:
    assert hypothesis["rule_id"] in registries[hypothesis["rule_id"]].rule_ids()

db = build_gate0_db().model_dump(mode="json")
for hypothesis, surface in surfaces:
    reservation = db["reservations"][surface["reservation_id"]]
    assert reservation["user_id"] == surface["user_id"]
    if hypothesis["hypothesis_id"] == "H-PAYMENT-HISTORICAL-SOURCE-REUSE":
        historical = surface["historical_payment_id"]
        assert historical in {row["payment_id"] for row in reservation["payment_history"]}
        assert historical not in db["users"][surface["user_id"]]["payment_methods"]

result = {
    "status": "PASS_OPEN_COMPETITION_STATIC_PREFLIGHT",
    "model_calls": 0,
    "hypothesis_count": 4,
    "surface_count": 8,
    "formal_task_ids_allocated": 0,
    "unique_users": 8,
    "unique_reservations": 8,
    "opening_path_leaks": 0,
    "deterministic_rules_available": sorted(registries),
    "next_gate": "RUN_8_E0_ROLLOUTS",
}
(HERE / "static_preflight.json").write_text(json.dumps(result, indent=2) + "\n")
print(result["status"])
