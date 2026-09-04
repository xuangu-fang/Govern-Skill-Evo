"""Reproducible, offline-only acceptance checks for the Step 14 Pilot."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import yaml
from pydantic import TypeAdapter

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from ..compliance.composite import evaluate_composed_compliance
from .composition_report import analyze_composition

ensure_tau2_importable()

from tau2.data_model.message import Message  # noqa: E402
from tau2.data_model.tasks import RewardType, Task  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "calibration/outputs_composition_baggage_confirmation"


def validate() -> dict:
    grid = yaml.safe_load((ROOT / "composition/examples/baggage_confirmation_grid.yaml").read_text())["composition_grid"]
    manifests = yaml.safe_load((ROOT / "surface/examples/composition_baggage_confirmation_manifestations.yaml").read_text())["manifestations"]
    scenarios = yaml.safe_load((ROOT / "realization/examples/composition_baggage_confirmation_scenarios.yaml").read_text())["scenarios"]
    tasks = [Task.model_validate(item) for item in json.loads((ROOT / "compiler/examples/tasks_composition_baggage_confirmation.json").read_text())]
    bundles = {
        item["task"]["id"]: CompiledTaskBundle.from_dict(item)
        for item in yaml.safe_load((ROOT / "compiler/examples/composition_baggage_confirmation_tasks.yaml").read_text())["compiled_bundles"]
    }
    fixtures = yaml.safe_load((ROOT / "compliance/examples/composition_baggage_confirmation_trajectories.yaml").read_text())["fixtures"]
    records = [json.loads(line) for line in (OUTPUT / "rollout_records.jsonl").read_text().splitlines() if line.strip()]
    adapter = TypeAdapter(list[Message])
    replay_matches = all(
        evaluate_composed_compliance(bundles[row["task_id"]], adapter.validate_python(row["trajectory"])).joint_compliant
        == row["joint_compliance"]
        for row in records
    )
    analysis = analyze_composition(records)
    audit = json.loads((ROOT / "compiler/examples/composition_baggage_confirmation_audit.json").read_text())
    old_regression = json.loads((OUTPUT / "oracle_regression_108.json").read_text())
    checks = {
        "four_composition_worlds": len(grid["worlds"]) == 4,
        "all_factor_combinations": {tuple(sorted(world["factor_values"].items())) for world in grid["worlds"]}
        == {tuple(sorted({"baggage_mandate_present": a, "explicit_confirmation_obtained_before_commit": b}.items())) for a in (False, True) for b in (False, True)},
        "factor_independence_audit": audit["grid_audit"]["passed"],
        "twelve_manifestations": len(manifests) == 12,
        "three_manifestations_per_world": set(Counter(item["provenance"]["composition_world_id"] for item in manifests).values()) == {3},
        "twelve_realized_scenarios": len(scenarios) == 12,
        "twelve_unique_tasks": len(tasks) == len({task.id for task in tasks}) == 12,
        "opaque_task_ids": all(re.fullmatch(r"gse_air_[0-9a-f]{12}", task.id) for task in tasks),
        "task_success_db_only": all(set(task.evaluation_criteria.reward_basis) == {RewardType.DB} and not task.evaluation_criteria.communicate_info for task in tasks),
        "task_audits_pass": len(audit["task_audits"]) == 12 and all(item["passed"] and item["gold_reward"] == 1.0 for item in audit["task_audits"]),
        "joint_compliance_is_and": all(row["joint_compliance"] == (row["baggage_compliance"] and row["confirmation_compliance"]) for row in records),
        "violation_patterns_complete": all(row["violation_pattern"] in {"none", "baggage_only", "confirmation_only", "both"} for row in records),
        "fixtures_pass": len(fixtures) == 9 and {item["violation_pattern"] for item in fixtures} == {"none", "baggage_only", "confirmation_only", "both"},
        "old_108_compliance_unchanged": old_regression["rollouts_replayed"] == 108 and old_regression["compliance_labels_unchanged"],
        "thirty_six_saved_rollouts": len(records) == 36,
        "three_rollouts_per_task": set(Counter(row["task_id"] for row in records).values()) == {3},
        "no_runtime_failures": all(row["runtime_status"] == "completed" for row in records),
        "saved_oracle_labels_replay": replay_matches,
        "summary_matches_records": analysis["overall"]["behavior_states"] == {"CS": 28, "VS": 5, "CF": 0, "VF": 3},
        "no_skill_evolution_or_llm_judge": all(not row.get("skill_evolution_enabled", False) for row in records),
    }
    result = {"schema_version": 1, "passed": all(checks.values()), "checks": checks, "new_rollouts_executed_by_validation": 0}
    (OUTPUT / "automatic_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if not result["passed"]:
        raise AssertionError([key for key, passed in checks.items() if not passed])
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
