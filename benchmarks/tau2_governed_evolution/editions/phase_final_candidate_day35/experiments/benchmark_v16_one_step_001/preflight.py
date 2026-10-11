#!/usr/bin/env python3
"""Zero-model preflight for the GSE-v16 one-step campaign."""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.construction.integration_audit.validate_integration import (
    main as validate_final_edition,
    run_insurance_path,
)
from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.experiments.benchmark_v16_one_step_001.benchmark_runtime import (
    AIRLINE_DOMAIN,
    CONFIG,
    CONTROL_TASKS,
    CORE_FAMILIES,
    EDITION,
    INTEGRATION_RESULT,
    RETAIL_DOMAIN,
    REPO,
    SPLITS,
    TASKS,
    BenchmarkRegistry,
    DeterministicEvaluatorDispatcher,
    UnifiedEnvironmentAdapter,
    audit_learner_request,
    compare_matched_rollouts,
    load,
    prepare_v16_diagnosis,
    synthetic_monitor_rows,
    unified_gate,
)


HERE = Path(__file__).resolve().parent
REPORT = HERE / "run/preflight_report.json"
STATE_MACHINE = (
    "S0_MONITOR_BASELINE",
    "S0_EVOLUTION_PARENT",
    "DIAGNOSIS_PROPOSAL_EDITOR",
    "S1_MONITOR_CANDIDATE",
    "UNIFIED_GATE",
    "FINALIZE",
)


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _synthetic_rollouts() -> list[dict[str, Any]]:
    return [
        {
            "messages": [
                {"role": "user", "content": f"Synthetic observed request {index}."},
                {"role": "assistant", "content": "Synthetic observed response."},
            ]
        }
        for index in (1, 2, 3)
    ]


def _fresh_environment_check(adapter: UnifiedEnvironmentAdapter, domain: str) -> dict[str, Any]:
    first = adapter.fresh_environment(domain)
    second = adapter.fresh_environment(domain)
    first_db = first.tools.db.model_dump(mode="json")
    second_db = second.tools.db.model_dump(mode="json")
    assert first is not second and first.tools is not second.tools
    assert first_db == second_db
    return {
        "domain": domain,
        "independent_environment_objects": True,
        "equal_initial_state": True,
        "tool_count": len(first.get_tools()),
    }


def _json_value(value: Any) -> Any:
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def _run_formal_actions(
    registry: BenchmarkRegistry,
    adapter: UnifiedEnvironmentAdapter,
    dispatcher: DeterministicEvaluatorDispatcher,
    task_id: str,
) -> str:
    entry = registry.get(task_id)
    environment = adapter.fresh_environment(entry.runtime_domain)
    initial = environment.tools.db.model_dump(mode="json")
    messages: list[dict[str, Any]] = []
    actions = list(entry.payload["evaluation_criteria"]["actions"])
    if entry.family == "RAP-01":
        target_by_name = {
            "modify_pending_order_address": "order",
            "modify_user_address": "profile",
        }
        position = {target: index for index, target in enumerate(entry.spec["correct_sequence"])}
        actions.sort(key=lambda action: position[target_by_name[action["name"]]])
    for index, action in enumerate(actions):
        call_id = f"preflight-{task_id}-{index}"
        name, arguments = action["name"], deepcopy(action["arguments"])
        messages.append({
            "role": "assistant",
            "tool_calls": [{
                "id": call_id,
                "name": name,
                "arguments": arguments,
                "requestor": "assistant",
            }],
        })
        try:
            content = json.dumps(_json_value(environment.tools.use_tool(name, **arguments)))
            failed = False
        except Exception as error:
            content, failed = f"Error: {error}", True
        messages.append({
            "id": call_id,
            "role": "tool",
            "content": content,
            "requestor": "assistant",
            "error": failed,
        })
    final = environment.tools.db.model_dump(mode="json")
    result = dispatcher.evaluate(
        task_id,
        initial_db=initial,
        final_db=final,
        simulation={"messages": messages},
    )
    assert result["quadrant"] == "CS", {
        "task_id": task_id,
        "quadrant": result["quadrant"],
        "success_record": result["success_record"],
        "compliance_record": result["compliance_record"],
    }
    return result["quadrant"]


def _evaluator_smoke_checks(
    registry: BenchmarkRegistry,
    adapter: UnifiedEnvironmentAdapter,
    dispatcher: DeterministicEvaluatorDispatcher,
) -> dict[str, str]:
    results = {
        family: _run_formal_actions(
            registry,
            adapter,
            dispatcher,
            next(task_id for task_id in registry.task_ids() if task_id.startswith(f"{family}-C")),
        )
        for family in ("EE-01", "RHP-01", "RAP-01", "JSG-01", "P4-01", "GPC-01", "GMB-01")
    }

    gir_id = "GIR-01-C01"
    gir_entry = registry.get(gir_id)
    airline = adapter.fresh_environment(gir_entry.runtime_domain)
    initial = airline.tools.db.model_dump(mode="json")
    messages = run_insurance_path(airline.tools, gir_entry.spec)
    final = airline.tools.db.model_dump(mode="json")
    gir = dispatcher.evaluate(
        gir_id,
        initial_db=initial,
        final_db=final,
        simulation={"messages": messages},
    )
    assert gir["quadrant"] == "CS"
    results["GIR-01"] = gir["quadrant"]

    trajectories = EDITION / "construction/integration_audit/control_e0/trajectories"
    for task_id in registry.task_ids("monitor"):
        if not task_id.startswith("CTRL-"):
            continue
        entry = registry.get(task_id)
        initial = adapter.fresh_environment(entry.runtime_domain).tools.db.model_dump(mode="json")
        control = dispatcher.evaluate(
            task_id,
            initial_db=initial,
            final_db=load(trajectories / f"{task_id}_seed_5211_final_db.json"),
            simulation=load(trajectories / f"{task_id}_seed_5211_raw.json"),
        )
        assert control["quadrant"] == "CS"
        results[task_id] = control["quadrant"]
    return results


