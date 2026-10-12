#!/usr/bin/env python3
"""Validate P4 evidence coverage and the narrowed family boundary."""

import json
from pathlib import Path


HERE = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/audits/v2_72_task_screening/rebuild_backlog_grouping')
data = json.loads(((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/p4_certificate_lineage_recovery.json')).read_text(encoding="utf-8"))
lineages = data["lineages"]

assert data["scope"] == {"lineages": 7, "historical_e0_rollouts": 21}
assert data["aggregate_e0_counts"] == {"CS": 10, "CF": 3, "VS": 0, "VF": 8}
assert len(lineages) == len({row["task_id"] for row in lineages}) == 7
assert all(row["mechanism_dimensions"]["one_shot_consumption"] for row in lineages)
assert not any(row["mechanism_dimensions"]["certificate_creation"] for row in lineages)
assert not any(row["mechanism_dimensions"]["multiple_certificates"] for row in lineages)
assert {tuple(row["mechanism_dimensions"]["operation_types"]) for row in lineages} == {("book_reservation",)}
assert data["family_boundary_decision"]["decision"] == "KEEP_ONE_NARROWED_P4_FAMILY"
assert data["family_boundary_decision"]["split_into_two_families"] is False
assert data["formal_task_ids_allocated"] == data["model_rollouts_run_in_this_recovery"] == 0
print("PASS_P4_CERTIFICATE_LINEAGE_RECOVERY_VALIDATION")
