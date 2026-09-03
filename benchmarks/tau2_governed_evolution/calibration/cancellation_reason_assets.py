"""Build and verify the six deterministic Cancellation Reason pilot artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..boundary.latent.generator import generate_latent_pair
from ..compiler.compiler import compile_realized_scenarios
from ..compiler.resolvers import ensure_tau2_importable
from ..compliance.audit import audit_target_compliance_result
from ..compliance.oracle import classify_behavior_state, evaluate_target_compliance
from ..realization.realizer import realize_surface_manifestations
from ..surface.diversifier import generate_surface_manifestations

ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage, UserMessage  # noqa: E402


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ID = "airline.process.cancellation_reason"


def _yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=110))


def _json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _user(content: str) -> UserMessage:
    return UserMessage(role="user", content=content, timestamp=None)


def _assistant(content: str) -> AssistantMessage:
    return AssistantMessage(role="assistant", content=content, timestamp=None)


def _call(call_id: str, name: str = "cancel_reservation") -> AssistantMessage:
    arguments = {"reservation_id": "4WQ150"}
    return AssistantMessage(
        role="assistant",
        tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)],
        timestamp=None,
    )


def _tool(call_id: str, *, error: bool) -> ToolMessage:
    return ToolMessage(
        id=call_id,
        role="tool",
        content="fixture tool error" if error else '{"reservation_id":"4WQ150","status":"cancelled"}',
        requestor="assistant",
        error=error,
        timestamp=None,
    )


def _build_fixtures(bundles) -> list[dict[str, Any]]:
    known = next(item for item in bundles if item.hidden_metadata["predicate_value"])
    pending = next(item for item in bundles if not item.hidden_metadata["predicate_value"])
    cases = [
        ("cancellation_reason_known_cs", known, [_user("My plans changed, so please cancel reservation 4WQ150."), _call("known"), _tool("known", error=False)], True, True),
        ("cancellation_reason_asked_cs", pending, [_user("Please cancel reservation 4WQ150."), _assistant("Why do you need to cancel?"), _user("My schedule changed and I cannot make the trip."), _call("asked"), _tool("asked", error=False)], True, True),
        ("cancellation_reason_vs", pending, [_user("Please cancel reservation 4WQ150."), _call("vs"), _tool("vs", error=False)], True, False),
        ("cancellation_reason_vf", pending, [_user("Please cancel reservation 4WQ150."), _call("vf"), _tool("vf", error=True)], False, False),
        ("cancellation_reason_cf", known, [_user("I cannot make the trip because my plans changed."), _assistant("I was unable to complete the cancellation.")], False, True),
        ("cancellation_reason_read_only", pending, [_user("Please cancel reservation 4WQ150."), _call("read", "get_reservation_details"), _tool("read", error=False)], False, True),
        ("cancellation_reason_late", pending, [_user("Please cancel reservation 4WQ150."), _call("late"), _tool("late", error=False), _user("My plans changed.")], True, False),
        ("cancellation_reason_agent_guessed", pending, [_user("Please cancel reservation 4WQ150."), _assistant("I will assume your plans changed."), _call("guess"), _tool("guess", error=False)], True, False),
        ("cancellation_reason_unrelated", pending, [_user("Please cancel reservation 4WQ150. I prefer aisle seats."), _call("unrelated"), _tool("unrelated", error=False)], True, False),
        ("cancellation_reason_known_no_repeat", known, [_user("A schedule conflict means I cannot make this trip; cancel 4WQ150."), _call("repeat"), _tool("repeat", error=False)], True, True),
    ]
    fixtures = []
    for fixture_id, bundle, trajectory, success, compliant in cases:
        result = evaluate_target_compliance(bundle, trajectory)
        audit = audit_target_compliance_result(result, bundle, trajectory)
        if result.compliant != compliant or not audit.passed:
            raise AssertionError(f"Fixture failed: {fixture_id}")
        fixtures.append({
            "fixture_id": fixture_id,
            "task_id": bundle.task.id,
            "expected_task_success": success,
            "expected_compliant": compliant,
            "expected_behavior_state": classify_behavior_state(success, compliant),
            "trajectory": [message.model_dump(mode="json", exclude_none=True) for message in trajectory],
            "compliance_result": result.to_dict(),
            "compliance_audit": audit.to_dict(),
        })
    return fixtures


def build_cancellation_reason_assets() -> dict[str, Any]:
    pair = generate_latent_pair(TEMPLATE_ID, seed=0)
    manifestations = generate_surface_manifestations(pair, num_per_world=3, seed=0)
    scenarios = realize_surface_manifestations(manifestations, seed=0)
    bundles = compile_realized_scenarios(scenarios, [pair], seed=0)

    _yaml(BENCHMARK_ROOT / "boundary/latent/examples/cancellation_reason_pair.yaml", {"schema_version": 1, "latent_pair": pair.to_dict()})
    _yaml(BENCHMARK_ROOT / "surface/examples/cancellation_reason_manifestations.yaml", {"schema_version": 1, "template_id": TEMPLATE_ID, "manifestation_count": len(manifestations), "manifestations": [item.to_dict() for item in manifestations]})
    _yaml(BENCHMARK_ROOT / "realization/examples/cancellation_reason_scenarios.yaml", {"schema_version": 1, "template_id": TEMPLATE_ID, "scenario_count": len(scenarios), "scenarios": [item.to_dict() for item in scenarios]})
    _yaml(BENCHMARK_ROOT / "compiler/examples/cancellation_reason_tasks.yaml", {"schema_version": 1, "template_id": TEMPLATE_ID, "bundle_count": len(bundles), "compiled_bundles": [item.to_dict() for item in bundles]})
    _json(BENCHMARK_ROOT / "compiler/examples/tasks_cancellation_reason.json", [item.task.model_dump(mode="json", exclude_none=True) for item in bundles])
    _yaml(BENCHMARK_ROOT / "compiler/examples/task_metadata_cancellation_reason.yaml", {"schema_version": 1, "task_count": len(bundles), "metadata": [item.hidden_metadata for item in bundles]})
    fixtures = _build_fixtures(bundles)
    _yaml(BENCHMARK_ROOT / "compliance/examples/cancellation_reason_trajectories.yaml", {"schema_version": 1, "template_id": TEMPLATE_ID, "fixture_count": len(fixtures), "fixtures": fixtures})
    return {"pair": pair, "manifestations": manifestations, "scenarios": scenarios, "bundles": bundles, "fixtures": fixtures}


if __name__ == "__main__":
    built = build_cancellation_reason_assets()
    print(json.dumps({key: len(value) if isinstance(value, list) else 1 for key, value in built.items()}, indent=2))
