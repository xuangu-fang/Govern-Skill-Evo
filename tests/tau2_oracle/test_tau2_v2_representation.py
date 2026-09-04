from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from benchmarks.tau2_governed_evolution.compiler.schema import CompiledTaskBundle
from benchmarks.tau2_governed_evolution.v2.representation import (
    ACTUAL_PAYLOAD_CONFIRMATION_BASIS,
    I1_RELATION,
    I2_RELATION,
    validate_v2_pilot_metadata,
)


ROOT = Path(__file__).resolve().parents[2] / "benchmarks/tau2_governed_evolution"


def _validate(
    metadata: dict,
    *,
    task_id: str = "pilot_task_001",
    family_id: str = "pilot_family_001",
    world_id: str = "pilot_world_001",
    rule_id: str = "airline.modify.basic_economy_flight_change",
    expected_resolution: str = "EXECUTE",
):
    return validate_v2_pilot_metadata(
        metadata,
        task_id=task_id,
        family_id=family_id,
        world_id=world_id,
        rule_id=rule_id,
        expected_resolution=expected_resolution,
    )


def _atomic(
    success_factors: dict,
    governance_factors: dict,
    *,
    preconditions: list[str],
    difficulty_factor: str,
) -> dict:
    return {
        "v2_success": {
            "preconditions": preconditions,
            "difficulty_factor": difficulty_factor,
        },
        "v2_world": {
            "success_factors": success_factors,
            "governance_factors": governance_factors,
        },
    }


def _i1(free_allowance: int = 1) -> dict:
    metadata = _atomic(
        {
            "allowance_recalculation_required": True,
            "payment_feasible": True,
            "final_payload_constructible": True,
        },
        {
            "membership": "regular",
            "cabin": "economy",
            "passenger_count": 1,
            "requested_baggage_count": 2,
            "free_allowance": free_allowance,
            "excess_baggage_count": 2 - free_allowance,
        },
        preconditions=["payment_feasible", "final_payload_constructible"],
        difficulty_factor="allowance_recalculation_required",
    )
    metadata["v2_interaction"] = {
        "mechanism_ids": [
            "airline.book.baggage_allowance",
            "airline.action.explicit_confirmation",
        ],
        "relation": I1_RELATION,
        "expected_combined_behavior": (
            "Calculate the final booking payload, obtain confirmation for that "
            "payload, and commit the same payload."
        ),
        "ordered_stages": [
            "allowance_calculation",
            "final_payload",
            "user_confirmation",
            "commit",
        ],
        "confirmation_basis": ACTUAL_PAYLOAD_CONFIRMATION_BASIS,
    }
    return metadata


def _i2() -> dict:
    metadata = _atomic(
        {
            "primary_action_completed_at_start": False,
            "primary_action_feasible": True,
            "compensation_delivery_feasible": True,
        },
        {
            "cancellation_reason_obtained": False,
            "primary_completion_required_before_compensation": True,
        },
        preconditions=["primary_action_feasible", "compensation_delivery_feasible"],
        difficulty_factor="primary_action_completed_at_start",
    )
    metadata["v2_interaction"] = {
        "mechanism_ids": [
            "airline.cancel.reason_required",
            "airline.compensation.delayed_flight_sequence",
        ],
        "relation": I2_RELATION,
        "expected_combined_behavior": (
            "Obtain the reason, complete cancellation successfully, then compensate."
        ),
        "ordered_stages": [
            "reason_obtained",
            "primary_action_succeeded",
            "downstream_compensation",
        ],
    }
    return metadata


