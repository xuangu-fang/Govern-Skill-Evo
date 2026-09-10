"""Recover a Compliance-only failure without rerunning a saved simulation."""

import sys

from src.skill_evolution.autonomous_gse_v14_unified_step1_pilot import (
    CAL, OUT, ROOT, SUITE, load, write,
)

sys.path.insert(0, str(CAL))
import run_calibration as calibration
from tau2.data_model.simulation import SimulationRun


def recover(task_id: str, rollout_index: int) -> None:
    specs = {item["task_id"]: item for item in load(SUITE / "metadata/task_role_manifest.json")["tasks"]}
    tasks = {item["id"]: calibration.Task.model_validate(item) for item in load(SUITE / "tasks/final_tasks.json")}
    seeds = load(SUITE / "metadata/calibration_seeds.json")["seeds"]
    contexts = calibration.load_authoritative_domain_contexts(ROOT / "external/tau2-bench")
    context_manifest = load(SUITE / "contexts/context_manifest.json")["contexts"]
    spec = specs[task_id]
    task = tasks[task_id]
    stem = OUT / "candidate_rollouts" / f"{task_id}_{rollout_index:02d}"
    simulation = SimulationRun.model_validate(load(stem.with_name(stem.name + "_evaluated.json")))
    attempts = []

    def caller(*args):
        for number in range(1, 4):
            try:
                value = calibration.default_judge_caller(*args)
            except RuntimeError as error:
                if str(error) != "Learner returned an empty Skill.":
                    raise
                attempts.append({"attempt": number, "empty": True})
                continue
            attempts.append({"attempt": number, "empty": not bool(value and value.strip())})
            if value and value.strip():
                return value
        raise RuntimeError("JUDGE_EMPTY_AFTER_3_ATTEMPTS")

    evidence = calibration._build_governed_evidence(
        source_id=f"{task_id}_{rollout_index}", domain=spec["domain"], task=task,
        simulation=simulation, domain_policy=contexts[spec["domain"]]["original_domain_policy"],
        available_tool_contracts=contexts[spec["domain"]]["available_tool_contracts"],
        judge_caller=caller,
    )
    result = {
        "task_id": task_id, "index": rollout_index,
        "seed": seeds[task_id][rollout_index - 1],
        "context_id": context_manifest[spec["domain"]]["context_id"],
        "evidence": evidence,
        "raw_sha256": calibration.sha(stem.with_name(stem.name + "_raw.json")),
        "judge_attempts": attempts,
        "compliance_only_recovery": True,
    }
    write(stem.with_suffix(".json"), result)
    write(OUT / "evaluations/compliance" / f"{task_id}_{rollout_index:02d}.json", evidence["compliance_evaluation"])
    print("COMPLIANCE_RECOVERED", task_id, rollout_index, evidence["state"], attempts, flush=True)


if __name__ == "__main__":
    recover("16", 1)
