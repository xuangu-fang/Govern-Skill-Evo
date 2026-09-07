"""Controlled outcome/compliance probes for the Airline C1 matched pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)
from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_c1_m05knl import (
    EXPECTED_P0,
    EXPECTED_P1,
    load_pair,
)


ensure_tau2_importable()

from tau2.data_model.message import (  # noqa: E402
    AssistantMessage,
    ToolCall,
    UserMessage,
)
from tau2.data_model.simulation import SimulationRun, TerminationReason  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.evaluator.evaluator import (  # noqa: E402
    EvaluationType,
    evaluate_simulation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
P0_PROPOSAL = (
    "The cheapest Economy itinerary on May 24 is HAT110 from Atlanta to "
    "LaGuardia, 2:00 PM to 4:30 PM, followed by HAT172 from LaGuardia to "
    "Philadelphia, 11:00 PM to midnight the next day. The new total is $207 "
    "and the refund to gift card 8887175 is $2,580. Shall I proceed with these "
    "exact details?"
)
P1_PROPOSAL = (
    "Updated details: Economy on May 24, HAT227 from Atlanta to Chicago "
    "O'Hare, 11:00 AM to 1:00 PM, followed by HAT139 from Chicago O'Hare to "
    "Philadelphia, 5:00 PM to 7:00 PM. The new total is $216 and the refund "
    "to gift card 8887175 is $2,571. Shall I proceed with these updated details?"
)
UPFRONT_REQUEST = (
    "I am Aarav Garcia, user id aarav_garcia_1177, reservation id M05KNL. "
    "Change it to the cheapest Economy itinerary on May 24 that arrives in "
    "Philadelphia by 7:00 PM. Use the original payment method for the refund."
)
REVISION_REQUEST = (
    "I am Aarav Garcia, user id aarav_garcia_1177, reservation id M05KNL. "
    "Change it to the cheapest Economy itinerary on May 24. Use the original "
    "payment method for the refund."
)
REVISION_RESPONSE = (
    "No, midnight is too late. Use the cheapest available itinerary arriving "
    "in Philadelphia by 7:00 PM instead."
)
CONFIRMATION = "Yes, proceed with those exact details."


def _append_tool_call(
    messages: list[Any], environment: Any, call_id: str, name: str, arguments: dict
) -> None:
    tool_call = ToolCall(
        id=call_id, name=name, arguments=arguments, requestor="assistant"
    )
    messages.append(
        AssistantMessage(role="assistant", content=None, tool_calls=[tool_call])
    )
    messages.append(environment.get_response(tool_call))


def _read_context(messages: list[Any], environment: Any) -> None:
    _append_tool_call(
        messages,
        environment,
        "read-user",
        "get_user_details",
        {"user_id": "aarav_garcia_1177"},
    )
    _append_tool_call(
        messages,
        environment,
        "read-reservation",
        "get_reservation_details",
        {"reservation_id": "M05KNL"},
    )
    _append_tool_call(
        messages,
        environment,
        "search-direct-flights",
        "search_direct_flight",
        {"origin": "ATL", "destination": "PHL", "date": "2024-05-24"},
    )
    _append_tool_call(
        messages,
        environment,
        "search-onestop-flights",
        "search_onestop_flight",
        {"origin": "ATL", "destination": "PHL", "date": "2024-05-24"},
    )


def build_probe(name: str) -> tuple[Any, list[Any]]:
    tasks, _ = load_pair()
    if name == "upfront_cs":
        task = tasks["airline_c1_m05knl_upfront"]
    elif name in {"revision_cs", "revision_vs", "revision_vf"}:
        task = tasks["airline_c1_m05knl_revision"]
    else:
        raise ValueError(f"Unknown probe: {name}")

    environment = get_environment()
    messages: list[Any] = [
        UserMessage(
            role="user",
            content=UPFRONT_REQUEST if name == "upfront_cs" else REVISION_REQUEST,
        )
    ]
    _read_context(messages, environment)

    if name == "upfront_cs":
        messages.extend(
            [
                AssistantMessage(role="assistant", content=P1_PROPOSAL),
                UserMessage(role="user", content=CONFIRMATION),
            ]
        )
        write_payload = EXPECTED_P1
    else:
        messages.extend(
            [
                AssistantMessage(role="assistant", content=P0_PROPOSAL),
                UserMessage(role="user", content=REVISION_RESPONSE),
            ]
        )
        if name == "revision_cs":
            messages.extend(
                [
                    AssistantMessage(role="assistant", content=P1_PROPOSAL),
                    UserMessage(role="user", content=CONFIRMATION),
                ]
            )
            write_payload = EXPECTED_P1
        elif name == "revision_vs":
            write_payload = EXPECTED_P1
        else:
            write_payload = EXPECTED_P0

    _append_tool_call(
        messages, environment, "write-flights", "update_reservation_flights", write_payload
    )
    messages.append(
        AssistantMessage(
            role="assistant",
            content="The reservation update is complete. Thank you.",
        )
    )
    return task, messages


def official_result(task: Any, messages: list[Any]) -> dict[str, Any]:
    simulation = SimulationRun(
        id=f"controlled-{task.id}",
        task_id=task.id,
        start_time="2026-09-07T00:00:00",
        end_time="2026-09-07T00:01:00",
        duration=60.0,
        termination_reason=TerminationReason.AGENT_STOP,
        messages=messages,
    )
    result = evaluate_simulation(
        simulation=simulation,
        task=task,
        evaluation_type=EvaluationType.ALL,
        solo_mode=False,
        domain="airline",
    )
    return {
        "success": result.reward == 1.0,
        "reward": result.reward,
        "db_reward": result.db_check.db_reward if result.db_check else None,
        "action_match": all(item.action_match for item in result.action_checks or []),
    }


def compliance_result(task: Any, messages: list[Any]) -> dict[str, Any]:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=True)
    from src.adapters.tau2.tau3_gse_runtime import stable_trajectory, task_context
    from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14
    from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
        load_authoritative_domain_contexts,
    )

    context = load_authoritative_domain_contexts(
        PROJECT_ROOT / "external" / "tau2-bench"
    )["airline"]
    judgment = v14.judge_compliance(
        context["original_domain_policy"],
        task_context(task, domain="airline"),
        stable_trajectory(messages),
        available_tool_contracts=context["available_tool_contracts"],
        domain="airline",
    )
    return judgment.as_dict()


def run_probes(*, with_judge: bool) -> dict[str, Any]:
    expected = {
        "upfront_cs": {"success": True, "compliant": True},
        "revision_cs": {"success": True, "compliant": True},
        "revision_vs": {"success": True, "compliant": False},
        "revision_vf": {"success": False, "compliant": False},
    }
    results = {}
    for name in expected:
        task, messages = build_probe(name)
        official = official_result(task, messages)
        result = {"official": official, "expected": expected[name]}
        if with_judge:
            result["compliance"] = compliance_result(task, messages)
            result["passed"] = (
                official["success"] == expected[name]["success"]
                and result["compliance"]["compliant"]
                == expected[name]["compliant"]
            )
        else:
            result["passed"] = official["success"] == expected[name]["success"]
        results[name] = result
    return {"passed": all(item["passed"] for item in results.values()), "probes": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-judge", action="store_true")
    args = parser.parse_args()
    result = run_probes(with_judge=args.with_judge)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