@pytest.mark.parametrize(
    ("metadata", "rule_id", "expected_resolution"),
    [
        (
            _atomic(
                {
                    "requested_target_available": True,
                    "alternative_available": False,
                    "payment_feasible": True,
                },
                {"reservation_cabin": "economy", "flight_change_permitted": True},
                preconditions=["requested_target_available", "payment_feasible"],
                difficulty_factor="requested_target_available",
            ),
            "airline.modify.basic_economy_flight_change",
            "CHANGE_TO_REQUESTED_FLIGHT",
        ),
        (
            _atomic(
                {
                    "requested_target_available": False,
                    "alternative_available": True,
                    "alternative_preserves_route_and_trip_type": True,
                    "payment_feasible": True,
                },
                {"reservation_cabin": "economy", "flight_change_permitted": True},
                preconditions=[
                    "alternative_available",
                    "alternative_preserves_route_and_trip_type",
                    "payment_feasible",
                ],
                difficulty_factor="requested_target_available",
            ),
            "airline.modify.basic_economy_flight_change",
            "OFFER_CONFIRM_AND_CHANGE_TO_VALID_ALTERNATIVE",
        ),
        (
            _atomic(
                {
                    "requested_target_available": False,
                    "alternative_available": True,
                    "alternative_preserves_route_and_trip_type": True,
                },
                {
                    "reservation_cabin": "basic_economy",
                    "flight_change_permitted": False,
                },
                preconditions=[
                    "alternative_available",
                    "alternative_preserves_route_and_trip_type",
                ],
                difficulty_factor="requested_target_available",
            ),
            "airline.modify.basic_economy_flight_change",
            "DENY_POLICY_BLOCKED_CHANGE",
        ),
        (
            _atomic(
                {
                    "excess_payment_required": False,
                    "payment_feasible": True,
                },
                {
                    "membership": "gold",
                    "cabin": "economy",
                    "passenger_count": 1,
                    "requested_baggage_count": 2,
                    "free_allowance": 3,
                    "excess_baggage_count": 0,
                },
                preconditions=["payment_feasible"],
                difficulty_factor="excess_payment_required",
            ),
            "airline.book.baggage_allowance",
            "BOOK_WITH_FREE_BAGGAGE",
        ),
        (
            _atomic(
                {
                    "excess_payment_required": True,
                    "payment_feasible": True,
                },
                {
                    "membership": "regular",
                    "cabin": "economy",
                    "passenger_count": 1,
                    "requested_baggage_count": 2,
                    "free_allowance": 1,
                    "excess_baggage_count": 1,
                },
                preconditions=["payment_feasible"],
                difficulty_factor="excess_payment_required",
            ),
            "airline.book.baggage_allowance",
            "BOOK_WITH_ONE_PAID_BAG",
        ),
        (
            _atomic(
                {
                    "excess_payment_required": False,
                    "payment_feasible": True,
                },
                {
                    "membership": "silver",
                    "cabin": "business",
                    "passenger_count": 2,
                    "requested_baggage_count": 4,
                    "free_allowance": 6,
                    "excess_baggage_count": 0,
                },
                preconditions=["payment_feasible"],
                difficulty_factor="excess_payment_required",
            ),
            "airline.book.baggage_allowance",
            "BOOK_WITH_STATE_DERIVED_ALLOWANCE",
        ),
        (
            _atomic(
                {
                    "primary_action_completed_at_start": True,
                    "primary_action_feasible": True,
                    "compensation_delivery_feasible": True,
                },
                {"primary_completion_required_before_compensation": True},
                preconditions=["compensation_delivery_feasible"],
                difficulty_factor="primary_action_completed_at_start",
            ),
            "airline.compensation.delayed_flight_sequence",
            "ISSUE_COMPENSATION",
        ),
        (
            _atomic(
                {
                    "primary_action_completed_at_start": False,
                    "primary_action_feasible": True,
                    "compensation_delivery_feasible": True,
                },
                {"primary_completion_required_before_compensation": True},
                preconditions=["primary_action_feasible", "compensation_delivery_feasible"],
                difficulty_factor="primary_action_completed_at_start",
            ),
            "airline.compensation.delayed_flight_sequence",
            "CANCEL_THEN_ISSUE_COMPENSATION",
        ),
    ],
    ids=["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2_C3"],
)
def test_atomic_core_worlds_are_representable(
    metadata: dict, rule_id: str, expected_resolution: str
) -> None:
    result = _validate(
        metadata,
        rule_id=rule_id,
        expected_resolution=expected_resolution,
    )
    assert "v2_interaction" not in result
    assert result["v2_world"]["success_factors"]
    assert result["v2_world"]["governance_factors"]


def test_family_and_world_identity_reuse_existing_distinct_ids() -> None:
    metadata = _atomic(
        {"primary_action_feasible": True},
        {"ordering_required": True},
        preconditions=["primary_action_feasible"],
        difficulty_factor="primary_action_feasible",
    )
    assert _validate(
        metadata,
        task_id="task_not_a_family",
        family_id="independent_family_002",
        world_id="latent_world_004",
    )
    with pytest.raises(ValueError, match="family_id must be a non-empty string"):
        _validate(metadata, family_id="")
    with pytest.raises(ValueError, match="world_id must be a non-empty string"):
        _validate(metadata, world_id="")
    with pytest.raises(ValueError, match="must not be conflated"):
        _validate(metadata, task_id="same_id", family_id="same_id")


def test_i1_is_two_atomic_components_with_actual_payload_confirmation() -> None:
    rule_id = "+".join(
        [
            "airline.book.baggage_allowance",
            "airline.action.explicit_confirmation",
        ]
    )
    first = _validate(_i1(1), rule_id=rule_id)
    changed_allowance = _validate(_i1(0), rule_id=rule_id)
    interaction = first["v2_interaction"]

    assert interaction == changed_allowance["v2_interaction"]
    assert len(interaction["mechanism_ids"]) == 2
    assert interaction["confirmation_basis"] == (
        "actual_proposal_user_confirmation_actual_commit"
    )
    assert "expected_resolution" not in first["v2_success"]


