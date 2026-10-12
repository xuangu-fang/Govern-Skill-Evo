"""Render a compact engineering calibration report from structured results."""

from __future__ import annotations

from typing import Any


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _states(row: dict[str, Any]) -> str:
    counts = row["behavior_states"]
    return " / ".join(f"{key} {counts[key]}" for key in ("CS", "VS", "CF", "VF"))


def render_calibration_report(
    analysis: dict[str, Any], run_config: dict[str, Any], run_status: dict[str, Any]
) -> str:
    overall = analysis["overall"]
    lines = [
        "# τ² Governed Evolution Pilot Calibration",
        "",
        "## 1. Run Configuration",
        "",
        f"- Tasks: {run_status['task_count']}",
        f"- Rollouts requested/completed: {run_status['requested_rollouts']}/{run_status['recorded_rollouts']}",
        f"- Base Agent: `{run_config['agent_implementation']}` / `{run_config['agent_model']}`; temperature {run_config['agent_temperature']}; thinking `{run_config['agent_thinking']}`; max tokens {run_config['agent_max_tokens']}",
        f"- User Simulator: `{run_config['user_implementation']}` / `{run_config['user_model']}`; temperature {run_config['user_temperature']}; thinking `{run_config['user_thinking']}`; max tokens {run_config['user_max_tokens']}",
        f"- Seeds: {run_config['rollout_seeds']}; max steps {run_config['max_steps']}; concurrency {run_config['max_concurrency']}",
        f"- Skill Evolution: {run_config['skill_evolution_enabled']}; auto-review / LLM compliance judge: {run_config['auto_review_enabled']}",
        f"- Runtime failures: {overall['runtime_failures']}",
        "",
        "## 2. Overall Success × Compliance",
        "",
        f"- {_states(overall)}",
        f"- Task Success: {_pct(overall['task_success_rate'])}",
        f"- Target Compliance: {_pct(overall['target_compliance_rate'])}",
        f"- CuP (CS / all rollouts): {_pct(overall['cup_rate'])}",
        "",
        "## 3. Per-Template Results",
        "",
    ]
    for row in analysis["template_summary"]:
        lines.extend(
            [
                f"### `{row['template_id']}`",
                "",
                f"- {_states(row)}; Success {_pct(row['task_success_rate'])}; Compliance {_pct(row['target_compliance_rate'])}; runtime failures {row['runtime_failures']}",
                f"- DB-correct but communication-check-only failures: {row['communication_only_failures']}",
                f"- Repair-prone side: `{row['repair_prone_side']}`; counterpart: `{row['benign_counterpart_side']}`",
                f"- Diagnosis: {', '.join(row['diagnosis_labels'])}",
                "",
            ]
        )
    lines.extend(["## 4. Predicate-Side Results", ""])
    for row in analysis["predicate_side_summary"]:
        lines.append(
            f"- `{row['template_id']}` / `{row['predicate_side']}`: {_states(row)}; Success {_pct(row['task_success_rate'])}; Compliance {_pct(row['target_compliance_rate'])}."
        )
    lines.extend(["", "## 5. Manifestation-Level Results", ""])
    for row in analysis["task_summary"]:
        lines.append(
            f"- `{row['task_id']}` ({row['predicate_side']}): success {row['success_count']}/3, violations {row['violation_count']}/3, {_states(row)}, dominant `{row['dominant_state']}`, stability `{row['state_consistency']}`."
        )
    lines.extend(["", "## 6. Concept Replication", ""])
    for row in analysis["replication_summary"]:
        lines.append(
            f"- `{row['template_id']}`: violation manifestations any/stable {row['violation_manifestations_any']}/{row['violation_manifestations_stable']}; failure manifestations any/stable {row['failure_manifestations_any']}/{row['failure_manifestations_stable']}; stable good manifestations {row['stable_good_manifestations']}."
        )
        for side in row["by_predicate_side"]:
            lines.append(
                f"  - `{side['predicate_side']}`: violation any/stable {side['violation_manifestations_any']}/{side['violation_manifestations_stable']}; failure any/stable {side['failure_manifestations_any']}/{side['failure_manifestations_stable']}; stable good {side['stable_good_manifestations']}."
            )
    lines.extend(["", "## 7. Surface Behavior Variation", ""])
    for row in analysis["surface_variation"]:
        signatures = "; ".join(
            f"{item['task_id']}={item['behavior_states']}" for item in row["manifestations"]
        )
        lines.append(
            f"- `{row['template_id']}` / `{row['predicate_side']}`: variation `{str(row['surface_behavior_variation']).lower()}` — {signatures}."
        )
    h = analysis["headroom"]
    lines.extend(
        [
            "",
            "## 8. Skill Evolution Headroom",
            "",
            f"- Non-CS rollouts: {h['total_non_cs_rollouts']}",
            f"- Violation-bearing rollouts (VS + VF): {h['violation_bearing_rollouts']}",
            f"- Compliant failures (CF): {h['compliant_failures']}",
            f"- DB-correct, communication-check-only failures: {h['communication_only_failures']}",
            f"- Tasks with at least one non-CS rollout: {h['tasks_with_at_least_one_non_cs']}",
            f"- Tasks with at least two of three non-CS rollouts: {h['tasks_with_at_least_two_of_three_non_cs']}",
            "",
            "## 9. Main Findings",
            "",
            "The pilot creates real non-CS headroom and strong predicate-side differences. Checked-baggage violations repeat across independent no-mandate manifestations, while the cabin block side also produces prohibited mutation attempts. Itinerary-identity failures contain no target-rule violations and therefore mostly expose resolution/evaluator capability rather than governance repair signal.",
            "",
            "A compiler/evaluation calibration issue is visible on denial tasks: many trajectories preserve the DB and communicate a semantically correct refusal such as ‘cannot be modified’, yet the deterministic COMMUNICATE evaluator requires the literal information string ‘cannot change’. These are counted exactly as upstream τ² Task Failures, but should not be interpreted as clean capability failures without inspecting the reward breakdown.",
            "",
            "The pilot therefore has a more Skill-Evolution-oriented structure—repeated rule manifestations, bad-side violations, and good-side protection cases—but the claim remains structural, not a measured improvement over original τ². A same-model original-task control would be needed for a numerical comparison, and the denial communication criterion should be reviewed before a later evolution experiment.",
            "",
            "The outputs preserve Task Success and Target Compliance independently. Runtime failures remain in the recorded denominator and are separately identified. No benchmark task, boundary, compiler artifact, or compliance rule was changed in response to these results.",
        ]
    )
    return "\n".join(lines) + "\n"
