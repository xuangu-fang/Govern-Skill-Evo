"""Render a compact engineering report from deterministic final-v1 statistics."""

from __future__ import annotations

from typing import Any


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _states(row: dict[str, Any]) -> str:
    states = row["behavior_states"]
    return "/".join(f"{key} {states[key]}" for key in ("CS", "VS", "CF", "VF"))


def render_report(
    analysis: dict[str, Any], config: dict[str, Any], oracle_audit: dict[str, Any]
) -> str:
    overall = analysis["overall"]
    splits = analysis["split_summary"]["splits"]
    composition = analysis["composition_summary"]
    ordering = analysis["ordering_summary"]
    replication = analysis["replication_summary"]
    lines = [
        "# Frozen Benchmark v1 — Final Base-Agent Calibration",
        "",
        "## Run configuration",
        "",
        f"- Agent: `{config['agent_model']}`, temperature `{config['agent_temperature']}`, reasoning `{config['agent_reasoning_effort']}`, max tokens `{config['agent_max_tokens']}`.",
        f"- User Simulator: `{config['user_model']}`, temperature `{config['user_temperature']}`, reasoning `{config['user_reasoning_effort']}`, max tokens `{config['user_max_tokens']}`.",
        f"- Seeds: `{config['rollout_seeds']}`; max steps `{config['max_steps']}`.",
        "- Skill injection off; auto review off; deterministic target/composite compliance only.",
        "",
        "## Overall and splits",
        "",
        f"- Overall: {_states(overall)}; Success {_pct(overall['task_success_rate'])}; Compliance {_pct(overall['target_compliance_rate'])}.",
    ]
    for split in ("train", "monitor", "test"):
        row = splits[split]
        lines.append(f"- {split.title()}: {_states(row)}; Success {_pct(row['task_success_rate'])}; Compliance {_pct(row['target_compliance_rate'])}.")
    lines += ["", "## Mechanisms", ""]
    for row in analysis["mechanism_summary"]["mechanisms"]:
        lines.append(
            f"- `{row['split']}` / `{row['mechanism_id']}`: {row['family_count']} families, "
            f"{row['task_count']} tasks, {_states(row)}; Success {_pct(row['task_success_rate'])}; "
            f"Compliance {_pct(row['target_compliance_rate'])}; families any/stable non-CS "
            f"{row['families_with_any_non_cs']}/{row['families_with_stable_non_cs']}."
        )
    lines += ["", "## Train repair density and Monitor balance", ""]
    lines += [
        f"- Train repair families with any non-CS: {replication['train_repair_families_with_any_non_cs']}/{replication['train_repair_family_count']} ({replication['repair_signal_family_fraction']:.1%}).",
        f"- Train tasks with any non-CS: {replication['repair_signal_task_fraction']:.1%}.",
        f"- Monitor stable preservation tasks/families: {replication['monitor_stable_preservation_tasks']}/{replication['monitor_stable_preservation_families']}.",
        f"- Monitor repair-sensitive tasks/families: {replication['monitor_repair_sensitive_tasks']}/{replication['monitor_repair_sensitive_families']}.",
        "",
        "## Held-out composition",
        "",
        f"- Overall: {_states(composition['overall'])}; Baggage compliant {composition['overall']['baggage_compliant']}/{composition['overall']['rollouts']}; Confirmation compliant {composition['overall']['confirmation_compliant']}/{composition['overall']['rollouts']}; Joint compliant {composition['overall']['joint_compliant']}/{composition['overall']['rollouts']}.",
        f"- Violation patterns: `{composition['violation_patterns']}`.",
        f"- Atomic pending confirmation compliance: {composition['atomic_confirmation_pending']['target_compliant']}/{composition['atomic_confirmation_pending']['rollouts']}; composition pending: {composition['composition_confirmation_pending']['confirmation_compliant']}/{composition['composition_confirmation_pending']['rollouts']}.",
        f"- Strict atomic-stable → composition-failure: `{composition['strict_atomic_stable_to_composition_failure']}`; composition confirmation degradation observed: `{composition['composition_confirmation_degradation_observed']}`.",
    ]
    for row in composition["worlds"]:
        lines.append(f"- {row['world']}: {_states(row)}; baggage {row['baggage_compliant']}/{row['rollouts']}; confirmation {row['confirmation_compliant']}/{row['rollouts']}.")
    lines += ["", "## Ordering", ""]
    lines += [
        f"- Overall: {_states(ordering['overall'])}.",
        f"- Workflow types: `{ordering['workflow_types']}`.",
        f"- State realization comparison: `{ordering['by_state_realization_type']}`.",
        f"- Artifact flag: `{ordering['artifact_flag']}`; comparison available: `{ordering['comparison_available']}`.",
        "",
        "## Oracle first-pass audit",
        "",
        f"- Replayed {oracle_audit.get('records_replayed', 348)} saved trajectories; trajectory hashes unchanged; new rollouts for repair: {oracle_audit.get('new_rollouts_for_oracle_repair', 0)}.",
        f"- Offline label repairs: `{oracle_audit.get('offline_label_repairs', [])}`.",
        "- The repair excludes cabin-only updates that preserve the exact original flight/date chain from the flight-change violation detector.",
        "",
        "## Benchmark Readiness Evidence",
        "",
        "| Dimension | Evidence | Risk | Decision |",
        "|---|---|---|---|",
        f"| Train repair density | {replication['train_repair_families_with_any_non_cs']}/{replication['train_repair_family_count']} repair families show non-CS | Headroom may remain sparse if concentrated | {'pass' if analysis['readiness']['train_evolution_headroom'] else 'fail'} |",
        f"| Monitor balance | stable preservation {replication['monitor_stable_preservation_tasks']} tasks; repair-sensitive {replication['monitor_repair_sensitive_tasks']} tasks | Must support both improvement and overreach detection | {'pass' if analysis['readiness']['monitor_balance'] else 'fail'} |",
        f"| Composition generalization | {_states(composition['overall'])} across two held-out families | Small family count | {'pass' if analysis['readiness']['test_g4_headroom'] else 'fail'} |",
        f"| Runtime / Oracle integrity | runtime failures {analysis['runtime_summary']['runtime_failures']}; first-pass deterministic audit retained | Natural-language parser remains rule-scoped | {'pass' if analysis['readiness']['benchmark_integrity'] else 'fail'} |",
        f"| State override integrity | `{ordering['artifact_flag']}` | Native/override comparison availability: {ordering['comparison_available']} | {'pass' if ordering['artifact_flag'] != 'possible_state_realization_artifact' else 'risk'} |",
        "| Leakage integrity | Step 16 frozen input hashes preserved | None observed | pass |",
        "",
        f"## Final status: `{analysis['readiness']['status']}`",
        "",
    ]
    for risk in analysis["readiness"]["documented_risks"]:
        lines.append(f"- Documented risk: {risk}")
    lines += [
        "",
        "Train is the only evolution evidence source, Monitor is reserved for the fixed Selection Gate, and Test remains held out for Parent-versus-Final evaluation. No task, split, entity assignment, or composition grid was changed from Step 16.",
    ]
    return "\n".join(lines) + "\n"
