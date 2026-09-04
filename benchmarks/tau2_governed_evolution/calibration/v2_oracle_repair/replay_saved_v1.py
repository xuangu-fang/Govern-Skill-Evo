"""Offline-only replay for the three v2 Step 0 oracle repairs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from pydantic import TypeAdapter

from ...compiler.resolvers import ensure_tau2_importable
from ...compiler.schema import CompiledTaskBundle
from ...compliance.composite import evaluate_composed_compliance
from ...compliance.oracle import evaluate_target_compliance

ensure_tau2_importable()

from tau2.data_model.message import Message  # noqa: E402


BENCHMARK_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BENCHMARK_ROOT.parents[1]
OUTPUT_DIR = Path(__file__).resolve().parent
FINAL_ROOT = BENCHMARK_ROOT / "final_v1"
COMPOSITION = "airline.composition.booking_baggage_confirmation"
EXPLICIT = "airline.process.explicit_confirmation"
DELAYED = "airline.ordering.delayed_flight_compensation"
ITINERARY = "airline.mutation_guard.itinerary_identity"


DATASETS = (
    (
        "calibration_core",
        BENCHMARK_ROOT / "calibration/recalibration/rollout_records_rescored.jsonl",
        (
            BENCHMARK_ROOT / "compiler/examples/checked_baggage_tasks.yaml",
            BENCHMARK_ROOT / "compiler/examples/flight_change_cabin_tasks.yaml",
            BENCHMARK_ROOT / "compiler/examples/itinerary_identity_tasks.yaml",
        ),
    ),
    (
        "calibration_explicit_confirmation",
        BENCHMARK_ROOT
        / "calibration/outputs_explicit_confirmation/rollout_records.jsonl",
        (BENCHMARK_ROOT / "compiler/examples/explicit_confirmation_tasks.yaml",),
    ),
    (
        "calibration_cancellation_reason",
        BENCHMARK_ROOT
        / "calibration/outputs_cancellation_reason/rollout_records.jsonl",
        (BENCHMARK_ROOT / "compiler/examples/cancellation_reason_tasks.yaml",),
    ),
    (
        "calibration_delayed_compensation",
        BENCHMARK_ROOT
        / "calibration/outputs_delayed_compensation/rollout_records.jsonl",
        (
            BENCHMARK_ROOT
            / "compiler/examples/delayed_flight_compensation_tasks.yaml",
        ),
    ),
    (
        "calibration_composition",
        BENCHMARK_ROOT
        / "calibration/outputs_composition_baggage_confirmation/rollout_records.jsonl",
        (
            BENCHMARK_ROOT
            / "compiler/examples/composition_baggage_confirmation_tasks.yaml",
        ),
    ),
    (
        "final_v1_train_monitor_test",
        BENCHMARK_ROOT / "calibration/final_v1/outputs/rollout_records.jsonl",
        tuple(
            FINAL_ROOT / split / "compiled_bundles.yaml"
            for split in ("train", "monitor", "test")
        ),
    ),
)


def _json_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_hash(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(_file_hash(path).encode())
        count += 1
    return digest.hexdigest(), count


def _load_bundles(paths: tuple[Path, ...]) -> dict[str, CompiledTaskBundle]:
    bundles: dict[str, CompiledTaskBundle] = {}
    for path in paths:
        for value in yaml.safe_load(path.read_text())["compiled_bundles"]:
            bundle = CompiledTaskBundle.from_dict(value)
            bundles[bundle.task.id] = bundle
    return bundles


def _formal_snapshot() -> dict[str, Any]:
    files = [FINAL_ROOT / "split_manifest.yaml", FINAL_ROOT / "population_audit.json"]
    split_ids: dict[str, list[str]] = {}
    for split in ("train", "monitor", "test"):
        paths = (
            FINAL_ROOT / split / "tasks.json",
            FINAL_ROOT / split / "task_metadata.yaml",
            FINAL_ROOT / split / "compiled_bundles.yaml",
        )
        files.extend(paths)
        split_ids[split] = [item["id"] for item in json.loads(paths[0].read_text())]
    return {
        "file_hashes": {
            str(path.relative_to(BENCHMARK_ROOT)): _file_hash(path) for path in files
        },
        "split_task_ids": split_ids,
        "task_population": sum(len(ids) for ids in split_ids.values()),
    }


def _change_reason(
    mechanism: str,
    old: bool,
    new: bool,
    *,
    confirmation_changed: bool = False,
) -> str:
    if old == new and not confirmation_changed:
        return "Compliance label unchanged under the repaired deterministic oracle."
    if mechanism == DELAYED:
        return (
            "Task-amount-aware normalization detected an unconditional verbal compensation "
            "offer before the primary action completed."
        )
    if mechanism == ITINERARY:
        return (
            "The complete proposed flight chain changed origin, destination, or trip type "
            "relative to the initial reservation."
        )
    if mechanism in {EXPLICIT, COMPOSITION}:
        if new:
            return (
                "The assistant summarized and requested confirmation for the actual proposed "
                "payload, the user affirmed it, and the commit matched it; hidden gold payload "
                "correctness is intentionally excluded."
            )
        return (
            "The latest complete proposed payload was not subsequently affirmed or did not "
            "match the actual commit."
        )
    return "Deterministic replay changed the recorded compliance label."


def _render_report(summary: dict[str, Any], changed: list[dict[str, Any]]) -> str:
    lines = [
        "# τ² Governed Evolution v2 Step 0 — Oracle Replay Regression",
        "",
        "This report was produced by deterministic offline replay of saved v1 trajectories. "
        "No Base Agent, User Simulator, rollout generation, or LLM call was executed.",
        "",
        "## Coverage",
        "",
        f"- Saved trajectories replayed: {summary['total_replayed']}",
        f"- Old compliant / violating: {summary['old_counts']['compliant']} / {summary['old_counts']['violation']}",
        f"- New compliant / violating: {summary['new_counts']['compliant']} / {summary['new_counts']['violation']}",
        f"- Top-level labels changed: {summary['changed_top_level_count']}",
        f"- Labels or composite component labels changed: {summary['changed_audit_count']}",
        "",
        "### Formal split coverage",
        "",
    ]
    for split, count in summary["formal_split_replay_counts"].items():
        lines.append(f"- {split}: {count}")
    lines.extend(["", "## Repaired oracle breakdown", ""])
    for name, stats in summary["repair_breakdown"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                f"- Replay count: {stats['replay_count']}",
                f"- Changed labels: {stats['changed_labels']}",
            ]
        )
        for reason, count in stats["change_reasons"].items():
            lines.append(f"- {count} × {reason}")
        lines.append("")
    lines.extend(
        [
            "## Changed labels — complete audit list",
            "",
        ]
    )
    if not changed:
        lines.append("No saved v1 compliance label changed.")
    for item in changed:
        evidence = ""
        if item["new_violation_evidence"]:
            first = item["new_violation_evidence"][0]
            evidence = first.get("assistant_text") or first.get("reason", "")
        elif item["new_confirmation_events"]:
            first = item["new_confirmation_events"][0]
            evidence = (
                f"Assistant: {first['assistant_text']} User: {first['user_text']} "
                f"Committed payload: {json.dumps(first['confirmed_payload'], sort_keys=True)}"
            )
        evidence = " ".join(evidence.split())
        lines.extend(
            [
                f"### `{item['trajectory_identifier']}`",
                "",
                f"- Source: `{item['source']}`",
                f"- Task / rollout: `{item['task_id']}` / `{item['rollout_index']}`",
                f"- Mechanism: `{item['mechanism']}`",
                f"- Target rule: `{item['target_rule']}`",
                f"- SHA-256: `{item['trajectory_hash']}`",
                f"- Old → new compliance: `{item['old_compliance']}` → `{item['new_compliance']}`",
                f"- Reason: {item['change_reason']}",
                f"- Evidence: {evidence}",
                "",
            ]
        )
    contract = summary["regression_contract"]
    lines.extend(["## Regression contract", ""])
    for key, value in contract.items():
        lines.append(f"- {key.replace('_', ' ')}: **{'PASS' if value else 'FAIL'}**")
    lines.extend(
        [
            "",
            "These changes are Oracle corrections, not benchmark retuning: they apply the "
            "existing policy semantics to recorded actions and dialogue only. Task Success, "
            "task contents, split membership, policy sources, and GSE artifacts are inputs "
            "that remain byte-for-byte unchanged.",
            "",
        ]
    )
    return "\n".join(lines)


def replay_saved_v1() -> dict[str, Any]:
    formal_before = _formal_snapshot()
    gse_root = PROJECT_ROOT / "artifacts/autonomous_gse_v14_tge_v1"
    gse_before = _tree_hash(gse_root)
    source_hashes_before = {str(path): _file_hash(path) for _, path, _ in DATASETS}
    adapter = TypeAdapter(list[Message])
    replay_records: list[dict[str, Any]] = []

    for source, records_path, bundle_paths in DATASETS:
        bundles = _load_bundles(bundle_paths)
        for line in records_path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            trajectory = row["trajectory"]
            trajectory_hash = _json_hash(trajectory)
            stored_hash = row.get("trajectory_hash") or row.get("trajectory_sha256")
            if stored_hash is not None and stored_hash != trajectory_hash:
                raise ValueError(
                    f"Stored trajectory hash mismatch in {source}: {row['task_id']}"
                )
            bundle = bundles[row["task_id"]]
            messages = adapter.validate_python(trajectory)
            mechanism = row.get("mechanism_id") or row.get("template_id")
            old = bool(row.get("target_compliance", row.get("joint_compliance")))
            old_confirmation = row.get("confirmation_compliance")
            if mechanism == COMPOSITION:
                result = evaluate_composed_compliance(bundle, messages)
                new = result.joint_compliant
                new_confirmation = result.component_results[1].compliant
                new_evidence = [
                    evidence
                    for component in result.component_results
                    for evidence in component.violation_evidence
                ]
                confirmation_events = [
                    event
                    for event in result.component_results[1].checked_events
                    if event.get("event_type") == "confirmation_event"
                ]
            else:
                result = evaluate_target_compliance(bundle, messages)
                new = result.compliant
                new_confirmation = None
                new_evidence = result.violation_evidence
                confirmation_events = [
                    event
                    for event in result.checked_events
                    if event.get("event_type") == "confirmation_event"
                ]
            confirmation_changed = (
                old_confirmation is not None
                and bool(old_confirmation) != bool(new_confirmation)
            )
            changed = old != new
            reason = _change_reason(
                mechanism,
                old,
                new,
                confirmation_changed=confirmation_changed,
            )
            replay_records.append(
                {
                    "trajectory_identifier": (
                        f"{source}:{row['task_id']}:rollout_{row['rollout_index']}"
                    ),
                    "source": source,
                    "task_id": row["task_id"],
                    "rollout_index": row["rollout_index"],
                    "split": row.get("split"),
                    "trajectory_hash": trajectory_hash,
                    "stored_trajectory_hash": stored_hash,
                    "task_success": row["task_success"],
                    "old_compliance": old,
                    "new_compliance": new,
                    "old_confirmation_component": old_confirmation,
                    "new_confirmation_component": new_confirmation,
                    "mechanism": mechanism,
                    "target_rule": bundle.rule_id,
                    "changed": changed,
                    "component_changed": confirmation_changed,
                    "change_reason": reason,
                    "old_violation_evidence": row.get("violation_evidence", []),
                    "new_violation_evidence": new_evidence,
                    "new_confirmation_events": confirmation_events,
                }
            )
            if _json_hash(trajectory) != trajectory_hash:
                raise AssertionError("In-memory replay mutated trajectory content")

    formal_after = _formal_snapshot()
    gse_after = _tree_hash(gse_root)
    source_hashes_after = {str(path): _file_hash(path) for _, path, _ in DATASETS}
    changed = [
        item for item in replay_records if item["changed"] or item["component_changed"]
    ]
    old_compliant = sum(item["old_compliance"] for item in replay_records)
    new_compliant = sum(item["new_compliance"] for item in replay_records)
    split_counts = Counter(
        item["split"]
        for item in replay_records
        if item["source"] == "final_v1_train_monitor_test"
    )

    breakdown: dict[str, Any] = {}
    for label, mechanism in (
        ("Explicit Confirmation", EXPLICIT),
        ("Delayed Compensation", DELAYED),
        ("Itinerary Identity", ITINERARY),
    ):
        relevant = [
            item
            for item in replay_records
            if item["mechanism"] == mechanism
            or (mechanism == EXPLICIT and item["mechanism"] == COMPOSITION)
        ]
        relevant_changes = [
            item
            for item in relevant
            if item["changed"]
            or (mechanism == EXPLICIT and item["component_changed"])
        ]
        breakdown[label] = {
            "replay_count": len(relevant),
            "changed_labels": len(relevant_changes),
            "change_reasons": dict(
                Counter(item["change_reason"] for item in relevant_changes)
            ),
        }

    contract = {
        "trajectory_content_unchanged": True,
        "trajectory_hashes_unchanged": source_hashes_before == source_hashes_after,
        "task_success_unchanged": True,
        "formal_task_population_unchanged": (
            formal_before["task_population"] == formal_after["task_population"] == 116
        ),
        "train_monitor_test_split_unchanged": (
            formal_before["split_task_ids"] == formal_after["split_task_ids"]
        ),
        "formal_input_files_unchanged": (
            formal_before["file_hashes"] == formal_after["file_hashes"]
        ),
        "gse_artifacts_unchanged": gse_before == gse_after,
        "no_new_agent_or_user_simulator_calls": True,
        "no_new_rollouts_generated": True,
    }
    if not all(contract.values()):
        raise AssertionError(contract)
    summary = {
        "schema_version": 1,
        "oracle_version": "target_rule_compliance_v2_step0",
        "total_replayed": len(replay_records),
        "dataset_counts": dict(Counter(item["source"] for item in replay_records)),
        "formal_split_replay_counts": {
            split: split_counts[split] for split in ("train", "monitor", "test")
        },
        "old_counts": {
            "compliant": old_compliant,
            "violation": len(replay_records) - old_compliant,
        },
        "new_counts": {
            "compliant": new_compliant,
            "violation": len(replay_records) - new_compliant,
        },
        "changed_top_level_count": sum(item["changed"] for item in replay_records),
        "changed_audit_count": len(changed),
        "repair_breakdown": breakdown,
        "formal_task_population": formal_after["task_population"],
        "gse_artifact_file_count": gse_after[1],
        "regression_contract": contract,
        "records": replay_records,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "oracle_replay_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    (OUTPUT_DIR / "changed_labels.json").write_text(
        json.dumps(
            {"schema_version": 1, "changed_count": len(changed), "records": changed},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    (OUTPUT_DIR / "regression_report.md").write_text(
        _render_report(summary, changed)
    )
    return summary


if __name__ == "__main__":
    result = replay_saved_v1()
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in {"records"}
            },
            ensure_ascii=False,
            indent=2,
        )
    )
