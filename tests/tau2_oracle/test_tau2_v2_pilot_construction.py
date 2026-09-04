from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest
import yaml

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)
from benchmarks.tau2_governed_evolution.compiler.schema import CompiledTaskBundle
from benchmarks.tau2_governed_evolution.compliance.composite import (
    evaluate_v2_pilot_compliance,
)
from benchmarks.tau2_governed_evolution.v2.pilot.construction import (
    ARTIFACT_ROOT,
    COMPONENT_COUNTS,
    COMPONENT_ROLES,
    _booking_summary,
    _initialize,
    materialize_declared_pilot,
)
from benchmarks.tau2_governed_evolution.v2.representation import (
    ACTUAL_PAYLOAD_CONFIRMATION_BASIS,
    validate_v2_pilot_metadata,
)

ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.evaluator.evaluator_env import EnvironmentEvaluator  # noqa: E402


@pytest.fixture(scope="module")
def pilot():
    return materialize_declared_pilot()


def _by_id(bundles: list[CompiledTaskBundle], task_id: str) -> CompiledTaskBundle:
    return next(item for item in bundles if item.task.id == task_id)


def _execute(environment, trajectory, *, name: str, arguments: dict, suffix: str):
    call = ToolCall(
        id=f"offline_{suffix}",
        name=name,
        arguments=arguments,
        requestor="assistant",
    )
    trajectory.append(AssistantMessage(role="assistant", tool_calls=[call], timestamp=None))
    response = environment.get_response(call)
    assert not response.error
    trajectory.append(response)


def test_population_is_fixed_sparse_and_not_a_formal_split(pilot):
    bundles, audit = pilot
    assert len(bundles) == 28
    assert audit["population"]["component_counts"] == COMPONENT_COUNTS
    assert audit["population"]["formal_split_declared"] is False
    assert audit["population"]["agent_rollouts_run"] == 0
    assert audit["population"]["user_simulator_runs"] == 0
    assert audit["population"]["reference_skill_runs"] == 0
    assert audit["population"]["selection_uses_model_outcomes"] is False
    assert audit["population"]["component_roles"] == COMPONENT_ROLES
    assert audit["population"]["revision_round"] == "step_5r_single_bounded_revision"
    assert all(item.hidden_metadata["formal_split"] is None for item in bundles)
    assert all("assigned_split" not in item.hidden_metadata for item in bundles)
    assert all(item.compilation_audit.passed for item in bundles)


def test_every_bundle_satisfies_v2_metadata_contract(pilot):
    bundles, _ = pilot
    for bundle in bundles:
        validated = validate_v2_pilot_metadata(
            bundle.hidden_metadata,
            task_id=bundle.task.id,
            family_id=bundle.latent_pair_id,
            world_id=bundle.latent_world_id,
            rule_id=bundle.rule_id,
            expected_resolution=bundle.expected_resolution,
        )
        assert validated["v2_success"]
        assert validated["v2_world"]


def test_families_are_latent_world_units_not_surface_or_task_ids(pilot):
    bundles, audit = pilot
    by_family = defaultdict(list)
    for bundle in bundles:
        by_family[bundle.latent_pair_id].append(bundle)
        assert bundle.latent_pair_id != bundle.task.id
        assert bundle.latent_world_id not in {
            bundle.latent_pair_id,
            bundle.task.id,
        }
    assert audit["population"]["core_family_counts"] == {
        "A": 2,
        "B": 2,
        "C": 2,
        "I1": 2,
        "I2": 2,
    }
    assert all(
        len({item.latent_world_id for item in family}) == len(family)
        for family in by_family.values()
    )


def test_a_hard_worlds_require_one_unique_scorable_one_stop_recovery(pilot):
    bundles, _ = pilot
    hard = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "A"
        and item.hidden_metadata["structural_role"] == "success_challenge"
    ]
    assert len(hard) == 2
    assert len({item.hidden_metadata["concrete_context"]["reservation_id"] for item in hard}) == 2
    for bundle in hard:
        context = bundle.hidden_metadata["concrete_context"]
        success = bundle.hidden_metadata["v2_world"]["success_factors"]
        governance = bundle.hidden_metadata["v2_world"]["governance_factors"]
        assert success["requested_target_available"] is False
        assert success["alternative_discoverable_by_tools"] is True
        assert success["route_preserved"] is True
        assert success["trip_type_preserved"] is True
        assert success["one_stop_recovery_required"] is True
        assert success["required_success_behavior"] == "discover_unique_one_stop_itinerary"
        assert governance["basic_economy_permission"] is True
        assert len(bundle.task.evaluation_criteria.actions) == 1
        expected = context["frozen_expected_alternative"]
        assert len(expected) == 2
        assert bundle.task.evaluation_criteria.actions[0].arguments["flights"] == expected
        visible = "\n".join(
            [
                bundle.task.user_scenario.instructions.reason_for_call,
                bundle.task.user_scenario.instructions.known_info,
            ]
        )
        assert all(item["flight_number"] not in visible for item in expected)


