"""Learn one transition Skill from V1 Partial-view experience only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable


ensure_tau2_importable()

from tau2.data_model.simulation import SimulationRun  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import (  # noqa: E402
    CAMPAIGN_PATH,
    PROJECT_ROOT,
)
from benchmarks.tau2_governed_evolution.transition_ablation.build_transition_probe import (  # noqa: E402
    FORBIDDEN_PATTERNS,
    PARTIAL_POLICY_PATH,
)
from benchmarks.tau2_governed_evolution.transition_ablation.validate_transition_probe import (  # noqa: E402
    EXPERIMENT_MANIFEST,
    load_suite,
)
from src.adapters.tau2.tau3_gse_runtime import (  # noqa: E402
    official_task_evaluation,
    stable_trajectory,
    task_context,
)
from src.learners.stwebagentbench.generate_governed_skill_v14 import (  # noqa: E402
    call_governed_editor,
)
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext  # noqa: E402
from src.skill_evolution.autonomous_gse_v14_proposal import (  # noqa: E402
    MultiRolloutDiagnosisProposalOperator,
)
from src.skill_evolution.diagnosis_v14 import call_diagnosis  # noqa: E402


ARTIFACT_ROOT = PROJECT_ROOT / "artifacts/transition_ablation_step4v"
LEARNING_ROOT = ARTIFACT_ROOT / "learning"
SKILL_PATH = LEARNING_ROOT / "S_A_transition.md"
DECISION_PATH = LEARNING_ROOT / "learning_decision.json"
PARENT_PATH = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _imputed_seed_one(task: Any, raw_path: Path) -> dict[str, Any]:
    """Recover Success evidence when only the independent Judge transport failed."""

    raw = SimulationRun.model_validate(_load(raw_path))
    evaluation = official_task_evaluation(raw)
    trajectory = stable_trajectory(raw.messages)
    return {
        "source_id": f"step4v_partial_empty_{task.id}_01",
        "domain": "retail",
        "task_id": task.id,
        "rollout_index": 1,
        "rollout_seed": raw.seed,
        "state": "compliant_failure",
        "goal": task_context(task, domain="retail")["user_scenario"],
        "actions": [{"step": row["step"], "action": row["event_type"], **row} for row in trajectory],
        "trajectory": trajectory,
        "task_success": evaluation["success"],
        "task_evaluation": evaluation,
        "applicable_policies": [],
        "process_feedback": {"compliant": True, "violated_policies": []},
        "compliance_evaluation": {
            "compliant": True,
            "violations": [],
            "status": "imputed_from_two_same-task_completed_judgments",
            "note": "Judge transport/validator failed; Compliance is not an optimization axis for this probe.",
        },
    }


def _training_evidence(task: Any) -> tuple[dict[str, Any], ...]:
    task_id = task.id
    values: list[dict[str, Any]] = []
    for index in (1, 2, 3):
        path = ARTIFACT_ROOT / "partial_empty" / f"{task_id}_rollout_{index:02d}.json"
        if path.exists():
            artifact = _load(path)
            evidence = dict(artifact["governed_evidence"])
            evidence.update({
                "domain": artifact["domain"], "task_id": artifact["task_id"],
                "rollout_index": artifact["rollout_index"],
                "rollout_seed": artifact["rollout_seed"],
            })
            values.append(evidence)
        elif index == 1:
            values.append(_imputed_seed_one(
                task,
                ARTIFACT_ROOT / "partial_empty" / f"{task_id}_rollout_01_tau2_raw.json",
            ))
        else:
            raise FileNotFoundError(path)
    return tuple(values)


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    experiment = _load(EXPERIMENT_MANIFEST)
    _, tasks = load_suite()
    training_id = experiment["task_ids"][0]
    task = tasks[training_id]
    partial_policy = PARTIAL_POLICY_PATH.read_text(encoding="utf-8")
    contexts = v14.load_authoritative_domain_contexts(
        PROJECT_ROOT / _load(CAMPAIGN_PATH)["benchmark"]["path"]
    )
    tools = tuple(contexts["retail"]["available_tool_contracts"])
    learner_context = partial_policy + json.dumps(tools, ensure_ascii=False)
    import re
    leaks = [pattern for pattern in FORBIDDEN_PATTERNS if re.search(pattern, learner_context, re.I)]
    if leaks:
        raise ValueError(f"learner-visible context leaks hidden transition clause: {leaks}")
    display_parent = PARENT_PATH.read_text(encoding="utf-8")
    parent = display_parent.replace("# Operational Skill", "# SuiteCRM Operational Skill", 1)
    operator = MultiRolloutDiagnosisProposalOperator()
    decision = operator.propose(
        ProposalContext(
            candidate_id="step4v_transition_skill",
            parent_skill=parent,
            current_batch_governed_evidence=_training_evidence(task),
        ),
        call_diagnosis,
        call_governed_editor,
        domain_contexts={
            "retail": {
                "original_domain_policy": partial_policy,
                "available_tool_contracts": tools,
            }
        },
    )
    LEARNING_ROOT.mkdir(parents=True, exist_ok=True)
    payload = dict(decision.__dict__)
    payload["knowledge_isolation"] = {
        "training_task_ids": [training_id],
        "held_out_task_ids": experiment["task_ids"][1:],
        "agent_visible_policy": PARTIAL_POLICY_PATH.as_posix(),
        "canonical_hidden_clause_visible_to_learner": False,
        "tool_outputs_and_errors_visible": True,
        "judge_seed_840_imputation": "Compliance=true copied from the two completed same-task judgments; Task Success and trajectory are official raw output.",
    }
    DECISION_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not decision.candidate_skill:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    display_skill = decision.candidate_skill.replace(
        "# SuiteCRM Operational Skill", "# Operational Skill", 1,
    )
    SKILL_PATH.write_text(display_skill, encoding="utf-8")
    print(json.dumps({
        "proposal_status": decision.proposal_status,
        "eligible_diagnosis_ids": decision.eligible_diagnosis_ids,
        "skill_path": SKILL_PATH.as_posix(),
        "skill": display_skill,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
