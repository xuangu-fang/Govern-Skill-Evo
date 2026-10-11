#!/usr/bin/env python3
"""Run the GSE-v16 one-step campaign after zero-model preflight."""

from __future__ import annotations

import argparse
import json
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.experiments.benchmark_v16_one_step_001.benchmark_runtime import (
    CONFIG,
    REPO,
    BenchmarkRegistry,
    DeterministicEvaluatorDispatcher,
    UnifiedEnvironmentAdapter,
    compare_matched_rollouts,
    load,
    prepare_v16_diagnosis,
    unified_gate,
)
from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.experiments.benchmark_v16_one_step_001.preflight import (
    run_preflight,
)
from src.learners.stwebagentbench.generate_skill import call_learner
from src.skill_evolution.autonomous_gse_v15_benchmark_runtime import propose_from_experience
from src.skill_evolution.information_boundary_v15 import unpack


HERE = Path(__file__).resolve().parent
RUN = HERE / "run"
BASELINE_DIR = RUN / "s0_monitor_baseline"
EVOLUTION_DIR = RUN / "step1/evolution_parent"
CANDIDATE_MONITOR_DIR = RUN / "step1/s1_monitor_candidate"
BASELINE_STAGE = RUN / "s0_monitor_baseline_stage.json"
EVOLUTION_STAGE = RUN / "step1/evolution_stage.json"


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    quadrants = Counter(row["quadrant"] for row in rows)
    total = len(rows)
    return {
        "tasks": len({row["task_id"] for row in rows}),
        "rollouts": total,
        "Capability Success": sum(row["success"] for row in rows) / total,
        "Governance Compliance": sum(row["compliant"] for row in rows) / total,
        **{name: quadrants[name] for name in ("CS", "CF", "VS", "VF")},
    }


