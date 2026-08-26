"""Thin τ³ runtime and governed-evidence conversion for Autonomous GSE v0.9."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator
from typing import Any

from src.adapters.tau2.tau3_compliance_judge import (
    JUDGE_MODEL,
    JUDGE_PROMPT_VERSION,
    JUDGE_TEMPERATURE,
    ComplianceJudgment,
    JudgeCaller,
    compatibility_policy_id,
    judge_compliance,
)
from src.skill_evolution.two_dimensional_gate import classify_state


DOMAINS = {"airline", "retail"}
SKILL_PATH_ENV = "TAU2_AGENT_SKILL_PATH"


class Tau3RuntimeError(RuntimeError):
    """Raised when official τ³ output cannot satisfy the v0.9 contract."""


@contextmanager
def _skill_environment(skill_path: Path | None) -> Iterator[str]:
    """Select the frozen τ³ agent and scope learned-Skill injection."""

    previous = os.environ.get(SKILL_PATH_ENV)
    if skill_path is None:
        os.environ.pop(SKILL_PATH_ENV, None)
        agent_name = "llm_agent"
    else:
        os.environ[SKILL_PATH_ENV] = str(skill_path.resolve())
        agent_name = "llm_agent_manual_skill"
    try:
        yield agent_name
    finally:
        if previous is None:
            os.environ.pop(SKILL_PATH_ENV, None)
        else:
            os.environ[SKILL_PATH_ENV] = previous


def _trajectory_model_args(
    config: dict[str, Any], rollout_seed: int, *, include_max_tokens: bool
) -> dict[str, Any]:
    """Build the frozen arguments for an Agent or UserSimulator call."""

    args = {
        "temperature": config["temperature"],
        "seed": rollout_seed,
    }
    if "reasoning_effort" in config:
        args["reasoning_effort"] = config["reasoning_effort"]
    if "empty_response_retries" in config:
        args["empty_response_retries"] = config["empty_response_retries"]
        args["empty_response_retry_max_tokens"] = config[
            "empty_response_retry_max_tokens"
        ]
        args["invalid_tool_arguments_retries"] = config[
            "empty_response_retries"
        ]
    if include_max_tokens:
        args["max_tokens"] = config["max_tokens"]
    return args


def _plain(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise Tau3RuntimeError("Expected a τ³ model or dictionary.")


def stable_trajectory(messages: list[Any]) -> list[dict[str, Any]]:
    """Linearize all observable messages and calls with one-based stable IDs."""

    events: list[dict[str, Any]] = []
    tool_names: dict[str, str] = {}
    for raw_message in messages:
        message = _plain(raw_message)
        role = message.get("role")
        if role in {"user", "assistant"}:
            content = message.get("content")
            if content is not None:
                events.append(
                    {
                        "step": len(events) + 1,
                        "actor": "user" if role == "user" else "agent",
                        "event_type": "message",
                        "content": content,
                    }
                )
            for call in message.get("tool_calls") or []:
                call = _plain(call)
                call_id = str(call.get("id", ""))
                if call_id:
                    tool_names[call_id] = str(call.get("name", ""))
                events.append(
                    {
                        "step": len(events) + 1,
                        "actor": "agent" if role == "assistant" else "user",
                        "event_type": "tool_call",
                        "tool_call_id": call_id,
                        "tool_name": call.get("name"),
                        "arguments": call.get("arguments") or {},
                    }
                )
        elif role == "tool":
            nested = message.get("tool_messages") or [message]
            for result in nested:
                result = _plain(result)
                call_id = str(result.get("id", ""))
                events.append(
                    {
                        "step": len(events) + 1,
                        "actor": "tool",
                        "event_type": "tool_result",
                        "tool_call_id": call_id,
                        "tool_name": tool_names.get(call_id),
                        "content": result.get("content"),
                        "error": bool(result.get("error", False)),
                    }
                )
        elif role != "system":
            raise Tau3RuntimeError(f"Unsupported τ³ message role: {role!r}")
    return events


def task_context(task: Any, *, domain: str | None = None) -> dict[str, Any]:
    """Allowlist scenario context and exclude every evaluator ground-truth field."""

    value = _plain(task)
    scenario = value.get("user_scenario")
    if not isinstance(scenario, dict):
        raise Tau3RuntimeError("τ³ task has no user scenario.")
    context = {"task_id": str(value.get("id")), "user_scenario": scenario}
    if domain is not None:
        context["domain"] = domain
    return context


def _breakdown_value(breakdown: dict[str, Any], name: str) -> float | None:
    for key, value in breakdown.items():
        key_text = getattr(key, "value", key)
        if str(key_text).casefold() == name.casefold():
            return float(value)
    return None


def official_task_evaluation(simulation: Any) -> dict[str, Any]:
    """Read Task Success only from τ³'s final official reward."""

    value = _plain(simulation)
    reward_info = value.get("reward_info")
    if not isinstance(reward_info, dict):
        raise Tau3RuntimeError("τ³ result has no official reward_info.")
    reward = reward_info.get("reward")
    if not isinstance(reward, (int, float)) or isinstance(reward, bool):
        raise Tau3RuntimeError("τ³ official reward is invalid.")
    breakdown = reward_info.get("reward_breakdown") or {}
    if not isinstance(breakdown, dict):
        raise Tau3RuntimeError("τ³ reward breakdown is invalid.")
    db_check = reward_info.get("db_check") or {}
    db_reward = db_check.get("db_reward") if isinstance(db_check, dict) else None
    if db_reward is None:
        db_reward = _breakdown_value(breakdown, "DB")
    communicate_reward = _breakdown_value(breakdown, "COMMUNICATE")
    return {
        "success": float(reward) == 1.0,
        "reward": float(reward),
        "db_reward": None if db_reward is None else float(db_reward),
        "communicate_reward": communicate_reward,
        "termination_reason": value.get("termination_reason"),
    }


