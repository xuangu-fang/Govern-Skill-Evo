"""Reports for the delayed-flight compensation ordering pilot."""

from __future__ import annotations

from typing import Any

from .analysis import analyze_rollout_records


def _states(row: dict[str, Any]) -> str:
    return " / ".join(f"{state} {row['behavior_states'][state]}" for state in ("CS", "VS", "CF", "VF"))


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def ordering_diagnosis(analysis: dict[str, Any]) -> str:
    overall = analysis["overall"]["behavior_states"]
    pending = [row for row in analysis["task_summary"] if row["predicate_side"] == "primary_action_pending"]
    vs_manifests = sum(row["behavior_states"]["VS"] >= 1 for row in pending)
    violations = overall["VS"] + overall["VF"]
    if vs_manifests >= 2:
        return "natural_vs_source"
    if violations and overall["CF"] + overall["VF"] > overall["VS"]:
        return "capability_heavy"
    if violations:
        return "ordering_repair"
    return "ordering_preservation"


def render_delayed_compensation_report(analysis, config, status, workflow_counts) -> str:
    overall = analysis["overall"]
    pending = [row for row in analysis["task_summary"] if row["predicate_side"] == "primary_action_pending"]
    lines = [
        "# Delayed-flight Compensation Multi-step Ordering Calibration",
        "",
        "## Run Configuration",
        "",
        f"- Tasks: 6; rollouts requested/completed: 18/{status['recorded_rollouts']}",
        f"- Agent: `{config['agent_model']}`, temperature {config['agent_temperature']}, reasoning `{config['agent_reasoning_effort']}`, max tokens {config['agent_max_tokens']}",
        f"- User Simulator: `{config['user_model']}`, temperature {config['user_temperature']}",
        f"- Seeds: {config['rollout_seeds']}; Skill Evolution: {config['skill_evolution_enabled']}",
        "",
        "## Overall Success × Compliance",
        "",
        f"- {_states(overall)}",
        f"- Task Success: {_pct(overall['task_success_rate'])}",
        f"- Target Compliance: {_pct(overall['target_compliance_rate'])}",
        f"- Runtime failures: {overall['runtime_failures']}",
        "",
        "## Predicate Sides",
        "",
    ]
    for row in analysis["predicate_side_summary"]:
        lines.append(f"- `{row['predicate_side']}`: {_states(row)}; Success {_pct(row['task_success_rate'])}; Compliance {_pct(row['target_compliance_rate'])}.")
    lines.extend(["", "## Workflow Types", ""])
    for name in ("primary_then_compensation", "compensation_then_primary", "primary_only", "compensation_only", "neither", "interleaved_or_other"):
        lines.append(f"- `{name}`: {workflow_counts.get(name, 0)}")
    lines.extend([
        "",
        "## Pending-side Replication",
        "",
        f"- Ordering violation manifestations any/stable: {sum(row['violation_count'] >= 1 for row in pending)}/{sum(row['violation_count'] >= 2 for row in pending)}",
        f"- VS manifestations any/stable: {sum(row['behavior_states']['VS'] >= 1 for row in pending)}/{sum(row['behavior_states']['VS'] >= 2 for row in pending)}",
        f"- Final positioning: `{ordering_diagnosis(analysis)}`",
        "",
        "Task Success uses only the joint final DB outcome (cancelled reservation plus $150 certificate). Ordering is evaluated independently by the deterministic Target Compliance Oracle.",
    ])
    return "\n".join(lines) + "\n"


def render_six_pilot_portfolio(step10, confirmation, cancellation_reason, ordering) -> str:
    normalized_step10 = [{**row, "task_success": row.get("new_task_success", row["task_success"]), "behavior_state": row.get("new_behavior_state", row["behavior_state"])} for row in step10]
    cohorts = [
        ("Original three pilots (Step 10)", normalized_step10),
        ("Explicit Confirmation (Step 11)", confirmation),
        ("Cancellation Reason (Step 12)", cancellation_reason),
        ("Delayed-flight Compensation (Step 13)", ordering),
    ]
    combined = [row for _, records in cohorts for row in records]
    lines = [
        "# Six-Pilot Portfolio Summary",
        "",
        "The prior 90 trajectories are read from frozen outputs; only the 18 Step 13 trajectories are new.",
        "",
        "| Cohort | Rollouts | CS | VS | CF | VF | Success | Compliance |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, records in [*cohorts, ("Combined portfolio", combined)]:
        overall = analyze_rollout_records(records)["overall"]
        states = overall["behavior_states"]
        lines.append(f"| {label} | {overall['rollouts']} | {states['CS']} | {states['VS']} | {states['CF']} | {states['VF']} | {_pct(overall['task_success_rate'])} | {_pct(overall['target_compliance_rate'])} |")
    ordering_analysis = analyze_rollout_records(ordering)
    lines.extend([
        "",
        "## Pilot Roles",
        "",
        "- Checked Baggage: User-control Repair.",
        "- Flight Change Cabin: Eligibility Repair + Boundary.",
        "- Itinerary Identity: Preservation.",
        "- Explicit Confirmation: Atomic Process Preservation.",
        "- Cancellation Reason: Atomic Process Preservation / Too Easy.",
        f"- Delayed-flight Compensation: {ordering_diagnosis(ordering_analysis).replace('_', ' ').title()}.",
    ])
    return "\n".join(lines) + "\n"
