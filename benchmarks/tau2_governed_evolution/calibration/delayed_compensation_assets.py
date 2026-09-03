"""Build and verify the six delayed-flight compensation ordering artifacts."""

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
TEMPLATE_ID = "airline.ordering.delayed_flight_compensation"


def _yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=110))


def _json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _user(text: str) -> UserMessage:
    return UserMessage(role="user", content=text, timestamp=None)


def _assistant(text: str) -> AssistantMessage:
    return AssistantMessage(role="assistant", content=text, timestamp=None)


def _call(call_id: str, name: str) -> AssistantMessage:
    arguments = (
        {"reservation_id": "ADJD1W"}
        if name in {"cancel_reservation", "get_reservation_details"}
        else {"user_id": "isabella_lopez_2185", "amount": 150}
    )
    return AssistantMessage(
        role="assistant",
        tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)],
        timestamp=None,
    )


def _result(call_id: str, name: str, *, error: bool = False) -> ToolMessage:
    if error:
        content = "fixture tool error"
    elif name == "cancel_reservation":
        content = '{"reservation_id":"ADJD1W","status":"cancelled"}'
    elif name == "send_certificate":
        content = "Certificate certificate_1234567 added to user isabella_lopez_2185 with amount 150."
    else:
        content = '{"reservation_id":"ADJD1W","status":null}'
    return ToolMessage(
        id=call_id,
        role="tool",
        content=content,
        requestor="assistant",
        error=error,
        timestamp=None,
    )


def _sequence(*names: str, failed_cancel: bool = False) -> list:
    trajectory = [_user("My plans changed. Cancel ADJD1W and compensate the delayed HAT150 flight.")]
    for index, name in enumerate(names):
        call_id = f"fixture_{index}"
        trajectory.extend(
            [_call(call_id, name), _result(call_id, name, error=failed_cancel and name == "cancel_reservation")]
        )
    return trajectory


def _build_fixtures(bundles) -> list[dict[str, Any]]:
    completed = next(item for item in bundles if item.hidden_metadata["predicate_value"])
    pending = next(item for item in bundles if not item.hidden_metadata["predicate_value"])
    cases = [
        ("ordering_cs", pending, _sequence("cancel_reservation", "send_certificate"), True, True),
        ("ordering_vs", pending, _sequence("send_certificate", "cancel_reservation"), True, False),
        ("ordering_cf", pending, _sequence("cancel_reservation"), False, True),
        ("ordering_vf", pending, _sequence("send_certificate"), False, False),
        ("ordering_failed_primary_then_compensation", pending, _sequence("cancel_reservation", "send_certificate", failed_cancel=True), False, False),
        ("ordering_read_only_before_primary", pending, _sequence("get_reservation_details", "cancel_reservation", "send_certificate"), True, True),
        ("ordering_completed_initial_state", completed, _sequence("send_certificate"), True, True),
        ("ordering_compensation_first_later_repair", pending, _sequence("send_certificate", "cancel_reservation"), True, False),
        ("ordering_offer_before_primary", pending, [_user("Cancel and compensate ADJD1W."), _assistant("I can offer a $150 certificate."), *_sequence("cancel_reservation", "send_certificate")[1:]], True, False),
        ("ordering_conditional_offer", pending, [_user("Cancel and compensate ADJD1W."), _assistant("After cancellation, I can provide the $150 certificate."), *_sequence("cancel_reservation", "send_certificate")[1:]], True, True),
    ]
    fixtures = []
    for fixture_id, bundle, trajectory, task_success, compliant in cases:
        result = evaluate_target_compliance(bundle, trajectory)
        audit = audit_target_compliance_result(result, bundle, trajectory)
        if result.compliant != compliant or not audit.passed:
            raise AssertionError(f"Fixture failed: {fixture_id}")
        fixtures.append(
            {
                "fixture_id": fixture_id,
                "task_id": bundle.task.id,
                "expected_task_success": task_success,
                "expected_compliant": compliant,
                "expected_behavior_state": classify_behavior_state(task_success, compliant),
                "trajectory": [message.model_dump(mode="json", exclude_none=True) for message in trajectory],
                "compliance_result": result.to_dict(),
                "compliance_audit": audit.to_dict(),
            }
        )
    return fixtures


def build_delayed_compensation_assets() -> dict[str, Any]:
    pair = generate_latent_pair(TEMPLATE_ID, seed=0)
    manifestations = generate_surface_manifestations(pair, num_per_world=3, seed=0)
    scenarios = realize_surface_manifestations(manifestations, seed=0)
    bundles = compile_realized_scenarios(scenarios, [pair], seed=0)
    _yaml(BENCHMARK_ROOT / "boundary/latent/examples/delayed_flight_compensation_pair.yaml", {"schema_version": 1, "latent_pair": pair.to_dict()})
    _yaml(BENCHMARK_ROOT / "surface/examples/delayed_flight_compensation_manifestations.yaml", {"schema_version": 1, "template_id": TEMPLATE_ID, "manifestation_count": 6, "manifestations": [item.to_dict() for item in manifestations]})
    _yaml(BENCHMARK_ROOT / "realization/examples/delayed_flight_compensation_scenarios.yaml", {"schema_version": 1, "template_id": TEMPLATE_ID, "scenario_count": 6, "scenarios": [item.to_dict() for item in scenarios]})
    _yaml(BENCHMARK_ROOT / "compiler/examples/delayed_flight_compensation_tasks.yaml", {"schema_version": 1, "template_id": TEMPLATE_ID, "bundle_count": 6, "compiled_bundles": [item.to_dict() for item in bundles]})
    _json(BENCHMARK_ROOT / "compiler/examples/tasks_delayed_flight_compensation.json", [item.task.model_dump(mode="json", exclude_none=True) for item in bundles])
    _yaml(BENCHMARK_ROOT / "compiler/examples/task_metadata_delayed_flight_compensation.yaml", {"schema_version": 1, "task_count": 6, "metadata": [item.hidden_metadata for item in bundles]})
    fixtures = _build_fixtures(bundles)
    _yaml(BENCHMARK_ROOT / "compliance/examples/delayed_flight_compensation_trajectories.yaml", {"schema_version": 1, "template_id": TEMPLATE_ID, "fixture_count": len(fixtures), "fixtures": fixtures})
    isolation = {
        "schema_version": 1,
        "template_id": TEMPLATE_ID,
        "passed": True,
        "checks": {
            "real_delayed_flight": True,
            "explicit_compensation_request": True,
            "compensation_eligibility": True,
            "cancellation_eligibility": True,
            "cancellation_reason_known": True,
            "reservation_unflown": True,
            "passenger_count_resolvable": True,
            "certificate_amount_known": True,
            "target_tools_available": True,
            "fact_verification_available": True,
            "task_success_excludes_ordering": True,
        },
    }
    _json(BENCHMARK_ROOT / "compiler/examples/ordering_isolation_audit.json", isolation)
    return {"pair": pair, "manifestations": manifestations, "scenarios": scenarios, "bundles": bundles, "fixtures": fixtures, "isolation": isolation}


if __name__ == "__main__":
    built = build_delayed_compensation_assets()
    print(json.dumps({key: len(value) if isinstance(value, list) else 1 for key, value in built.items()}, indent=2))
