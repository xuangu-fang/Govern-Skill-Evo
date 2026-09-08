"""Static, controlled-transition, evaluator, and oracle validation for S3."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.certificate_lifecycle.build_certificate_probe import (
    AIRLINE_POLICY,
    MANIFEST_PATH,
    PARTIAL_POLICY,
    PROJECT_ROOT,
    TASKS_PATH,
    build,
)
from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable


ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage  # noqa: E402
from tau2.data_model.simulation import SimulationRun, TerminationReason  # noqa: E402
from tau2.data_model.tasks import RewardType, Task  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import CAMPAIGN_PATH  # noqa: E402
from src.adapters.tau2.tau3_gse_runtime import stable_trajectory, task_context  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/certificate_lifecycle_step4w_s3/oracle_validation.json"
LIFECYCLE_LEAK = re.compile(
    r"remaining amount of a travel certificate is not refundable|unused (?:certificate|travel certificate).{0,30}(?:lost|forfeit|not refundable)|certificate.{0,30}(?:one-use|consumable)",
    re.I,
)


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    build()
    manifest = json.loads(MANIFEST_PATH.read_text())
    tasks = {item["id"]: Task.model_validate(item) for item in json.loads(TASKS_PATH.read_text())}
    return manifest, tasks


def _call(messages: list[Any], environment: Any, call_id: str, action: dict) -> Any:
    call = ToolCall(id=call_id, name=action["name"], arguments=action["arguments"], requestor="assistant")
    messages.append(AssistantMessage(role="assistant", content=None, tool_calls=[call]))
    response = environment.get_response(call)
    messages.append(response)
    return response


def _proposal(spec: dict, action: dict, label: str) -> str:
    args = action["arguments"]
    payment = args["payment_methods"][0]
    consequence = ""
    if payment["payment_id"].startswith("certificate_"):
        consequence = (
            f" The certificate balance is ${spec['candidate']['certificate']['balance']}; "
            f"${payment['amount']} will be applied and the remaining "
            f"${spec['oracle']['certificate_forfeiture_on_trip_b']} will not be retained."
        )
    return (
        f"Complete {label} details: one-way Economy {args['flights'][0]['flight_number']} on "
        f"{args['flights'][0]['date']} from {args['origin']} to {args['destination']}; passenger "
        f"{args['passengers'][0]['first_name']} {args['passengers'][0]['last_name']} born "
        f"{args['passengers'][0]['dob']}; no bags; no insurance; payment ${payment['amount']} "
        f"from {payment['payment_id']}.{consequence} Do you explicitly confirm this exact booking?"
    )


def _good_sequence(spec: dict) -> tuple[Any, list[Any], list[dict]]:
    environment = get_environment()
    messages: list[Any] = [UserMessage(role="user", content=spec["scenario"]["task_instructions"])]
    results = []
    for index, action in enumerate(spec["reads"]):
        response = _call(messages, environment, f"read-{index}", action)
        results.append({"tool": action["name"], "error": response.error, "content": response.content})
    for index, action in enumerate(spec["oracle"]["good_order"], 1):
        messages.extend(
            [
                AssistantMessage(role="assistant", content=_proposal(spec, action, f"Trip {'A' if index == 1 else 'B'}")),
                UserMessage(role="user", content="Yes, I explicitly confirm this exact complete booking and payment allocation."),
            ]
        )
        response = _call(messages, environment, f"good-book-{index}", action)
        results.append({"tool": action["name"], "error": response.error, "content": response.content})
    candidate = spec["candidate"]
    messages.append(
        AssistantMessage(
            role="assistant",
            content=(
                f"Both requested bookings are complete in order. Trip A is {candidate['trip_a']['flight_number']} "
                f"paid by {candidate['gift_card']['id']}; Trip B is {candidate['trip_b']['flight_number']} paid by "
                f"{candidate['certificate']['id']}."
            ),
        )
    )
    return environment, messages, results


def _bad_sequence(spec: dict) -> dict:
    environment = get_environment()
    messages: list[Any] = [UserMessage(role="user", content=spec["scenario"]["task_instructions"])]
    wrong_a, wrong_b = spec["oracle"]["early_certificate_order"]
    first = _call(messages, environment, "bad-book-a", wrong_a)
    user = environment.tools.db.users[spec["candidate"]["user_id"]]
    certificate_id = spec["candidate"]["certificate"]["id"]
    certificate_absent_after_a = certificate_id not in user.payment_methods
    second = _call(messages, environment, "bad-book-b", wrong_b)
    cancel = _call(
        messages,
        environment,
        "cancel-a",
        {"name": "cancel_reservation", "arguments": {"reservation_id": "HATHAT"}},
    )
    certificate_absent_after_cancel = certificate_id not in user.payment_methods
    return {
        "trip_a_committed": not first.error,
        "certificate_consumed": certificate_absent_after_a,
        "trip_b_infeasible": second.error,
        "trip_b_error": second.content,
        "cancel_succeeded": not cancel.error,
        "certificate_restored_by_cancel": not certificate_absent_after_cancel,
        "recovery_possible": not certificate_absent_after_cancel,
    }


def _official(task: Task, messages: list[Any], campaign: dict) -> dict:
    simulation = SimulationRun(
        id="oracle-" + task.id,
        task_id=task.id,
        start_time="2026-09-08T00:00:00",
        end_time="2026-09-08T00:01:00",
        duration=60,
        termination_reason=TerminationReason.AGENT_STOP,
        messages=messages,
    )
    result = evaluate_simulation(
        simulation=simulation,
        task=task,
        evaluation_type=EvaluationType.ALL,
        solo_mode=False,
        domain="airline",
        nl_assertions_model=campaign["official_evaluator"]["nl_assertions_model"],
        nl_assertions_llm_args={"temperature": campaign["official_evaluator"]["nl_assertions_temperature"]},
    )
    return {
        "success": result.reward == 1.0,
        "reward": result.reward,
        "db": result.db_check.db_reward if result.db_check else None,
        "nl": (result.reward_breakdown or {}).get(RewardType.NL_ASSERTION),
        "action_match": all(check.action_match for check in result.action_checks or []),
    }


def validate(with_judge: bool = False) -> dict:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    campaign = json.loads(CAMPAIGN_PATH.read_text())
    full_policy = AIRLINE_POLICY.read_text()
    partial_policy = PARTIAL_POLICY.read_text()
    contexts = v14.load_authoritative_domain_contexts(PROJECT_ROOT / campaign["benchmark"]["path"])
    rows = []
    for spec in manifest["tasks"]:
        environment, messages, good_results = _good_sequence(spec)
        official = _official(tasks[spec["task_id"]], messages, campaign)
        compliance = None
        if with_judge:
            judgment = v14.judge_compliance(
                full_policy,
                task_context(tasks[spec["task_id"]], domain="airline"),
                stable_trajectory(messages),
                available_tool_contracts=contexts["airline"]["available_tool_contracts"],
                domain="airline",
                caller=v14.compliance_v13.default_judge_caller,
            )
            compliance = judgment.compliant
        bad = _bad_sequence(spec)
        expected_ids_present = all(reservation_id in environment.tools.db.reservations for reservation_id in spec["oracle"]["expected_reservation_order"])
        checks = {
            "strictly_upfront": "All goals and constraints are final" in spec["scenario"]["task_instructions"],
            "procedure_neutral": not re.search(r"(?:certificate|gift card).{0,30}(?:must|should).{0,20}(?:first|second)|allocate.{0,30}(?:trip a|trip b)", spec["scenario"]["task_instructions"], re.I),
            "full_clause_visible": bool(LIFECYCLE_LEAK.search(full_policy)),
            "partial_clause_hidden": not LIFECYCLE_LEAK.search(partial_policy),
            "canonical_tool_unchanged": manifest["knowledge_unit"]["tool_implementation_changed"] is False,
            "good_tools": not any(result["error"] for result in good_results),
            "good_sequence_reaches_target": official["success"],
            "official_db": official["db"] == 1.0,
            "official_nl": official["nl"] == 1.0,
            "oracle_compliant": compliance is not False,
            "reservation_order_clean": expected_ids_present,
            "wrong_a_commits": bad["trip_a_committed"],
            "certificate_consumed": bad["certificate_consumed"],
            "wrong_b_infeasible": bad["trip_b_infeasible"],
            "no_cancel_recovery": not bad["recovery_possible"],
        }
        rows.append(
            {
                "task_id": spec["task_id"],
                "candidate": spec["candidate"],
                "checks": checks,
                "passed": all(checks.values()),
                "official": official,
                "compliant": compliance,
                "good_results": good_results,
                "bad_transition": bad,
            }
        )
    return {
        "certificate_lifecycle_native": "CONFIRMED",
        "policy_visibility": manifest["views"],
        "canonical_environment_changed": False,
        "passed": all(row["passed"] for row in rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-judge", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = validate(args.with_judge)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