def build_governed_evidence(
    *,
    source_id: str,
    domain: str,
    task: Any,
    simulation: Any,
    domain_policy: str,
    judgment: ComplianceJudgment,
) -> dict[str, Any]:
    """Map independent τ³ outcome and judge facts into v0.9 governed evidence."""

    if domain not in DOMAINS or not source_id:
        raise Tau3RuntimeError("Invalid governed-evidence lineage.")
    simulation_value = _plain(simulation)
    trajectory = stable_trajectory(simulation_value.get("messages") or [])
    evaluation = official_task_evaluation(simulation_value)
    violations = [
        {
            "policy_template_id": compatibility_policy_id(
                domain, violation.policy_requirement
            ),
            "policy_id": compatibility_policy_id(domain, violation.policy_requirement),
            "policy_requirement": violation.policy_requirement,
            "description": violation.policy_requirement,
            "evidence_steps": list(violation.evidence_steps),
            "reason": violation.reason,
        }
        for violation in judgment.violations
    ]
    state = classify_state(evaluation["success"], judgment.compliant).value
    return {
        "source_id": source_id,
        "state": state,
        "goal": task_context(task, domain=domain)["user_scenario"],
        "actions": [
            {"step": item["step"], "action": item["event_type"], **item}
            for item in trajectory
        ],
        "task_success": evaluation["success"],
        "task_evaluation": evaluation,
        "applicable_policies": [],
        "process_feedback": {
            "compliant": judgment.compliant,
            "violated_policies": violations,
        },
        "compliance_evaluation": {
            "compliant": judgment.compliant,
            "judge_model": JUDGE_MODEL,
            "judge_temperature": JUDGE_TEMPERATURE,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            "violations": violations,
        },
        "trajectory": trajectory,
    }


