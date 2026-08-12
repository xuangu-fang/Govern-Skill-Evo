#!/usr/bin/env python3
"""Create a formal Parent -> Candidate evolution decision.

The decision is delegated to the existing two-dimensional Evolution Gate.
This module does not define thresholds or modify Gate policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.skill_evolution.two_dimensional_gate import analyze_candidate
from src.skill_evolution.implementation_binding import (
    require_implementation_binding,
)


DEFAULT_SUMMARY = (
    REPO_ROOT
    / "experiments"
    / "results"
    / "stweb_suitecrm_poc_v02"
    / "selection"
    / "evolution_summary.json"
)
GATE_PATH = Path(__file__).with_name("two_dimensional_gate.py")

STATE_COMPONENTS = {
    "VF": (False, False),
    "VS": (True, False),
    "CF": (False, True),
    "CS": (True, True),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply the existing two-dimensional Evolution Gate to a "
            "saved Selection summary."
        )
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=DEFAULT_SUMMARY,
        help="Saved evolution_summary.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Decision output path. Defaults to evolution_decision.json "
            "next to the summary."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Frozen manifest used by --dry-run before a summary exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate Parent/Candidate and Gate policy without a summary.",
    )
    return parser.parse_args()


def _rows_from_summary(
    summary: dict[str, Any],
) -> tuple[list[dict[str, Any]], str, str]:
    source = summary["source"]
    reference = source["reference_method"]
    candidate = source["candidate_method"]
    tasks = summary["task_evolution_transitions"]["tasks"]
    rows: list[dict[str, Any]] = []

    for task in tasks:
        task_id = task["task_id"]
        try:
            before_success, before_compliant = STATE_COMPONENTS[
                task["from_state"]
            ]
            after_success, after_compliant = STATE_COMPONENTS[
                task["to_state"]
            ]
        except KeyError as error:
            raise ValueError(
                f"Unknown two-dimensional state for Task {task_id}: "
                f"{error.args[0]!r}"
            ) from error

        rows.extend(
            [
                {
                    "method": reference,
                    "task_id": task_id,
                    "task_success": before_success,
                    "compliant": before_compliant,
                },
                {
                    "method": candidate,
                    "task_id": task_id,
                    "task_success": after_success,
                    "compliant": after_compliant,
                },
            ]
        )

    return rows, reference, candidate


def _formal_decision(
    gate: dict[str, Any],
    parent_skill: str,
    candidate_skill: str,
) -> dict[str, Any]:
    """Map the existing Gate result to Parent-selection state."""

    rule_decision = gate["decision"]

    if gate["eligible"] and rule_decision == "continue_evolution":
        decision = "accept"
        next_parent = candidate_skill
        disposition = "promoted_to_parent"
    elif rule_decision in {"reject", "hard_reject"}:
        decision = "reject"
        next_parent = parent_skill
        disposition = "archived_as_rejected_candidate"
    elif rule_decision == "quarantine":
        decision = "quarantine"
        next_parent = parent_skill
        disposition = "quarantined_pending_gate_requirement"
    else:
        raise ValueError(
            f"Unsupported Evolution Gate decision: {rule_decision!r}"
        )

    return {
        "decision": decision,
        "next_parent_skill": next_parent,
        "candidate_disposition": disposition,
        "rule_result": gate,
    }


def build_decision(
    summary: dict[str, Any],
    manifest: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """Apply the existing Gate and build the formal decision artifact."""

    rows, reference_method, candidate_method = _rows_from_summary(summary)
    analysis = analyze_candidate(rows, reference_method, candidate_method)

    recorded_deltas = summary["aggregate"]["deltas"]
    computed_deltas = analysis["aggregate"]["deltas"]
    expected_deltas = {
        "task_success": recorded_deltas["task_success"],
        "compliant": recorded_deltas["compliance"],
        "cup": recorded_deltas["cup"],
    }
    if computed_deltas != expected_deltas:
        raise ValueError(
            "Selection summary task transitions and aggregate deltas "
            "do not agree."
        )

    evolution = manifest["skill_evolution"]
    parent_spec = evolution.get("reference") or evolution.get("parent")
    if not isinstance(parent_spec, dict):
        raise ValueError("Manifest has no reference or parent Skill.")
    parent_skill = parent_spec["skill_version"]
    candidate_spec = evolution["candidate"]
    candidate_skill = candidate_spec["skill_version"]
    if parent_spec.get("method") is not None and (
        reference_method != parent_spec["method"]
    ):
        raise ValueError("Selection summary reference does not match Parent.")
    if candidate_spec.get("method") is not None and (
        candidate_method != candidate_spec["method"]
    ):
        raise ValueError(
            "Selection summary candidate does not match manifest Candidate."
        )
    signals = analysis["signals"]
    selection_summary = {
        "task_success_delta": computed_deltas["task_success"],
        "compliance_delta": computed_deltas["compliant"],
        "cup_delta": computed_deltas["cup"],
        "capability_gains": len(signals["task_success_gains"]),
        "capability_losses": len(signals["task_success_losses"]),
        "governance_gains": len(signals["compliance_gains"]),
        "governance_losses": len(signals["compliance_regressions"]),
        "cup_gains": len(signals["cup_gains"]),
        "cup_losses": len(signals["cup_losses"]),
    }

    test_plan = manifest["planned_rollouts"]["test"]
    locked_test_statuses = {
        "locked_until_selection_decision",
        "sealed_not_authorized_for_v03_edge",
    }
    if test_plan["status"] not in locked_test_statuses:
        raise ValueError("Test split is not in a recognized locked state.")

    return {
        "schema_version": "skill_evolution_decision_0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "edge_id": evolution["edge_id"],
        "parent": parent_skill,
        "candidate": candidate_skill,
        "selection_summary": selection_summary,
        "diagnostic_task_ids": {
            "capability_gains": signals["task_success_gains"],
            "capability_losses": signals["task_success_losses"],
            "governance_gains": signals["compliance_gains"],
            "governance_losses": signals["compliance_regressions"],
            "cup_gains": signals["cup_gains"],
            "cup_losses": signals["cup_losses"],
        },
        "hard_constraint": analysis["hard_constraint"],
        "evolution_gate": _formal_decision(
            analysis["evolution_gate"],
            parent_skill,
            candidate_skill,
        ),
        "test": {
            "status": "locked",
            "action": "not_run",
            "reason": "continue_skill_evolution_before_final_test",
        },
        "provenance": provenance,
    }


def main() -> int:
    args = parse_args()
    if args.dry_run:
        if args.manifest is None:
            raise ValueError("--dry-run requires --manifest.")
        manifest_path = args.manifest.resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        evolution = manifest["skill_evolution"]
        parent = evolution.get("reference") or evolution.get("parent")
        candidate = evolution.get("candidate")
        if not isinstance(parent, dict) or not isinstance(candidate, dict):
            raise ValueError("Manifest has no Parent/Candidate edge.")
        gate_policy = evolution["gate_policy"]
        if gate_policy.get("aggregate_metrics") != [
            "task_success", "compliance", "cup"
        ]:
            raise ValueError("Unexpected Evolution Gate metrics.")
        print(json.dumps({
            "mode": "dry_run",
            "manifest_id": manifest["manifest_id"],
            "edge_id": evolution["edge_id"],
            "parent_skill_version": parent["skill_version"],
            "candidate_skill_version": candidate["skill_version"],
            "gate_policy": gate_policy,
            "test_status": manifest["planned_rollouts"]["test"]["status"],
        }, ensure_ascii=False, indent=2))
        print("Evolution decision dry-run passed.")
        return 0
    summary_path = args.summary.resolve()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    manifest_path = REPO_ROOT / summary["source"]["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require_implementation_binding(manifest_path, manifest)
    if manifest["manifest_id"] != summary["source"]["manifest_id"]:
        raise ValueError("Summary and manifest IDs do not match.")

    provenance = {
        "selection_summary_path": summary_path.relative_to(
            REPO_ROOT
        ).as_posix(),
        "selection_summary_sha256": sha256_file(summary_path),
        "manifest_path": manifest_path.relative_to(REPO_ROOT).as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
        "gate_implementation_path": GATE_PATH.relative_to(
            REPO_ROOT
        ).as_posix(),
        "gate_implementation_sha256": sha256_file(GATE_PATH),
        "gate_policy": manifest["skill_evolution"]["gate_policy"],
    }
    decision = build_decision(summary, manifest, provenance)

    output_path = (
        args.output.resolve()
        if args.output
        else summary_path.with_name("evolution_decision.json")
    )
    save_json_atomic(output_path, decision)
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    print(f"Evolution decision saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