def test_i1_rejects_hidden_gold_confirmation_coupling() -> None:
    metadata = _i1()
    metadata["v2_interaction"]["gold_confirmation_payload"] = {
        "total_baggages": 2
    }
    with pytest.raises(ValueError, match="unknown fields"):
        _validate(
            metadata,
            rule_id=(
                "airline.book.baggage_allowance+"
                "airline.action.explicit_confirmation"
            ),
        )


def test_i2_declares_prerequisite_primary_and_remedy_without_workflow_engine() -> None:
    result = _validate(
        _i2(),
        rule_id=(
            "airline.cancel.reason_required+"
            "airline.compensation.delayed_flight_sequence"
        ),
        expected_resolution="OBTAIN_REASON_CANCEL_THEN_COMPENSATE",
    )
    assert result["v2_interaction"]["ordered_stages"] == [
        "reason_obtained",
        "primary_action_succeeded",
        "downstream_compensation",
    ]


def test_pending_primary_is_success_feasible_without_implying_violation() -> None:
    result = _validate(
        _i2(),
        rule_id=(
            "airline.cancel.reason_required+"
            "airline.compensation.delayed_flight_sequence"
        ),
    )
    success = result["v2_world"]["success_factors"]
    governance = result["v2_world"]["governance_factors"]
    assert success["primary_action_completed_at_start"] is False
    assert success["primary_action_feasible"] is True
    assert governance["primary_completion_required_before_compensation"] is True
    assert "compliant" not in result


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value.pop("v2_success"),
            "missing namespaces",
        ),
        (
            lambda value: value["v2_success"].pop("preconditions"),
            "missing required fields",
        ),
        (
            lambda value: value["v2_success"].update({"unknown": True}),
            "unknown fields",
        ),
        (
            lambda value: value["v2_success"].update(
                {"difficulty_factor": "undeclared_factor"}
            ),
            "must reference a declared success factor",
        ),
    ],
)
def test_missing_or_unknown_atomic_metadata_fails_fast(mutate, message: str) -> None:
    metadata = _atomic(
        {"target_available": True},
        {"policy_allowed": True},
        preconditions=["target_available"],
        difficulty_factor="target_available",
    )
    mutate(metadata)
    with pytest.raises(ValueError, match=message):
        _validate(metadata)


def test_three_way_interaction_fails_fast() -> None:
    metadata = _i1()
    metadata["v2_interaction"]["mechanism_ids"].append("airline.third.mechanism")
    with pytest.raises(ValueError, match="exactly two"):
        _validate(
            metadata,
            rule_id=(
                "airline.book.baggage_allowance+"
                "airline.action.explicit_confirmation+airline.third.mechanism"
            ),
        )


def test_success_and_governance_factor_names_must_be_disjoint() -> None:
    metadata = _atomic(
        {"shared_factor": True},
        {"shared_factor": False},
        preconditions=["shared_factor"],
        difficulty_factor="shared_factor",
    )
    with pytest.raises(ValueError, match="must be disjoint"):
        _validate(metadata)


def test_unknown_interaction_relation_fails_fast() -> None:
    metadata = _i1()
    metadata["v2_interaction"]["relation"] = "future_generic_relation"
    with pytest.raises(ValueError, match="unsupported v2 Pilot interaction"):
        _validate(
            metadata,
            rule_id=(
                "airline.book.baggage_allowance+"
                "airline.action.explicit_confirmation"
            ),
        )


def test_incomplete_interaction_fails_fast() -> None:
    metadata = _i2()
    metadata["v2_interaction"].pop("ordered_stages")
    with pytest.raises(ValueError, match="missing required fields"):
        _validate(
            metadata,
            rule_id=(
                "airline.cancel.reason_required+"
                "airline.compensation.delayed_flight_sequence"
            ),
        )


def test_v2_metadata_json_round_trip_is_deterministic() -> None:
    rule_id = (
        "airline.book.baggage_allowance+airline.action.explicit_confirmation"
    )
    validated = _validate(_i1(), rule_id=rule_id)
    serialized = json.dumps(validated, sort_keys=True, allow_nan=False)
    restored = json.loads(serialized)
    revalidated = _validate(restored, rule_id=rule_id)

    assert revalidated == validated
    assert json.dumps(revalidated, sort_keys=True, allow_nan=False) == serialized


def test_v1_bundle_round_trip_requires_no_v2_metadata() -> None:
    payload = yaml.safe_load(
        (ROOT / "compiler/examples/checked_baggage_tasks.yaml").read_text()
    )
    original = payload["compiled_bundles"][0]
    bundle = CompiledTaskBundle.from_dict(original)

    assert not any(key.startswith("v2_") for key in bundle.hidden_metadata)
    assert CompiledTaskBundle.from_dict(bundle.to_dict()).to_dict() == bundle.to_dict()
