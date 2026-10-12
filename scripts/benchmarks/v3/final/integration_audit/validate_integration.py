#!/usr/bin/env python3
"""Global audit for the 64-task Core plus nine Protected Controls."""

from __future__ import annotations

import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import BaseModel


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction/integration_audit'))
EDITION = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/editions/phase_final_candidate_day35')
REPO = EDITION.parents[3]
ROOT = REPO / "benchmarks/tau2_governed_evolution"
V3 = ROOT / "editions/phase_v3_day34"
FC = ROOT / "final_candidate"
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from tau2.data_model.tasks import Task  # noqa: E402

from src.benchmark_v3.final.environment.airline import get_environment as get_airline_environment, get_tasks as get_airline_tasks
from src.benchmark_v3.final.environment.retail import get_environment as get_retail_environment, get_tasks as get_retail_tasks
from scripts.benchmarks.v3.final.integration_audit.validate_controls import main as validate_controls  # noqa: E402
from src.benchmark_v3.development.joint_settlement_destination_scope.candidate_tasks.evaluators.evaluate_jsg01 import evaluate as evaluate_jsg  # noqa: E402
from src.benchmark_v3.development.latent_settlement_contract.candidate_tasks.evaluators.evaluate_latent_settlement import evaluate_success as evaluate_ee  # noqa: E402
from src.benchmark_v3.development.retail_address_propagation.candidate_tasks.evaluators.evaluate_rap01 import evaluate_success as evaluate_rap  # noqa: E402
from src.benchmark_v3.development.retail_hidden_operational_path.candidate_tasks.evaluators.evaluate_rhp01 import evaluate_success as evaluate_rhp  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, evaluate_success as evaluate_booking  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator import build_lga03_evidence_registry, evaluate_trace  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.p4_certificate_allocation.evaluator import evaluate as evaluate_p4  # noqa: E402
from src.benchmark_v3.construction.governance_core_expansion.insurance_reason_eligibility.multi_surface.evaluator import evaluate as evaluate_insurance  # noqa: E402