class OneStepCampaign:
    def __init__(self) -> None:
        self.config = load(CONFIG)
        self.registry = BenchmarkRegistry()
        self.adapter = UnifiedEnvironmentAdapter(self.registry)
        self.evaluator = DeterministicEvaluatorDispatcher(self.registry)
        self.base_config = load(REPO / self.config["base_run_config"])
        self.initial_skill_path = REPO / self.config["initial_skill"]
        self.seeds = tuple(self.config["rollout_seeds"])

    @property
    def parent(self) -> dict[str, str]:
        return {
            "skill_id": "S0",
            "skill_path": str(self.initial_skill_path.resolve()),
        }

    def _require_preflight(self) -> dict[str, Any]:
        report_path = RUN / "preflight_report.json"
        report = load(report_path) if report_path.is_file() else run_preflight()
        if report.get("status") != "PASS_GSE_V16_ONE_STEP_ZERO_MODEL_PREFLIGHT":
            raise RuntimeError("GSE-v16 zero-model preflight has not passed")
        return report

    def _load_completed_rollouts(
        self,
        phase_dir: Path,
        task_ids: list[str],
        skill_id: str,
    ) -> list[dict[str, Any]]:
        path = phase_dir / "rollout_results.json"
        if not path.is_file():
            raise RuntimeError(f"Required stage is incomplete: {path}")
        rows = load(path)
        expected = {
            (task_id, rollout_index, seed)
            for task_id in task_ids
            for rollout_index, seed in enumerate(self.seeds, 1)
        }
        observed = {
            (row["task_id"], row["rollout_index"], row["rollout_seed"])
            for row in rows
            if row.get("skill_id") == skill_id
        }
        if observed != expected or len(rows) != len(expected):
            raise RuntimeError(
                f"Required stage has incomplete or mismatched rollout lineage: {path}"
            )
        return rows

    def _run_one(
        self,
        task_id: str,
        rollout_index: int,
        seed: int,
        skill: dict[str, str],
        phase_dir: Path,
    ) -> dict[str, Any]:
        stem = phase_dir / "trajectories" / f"{task_id}_rollout_{rollout_index:02d}"
        result_path = stem.with_suffix(".json")
        raw_path = stem.with_name(stem.name + "_raw.json")
        final_db_path = stem.with_name(stem.name + "_final_db.json")
        error_path = stem.with_name(stem.name + "_error.json")
        if result_path.is_file():
            cached = load(result_path)
            if (
                cached.get("task_id") == task_id
                and cached.get("rollout_seed") == seed
                and cached.get("skill_id") == skill["skill_id"]
            ):
                return cached

        try:
            orchestrator, _ = self.adapter.build_orchestrator(
                task_id,
                base_config=self.base_config,
                seed=seed,
                skill_path=Path(skill["skill_path"]),
                initial_skill_path=self.initial_skill_path,
            )
            initial_db = orchestrator.environment.tools.db.model_dump(mode="json")
            simulation = orchestrator.run()
            final_db = orchestrator.environment.tools.db.model_dump(mode="json")
            serialized = simulation.model_dump(mode="json")
            evaluation = self.evaluator.evaluate(
                task_id,
                initial_db=initial_db,
                final_db=final_db,
                simulation=serialized,
            )
            entry = self.registry.get(task_id)
            row = {
                "campaign_id": self.config["campaign_id"],
                "phase": phase_dir.name,
                "task_id": task_id,
                "family": entry.family,
                "domain": entry.runtime_domain,
                "split": entry.split,
                "monitor_role": entry.monitor_role,
                "rollout_index": rollout_index,
                "rollout_seed": seed,
                "skill_id": skill["skill_id"],
                "skill_path": skill["skill_path"],
                "success": evaluation["success"],
                "compliant": evaluation["compliant"],
                "quadrant": evaluation["quadrant"],
                "evaluation": evaluation,
                "raw_path": str(raw_path.resolve()),
                "final_db_path": str(final_db_path.resolve()),
            }
            write(raw_path, serialized)
            write(final_db_path, final_db)
            write(result_path, row)
            error_path.unlink(missing_ok=True)
            return row
        except Exception as error:
            write(error_path, {
                "task_id": task_id,
                "rollout_index": rollout_index,
                "rollout_seed": seed,
                "skill_id": skill["skill_id"],
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            })
            raise

    def run_rollouts(
        self,
        task_ids: list[str],
        *,
        skill: dict[str, str],
        phase_dir: Path,
    ) -> list[dict[str, Any]]:
        jobs = [
            (task_id, rollout_index, seed)
            for task_id in task_ids
            for rollout_index, seed in enumerate(self.seeds, 1)
        ]
        rows: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=self.config["max_workers"]) as pool:
            futures = [
                pool.submit(self._run_one, task_id, rollout_index, seed, skill, phase_dir)
                for task_id, rollout_index, seed in jobs
            ]
            for future in as_completed(futures):
                rows.append(future.result())
                rows.sort(key=lambda row: (row["task_id"], row["rollout_index"]))
                write(phase_dir / "rollout_progress.json", {
                    "completed": len(rows), "planned": len(jobs), "rows": rows,
                })
                print(json.dumps({
                    "phase": phase_dir.name,
                    "completed": len(rows),
                    "planned": len(jobs),
                }), flush=True)
        write(phase_dir / "rollout_results.json", rows)
        return rows

    def _learner_transport(
        self,
        system: str,
        user: str,
        response_format: dict[str, Any],
    ) -> str:
        response, _, _ = call_learner(
            self.config["learner_model"],
            system,
            user,
            temperature=0.0,
            response_format=response_format,
            max_completion_tokens=16_000,
        )
        if not response or not response.strip():
            raise RuntimeError("Empty learner response")
        return response.strip()

    def diagnose_and_edit(
        self,
        evolution_rows: list[dict[str, Any]],
        parent: dict[str, str],
    ) -> tuple[dict[str, str] | None, dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in evolution_rows:
            grouped[row["task_id"]].append(row)
        parent_text = Path(parent["skill_path"]).read_text(encoding="utf-8")
        requests = []
        for task_id in sorted(grouped):
            rows = sorted(grouped[task_id], key=lambda row: row["rollout_index"])
            if len(rows) != 3:
                raise ValueError(f"Diagnosis requires three Parent rollouts: {task_id}")
            _, view = self.adapter.build_orchestrator(
                task_id,
                base_config=self.base_config,
                seed=self.seeds[0],
                skill_path=Path(parent["skill_path"]),
                initial_skill_path=self.initial_skill_path,
            )
            requests.append(prepare_v16_diagnosis(
                view,
                parent_text,
                [load(Path(row["raw_path"])) for row in rows],
                [row["evaluation"] for row in rows],
            ))

        raw_calls: dict[str, list[str]] = {"diagnosis": [], "editor": []}

        def diagnosis_transport(system: str, user: str, response_format: dict[str, Any]) -> str:
            raw = self._learner_transport(system, user, response_format)
            raw_calls["diagnosis"].append(raw)
            write(RUN / "step1/learner_raw_calls.json", raw_calls)
            return raw

        def editor_transport(system: str, user: str, response_format: dict[str, Any]) -> str:
            raw = self._learner_transport(system, user, response_format)
            raw_calls["editor"].append(raw)
            write(RUN / "step1/learner_raw_calls.json", raw_calls)
            return raw

        result = propose_from_experience(
            tuple(requests),
            diagnosis_transport=diagnosis_transport,
            editor_transport=editor_transport,
        )
        summary = {
            "status": result["status"],
            "tasks_diagnosed": len(requests),
            "decisions": result["decisions"],
        }
        write(RUN / "step1/diagnosis_proposal_summary.json", summary)
        if result["candidate"] is None:
            return None, summary
        candidate = unpack(result["candidate"], "LEARNER_INFERRED_SKILL")
        candidate_path = RUN / "step1/candidate_skill.md"
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(candidate["candidate_skill"], encoding="utf-8")
        write(RUN / "step1/editor_output.json", {
            "status": result["status"],
            "canonical_edits": candidate["canonical_edits"],
        })
        return {
            "skill_id": "S1_candidate",
            "skill_path": str(candidate_path.resolve()),
        }, summary

    def monitor_analysis(self, comparison: dict[str, Any]) -> dict[str, Any]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        families: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for pair in comparison["matched_pairs"]:
            entry = self.registry.get(pair["task_id"])
            groups[entry.monitor_role or "UNASSIGNED"].append(pair)
            families[entry.family].append(pair)

        def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
            return {
                "matched_rollouts": len(rows),
                "delta_success": sum(row["delta_success"] for row in rows),
                "delta_compliance": sum(row["delta_compliance"] for row in rows),
                "repairs": sum(row["parent_state"] != "CS" and row["candidate_state"] == "CS" for row in rows),
                "regressions": sum(row["parent_state"] == "CS" and row["candidate_state"] != "CS" for row in rows),
            }

        return {
            "by_monitor_role": {name: summarize(rows) for name, rows in sorted(groups.items())},
            "by_family": {name: summarize(rows) for name, rows in sorted(families.items())},
        }

    def run_baseline(self) -> dict[str, Any]:
        self._require_preflight()
        monitor_ids = self.registry.task_ids("monitor")
        parent_monitor = self.run_rollouts(
            monitor_ids,
            skill=self.parent,
            phase_dir=BASELINE_DIR,
        )
        result = {
            "campaign_id": self.config["campaign_id"],
            "stage": "S0_MONITOR_BASELINE",
            "status": "COMPLETED",
            "skill": self.parent,
            "metrics": metrics(parent_monitor),
            "next_command": "evolve",
        }
        write(BASELINE_STAGE, result)
        return result

    def run_evolution(self) -> dict[str, Any]:
        self._require_preflight()
        self._load_completed_rollouts(
            BASELINE_DIR,
            self.registry.task_ids("monitor"),
            self.parent["skill_id"],
        )
        if EVOLUTION_STAGE.is_file():
            completed = load(EVOLUTION_STAGE)
            if completed.get("status") == "COMPLETED":
                self._load_completed_rollouts(
                    EVOLUTION_DIR,
                    self.registry.task_ids("train"),
                    self.parent["skill_id"],
                )
                candidate = completed.get("candidate")
                if candidate is not None and not Path(candidate["skill_path"]).is_file():
                    raise RuntimeError("Completed Evolution stage is missing Candidate Skill")
                return completed

        evolution_ids = self.registry.task_ids("train")
        evolution_rows = self.run_rollouts(
            evolution_ids,
            skill=self.parent,
            phase_dir=EVOLUTION_DIR,
        )
        candidate, diagnosis = self.diagnose_and_edit(evolution_rows, self.parent)
        result = {
            "campaign_id": self.config["campaign_id"],
            "stage": "S0_EVOLUTION_AND_CANDIDATE",
            "status": "COMPLETED",
            "parent": self.parent,
            "evolution_parent": metrics(evolution_rows),
            "diagnosis": diagnosis,
            "candidate": candidate,
            "next_command": "candidate-monitor",
        }
        write(EVOLUTION_STAGE, result)
        return result

    def run_candidate_monitor_and_gate(self) -> dict[str, Any]:
        self._require_preflight()
        monitor_ids = self.registry.task_ids("monitor")
        evolution_ids = self.registry.task_ids("train")
        parent_monitor = self._load_completed_rollouts(
            BASELINE_DIR,
            monitor_ids,
            self.parent["skill_id"],
        )
        self._load_completed_rollouts(
            EVOLUTION_DIR,
            evolution_ids,
            self.parent["skill_id"],
        )
        if not EVOLUTION_STAGE.is_file():
            raise RuntimeError("Evolution and Candidate stage has not completed")
        evolution_stage = load(EVOLUTION_STAGE)
        if evolution_stage.get("status") != "COMPLETED":
            raise RuntimeError("Evolution and Candidate stage has not completed")
        candidate = evolution_stage.get("candidate")
        if candidate is None:
            gate = {
                "gate_id": "GSE_V16_UNIFIED_MONITOR_GATE",
                "decision": "RETAIN",
                "reason": "NO_UPDATE_ELIGIBLE_DIAGNOSIS",
            }
            comparison = None
            final_skill = self.parent
        else:
            candidate_monitor = self.run_rollouts(
                monitor_ids,
                skill=candidate,
                phase_dir=CANDIDATE_MONITOR_DIR,
            )
            comparison = compare_matched_rollouts(parent_monitor, candidate_monitor)
            comparison["analysis"] = self.monitor_analysis(comparison)
            gate_config = self.config["gate"]
            gate = unified_gate(
                comparison,
                replicates=gate_config["bootstrap_replicates"],
                bootstrap_seed=gate_config["bootstrap_seed"],
                epsilon_pair_count=gate_config["epsilon_pair_count"],
                threshold=gate_config["positive_probability_threshold"],
            )
            write(RUN / "step1/monitor_comparison.json", comparison)
            write(RUN / "step1/gate_result.json", gate)
            final_skill = candidate if gate["decision"] == "ACCEPT" else self.parent

        state = {
            "campaign_id": self.config["campaign_id"],
            "status": "COMPLETED",
            "protocol": "ONE_STEP",
            "parent": self.parent,
            "evolution_parent": evolution_stage["evolution_parent"],
            "monitor_parent": metrics(parent_monitor),
            "diagnosis": evolution_stage["diagnosis"],
            "candidate": candidate,
            "monitor_comparison": comparison,
            "gate": gate,
            "final_skill": final_skill,
        }
        write(RUN / "final/final_summary.json", state)
        final_path = RUN / "final/final_skill.md"
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_text(Path(final_skill["skill_path"]).read_text(encoding="utf-8"), encoding="utf-8")
        return state

    def run(self) -> dict[str, Any]:
        self.run_baseline()
        self.run_evolution()
        return self.run_candidate_monitor_and_gate()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("preflight", "baseline", "evolve", "candidate-monitor", "run"),
    )
    args = parser.parse_args()
    load_dotenv(REPO / ".env", override=True)
    if args.command == "preflight":
        result = run_preflight()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    campaign = OneStepCampaign()
    if args.command == "baseline":
        state = campaign.run_baseline()
    elif args.command == "evolve":
        state = campaign.run_evolution()
    elif args.command == "candidate-monitor":
        state = campaign.run_candidate_monitor_and_gate()
    else:
        state = campaign.run()
    print(json.dumps({
        "status": state["status"],
        "stage": state.get("stage", "FINAL"),
        "gate": state.get("gate"),
        "candidate": state.get("candidate"),
        "final_skill": state.get("final_skill"),
        "next_command": state.get("next_command"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
