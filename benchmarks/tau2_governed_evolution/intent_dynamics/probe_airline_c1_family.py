"""Controlled official-evaluator and v14 Judge probes for the Airline C1 family."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)
from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_c1_family import (
    load_family,
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
PROBE_NAMES = ("upfront_cs", "revision_cs", "revision_vs", "revision_vf")
EXPECTED = {
    "upfront_cs": {"success": True, "compliant": True},
    "revision_cs": {"success": True, "compliant": True},
    "revision_vs": {"success": True, "compliant": False},
    "revision_vf": {"success": False, "compliant": False},
}


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


def build_probe(record: dict[str, Any], name: str) -> tuple[Any, list[Any]]:
    if name not in PROBE_NAMES:
        raise ValueError(f"Unknown probe: {name}")
    pair, tasks = record["pair"], record["tasks"]
    variant = "upfront" if name == "upfront_cs" else "revision"
    task_id = next(
        item["task_id"] for item in pair["variants"] if item["variant"] == variant
    )
    task = tasks[task_id]
    text = pair["probe_text"]
    underlying = pair["underlying_state"]
    environment = get_environment()
    messages: list[Any] = [
        UserMessage(
            role="user",
            content=(
                text["upfront_request"]
                if name == "upfront_cs"
                else text["revision_request"]
            ),
        )
    ]
    _append_tool_call(
        messages,
        environment,
        f"{pair['pair_id']}-read-user",
        "get_user_details",
        {"user_id": underlying["user_id"]},
    )
    _append_tool_call(
        messages,
        environment,
        f"{pair['pair_id']}-read-reservation",
        "get_reservation_details",
        {"reservation_id": underlying["reservation_id"]},
    )
    for index, call in enumerate(pair["search_calls"]):
        _append_tool_call(
            messages,
            environment,
            f"{pair['pair_id']}-search-{index}",
            call["name"],
            call["arguments"],
        )

    if name == "upfront_cs":
        messages.extend(
            [
                AssistantMessage(role="assistant", content=text["p1_proposal"]),
                UserMessage(role="user", content=text["confirmation"]),
            ]
        )
        write_payload = pair["shared_final_target"]["arguments"]
    else:
        messages.extend(
            [
                AssistantMessage(role="assistant", content=text["p0_proposal"]),
                UserMessage(role="user", content=text["revision_response"]),
            ]
        )
        if name == "revision_cs":
            messages.extend(
                [
                    AssistantMessage(role="assistant", content=text["p1_proposal"]),
                    UserMessage(role="user", content=text["confirmation"]),
                ]
            )
            write_payload = pair["shared_final_target"]["arguments"]
        elif name == "revision_vs":
            write_payload = pair["shared_final_target"]["arguments"]
        else:
            write_payload = pair["p0"]["arguments"]

    _append_tool_call(
        messages,
        environment,
        f"{pair['pair_id']}-write",
        "update_reservation_flights",
        write_payload,
    )
    messages.append(
        AssistantMessage(
            role="assistant", content="The reservation update is complete. Thank you."
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


@lru_cache(maxsize=1)
def _judge_context() -> dict[str, Any]:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=True)
    from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
        load_authoritative_domain_contexts,
    )

    return load_authoritative_domain_contexts(
        PROJECT_ROOT / "external" / "tau2-bench"
    )["airline"]


def compliance_result(task: Any, messages: list[Any]) -> dict[str, Any]:
    from src.adapters.tau2.tau3_gse_runtime import stable_trajectory, task_context
    from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14

    context = _judge_context()
    judgment = v14.judge_compliance(
        context["original_domain_policy"],
        task_context(task, domain="airline"),
        stable_trajectory(messages),
        available_tool_contracts=context["available_tool_contracts"],
        domain="airline",
    )
    return judgment.as_dict()


def _run_one(
    pair_id: str, record: dict[str, Any], name: str, with_judge: bool
) -> tuple[str, str, dict[str, Any]]:
    task, messages = build_probe(record, name)
    official = official_result(task, messages)
    result: dict[str, Any] = {"official": official, "expected": EXPECTED[name]}
    if with_judge:
        result["compliance"] = compliance_result(task, messages)
        result["passed"] = (
            official["success"] == EXPECTED[name]["success"]
            and result["compliance"]["compliant"] == EXPECTED[name]["compliant"]
        )
    else:
        result["passed"] = official["success"] == EXPECTED[name]["success"]
    return pair_id, name, result


def run_probes(
    *,
    with_judge: bool,
    pair_ids: tuple[str, ...] | None = None,
    probe_names: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    _, records = load_family()
    selected = tuple(pair_ids or records.keys())
    unknown = set(selected) - set(records)
    if unknown:
        raise ValueError(f"Unknown pair IDs: {sorted(unknown)}")
    selected_probes = tuple(probe_names or PROBE_NAMES)
    unknown_probes = set(selected_probes) - set(PROBE_NAMES)
    if unknown_probes:
        raise ValueError(f"Unknown probes: {sorted(unknown_probes)}")
    results: dict[str, dict[str, Any]] = {pair_id: {} for pair_id in selected}
    jobs = [
        (pair_id, records[pair_id], name, with_judge)
        for pair_id in selected
        for name in selected_probes
    ]
    max_workers = min(4 if with_judge else 8, len(jobs))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_run_one, *job) for job in jobs]
        for future in as_completed(futures):
            pair_id, name, result = future.result()
            results[pair_id][name] = result
    ordered = {
        pair_id: {name: results[pair_id][name] for name in selected_probes}
        for pair_id in selected
    }
    return {
        "with_judge": with_judge,
        "passed": all(
            probe["passed"] for pair in ordered.values() for probe in pair.values()
        ),
        "pairs": ordered,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-judge", action="store_true")
    parser.add_argument("--pairs", nargs="+")
    parser.add_argument("--probes", nargs="+", choices=PROBE_NAMES)
    args = parser.parse_args()
    result = run_probes(
        with_judge=args.with_judge,
        pair_ids=tuple(args.pairs) if args.pairs else None,
        probe_names=tuple(args.probes) if args.probes else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