TASKS = EDITION / "benchmark/tasks.json"
CONTROL_TASKS = EDITION / "benchmark/control_tasks.json"
SPLITS = EDITION / "benchmark/splits.json"
NEW_SPECS = EDITION / "benchmark/new_family_specs.json"
CONTROL_SPECS = EDITION / "benchmark/control_specs.json"
CONTROL_RESULT = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction/integration_audit/control_regression_validation.json')
CONTROL_SANITY = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction/integration_audit/control_e0_sanity_summary.json')
RESULT = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction/integration_audit/integration_validation.json')
V3_SPEC_FILES = {
    "EE-01": V3 / "construction/latent_settlement_contract/core_family/candidates/task_specs.json",
    "RHP-01": V3 / "construction/retail_hidden_operational_path/core_family/candidates/task_specs.json",
    "RAP-01": V3 / "construction/retail_address_propagation/core_family/candidates/task_specs.json",
    "JSG-01": V3 / "construction/joint_settlement_destination_scope/core_family/candidates/task_specs.json",
}
FAMILIES = {"EE-01", "RHP-01", "RAP-01", "JSG-01", "P4-01", "GPC-01", "GMB-01", "GIR-01"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def family(task_id: str) -> str:
    return task_id.rsplit("-C", 1)[0]


def json_value(value: Any) -> Any:
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else value


def identifiers(value: Any, key: str = "") -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for child_key, child in value.items():
            found |= identifiers(child, child_key)
    elif isinstance(value, list):
        for child in value:
            found |= identifiers(child, key)
    elif isinstance(value, str) and (
        key.endswith("_id") or key in {"flight_number", "retained_flight", "preferred_flight", "fallback_flight", "old_item_id", "new_item_id"}
    ):
        found.add(value)
    return found


def run_action(tools: Any, name: str, arguments: dict[str, Any]) -> Any:
    return tools.use_tool(name, **deepcopy(arguments))


def run_insurance_path(tools: Any, spec: dict[str, Any]) -> list[dict[str, Any]]:
    calls = [
        ("get_user_details", {"user_id": spec["user_id"]}),
        ("get_reservation_details", {"reservation_id": spec["reservation_id"]}),
        ("get_flight_status", {"flight_number": spec["flight_number"], "date": spec["flight_date"]}),
        ("transfer_to_human_agents", {"summary": "Insured cancellation reason requires human handling after verification."}),
    ]
    messages: list[dict[str, Any]] = []
    for index, (name, arguments) in enumerate(calls):
        call_id = f"{spec['task_id']}-{index}"
        messages.append({"role": "assistant", "tool_calls": [{"id": call_id, "name": name, "arguments": arguments, "requestor": "assistant"}]})
        try:
            result = run_action(tools, name, arguments)
            content, failed = json.dumps(json_value(result)), False
        except Exception as error:
            content, failed = f"Error: {error}", True
        messages.append({"id": call_id, "role": "tool", "content": content, "requestor": "assistant", "error": failed})
    return messages


def apply_retail_address_write(tools: Any, spec: dict[str, Any], target: str) -> None:
    if target == "order":
        tools.modify_pending_order_address(spec["order_id"], **spec["order_address"])
    else:
        tools.modify_user_address(spec["user_id"], **spec["profile_address"])


def audit_source_gates() -> dict[str, str]:
    files = {
        "v3": (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/integration_audit/integration_validation.json'),
        "P4-01": (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface/shortcut_audit.json'),
        "GPC-01": (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/cardinality_candidates/shortcut_audit.json'),
        "GMB-01": (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/baggage_candidates/shortcut_audit.json'),
        "GIR-01": (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/multi_surface/shortcut_audit.json'),
        "GIR-01-gate0": (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/multi_surface/gate0_validation.json'),
    }
    statuses = {name: load(path)["status"] for name, path in files.items()}
    assert all(status.startswith("PASS") for status in statuses.values())
    joint = load(FC / "construction/integrated_pre_id_realization/joint_candidates/joint_portfolio_closure.json")
    assert joint["status"] == "CLOSED__JSG01_ONLY" and joint["new_joint_formal_task_count"] == 0
    return statuses


def main() -> None:
    tasks = load(TASKS) + load(CONTROL_TASKS)
    task_by_id = {row["id"]: row for row in tasks}
    split_payload = load(SPLITS)
    splits = {name: set(ids) for name, ids in split_payload["splits"].items()}
    monitor_roles = {name: set(ids) for name, ids in split_payload["monitor_roles"].items()}
    assert len(tasks) == len(task_by_id) == 73
    assert set(splits) == {"train", "monitor"}
    assert len(splits["train"]) == 32 and len(splits["monitor"]) == 41
    assert set(monitor_roles) == {"CORE_GENERALIZATION", "REGRESSION_GUARD"}
    assert len(monitor_roles["CORE_GENERALIZATION"]) == 32
    assert len(monitor_roles["REGRESSION_GUARD"]) == 9
    assert monitor_roles["CORE_GENERALIZATION"].isdisjoint(monitor_roles["REGRESSION_GUARD"])
    assert monitor_roles["CORE_GENERALIZATION"] | monitor_roles["REGRESSION_GUARD"] == splits["monitor"]
    assert splits["train"].isdisjoint(splits["monitor"])
    assert splits["train"] | splits["monitor"] == set(task_by_id)
    for row in tasks:
        Task.model_validate(row)

    core_monitor_ids = monitor_roles["CORE_GENERALIZATION"]
    regression_guard_ids = monitor_roles["REGRESSION_GUARD"]
    core_ids = splits["train"] | core_monitor_ids
    family_counts = Counter(family(task_id) for task_id in core_ids)
    assert family_counts == {name: 8 for name in FAMILIES}
    family_split_counts = {
        "train": dict(Counter(family(task_id) for task_id in splits["train"])),
        "monitor_core_generalization": dict(Counter(family(task_id) for task_id in core_monitor_ids)),
    }
    assert all(counts == {name: 4 for name in FAMILIES} for counts in family_split_counts.values())

    v3_specs: dict[str, dict[str, Any]] = {}
    for path in V3_SPEC_FILES.values():
        v3_specs.update({row["task_id"]: row for row in load(path)["tasks"]})
    new_specs = {row["task_id"]: row for row in load(NEW_SPECS)["tasks"]}
    all_specs = {**v3_specs, **new_specs}
    control_specs = {row["task_id"]: row for row in load(CONTROL_SPECS)["controls"]}
    assert set(all_specs) == core_ids
    assert set(control_specs) == regression_guard_ids
    train_entities = set().union(*(identifiers(all_specs[task_id]) for task_id in splits["train"]))
    monitor_entities = set().union(*(identifiers(all_specs[task_id]) for task_id in core_monitor_ids))
    assert train_entities.isdisjoint(monitor_entities)
    control_entities = set().union(*(identifiers(control_specs[task_id]) for task_id in regression_guard_ids))
    assert control_entities.isdisjoint(train_entities | monitor_entities)
    assert train_entities.isdisjoint(monitor_entities | control_entities)

    domains = Counter(row["user_scenario"]["instructions"]["domain"] for row in tasks)
    assert domains == {"airline-final-candidate-unified": 54, "retail-final-candidate-unified": 19}
    visible = json.dumps([row["user_scenario"]["instructions"] for row in tasks], ensure_ascii=False).lower()
    forbidden = (
        "retained_historical", "complete_current", "exchange_protection_behavior", "propagation_source",
        "max_passengers_per_reservation", "membership_offset", "cabin_offset", "changed_plans",
    )
    assert all(token not in visible for token in forbidden)

    # Split-level counterbalancing for the three newly realized Governance families.
    for split, ids in (("train", splits["train"]), ("monitor_core_generalization", core_monitor_ids)):
        cardinality = [new_specs[item] for item in ids if family(item) == "GPC-01"]
        baggage = [new_specs[item] for item in ids if family(item) == "GMB-01"]
        insurance = [new_specs[item] for item in ids if family(item) == "GIR-01"]
        assert Counter(row["role"] for row in cardinality) == {"trigger": 2, "support": 2}
        assert Counter(row["role"] for row in baggage) == {"trigger": 2, "support": 2}
        assert Counter(row["answer_direction"] for row in baggage) == {"zero": 2, "positive": 2}
        assert len(insurance) == 4 and all(row["role"] == "trigger" for row in insurance)
        assert len({row["wording_group"] for row in insurance}) == 4

    source_gates = audit_source_gates()
    airline = get_airline_environment()
    retail = get_retail_environment()
    airline_policy = airline.policy.lower()
    retail_policy = retail.policy.lower()
    assert all(token not in airline_policy for token in ("horizon", "summit", "at most five passengers", "regular member:", "health or weather reasons"))
    assert all(token not in retail_policy for token in ("consolidated", "partner_direct", "cedar", "orbit"))

    runtime = Counter()
    for task_id, spec in all_specs.items():
        name = family(task_id)
        # A benchmark rollout starts from a fresh task environment. Rebuilding
        # here also prevents generated reservation IDs from coupling tasks.
        airline = get_airline_environment()
        retail = get_retail_environment()
        if name == "EE-01":
            airline.tools.update_reservation_flights(
                reservation_id=spec["reservation_id"],
                flights=[{"flight_number": spec["retained_flight"], "date": spec["date"]}, {"flight_number": spec["expected_flight"], "date": spec["date"]}],
                cabin="economy",
                payment_id=spec["payment_id"],
            )
            assert evaluate_ee(spec, airline.tools.db.model_dump(mode="json"))["success"]
        elif name == "JSG-01":
            airline.tools.update_reservation_flights(
                reservation_id=spec["reservation_id"],
                flights=[{"flight_number": spec["retained_flight"], "date": spec["date"]}, {"flight_number": spec[f"{spec['expected_branch']}_legal"], "date": spec["date"]}],
                cabin="economy",
                payment_id=spec["payment_id"],
            )
            result = evaluate_jsg(spec, airline.tools.db.model_dump(mode="json"))
            assert result["joint_success"] and result["success"] and result["compliant"]
        elif name == "RHP-01":
            if spec["expected_resolution"] == "exchange":
                retail.tools.exchange_delivered_order_items(spec["order_id"], [spec["old_item_id"]], [spec["new_item_id"]], spec["payment_id"])
            else:
                retail.tools.return_delivered_order_items(spec["order_id"], [spec["old_item_id"]], spec["payment_id"])
            assert evaluate_rhp(spec, retail.tools.db.model_dump(mode="json"))["success"]
        elif name == "RAP-01":
            for target in spec["correct_sequence"]:
                apply_retail_address_write(retail.tools, spec, target)
            assert evaluate_rap(spec, retail.tools.db.model_dump(mode="json"))["success"]
        elif name == "GIR-01":
            initial = airline.tools.db.model_dump(mode="json")
            messages = run_insurance_path(airline.tools, spec)
            final = airline.tools.db.model_dump(mode="json")
            success = evaluate_insurance(spec, initial, messages, final)
            trace = evaluate_trace(
                initial_db=initial,
                messages_or_simulation=messages,
                final_db=final,
                task_success=success["success"],
                registry=build_lga03_evidence_registry(),
                evaluator_context={"cancellation_reason_category": spec["reason_category"], "reason_source_message_index": 0},
            )
            assert success["success"] and trace["quadrant"] == "CS"
        else:
            initial = airline.tools.db.model_dump(mode="json")
            events = []
            for target in task_by_id[task_id]["evaluation_criteria"]["actions"]:
                run_action(airline.tools, target["name"], target["arguments"])
                events.append({"tool_name": target["name"], "arguments": target["arguments"]})
            final = airline.tools.db.model_dump(mode="json")
            if name == "P4-01":
                assert evaluate_p4(spec, initial, final)["success"]
                assert evaluate_compliance(initial, events)["compliant"]
            else:
                assert evaluate_booking(spec, initial, final)["success"]
                assert evaluate_compliance(initial, events)["compliant"]
        runtime[name] += 1
    assert runtime == {name: 8 for name in FAMILIES}

    validate_controls()
    control_result = load(CONTROL_RESULT)
    assert control_result["status"] == "PASS_9_PROTECTED_CONTROL_REALIZATION_AND_10_REGRESSION_AUDIT"
    control_sanity = load(CONTROL_SANITY)
    assert control_sanity["status"] == "PASS_9_CONTROL_E0_SANITY"
    assert control_sanity["rollout_count"] == control_sanity["task_success_count"] == 9

    loaders = {
        "airline": {"all": len(get_airline_tasks()), "train": len(get_airline_tasks("train")), "monitor": len(get_airline_tasks("monitor"))},
        "retail": {"all": len(get_retail_tasks()), "train": len(get_retail_tasks("train")), "monitor": len(get_retail_tasks("monitor"))},
    }
    assert loaders == {
        "airline": {"all": 54, "train": 24, "monitor": 30},
        "retail": {"all": 19, "train": 8, "monitor": 11},
    }
    result = {
        "status": "PASS_73_TASK_EVOLUTION32_MONITOR41",
        "model_calls": 0,
        "formal_task_count": 73,
        "core_task_count": 64,
        "protected_control_task_count": 9,
        "split_counts": {"train": 32, "monitor": 41, "test": 0},
        "monitor_role_counts": {"CORE_GENERALIZATION": 32, "REGRESSION_GUARD": 9},
        "family_counts": dict(sorted(family_counts.items())),
        "family_split_counts": family_split_counts,
        "domain_counts": dict(domains),
        "train_monitor_entity_overlap": 0,
        "source_shortcut_and_gate0_statuses": source_gates,
        "joint_portfolio": "JSG-01_ONLY__TWO_NEW_HYPOTHESES_REJECTED",
        "uniform_environments": {
            "airline-final-candidate-unified": {"tasks": 54, "core_families": ["EE-01", "JSG-01", "P4-01", "GPC-01", "GMB-01", "GIR-01"], "controls": 6},
            "retail-final-candidate-unified": {"tasks": 19, "core_families": ["RHP-01", "RAP-01"], "controls": 3},
        },
        "task_visible_text_hides_oracle_mappings": True,
        "new_governance_split_counterbalance": True,
        "oracle_runtime_successes": dict(sorted(runtime.items())),
        "oracle_runtime_total": sum(runtime.values()),
        "task_loader_counts": loaders,
        "protected_controls": {
            "status": control_result["status"],
            "correct_paths_passed": control_result["correct_paths_passed"],
            "targeted_regressions_detected": control_result["targeted_regressions_detected"],
            "e0_sanity_status": control_sanity["status"],
            "e0_sanity_successes": control_sanity["task_success_count"],
            "included_in_core_improvement_rates": False,
        },
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS final candidate integration: 64/64 Core oracle paths + 9/9 regression-guard paths + 10/10 regressions + 9/9 E0 sanity; Evolution 32 / Monitor 41")


if __name__ == "__main__":
    main()