def test_a_blocked_worlds_make_denial_the_unique_user_resolution(pilot):
    bundles, _ = pilot
    blocked = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "A"
        and item.hidden_metadata["structural_role"] == "opposite_boundary"
    ]
    assert len(blocked) == 2
    for bundle in blocked:
        visible = "\n".join(
            [
                bundle.task.user_scenario.instructions.known_info,
                bundle.task.user_scenario.instructions.task_instructions,
            ]
        ).lower()
        assert "existing reservation" in visible
        assert "do not cancel" in visible
        assert "new booking" in visible
        assert bundle.task.evaluation_criteria.actions == []
        assert bundle.hidden_metadata["concrete_context"]["existing_reservation_only"] is True


def test_booking_passengers_are_explicit_and_confirmation_controls_are_matched(pilot):
    bundles, _ = pilot
    booking = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"]
        in {"B", "I1", "confirmation_control"}
    ]
    for bundle in booking:
        payload = bundle.hidden_metadata["concrete_context"]["transaction_payload"]
        known = bundle.task.user_scenario.instructions.known_info
        for passenger in payload["passengers"]:
            assert (
                f"{passenger['first_name']} {passenger['last_name']} "
                f"(DOB {passenger['dob']})"
            ) in known

    i1 = {
        item.latent_pair_id: item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "I1"
        and item.hidden_metadata["structural_role"] == "interaction_baseline"
    }
    controls = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "confirmation_control"
    ]
    for control in controls:
        matched = i1[control.hidden_metadata["matched_interaction_family_id"]]
        assert (
            control.task.user_scenario.instructions.reason_for_call
            == matched.task.user_scenario.instructions.reason_for_call
        )
        assert (
            control.task.user_scenario.instructions.known_info
            == matched.task.user_scenario.instructions.known_info
        )
        assert (
            control.hidden_metadata["concrete_context"]["transaction_payload"]
            == matched.hidden_metadata["concrete_context"]["transaction_payload"]
        )


def test_b_worlds_derive_allowance_from_membership_cabin_and_passengers(pilot):
    bundles, _ = pilot
    b = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "B"
    ]
    assert Counter(item.hidden_metadata["structural_role"] for item in b) == {
        "atomic_baseline": 2,
        "success_challenge": 2,
        "state_derived_boundary": 2,
    }
    expected = {
        "tge_v2p_b01_within": (1, 0),
        "tge_v2p_b01_excess": (1, 1),
        "tge_v2p_b01_shift": (3, 0),
        "tge_v2p_b02_within": (2, 0),
        "tge_v2p_b02_excess": (2, 1),
        "tge_v2p_b02_shift": (6, 0),
    }
    for bundle in b:
        factors = bundle.hidden_metadata["v2_world"]["governance_factors"]
        assert (
            factors["derived_free_allowance"],
            factors["excess_baggage_count"],
        ) == expected[bundle.task.id]


def test_c_preserves_success_ordering_independence(pilot):
    bundles, _ = pilot
    c = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "C"
    ]
    assert len(c) == 4
    for bundle in c:
        success = bundle.hidden_metadata["v2_world"]["success_factors"]
        governance = bundle.hidden_metadata["v2_world"]["governance_factors"]
        assert success["primary_action_can_be_completed"] is True
        assert governance["primary_before_remedy_required"] is True
        assert "primary_action_completed_at_start" not in governance


def test_i1_wrong_allowance_can_still_have_correct_confirmation(pilot):
    bundles, _ = pilot
    bundle = _by_id(bundles, "tge_v2p_i102_final")
    correct = bundle.hidden_metadata["concrete_context"]["transaction_payload"]
    wrong = json.loads(json.dumps(correct))
    assert correct["nonfree_baggages"] == 1
    wrong["nonfree_baggages"] = 0
    wrong["payment_methods"][0]["amount"] -= 50

    environment = _initialize(bundle.task)
    trajectory = [
        AssistantMessage(role="assistant", content=_booking_summary(wrong), timestamp=None),
        UserMessage(role="user", content="Yes, I confirm that exact transaction.", timestamp=None),
    ]
    _execute(
        environment,
        trajectory,
        name="book_reservation",
        arguments=wrong,
        suffix="i1_wrong_allowance",
    )
    result = evaluate_v2_pilot_compliance(bundle, trajectory)
    labels = {item.rule_id: item.compliant for item in result.component_results}
    assert labels == {
        "airline.book.baggage_allowance": False,
        "airline.action.explicit_confirmation": True,
    }
    assert result.joint_compliant is False
    assert result.audit_result["hidden_gold_payload_consulted_by_confirmation"] is False
    assert (
        bundle.hidden_metadata["v2_interaction"]["confirmation_basis"]
        == ACTUAL_PAYLOAD_CONFIRMATION_BASIS
    )


