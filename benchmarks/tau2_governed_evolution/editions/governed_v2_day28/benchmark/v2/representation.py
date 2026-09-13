"""Minimal namespaced metadata validation for the v2 Structural Pilot."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any, Mapping, NotRequired, TypedDict, cast


JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


class V2SuccessMetadata(TypedDict):
    """Success preconditions reference concrete keys in ``success_factors``."""

    preconditions: list[str]
    difficulty_factor: str


class V2WorldMetadata(TypedDict):
    """Sparse, explicitly declared success and governance factors."""

    success_factors: dict[str, JSONValue]
    governance_factors: dict[str, JSONValue]


class V2InteractionMetadata(TypedDict):
    """Declarative representation of one frozen 2-way Pilot interaction."""

    mechanism_ids: list[str]
    relation: str
    expected_combined_behavior: str
    ordered_stages: list[str]
    confirmation_basis: NotRequired[str]


class V2PilotMetadata(TypedDict):
    """The only metadata namespaces introduced by the v2 Pilot contract."""

    v2_success: V2SuccessMetadata
    v2_world: V2WorldMetadata
    v2_interaction: NotRequired[V2InteractionMetadata]


I1_RELATION = "calculation_before_confirmation_commit"
I2_RELATION = "prerequisite_before_primary_before_remedy"
ACTUAL_PAYLOAD_CONFIRMATION_BASIS = (
    "actual_proposal_user_confirmation_actual_commit"
)

_I1_MECHANISMS = (
    "airline.book.baggage_allowance",
    "airline.action.explicit_confirmation",
)
_I2_MECHANISMS = (
    "airline.cancel.reason_required",
    "airline.compensation.delayed_flight_sequence",
)
_I1_STAGES = (
    "allowance_calculation",
    "final_payload",
    "user_confirmation",
    "commit",
)
_I2_STAGES = (
    "reason_obtained",
    "primary_action_succeeded",
    "downstream_compensation",
)
_REQUIRED_NAMESPACES = {"v2_success", "v2_world"}
_KNOWN_NAMESPACES = {*_REQUIRED_NAMESPACES, "v2_interaction"}


def _require_nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value


def _require_exact_keys(
    value: Any, *, required: set[str], optional: set[str], path: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    missing = required - value.keys()
    if missing:
        raise ValueError(f"{path} missing required fields: {sorted(missing)}")
    unknown = value.keys() - required - optional
    if unknown:
        raise ValueError(f"{path} has unknown fields: {sorted(unknown)}")
    return value


def _validate_json_value(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{path} must contain finite JSON numbers")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _require_nonempty_string(key, f"{path} key")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise ValueError(f"{path} must contain only JSON-serializable values")


def _validate_factors(value: Any, path: str) -> dict[str, JSONValue]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{path} must be a non-empty object")
    for key, item in value.items():
        _require_nonempty_string(key, f"{path} key")
        _validate_json_value(item, f"{path}.{key}")
    return cast(dict[str, JSONValue], value)


def _validate_string_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path} must be a non-empty list")
    items = [_require_nonempty_string(item, f"{path} item") for item in value]
    if len(items) != len(set(items)):
        raise ValueError(f"{path} must not contain duplicates")
    return items


def _validate_interaction(value: Any, rule_id: str) -> None:
    common = {
        "mechanism_ids",
        "relation",
        "expected_combined_behavior",
        "ordered_stages",
    }
    raw = _require_exact_keys(
        value,
        required=common,
        optional={"confirmation_basis"},
        path="v2_interaction",
    )
    mechanism_ids = _validate_string_list(
        raw["mechanism_ids"], "v2_interaction.mechanism_ids"
    )
    if len(mechanism_ids) != 2:
        raise ValueError(
            "v2_interaction.mechanism_ids must contain exactly two mechanisms"
        )
    relation = _require_nonempty_string(raw["relation"], "v2_interaction.relation")
    _require_nonempty_string(
        raw["expected_combined_behavior"],
        "v2_interaction.expected_combined_behavior",
    )
    stages = _validate_string_list(
        raw["ordered_stages"], "v2_interaction.ordered_stages"
    )
    if relation == I1_RELATION:
        if tuple(mechanism_ids) != _I1_MECHANISMS:
            raise ValueError("I1 must declare the frozen baggage/confirmation pair")
        if tuple(stages) != _I1_STAGES:
            raise ValueError("I1 must declare calculation-to-commit stages in order")
        basis = _require_nonempty_string(
            raw.get("confirmation_basis"),
            "v2_interaction.confirmation_basis",
        )
        if basis != ACTUAL_PAYLOAD_CONFIRMATION_BASIS:
            raise ValueError(
                "I1 confirmation must use actual proposal, user confirmation, and "
                "actual commit"
            )
    elif relation == I2_RELATION:
        if "confirmation_basis" in raw:
            raise ValueError("I2 must not declare confirmation_basis")
        if tuple(mechanism_ids) != _I2_MECHANISMS:
            raise ValueError("I2 must declare the frozen reason/ordering pair")
        if tuple(stages) != _I2_STAGES:
            raise ValueError("I2 must declare prerequisite-to-remedy stages in order")
    else:
        raise ValueError(f"unsupported v2 Pilot interaction relation: {relation}")

    if rule_id != "+".join(mechanism_ids):
        raise ValueError(
            "interaction rule_id must reuse the ordered participating mechanism ids"
        )


def validate_v2_pilot_metadata(
    hidden_metadata: Mapping[str, Any],
    *,
    task_id: str,
    family_id: str,
    world_id: str,
    rule_id: str,
    expected_resolution: str,
) -> V2PilotMetadata:
    """Validate only explicitly supplied v2 Pilot metadata.

    ``family_id``, ``world_id``, ``rule_id``, and ``expected_resolution`` are passed
    from the existing bundle fields. They are intentionally not duplicated inside
    the v2 namespaces. This function is not called by the v1 compiler or loader.
    """

    task_id = _require_nonempty_string(task_id, "task_id")
    family_id = _require_nonempty_string(family_id, "family_id")
    world_id = _require_nonempty_string(world_id, "world_id")
    rule_id = _require_nonempty_string(rule_id, "rule_id")
    _require_nonempty_string(expected_resolution, "expected_resolution")
    if family_id == task_id:
        raise ValueError("family_id must not be conflated with task_id")
    if world_id in {task_id, family_id}:
        raise ValueError("world_id must be distinct from task_id and family_id")

    v2_keys = {
        key
        for key in hidden_metadata
        if isinstance(key, str) and key.startswith("v2_")
    }
    missing = _REQUIRED_NAMESPACES - v2_keys
    if missing:
        raise ValueError(f"v2 Pilot metadata missing namespaces: {sorted(missing)}")
    unknown = v2_keys - _KNOWN_NAMESPACES
    if unknown:
        raise ValueError(f"unknown v2 Pilot metadata namespaces: {sorted(unknown)}")

    success = _require_exact_keys(
        hidden_metadata["v2_success"],
        required={"preconditions", "difficulty_factor"},
        optional=set(),
        path="v2_success",
    )
    world = _require_exact_keys(
        hidden_metadata["v2_world"],
        required={"success_factors", "governance_factors"},
        optional=set(),
        path="v2_world",
    )
    success_factors = _validate_factors(
        world["success_factors"], "v2_world.success_factors"
    )
    governance_factors = _validate_factors(
        world["governance_factors"], "v2_world.governance_factors"
    )
    overlapping_factors = success_factors.keys() & governance_factors.keys()
    if overlapping_factors:
        raise ValueError(
            "success and governance factors must be disjoint: "
            f"{sorted(overlapping_factors)}"
        )
    preconditions = _validate_string_list(
        success["preconditions"], "v2_success.preconditions"
    )
    unknown_preconditions = set(preconditions) - success_factors.keys()
    if unknown_preconditions:
        raise ValueError(
            "v2_success.preconditions reference unknown success factors: "
            f"{sorted(unknown_preconditions)}"
        )
    difficulty_factor = _require_nonempty_string(
        success["difficulty_factor"], "v2_success.difficulty_factor"
    )
    if difficulty_factor not in success_factors:
        raise ValueError(
            "v2_success.difficulty_factor must reference a declared success factor"
        )

    if "v2_interaction" in hidden_metadata:
        _validate_interaction(hidden_metadata["v2_interaction"], rule_id)
    elif "+" in rule_id:
        raise ValueError("composed rule_id requires complete v2_interaction metadata")

    normalized = {
        key: deepcopy(hidden_metadata[key])
        for key in ("v2_success", "v2_world", "v2_interaction")
        if key in hidden_metadata
    }
    _validate_json_value(normalized, "v2 Pilot metadata")
    return cast(V2PilotMetadata, normalized)
