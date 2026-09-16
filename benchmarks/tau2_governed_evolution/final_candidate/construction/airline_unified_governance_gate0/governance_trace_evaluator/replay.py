"""Replay normalized Airline tool events on an isolated initial DB."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.data_model import (
    FinalCandidateAirlineDB,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.tools import (
    FinalCandidateAirlineTools,
)
from .normalizer import NormalizedEvent


class TraceReplayError(ValueError):
    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        step_index: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.step_index = step_index


@dataclass(frozen=True)
class ReplayEvent:
    event: NormalizedEvent
    pre_state: dict[str, Any]
    post_state: dict[str, Any]


@dataclass(frozen=True)
class ReplayResult:
    events: list[ReplayEvent]
    final_state: dict[str, Any]


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def replay_trace(
    initial_db: dict[str, Any],
    events: list[NormalizedEvent],
    final_db: dict[str, Any],
) -> ReplayResult:
    """Replay writes, validate outcomes, and preserve per-event state evidence."""
    replay_db = FinalCandidateAirlineDB.model_validate(deepcopy(initial_db))
    toolkit = FinalCandidateAirlineTools(replay_db)
    replayed: list[ReplayEvent] = []

    for event in events:
        pre_state = toolkit.db.model_dump(mode="json")
        if event.call_kind == "READ":
            replayed.append(
                ReplayEvent(event=event, pre_state=pre_state, post_state=pre_state)
            )
            continue

        try:
            observed_result = _json_value(
                toolkit.use_tool(event.tool_name, **deepcopy(event.arguments))
            )
            observed_outcome = "SUCCEEDED"
            observed_error = None
        except Exception as error:
            observed_result = None
            observed_outcome = "FAILED"
            observed_error = f"Error: {error}"

        post_state = toolkit.db.model_dump(mode="json")
        if observed_outcome != event.outcome:
            raise TraceReplayError(
                "REPLAY_OUTCOME_MISMATCH",
                (
                    f"{event.tool_name} recorded {event.outcome} but replayed "
                    f"{observed_outcome}."
                ),
                step_index=event.step_index,
            )
        if observed_outcome == "SUCCEEDED" and observed_result != event.result:
            raise TraceReplayError(
                "REPLAY_RESULT_MISMATCH",
                f"{event.tool_name} replay result differs from recorded result.",
                step_index=event.step_index,
            )
        if observed_outcome == "FAILED":
            if post_state != pre_state:
                raise TraceReplayError(
                    "FAILED_WRITE_MUTATED_STATE",
                    f"Failed {event.tool_name} mutated replay state.",
                    step_index=event.step_index,
                )
            recorded_error = (event.error or {}).get("message")
            if recorded_error != observed_error:
                raise TraceReplayError(
                    "REPLAY_RESULT_MISMATCH",
                    f"{event.tool_name} replay error differs from recorded error.",
                    step_index=event.step_index,
                )

        replayed.append(
            ReplayEvent(event=event, pre_state=pre_state, post_state=post_state)
        )

    replay_final = toolkit.db.model_dump(mode="json")
    expected_final = FinalCandidateAirlineDB.model_validate(
        deepcopy(final_db)
    ).model_dump(mode="json")
    if replay_final != expected_final:
        raise TraceReplayError(
            "REPLAY_FINAL_STATE_MISMATCH",
            "Replayed final DB differs from the provided final DB.",
        )
    return ReplayResult(events=replayed, final_state=replay_final)