def evaluate_simulation(
    *,
    source_id: str,
    domain: str,
    task: Any,
    simulation: Any,
    domain_policy: str,
    judge_caller: JudgeCaller,
) -> dict[str, Any]:
    """Execute reward→judge→four-state conversion without cross-channel leakage."""

    simulation_value = _plain(simulation)
    # Validate and freeze the official channel before the independent judge call.
    # Its values are deliberately not included in the judge payload.
    official_task_evaluation(simulation_value)
    trajectory = stable_trajectory(simulation_value.get("messages") or [])
    judgment = judge_compliance(
        domain_policy,
        task_context(task, domain=domain),
        trajectory,
        domain=domain,
        caller=judge_caller,
    )
    return build_governed_evidence(
        source_id=source_id,
        domain=domain,
        task=task,
        simulation=simulation_value,
        domain_policy=domain_policy,
        judgment=judgment,
    )


def policy_provenance(policy_path: Path) -> dict[str, str]:
    data = policy_path.read_bytes()
    return {
        "domain_policy_file": policy_path.as_posix(),
        "policy_file_sha256": hashlib.sha256(data).hexdigest(),
    }


def run_official_rollout(
    *,
    tau2_root: Path,
    domain: str,
    task_id: str,
    rollout_seed: int,
    agent_config: dict[str, Any],
    user_simulator_config: dict[str, Any],
    official_evaluator_config: dict[str, Any],
    skill_path: Path | None,
    task_split: str = "train",
) -> tuple[Any, Any]:
    """Run exactly one official Airline/Retail task with the official evaluator."""

    if domain not in DOMAINS:
        raise Tau3RuntimeError("Only Airline and Retail are supported.")
    source_root = str((tau2_root / "src").resolve())
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    from tau2.data_model.simulation import TextRunConfig
    from tau2.run import get_tasks, run_single_task
    from tau2.evaluator import evaluator_nl_assertions

    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = (
        official_evaluator_config["nl_assertions_model"]
    )
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
        "temperature": official_evaluator_config["nl_assertions_temperature"]
    }

    if task_split not in {"train", "test"}:
        raise Tau3RuntimeError("Only official train/test splits are supported.")
    tasks = get_tasks(domain, task_split_name=task_split, task_ids=[str(task_id)])
    task = tasks[0]
    agent_args = _trajectory_model_args(
        agent_config, rollout_seed, include_max_tokens=True
    )
    if skill_path is not None:
        agent_args["manual_skill_path"] = str(skill_path.resolve())
    with _skill_environment(skill_path) as agent_name:
        config = TextRunConfig(
            domain=domain,
            task_split_name=task_split,
            task_ids=[str(task_id)],
            agent=agent_name,
            user="user_simulator",
            llm_agent=agent_config["model"],
            llm_args_agent=agent_args,
            llm_user=user_simulator_config["model"],
            llm_args_user=_trajectory_model_args(
                user_simulator_config, rollout_seed, include_max_tokens=True
            ),
            max_steps=agent_config["max_steps"],
            seed=rollout_seed,
            max_retries=0,
            auto_review=False,
        )
        simulation = run_single_task(config, task, seed=rollout_seed)
    return task, simulation


def write_rollout_artifact(
    path: Path,
    *,
    domain: str,
    task_id: str,
    phase: str,
    skill_version: str,
    rollout_index: int,
    rollout_seed: int,
    governed_evidence: dict[str, Any],
    provenance: dict[str, Any],
) -> None:
    payload = {
        "schema_version": "tau3_gse_rollout_0.9.0",
        "domain": domain,
        "task_id": str(task_id),
        "phase": phase,
        "skill_version": skill_version,
        "rollout_index": rollout_index,
        "rollout_seed": rollout_seed,
        "seed_lineage": {
            "rollout_seed": rollout_seed,
            "agent_seed": rollout_seed,
            "user_simulator_seed": rollout_seed,
            "environment_seed": rollout_seed,
        },
        "task_evaluation": governed_evidence["task_evaluation"],
        "compliance_evaluation": governed_evidence["compliance_evaluation"],
        "state": governed_evidence["state"],
        "trajectory": governed_evidence["trajectory"],
        "governed_evidence": governed_evidence,
        "provenance": provenance,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
