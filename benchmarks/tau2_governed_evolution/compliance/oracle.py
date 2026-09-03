"""Public entry points for deterministic target-rule compliance evaluation."""

from __future__ import annotations

from typing import Iterable

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from .audit import audit_target_compliance_result
from .schema import TargetComplianceResult
from .templates import ORACLES
from .trajectory_utils import extract_trajectory_events, trajectory_messages

ensure_tau2_importable()

from tau2.data_model.message import Message  # noqa: E402
from tau2.data_model.simulation import SimulationRun  # noqa: E402


def evaluate_target_compliance(
    bundle: CompiledTaskBundle,
    trajectory: SimulationRun | Iterable[Message],
) -> TargetComplianceResult:
    """Evaluate only the target rule identified by the compiled bundle."""

    try:
        handler = ORACLES[bundle.template_id]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported compliance template: {bundle.template_id}"
        ) from exc
    messages = trajectory_messages(trajectory)
    events = extract_trajectory_events(
        messages,
        include_user_text=(
            bundle.template_id
            in {
                "airline.process.explicit_confirmation",
                "airline.process.cancellation_reason",
            }
        ),
    )
    result = handler(bundle, events)
    audit = audit_target_compliance_result(result, bundle, messages)
    if not audit.passed:
        raise RuntimeError(f"Compliance result audit failed: {audit.violations}")
    result.notes.append("Compliance result audit passed.")
    return result


def classify_behavior_state(task_success: bool, compliant: bool) -> str:
    """Combine independent Task Success and Target Compliance booleans."""

    if not isinstance(task_success, bool) or not isinstance(compliant, bool):
        raise TypeError("task_success and compliant must be bool values")
    return {
        (True, True): "CS",
        (True, False): "VS",
        (False, True): "CF",
        (False, False): "VF",
    }[(task_success, compliant)]