def run_preflight() -> dict[str, Any]:
    # Re-run the edition's existing oracle and regression audit as part of this
    # preflight; it performs no model calls.
    validate_final_edition()

    config = load(CONFIG)
    registry = BenchmarkRegistry()
    adapter = UnifiedEnvironmentAdapter(registry)
    dispatcher = DeterministicEvaluatorDispatcher(registry)
    split_payload = load(SPLITS)
    all_ids = set(registry.task_ids())
    train_ids = set(registry.task_ids("train"))
    monitor_ids = set(registry.task_ids("monitor"))
    core_monitor = set(split_payload["monitor_roles"]["CORE_GENERALIZATION"])
    regression_guard = set(split_payload["monitor_roles"]["REGRESSION_GUARD"])

    assert len(load(TASKS)) == 64 and len(load(CONTROL_TASKS)) == 9
    assert len(all_ids) == 73 and len(train_ids) == 32 and len(monitor_ids) == 41
    assert train_ids.isdisjoint(monitor_ids) and train_ids | monitor_ids == all_ids
    assert len(core_monitor) == 32 and len(regression_guard) == 9
    assert core_monitor | regression_guard == monitor_ids
    family_counts = Counter(
        entry.family for entry in registry.entries.values() if entry.family in CORE_FAMILIES
    )
    assert family_counts == {family: 8 for family in CORE_FAMILIES}

    routes = {task_id: dispatcher.route(task_id) for task_id in registry.task_ids()}
    assert len(routes) == 73
    environment_checks = [
        _fresh_environment_check(adapter, AIRLINE_DOMAIN),
        _fresh_environment_check(adapter, RETAIL_DOMAIN),
    ]
    evaluator_smoke = _evaluator_smoke_checks(registry, adapter, dispatcher)

    parent_skill_path = REPO / config["initial_skill"]
    parent_skill = parent_skill_path.read_text(encoding="utf-8")
    synthetic_rollouts = _synthetic_rollouts()
    labels = [{"success": True, "compliant": True} for _ in range(3)]
    learner_checks = []
    for task_id in (next(item for item in sorted(all_ids) if item.startswith("EE-01")), next(item for item in sorted(all_ids) if item.startswith("RHP-01"))):
        request = prepare_v16_diagnosis(
            adapter.visible_view_without_models(task_id),
            parent_skill,
            synthetic_rollouts,
            labels,
        )
        learner_checks.append(audit_learner_request(request))

    retain_parent, retain_candidate = synthetic_monitor_rows(improved=False)
    accept_parent, accept_candidate = synthetic_monitor_rows(improved=True)
    retain = unified_gate(compare_matched_rollouts(retain_parent, retain_candidate))
    accept = unified_gate(compare_matched_rollouts(accept_parent, accept_candidate))
    assert retain["decision"] == "RETAIN" and accept["decision"] == "ACCEPT"

    integration = load(INTEGRATION_RESULT)
    assert integration["status"] == "PASS_73_TASK_EVOLUTION32_MONITOR41"
    assert config["protocol"] == "ONE_STEP"
    assert config["rollouts_per_task"] == 3
    assert config["gate"]["decision_count"] == 1
    assert len(STATE_MACHINE) == 6 and STATE_MACHINE.count("UNIFIED_GATE") == 1

    result = {
        "status": "PASS_GSE_V16_ONE_STEP_ZERO_MODEL_PREFLIGHT",
        "campaign_id": config["campaign_id"],
        "model_calls": 0,
        "task_registry": {
            "total": len(all_ids),
            "evolution": len(train_ids),
            "monitor": len(monitor_ids),
            "core_generalization": len(core_monitor),
            "regression_guard": len(regression_guard),
            "family_counts": dict(sorted(family_counts.items())),
        },
        "evaluator_dispatch": {
            "covered": len(routes),
            "route_counts": dict(sorted(Counter(routes.values()).items())),
            "executed_smoke_paths": len(evaluator_smoke),
            "smoke_results": evaluator_smoke,
            "kind": "DETERMINISTIC",
            "llm_judge": False,
        },
        "environment_checks": environment_checks,
        "learner_safe_supervision": learner_checks,
        "unified_gate": {
            "monitor_tasks": 41,
            "matched_rollouts": 123,
            "synthetic_retain": retain["decision"],
            "synthetic_accept": accept["decision"],
            "decision_count": 1,
        },
        "state_machine": list(STATE_MACHINE),
        "source_integration_audit": integration["status"],
    }
    write(REPORT, result)
    return result


def main() -> int:
    result = run_preflight()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
