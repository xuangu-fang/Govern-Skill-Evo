"""Small schemas used by the calibration runner and reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CalibrationConfig:
    agent_implementation: str
    agent_model: str
    agent_temperature: float
    agent_thinking: str
    agent_reasoning_effort: str
    agent_max_tokens: int
    max_steps: int
    user_implementation: str
    user_model: str
    user_temperature: float
    user_thinking: str
    user_reasoning_effort: str
    user_max_tokens: int
    rollout_seeds: tuple[int, ...]
    max_concurrency: int
    skill_evolution_enabled: bool = False
    auto_review_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rollout_seeds"] = list(self.rollout_seeds)
        return data


@dataclass
class CalibrationRunResult:
    requested_tasks: int
    requested_rollouts: int
    completed_rollouts: int
    runtime_failures: int
    outputs: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
