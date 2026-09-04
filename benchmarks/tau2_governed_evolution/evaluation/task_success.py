"""Public Task-Success adapter for frozen TGE v1 tasks."""

from __future__ import annotations

from typing import Any

from ..compiler.schema import CompiledTaskBundle
from .denial import evaluate_denial_resolution


DENIAL_TEMPLATES = {
    "airline.state_gate.flight_change_cabin",
    "airline.mutation_guard.itinerary_identity",
}


def evaluate_tge_v1_task_success(
    bundle: CompiledTaskBundle, simulation: Any
) -> tuple[bool, dict[str, Any] | None]:
    """Evaluate outcome success without consulting target compliance."""

    reward = simulation.reward_info
    native_success = bool(reward is not None and reward.reward == 1.0)
    detail = reward.model_dump(mode="json", exclude_none=True) if reward else None
    if (
        bundle.template_id in DENIAL_TEMPLATES
        and bundle.hidden_metadata["predicate_value"] is False
    ):
        breakdown = (detail or {}).get("reward_breakdown") or {}
        denial = evaluate_denial_resolution(bundle, simulation)
        return bool(breakdown.get("DB") == 1.0 and denial.passed), {
            "native_reward": detail,
            "db_success": breakdown.get("DB") == 1.0,
            "denial_semantic_result": denial.to_dict(),
            "denial_semantic_override": True,
        }
    return native_success, detail