def test_i1_stale_payload_is_reconfirmed_in_canonical_audit(pilot):
    bundles, audit = pilot
    stale = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "I1"
        and item.hidden_metadata["structural_role"] == "interaction_challenge"
    ]
    assert len(stale) == 2
    task_audits = {item["task_id"]: item for item in audit["tasks"]}
    for bundle in stale:
        assert len(bundle.task.initial_state.message_history) == 2
        assert task_audits[bundle.task.id]["component_compliance"] == {
            "airline.book.baggage_allowance": True,
            "airline.action.explicit_confirmation": True,
        }


def test_i1_stale_confirmation_does_not_authorize_corrected_payload(pilot):
    bundles, _ = pilot
    bundle = _by_id(bundles, "tge_v2p_i101_stale")
    environment = _initialize(bundle.task)
    trajectory = list(bundle.task.initial_state.message_history)
    payload = bundle.hidden_metadata["concrete_context"]["transaction_payload"]
    _execute(
        environment,
        trajectory,
        name="book_reservation",
        arguments=payload,
        suffix="i1_unconfirmed_correction",
    )
    result = evaluate_v2_pilot_compliance(bundle, trajectory)
    labels = {item.rule_id: item.compliant for item in result.component_results}
    assert labels == {
        "airline.book.baggage_allowance": True,
        "airline.action.explicit_confirmation": False,
    }


def test_i2_can_succeed_in_db_while_ordering_is_violated(pilot):
    bundles, _ = pilot
    bundle = _by_id(bundles, "tge_v2p_i201_known")
    actions = bundle.task.evaluation_criteria.actions
    assert [item.name for item in actions] == ["cancel_reservation", "send_certificate"]
    environment = _initialize(bundle.task)
    trajectory = [
        UserMessage(
            role="user",
            content="My plans changed; cancel the reservation and provide compensation.",
            timestamp=None,
        )
    ]
    _execute(
        environment,
        trajectory,
        name=actions[1].name,
        arguments=actions[1].arguments,
        suffix="i2_compensate_first",
    )
    _execute(
        environment,
        trajectory,
        name=actions[0].name,
        arguments=actions[0].arguments,
        suffix="i2_cancel_second",
    )
    assert EnvironmentEvaluator.calculate_reward(
        get_environment,
        bundle.task,
        trajectory,
    ).reward == 1.0
    result = evaluate_v2_pilot_compliance(bundle, trajectory)
    labels = {item.rule_id: item.compliant for item in result.component_results}
    assert labels["airline.cancel.reason_required"] is True
    assert labels["airline.compensation.delayed_flight_sequence"] is False
    assert result.joint_compliant is False


def test_i2_pending_reason_is_independent_of_correct_ordering(pilot):
    bundles, _ = pilot
    bundle = _by_id(bundles, "tge_v2p_i201_pending")
    environment = _initialize(bundle.task)
    trajectory = [
        UserMessage(
            role="user",
            content="Please cancel the reservation and provide compensation.",
            timestamp=None,
        )
    ]
    for index, action in enumerate(bundle.task.evaluation_criteria.actions):
        _execute(
            environment,
            trajectory,
            name=action.name,
            arguments=action.arguments,
            suffix=f"i2_no_reason_{index}",
        )
    result = evaluate_v2_pilot_compliance(bundle, trajectory)
    labels = {item.rule_id: item.compliant for item in result.component_results}
    assert labels == {
        "airline.cancel.reason_required": False,
        "airline.compensation.delayed_flight_sequence": True,
    }


def test_i2_confounders_are_fixed_satisfied(pilot):
    bundles, _ = pilot
    i2 = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "I2"
    ]
    assert len(i2) == 4
    for bundle in i2:
        factors = bundle.hidden_metadata["v2_world"]["governance_factors"]
        assert factors["cancellation_eligible"] is True
        assert factors["compensation_eligible"] is True
        assert factors["compensation_requested"] is True
        assert factors["delay_fact_verifiable"] is True


def test_committed_artifacts_round_trip_and_rebuild_deterministically(tmp_path, pilot):
    bundles, audit = pilot
    stored_audit = json.loads((ARTIFACT_ROOT / "construction_audit.json").read_text())
    assert audit["compiled_bundle_sha256"] == stored_audit["compiled_bundle_sha256"]
    stored = yaml.safe_load((ARTIFACT_ROOT / "compiled_bundles.yaml").read_text())
    loaded = [CompiledTaskBundle.from_dict(item) for item in stored]
    assert [item.to_dict() for item in loaded] == [item.to_dict() for item in bundles]

    materialize_declared_pilot(output_dir=tmp_path)
    for filename in ("compiled_bundles.yaml", "tasks.json", "construction_audit.json"):
        assert (tmp_path / filename).read_bytes() == (ARTIFACT_ROOT / filename).read_bytes()


def test_step4b_did_not_create_a_generic_framework():
    forbidden = {
        "world_generator.py",
        "success_generator.py",
        "interaction_generator.py",
        "family_generator.py",
        "composition_engine.py",
        "interaction_graph.py",
        "joint_world.py",
    }
    pilot_root = Path(__file__).parents[2] / "benchmarks/tau2_governed_evolution/v2/pilot"
    assert not ({path.name for path in pilot_root.rglob("*.py")} & forbidden)
