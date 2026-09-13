"""Evaluator-only recovery for recorded Phase-3 trajectories; never reruns behavior."""
import json
import traceback
from pathlib import Path

import run_phase3 as run
from tau2.data_model.simulation import RewardInfo, SimulationRun


TARGETS = (("travel_request_001", 3), ("travel_request_002", 3))


def main():
    manifest = run.load(run.HERE / "runtime/run_manifest.json")
    specs = {row["task_id"]: row for row in manifest["tasks"]}
    tasks = {row["id"]: run.Task.model_validate(row) for row in run.load(run.PHASE2 / "tasks/candidate_tasks.json")}
    contexts = run.load_authoritative_domain_contexts(run.REPO / "external/tau2-bench")
    recovery_rows = []
    for task_id, index in TARGETS:
        stem = run.HERE / "trajectories" / f"{task_id}_{index:02d}"
        raw = Path(str(stem) + "_raw.json")
        output = Path(str(stem) + ".json")
        original_error = Path(str(stem) + "_error.json")
        if output.exists():
            raise RuntimeError(f"Refusing to overwrite {output}")
        simulation = SimulationRun.model_validate(run.load(raw))
        success = run.load(run.HERE / "evaluations/success" / f"{task_id}_{index:02d}.json")
        simulation.reward_info = RewardInfo(reward=float(success["success"]), info={"candidate_goal_predicate": success})
        attempts = []
        evidence = None
        for attempt in range(1, 4):
            try:
                evidence = run._build_governed_evidence(
                    source_id=f"{task_id}_{index:02d}", domain="airline", task=tasks[task_id], simulation=simulation,
                    domain_policy=contexts["airline"]["original_domain_policy"],
                    available_tool_contracts=contexts["airline"]["available_tool_contracts"],
                    judge_caller=run.default_judge_caller,
                )
                attempts.append({"attempt": attempt, "status": "valid"})
                break
            except Exception as error:
                attempts.append({"attempt": attempt, "status": "invalid", "error_type": type(error).__name__, "message": str(error)})
        if evidence is None:
            raise RuntimeError(f"Compliance recovery exhausted for {task_id}_{index:02d}: {attempts}")
        compliance = evidence["compliance_evaluation"]
        run.write(run.HERE / "evaluations/compliance" / f"{task_id}_{index:02d}.json", compliance)
        spec = specs[task_id]
        result = {
            "task_id": task_id, "rollout_index": index, "seed": spec["seeds"][index - 1],
            "mechanism": spec["mechanism"], "polarity": spec.get("polarity"), "topology": spec["topology"],
            "context_id": "AIRLINE_PHASE_A_FINAL_V1", "success": bool(success["success"]),
            "compliance": bool(compliance["compliant"]), "judge_attempts": attempts,
            "judge_evaluator_recovery": True, "raw_sha256": run.sha256(raw), "evidence": evidence,
        }
        run.write(output, result)
        recovery_rows.append({
            "task_id": task_id, "rollout_index": index, "JUDGE_EVALUATOR_RECOVERY": True,
            "RECOVERY_REASON": run.load(original_error)["message"],
            "ORIGINAL_INVALID_ARTIFACT": str(original_error.relative_to(run.HERE)),
            "RECOVERY_COUNT": len(attempts), "trajectory_rerun": False,
            "raw_sha256": run.sha256(raw), "completed": True,
        })
    run.write(run.HERE / "runtime/evaluator_recovery.json", recovery_rows)
    print(json.dumps(recovery_rows, indent=2))


if __name__ == "__main__":
    main()
