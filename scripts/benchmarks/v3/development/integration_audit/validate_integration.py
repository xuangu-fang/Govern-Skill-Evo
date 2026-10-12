#!/usr/bin/env python3
"""Audit the 32-task v3 benchmark, unified environments, and Train/Monitor split."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/integration_audit'))
EDITION = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from tau2.data_model.tasks import Task  # noqa: E402

from src.benchmark_v3.development.joint_settlement_destination_scope.candidate_tasks.evaluators.evaluate_jsg01 import evaluate as evaluate_jsg  # noqa: E402
from src.benchmark_v3.development.latent_settlement_contract.candidate_tasks.evaluators.evaluate_latent_settlement import evaluate_success as evaluate_ee  # noqa: E402
from src.benchmark_v3.development.retail_address_propagation.candidate_tasks.evaluators.evaluate_rap01 import evaluate_success as evaluate_rap  # noqa: E402
from src.benchmark_v3.development.retail_hidden_operational_path.candidate_tasks.evaluators.evaluate_rhp01 import evaluate_success as evaluate_rhp  # noqa: E402
from src.benchmark_v3.development.unified_environment.airline import get_environment as get_airline_environment  # noqa: E402
from src.benchmark_v3.development.unified_environment.airline import get_tasks as get_airline_tasks  # noqa: E402
from src.benchmark_v3.development.unified_environment.retail import get_environment as get_retail_environment  # noqa: E402
from src.benchmark_v3.development.unified_environment.retail import get_tasks as get_retail_tasks  # noqa: E402


TASKS = EDITION / "benchmark/tasks.json"
SPLITS = EDITION / "benchmark/splits.json"
RESULT = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/integration_audit/integration_validation.json')
SPEC_FILES = {
    "EE-01": EDITION / "construction/latent_settlement_contract/core_family/candidates/task_specs.json",
    "RHP-01": EDITION / "construction/retail_hidden_operational_path/core_family/candidates/task_specs.json",
    "RAP-01": EDITION / "construction/retail_address_propagation/core_family/candidates/task_specs.json",
    "JSG-01": EDITION / "construction/joint_settlement_destination_scope/core_family/candidates/task_specs.json",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def family(task_id: str) -> str:
    return task_id.rsplit("-C", 1)[0]


def apply_airline_update(tools: Any, spec: dict[str, Any], flight: str) -> None:
    tools.update_reservation_flights(
        reservation_id=spec["reservation_id"],
        cabin="economy",
        flights=[
            {"flight_number": spec["retained_flight"], "date": spec["date"]},
            {"flight_number": flight, "date": spec["date"]},
        ],
        payment_id=spec["payment_id"],
    )


def apply_retail_address_write(tools: Any, spec: dict[str, Any], target: str) -> None:
    if target == "order":
        tools.modify_pending_order_address(spec["order_id"], **spec["order_address"])
    else:
        tools.modify_user_address(spec["user_id"], **spec["profile_address"])


def assert_balanced(specs: dict[str, dict[str, Any]], split_ids: set[str]) -> dict[str, Any]:
    selected = {
        name: [
            spec
            for tid, spec in specs.items()
            if tid in split_ids and family(tid) == name
        ]
        for name in SPEC_FILES
    }
    ee = Counter((row["ticketing_channel"], "preferred" if row["expected_flight"] == row["preferred_flight"] else "fallback") for row in selected["EE-01"])
    rhp = Counter(row["fulfillment_mode"] for row in selected["RHP-01"])
    rap = Counter(row["address_contract"] for row in selected["RAP-01"])
    jsg = Counter((row["ticketing_channel"], row["expected_branch"]) for row in selected["JSG-01"])
    assert ee == {("horizon", "preferred"): 1, ("horizon", "fallback"): 1, ("summit", "preferred"): 1, ("summit", "fallback"): 1}
    assert rhp == {"consolidated": 2, "partner_direct": 2}
    assert rap == {"cedar": 2, "orbit": 2}
    assert jsg == {("horizon", "preferred"): 1, ("horizon", "fallback"): 1, ("summit", "preferred"): 1, ("summit", "fallback"): 1}
    return {
        "EE-01": {f"{a}_{b}": n for (a, b), n in sorted(ee.items())},
        "RHP-01": dict(sorted(rhp.items())),
        "RAP-01": dict(sorted(rap.items())),
        "JSG-01": {f"{a}_{b}": n for (a, b), n in sorted(jsg.items())},
    }


def assert_surface_balance(specs: dict[str, dict[str, Any]]) -> None:
    for name in ("EE-01", "JSG-01"):
        rows = [spec for tid, spec in specs.items() if family(tid) == name]
        for surface in range(1, 5):
            pair = [row for row in rows if row["surface"] == surface]
            assert {row["ticketing_channel"] for row in pair} == {"horizon", "summit"}
            branches = {
                row["expected_branch"]
                if "expected_branch" in row
                else (
                    "preferred"
                    if row["expected_flight"] == row["preferred_flight"]
                    else "fallback"
                )
                for row in pair
            }
            assert branches == {"preferred", "fallback"}
    for name, key, values in (
        ("RHP-01", "fulfillment_mode", {"consolidated", "partner_direct"}),
        ("RAP-01", "address_contract", {"cedar", "orbit"}),
    ):
        rows = [spec for tid, spec in specs.items() if family(tid) == name]
        for surface in range(1, 5):
            assert {row[key] for row in rows if row["surface"] == surface} == values


def entity_set(spec: dict[str, Any]) -> set[str]:
    values = set()
    for key, value in spec.items():
        if key.endswith("_id") or key.endswith("_flight") or key.endswith("_legal") or key.endswith("_alternate"):
            if isinstance(value, str):
                values.add(value)
    return values


def main() -> None:
    tasks = load(TASKS)
    split_payload = load(SPLITS)
    split_ids = {name: set(ids) for name, ids in split_payload["splits"].items()}
    assert set(split_ids) == {"train", "monitor"}
    assert split_payload.get("test_split") is None
    assert len(tasks) == len({task["id"] for task in tasks}) == 32
    assert len(split_ids["train"]) == len(split_ids["monitor"]) == 16
    assert split_ids["train"].isdisjoint(split_ids["monitor"])
    assert split_ids["train"] | split_ids["monitor"] == {task["id"] for task in tasks}
    for task in tasks:
        Task.model_validate(task)

    specs: dict[str, dict[str, Any]] = {}
    for path in SPEC_FILES.values():
        specs.update({row["task_id"]: row for row in load(path)["tasks"]})
    assert set(specs) == {task["id"] for task in tasks}
    family_split_counts = {
        split: dict(Counter(family(tid) for tid in ids)) for split, ids in split_ids.items()
    }
    assert all(count == 4 for counts in family_split_counts.values() for count in counts.values())
    assert all(set(counts) == set(SPEC_FILES) for counts in family_split_counts.values())
    train_entities = set().union(*(entity_set(specs[tid]) for tid in split_ids["train"]))
    monitor_entities = set().union(*(entity_set(specs[tid]) for tid in split_ids["monitor"]))
    assert train_entities.isdisjoint(monitor_entities)
    balance = {split: assert_balanced(specs, ids) for split, ids in split_ids.items()}
    assert_surface_balance(specs)

    domain_counts = Counter(task["user_scenario"]["instructions"]["domain"] for task in tasks)
    assert domain_counts == {"airline-v3-unified": 16, "retail-v3-unified": 16}
    assert all(
        task["user_scenario"]["instructions"]["domain"] == ("airline-v3-unified" if family(task["id"]) in {"EE-01", "JSG-01"} else "retail-v3-unified")
        for task in tasks
    )

    visible_task_text = json.dumps(
        [task["user_scenario"]["instructions"] for task in tasks], ensure_ascii=False
    ).lower()
    for forbidden in ("retained_historical", "complete_current", "exchange_protection_behavior", "propagation_source"):
        assert forbidden not in visible_task_text

    airline = get_airline_environment()
    retail = get_retail_environment()
    airline_policy = airline.policy.lower()
    retail_policy = retail.policy.lower()
    assert "horizon" not in airline_policy and "summit" not in airline_policy
    assert all(label not in retail_policy for label in ("consolidated", "partner_direct", "partner-direct", "cedar", "orbit"))
    assert "fulfillment-resolution extension" in retail_policy
    assert "address synchronization extension" in retail_policy

    airline_specs = [spec for tid, spec in specs.items() if family(tid) in {"EE-01", "JSG-01"}]
    for spec in airline_specs:
        context = airline.tools.get_settlement_context(spec["reservation_id"])
        assert context["ticketing_channel"] == spec["ticketing_channel"]
        assert "settlement_baseline" not in context
    retail_specs = [spec for tid, spec in specs.items() if family(tid) in {"RHP-01", "RAP-01"}]
    for spec in retail_specs:
        order_id = spec["order_id"]
        assert order_id in retail.tools.db.resolution_contracts
        assert order_id in retail.tools.db.address_propagation_contracts
        resolution = retail.tools.get_resolution_context(order_id)
        address = retail.tools.get_address_propagation_context(order_id)
        assert "exchange_protection_behavior" not in resolution
        assert "propagation_source" not in address

    # Replay every oracle path in the unified environments. Entities are disjoint,
    # so a single domain DB intentionally exercises cross-family coexistence.
    runtime = {name: 0 for name in SPEC_FILES}
    for tid, spec in specs.items():
        name = family(tid)
        if name == "EE-01":
            apply_airline_update(airline.tools, spec, spec["expected_flight"])
            assert evaluate_ee(spec, airline.tools.db.model_dump(mode="json"))["success"]
        elif name == "JSG-01":
            apply_airline_update(airline.tools, spec, spec[f"{spec['expected_branch']}_legal"])
            outcome = evaluate_jsg(spec, airline.tools.db.model_dump(mode="json"))
            assert outcome["joint_success"] and outcome["success"] and outcome["compliant"]
        elif name == "RHP-01":
            if spec["expected_resolution"] == "exchange":
                retail.tools.exchange_delivered_order_items(spec["order_id"], [spec["old_item_id"]], [spec["new_item_id"]], spec["payment_id"])
            else:
                retail.tools.return_delivered_order_items(spec["order_id"], [spec["old_item_id"]], spec["payment_id"])
            assert evaluate_rhp(spec, retail.tools.db.model_dump(mode="json"))["success"]
        else:
            for target in spec["correct_sequence"]:
                apply_retail_address_write(retail.tools, spec, target)
            assert evaluate_rap(spec, retail.tools.db.model_dump(mode="json"))["success"]
        runtime[name] += 1

    loaders = {
        "airline": {"base": len(get_airline_tasks()), "train": len(get_airline_tasks("train")), "monitor": len(get_airline_tasks("monitor"))},
        "retail": {"base": len(get_retail_tasks()), "train": len(get_retail_tasks("train")), "monitor": len(get_retail_tasks("monitor"))},
    }
    assert loaders == {
        "airline": {"base": 16, "train": 8, "monitor": 8},
        "retail": {"base": 16, "train": 8, "monitor": 8},
    }

    result = {
        "status": "PASS_32_TASK_UNIFIED_ENVIRONMENT_TRAIN_MONITOR",
        "model_calls": 0,
        "formal_task_count": 32,
        "split_counts": {"train": 16, "monitor": 16, "test": 0},
        "family_split_counts": family_split_counts,
        "domain_counts": dict(domain_counts),
        "train_monitor_entity_overlap": 0,
        "split_balance": balance,
        "uniform_environments": {
            "airline-v3-unified": {"tasks": 16, "hidden_mechanisms": ["channel-conditioned settlement baseline"]},
            "retail-v3-unified": {"tasks": 16, "hidden_mechanisms": ["fulfillment-conditioned resolution outcome", "address-contract propagation source"]},
        },
        "all_airline_tasks_share_policy_tool_schema_and_hide_same_mapping": True,
        "all_retail_tasks_share_policy_tool_schema_and_hide_both_mappings": True,
        "task_visible_text_does_not_reveal_latent_answers": True,
        "evaluator_only_oracle_fields_are_not_agent_visible": True,
        "every_surface_spans_both_answers_in_each_family": True,
        "surface_shortcut_repairs": ["EE-01-C05..C08 surface reassignment", "RHP-01-C05..C08 surface reassignment"],
        "unified_runtime_oracle_successes": runtime,
        "task_loader_counts": loaders,
    }
    (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/integration_audit').mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS v3 integration: 32 tasks; Train 16 / Monitor 16; two unified domains; 32/32 oracle paths")


if __name__ == "__main__":
    main()
