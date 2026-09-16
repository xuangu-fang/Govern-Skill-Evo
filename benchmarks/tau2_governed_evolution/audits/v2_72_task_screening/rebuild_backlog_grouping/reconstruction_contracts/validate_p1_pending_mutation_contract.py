#!/usr/bin/env python3
"""Validate the P1 trigger-first reconstruction design contract."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
contract = json.loads(
    (HERE / "p1_pending_mutation_reconstruction_contract.json").read_text(
        encoding="utf-8"
    )
)

assert contract["status"] == "PASS_DESIGN_CONTRACT_ONLY"
assert contract["family_id"] == "C-RET-P1-PENDING-MUTATION-SEQUENCE"
assert contract["formal_task_ids_allocated"] == 0
assert contract["support_required"] is False
assert contract["native_transition"]["focal_dependency"] == "payment_before_items"
assert contract["native_transition"]["correct_label"] == "CS"
assert contract["native_transition"]["wrong_label"] == "CF"
assert contract["environment"]["family_specific_tools"] is False
assert contract["environment"]["information_boundary_change"] == (
    "DOMAIN_WIDE_NATIVE_ITEM_TRANSITION_NEUTRALIZATION__NO_FAMILY_VARIATION"
)
assert contract["gate0"]["expected"] == ["CS", "CF", "CS", "CF"]
assert contract["gate1"]["planned_rollouts"] == 8
print("PASS_P1_PENDING_MUTATION_RECONSTRUCTION_CONTRACT")
