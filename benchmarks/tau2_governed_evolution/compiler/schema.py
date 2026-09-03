"""Internal wrapper schemas for compiled executable tau2 tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .resolvers import ensure_tau2_importable

ensure_tau2_importable()

from tau2.data_model.tasks import Task  # noqa: E402


@dataclass
class CompilationAuditResult:
    passed: bool
    schema_valid: bool
    provenance_preserved: bool
    predicate_materialized: bool
    user_goal_preserved: bool
    no_extra_policy_blocker: bool
    expected_resolution_consistent: bool
    environment_loadable: bool
    gold_satisfiable: bool
    violations: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompilationAuditResult":
        return cls(**data)


@dataclass
class CompiledTaskBundle:
    compiled_task_id: str
    scenario_id: str
    manifestation_id: str
    latent_pair_id: str
    latent_world_id: str
    template_id: str
    concept_id: str
    rule_id: str
    task: Task
    expected_governance: str
    expected_resolution: str
    hidden_metadata: dict[str, Any]
    compilation_audit: CompilationAuditResult

    def __post_init__(self) -> None:
        if not isinstance(self.task, Task):
            raise TypeError("task must be a tau2 Task")

    def to_dict(self) -> dict[str, Any]:
        values = asdict(self)
        values["task"] = self.task.model_dump(mode="json", exclude_none=True)
        return values

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompiledTaskBundle":
        values = dict(data)
        values["task"] = Task.model_validate(values["task"])
        values["compilation_audit"] = CompilationAuditResult.from_dict(
            values["compilation_audit"]
        )
        return cls(**values)
