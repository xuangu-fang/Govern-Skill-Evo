"""Final-candidate registry, runtime adapter and deterministic evaluation for v16."""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


HERE = Path(__file__).resolve().parent
EDITION = HERE.parents[1]
REPO = EDITION.parents[3]
TAU2 = REPO / "external/tau2-bench"
sys.path[:0] = [str(REPO), str(TAU2 / "src")]

from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.construction.integration_audit.control_evaluator import (  # noqa: E402
    evaluate as evaluate_control,
)
from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.environment import (  # noqa: E402
    register_domains,
)
from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.environment.airline import (  # noqa: E402
    DOMAIN_NAME as AIRLINE_DOMAIN,
    get_environment as get_airline_environment,
)
from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.environment.retail import (  # noqa: E402
    DOMAIN_NAME as RETAIL_DOMAIN,
    get_environment as get_retail_environment,
)
from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import (  # noqa: E402
    _config as base_text_config,
)
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.joint_settlement_destination_scope.candidate_tasks.evaluators.evaluate_jsg01 import (  # noqa: E402
    evaluate as evaluate_jsg,
)
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.latent_settlement_contract.candidate_tasks.evaluators.evaluate_latent_settlement import (  # noqa: E402
    evaluate_success as evaluate_ee,
)
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_address_propagation.candidate_tasks.evaluators.evaluate_rap01 import (  # noqa: E402
    evaluate_success as evaluate_rap,
)
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.candidate_tasks.evaluators.evaluate_rhp01 import (  # noqa: E402
    evaluate_success as evaluate_rhp,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.evaluators import (  # noqa: E402
    evaluate_compliance as evaluate_booking_compliance,
    evaluate_success as evaluate_booking,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator import (  # noqa: E402
    build_lga03_evidence_registry,
    evaluate_trace,
    normalize_trace,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.data_model import (  # noqa: E402
    FinalCandidateAirlineDB,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.tools import (  # noqa: E402
    FinalCandidateAirlineTools,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.p4_certificate_allocation.evaluator import (  # noqa: E402
    evaluate as evaluate_p4,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.governance_core_expansion.insurance_reason_eligibility.multi_surface.evaluator import (  # noqa: E402
    evaluate as evaluate_insurance,
)
from src.skill_evolution.autonomous_gse_v15_benchmark_runtime import (  # noqa: E402
    prepare_diagnosis_from_stored,
)
from src.skill_evolution.information_boundary_v15 import (  # noqa: E402
    agent_payload,
    capture_agent_visible_view,
    unpack,
)
from src.skill_evolution.distributional_gate_v14 import (  # noqa: E402
    gate_decision,
    is_epsilon_pareto_positive,
)


TASKS = EDITION / "benchmark/tasks.json"
CONTROL_TASKS = EDITION / "benchmark/control_tasks.json"
SPLITS = EDITION / "benchmark/splits.json"
NEW_SPECS = EDITION / "benchmark/new_family_specs.json"
CONTROL_SPECS = EDITION / "benchmark/control_specs.json"
CONFIG = HERE / "campaign_config.json"
INTEGRATION_RESULT = EDITION / "construction/integration_audit/integration_validation.json"
V3 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v3_day34"
V3_SPEC_FILES = {
    "EE-01": V3 / "construction/latent_settlement_contract/core_family/candidates/task_specs.json",
    "RHP-01": V3 / "construction/retail_hidden_operational_path/core_family/candidates/task_specs.json",
    "RAP-01": V3 / "construction/retail_address_propagation/core_family/candidates/task_specs.json",
    "JSG-01": V3 / "construction/joint_settlement_destination_scope/core_family/candidates/task_specs.json",
}
CORE_FAMILIES = {"EE-01", "RHP-01", "RAP-01", "P4-01", "GPC-01", "GMB-01", "GIR-01", "JSG-01"}
CAPABILITY_FAMILIES = {"EE-01", "RHP-01", "RAP-01", "P4-01"}
GOVERNANCE_FAMILIES = {"GPC-01", "GMB-01", "GIR-01"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def family_of(task_id: str) -> str:
    return "CONTROL" if task_id.startswith("CTRL-") else task_id.rsplit("-C", 1)[0]


def logical_domain(runtime_domain: str) -> str:
    if runtime_domain == AIRLINE_DOMAIN:
        return "airline"
    if runtime_domain == RETAIL_DOMAIN:
        return "retail"
    raise ValueError(f"Unsupported final-candidate domain: {runtime_domain}")


@dataclass(frozen=True)
class BenchmarkEntry:
    task: Task
    payload: dict[str, Any]
    spec: dict[str, Any]
    family: str
    split: str
    monitor_role: str | None
    runtime_domain: str
    logical_domain: str


class BenchmarkRegistry:
    """Single authoritative view of all 73 formal tasks and evaluator specs."""

    def __init__(self) -> None:
        task_payloads = load(TASKS) + load(CONTROL_TASKS)
        split_payload = load(SPLITS)
        split_by_id = {
            task_id: split
            for split, task_ids in split_payload["splits"].items()
            for task_id in task_ids
        }
        role_by_id = {
            task_id: role
            for role, task_ids in split_payload["monitor_roles"].items()
            for task_id in task_ids
        }
        specs: dict[str, dict[str, Any]] = {}
        for path in V3_SPEC_FILES.values():
            specs.update({row["task_id"]: row for row in load(path)["tasks"]})
        specs.update({row["task_id"]: row for row in load(NEW_SPECS)["tasks"]})
        specs.update({row["task_id"]: row for row in load(CONTROL_SPECS)["controls"]})

        self.entries: dict[str, BenchmarkEntry] = {}
        for payload in task_payloads:
            task_id = str(payload["id"])
            runtime_domain = payload["user_scenario"]["instructions"]["domain"]
            self.entries[task_id] = BenchmarkEntry(
                task=Task.model_validate(payload),
                payload=payload,
                spec=specs[task_id],
                family=family_of(task_id),
                split=split_by_id[task_id],
                monitor_role=role_by_id.get(task_id),
                runtime_domain=runtime_domain,
                logical_domain=logical_domain(runtime_domain),
            )

    def task_ids(self, split: str | None = None) -> list[str]:
        return sorted(
            task_id
            for task_id, entry in self.entries.items()
            if split is None or entry.split == split
        )

    def get(self, task_id: str) -> BenchmarkEntry:
        return self.entries[task_id]


class UnifiedEnvironmentAdapter:
    """Build fresh final-candidate environments and v15-visible views."""

    def __init__(self, registry: BenchmarkRegistry) -> None:
        self.registry = registry
        register_domains()

    @staticmethod
    def fresh_environment(runtime_domain: str):
        if runtime_domain == AIRLINE_DOMAIN:
            return get_airline_environment()
        if runtime_domain == RETAIL_DOMAIN:
            return get_retail_environment()
        raise ValueError(f"Unknown runtime domain: {runtime_domain}")

    def visible_view_without_models(self, task_id: str):
        entry = self.registry.get(task_id)
        environment = self.fresh_environment(entry.runtime_domain)
        agent_like = SimpleNamespace(
            domain_policy=environment.get_policy(),
            tools=environment.get_tools(),
        )
        return capture_agent_visible_view(agent_like, entry.logical_domain)

    def build_orchestrator(
        self,
        task_id: str,
        *,
        base_config: dict[str, Any],
        seed: int,
        skill_path: Path,
        initial_skill_path: Path,
    ):
        entry = self.registry.get(task_id)
        config = base_text_config(
            base_config,
            {"domain": entry.runtime_domain, "task_id": task_id},
            seed,
        )
        if skill_path.resolve() != initial_skill_path.resolve():
            config.agent = "llm_agent_manual_skill"
            config.llm_args_agent = {
                **config.llm_args_agent,
                "manual_skill_path": str(skill_path.resolve()),
            }
        orchestrator = build_text_orchestrator(config, entry.task, seed=seed)
        view = capture_agent_visible_view(orchestrator.agent, entry.logical_domain)
        return orchestrator, view


class DeterministicEvaluatorDispatcher:
    """Map every formal task to deterministic Success and Compliance labels."""

    def __init__(self, registry: BenchmarkRegistry) -> None:
        self.registry = registry

    def route(self, task_id: str) -> str:
        family = self.registry.get(task_id).family
        if family in CORE_FAMILIES:
            return family
        if family == "CONTROL":
            return "CONTROL"
        raise ValueError(f"No evaluator route for {task_id}")

    @staticmethod
    def _messages(simulation: dict[str, Any] | Any) -> dict[str, Any]:
        if hasattr(simulation, "model_dump"):
            return simulation.model_dump(mode="json")
        if isinstance(simulation, dict) and isinstance(simulation.get("messages"), list):
            return simulation
        raise ValueError("Serialized tau2 simulation with messages is required")

    def evaluate(
        self,
        task_id: str,
        *,
        initial_db: dict[str, Any],
        final_db: dict[str, Any],
        simulation: dict[str, Any] | Any,
    ) -> dict[str, Any]:
        entry = self.registry.get(task_id)
        spec, family = entry.spec, entry.family
        serialized = self._messages(simulation)

        if family == "EE-01":
            success_record = evaluate_ee(spec, final_db)
        elif family == "RHP-01":
            success_record = evaluate_rhp(spec, final_db)
        elif family == "RAP-01":
            success_record = evaluate_rap(spec, final_db)
        elif family == "JSG-01":
            joint = evaluate_jsg(spec, final_db)
            success_record = {"success": joint["success"], "details": joint}
        elif family == "P4-01":
            success_record = evaluate_p4(spec, initial_db, final_db)
        elif family in {"GPC-01", "GMB-01"}:
            success_record = evaluate_booking(spec, initial_db, final_db)
        elif family == "GIR-01":
            success_record = evaluate_insurance(spec, initial_db, serialized, final_db)
        elif family == "CONTROL":
            success_record = evaluate_control(task_id, initial_db, final_db)
        else:
            raise ValueError(f"Unsupported evaluator family: {family}")

        if family == "JSG-01":
            compliance_record = {
                "compliant": bool(joint["compliant"]),
                "details": joint["compliance_invariant"],
            }
        elif family == "GIR-01":
            trace = evaluate_trace(
                initial_db=initial_db,
                messages_or_simulation=serialized,
                final_db=final_db,
                task_success=bool(success_record["success"]),
                registry=build_lga03_evidence_registry(),
                evaluator_context={
                    "cancellation_reason_category": spec["reason_category"],
                    "reason_source_message_index": 0,
                },
                environment_version=AIRLINE_DOMAIN,
            )
            compliance_record = self._trace_compliance(trace)
        elif family in {"GPC-01", "GMB-01"}:
            normalized = normalize_trace(
                serialized,
                FinalCandidateAirlineTools(FinalCandidateAirlineDB.model_validate(initial_db)),
            )
            committed_writes = [
                {"tool_name": event.tool_name, "arguments": event.arguments}
                for event in normalized
                if event.call_kind == "WRITE" and event.outcome == "SUCCEEDED"
            ]
            compliance_record = evaluate_booking_compliance(initial_db, committed_writes)
        else:
            compliance_record = {
                "compliant": True,
                "details": "No focal Governance rule is assigned by the formal evaluation manifest.",
            }

        success = bool(success_record["success"])
        compliant = bool(compliance_record["compliant"])
        return {
            "task_id": task_id,
            "family": family,
            "success": success,
            "compliant": compliant,
            "quadrant": ("C" if compliant else "V") + ("S" if success else "F"),
            "success_record": success_record,
            "compliance_record": compliance_record,
            "evaluator_kind": "DETERMINISTIC",
        }

    @staticmethod
    def _trace_compliance(trace: dict[str, Any]) -> dict[str, Any]:
        if trace["trace_status"] != "TRACE_VALID" or trace["benchmark_governance_compliant"] is None:
            raise ValueError(f"Deterministic Governance trace is unscored: {trace['trace_error']}")
        return {
            "compliant": bool(trace["benchmark_governance_compliant"]),
            "trace": trace,
        }


def prepare_v16_diagnosis(
    view,
    parent_skill: str,
    serialized_rollouts: list[dict[str, Any]],
    evaluation_records: list[dict[str, Any]],
):
    """Adapt deterministic v16 labels to the unchanged v15 learner boundary."""
    return prepare_diagnosis_from_stored(
        view,
        parent_skill,
        serialized_rollouts,
        [{"success": bool(row["success"])} for row in evaluation_records],
        [{"compliant": bool(row["compliant"])} for row in evaluation_records],
    )


def audit_learner_request(request) -> dict[str, Any]:
    """Assert that benchmark-private metadata is absent from a v16 request."""
    payload = unpack(request.learner_view, "LEARNER_SAFE_VIEW")
    text = json.dumps(payload, ensure_ascii=False).lower()
    forbidden = (
        '"family"', '"monitor_role"', '"expected_action"',
        '"settlement_baseline"', '"propagation_source"',
        '"max_passengers_per_reservation"', '"membership_offset"',
        '"cabin_offset"', '"cancellation_reason_category"',
    )
    leaked = [token for token in forbidden if token in text]
    if leaked:
        raise ValueError(f"Learner request contains benchmark-private metadata: {leaked}")
    return {
        "learner_setting": payload["learner_setting"],
        "domain": payload["domain"],
        "rollout_count": len(payload["rollouts"]),
        "private_metadata_tokens_found": leaked,
    }


def compare_matched_rollouts(
    parent_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    key = lambda row: (row["domain"], row["task_id"], row["rollout_index"], row["rollout_seed"])
    parents = {key(row): row for row in parent_rows}
    candidates = {key(row): row for row in candidate_rows}
    if set(parents) != set(candidates):
        raise ValueError("Parent and Candidate Monitor lineage differs")
    pairs = []
    transitions = Counter()
    for lineage in sorted(parents):
        parent, candidate = parents[lineage], candidates[lineage]
        transition = f"{parent['quadrant']}->{candidate['quadrant']}"
        transitions[transition] += 1
        pairs.append({
            "domain": parent["domain"],
            "task_id": parent["task_id"],
            "rollout_index": parent["rollout_index"],
            "rollout_seed": parent["rollout_seed"],
            "parent_state": parent["quadrant"],
            "candidate_state": candidate["quadrant"],
            "delta_success": int(candidate["success"]) - int(parent["success"]),
            "delta_compliance": int(candidate["compliant"]) - int(parent["compliant"]),
        })
    return {"matched_pairs": pairs, "transition_matrix": dict(transitions)}


def unified_gate(
    comparison: dict[str, Any],
    *,
    replicates: int = 10_000,
    bootstrap_seed: int = 200,
    epsilon_pair_count: int = 1,
    threshold: float = 0.80,
) -> dict[str, Any]:
    """The sole v16 decision over all 41 Monitor task clusters."""
    pairs = comparison["matched_pairs"]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        grouped[(pair["domain"], pair["task_id"])].append(pair)
    if len(grouped) != 41 or len(pairs) != 123:
        raise ValueError("Unified Gate requires 41 tasks x 3 matched rollouts")
    if any(len(rows) != 3 or {row["rollout_index"] for row in rows} != {1, 2, 3} for rows in grouped.values()):
        raise ValueError("Every unified-Gate task cluster requires rollout indices 1/2/3")

    strata: dict[str, list[dict[str, int]]] = defaultdict(list)
    for (domain, task_id), rows in grouped.items():
        strata[domain].append({
            "task_id": task_id,
            "success": sum(row["delta_success"] for row in rows),
            "compliance": sum(row["delta_compliance"] for row in rows),
        })
    rng = random.Random(bootstrap_seed)
    positive = 0
    for _ in range(replicates):
        delta_success = delta_compliance = 0
        for rows in strata.values():
            draw = rng.choices(rows, k=len(rows))
            delta_success += sum(row["success"] for row in draw)
            delta_compliance += sum(row["compliance"] for row in draw)
        positive += is_epsilon_pareto_positive(
            delta_success, delta_compliance, epsilon_pair_count
        )
    probability = positive / replicates
    observed_success = sum(row["success"] for rows in strata.values() for row in rows)
    observed_compliance = sum(row["compliance"] for rows in strata.values() for row in rows)
    return {
        "gate_id": "GSE_V16_UNIFIED_MONITOR_GATE",
        "monitor_tasks": len(grouped),
        "matched_rollouts": len(pairs),
        "domain_task_counts": {domain: len(rows) for domain, rows in strata.items()},
        "bootstrap_unit": "task",
        "bootstrap_replicates": replicates,
        "bootstrap_seed": bootstrap_seed,
        "epsilon_pair_count": epsilon_pair_count,
        "observed_delta_success_count": observed_success,
        "observed_delta_compliance_count": observed_compliance,
        "positive_probability": probability,
        "threshold": threshold,
        "decision": gate_decision(probability, threshold),
    }


def synthetic_monitor_rows(*, improved: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build deterministic Gate-only fixtures; no model or benchmark mutation."""
    registry = BenchmarkRegistry()
    parent, candidate = [], []
    monitor_ids = registry.task_ids("monitor")
    for task_id in monitor_ids:
        entry = registry.get(task_id)
        for rollout_index, seed in enumerate((200, 201, 202), 1):
            base = {
                "domain": entry.runtime_domain,
                "task_id": task_id,
                "rollout_index": rollout_index,
                "rollout_seed": seed,
                "success": not improved,
                "compliant": True,
            }
            base["quadrant"] = ("C" if base["compliant"] else "V") + ("S" if base["success"] else "F")
            parent.append(base)
            changed = dict(base)
            if improved:
                changed["success"] = True
                changed["quadrant"] = "CS"
            candidate.append(changed)
    return parent, candidate
