#!/usr/bin/env python3
"""Read-only task/source inventory; never launches ALFWorld or selects a fallback.

Ranking rule is fixed here before inspection of any new task outcome.  The
inventory deliberately produces no executable task_manifest when fewer than
20 previously unexposed tasks exist in the declared 39-item Train edition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
TRAIN = Path("benchmarks/alfworld/editions/skillopt_39_18_134/train/items.json")
SEED = "v22.unified_dsc.v2.train-stream.20261016.seed42"
REQUIRED_TASKS = 20
TASK_REFERENCE = re.compile(r"\btrain[:_](\d{4})\b")
ARTIFACT_ROOTS = {
    "01": ["no_history_20261014"],
    "02": ["behavior_feedback_20261014"],
    "03": ["compact_cycle_20261014"],
    "04": ["fixed_consumption_20261014"],
    "05": ["conditional_trial_20261014"],
    "06": ["failure_trial_20261015"],
    "07": ["train_response_20261015"],
    "08": ["08_grouped_continual_live_20261015", "08_grouped_continual_recovered_20261015", "08_grouped_continual_fusion_resumed_20261015"],
}
REUSE_INPUTS = {
    "02": ["behavior_feedback_20261014/replay/input.json", "behavior_feedback_20261014/replay_recovery/input.json"],
    "03": ["compact_cycle_20261014/run/inputs/learn_initial.json", "compact_cycle_20261014/recovery/inputs/diagnosis.json"],
    "04": ["fixed_consumption_20261014/recovery/inputs/memory.json", "fixed_consumption_20261014/recovery/inputs/current_fusion.json"],
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path):
    return json.loads(path.read_text())


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def rank(task: dict) -> str:
    # No task family, prior outcome, task text, hidden game state, or repair
    # potential participates in the ranking.
    return digest(f"{SEED}\n{task['id']}\n{task['gamefile']}\n".encode())


def inventory(data_root: Path) -> dict:
    tasks = read(ROOT / TRAIN)
    task_ids = {t["id"] for t in tasks}
    assert len(task_ids) == len(tasks) == 39
    sources = []
    missing_sources = []

    def add(path: Path, experiment: str, kind: str, ids=None) -> None:
        if not path.is_file():
            missing_sources.append(str(path.relative_to(ROOT)))
            return
        raw = path.read_bytes()
        found = ids if ids is not None else {"train:" + n for n in TASK_REFERENCE.findall(raw.decode())}
        found = sorted(set(found) & task_ids)
        sources.append({"path": str(path.relative_to(ROOT)), "sha256": digest(raw),
                        "experiment": experiment, "kind": kind, "task_ids": found})

    for experiment, names in ARTIFACT_ROOTS.items():
        for name in names:
            folder = ROOT / "artifacts/methods/v22" / name
            if not folder.is_dir():
                missing_sources.append(str(folder.relative_to(ROOT)))
            for path in sorted(folder.rglob("trajectory.json")):
                identity = read(path).get("task", {}).get("id")
                if identity in task_ids:
                    add(path, experiment, "real_execution_archive", [identity])
        for folder in sorted((ROOT / "experiments/methods/v22").glob(experiment + "_*")):
            for path in sorted((folder / "config").glob("*.json")):
                add(path, experiment, "declared_or_historical_identity_reference")
        for relative in REUSE_INPUTS.get(experiment, []):
            add(ROOT / "artifacts/methods/v22" / relative, experiment, "reused_real_input")

    # Operation 05/07 explicitly identifies six preceding Train contacts.  Keep
    # their actual execution evidence separate from the numbered V22 episodes.
    upstream = ROOT / "artifacts/benchmarks/alfworld/upstream_noskill_train_check_20261014"
    for path in sorted(upstream.rglob("trajectory.json")):
        identity = read(path).get("task", {}).get("id")
        if identity in task_ids:
            add(path, "prior_train_referenced_by_05_07", "real_execution_archive", [identity])

    root09 = ROOT / "artifacts/methods/v22/09_unified_dsc_model_validation_20261015"
    add(root09 / "protocol.json", "09", "semantic_validation_protocol")
    cases09 = []
    for case in read(root09 / "protocol.json")["cases"]:
        kind = "reused_real_input" if case["material"].startswith("archived_real") else "synthetic_not_environment_evidence"
        path = root09 / "cases" / case["id"] / "payload.json"
        add(path, "09", kind)
        cases09.append({"id": case["id"], "material": case["material"],
                        "task_ids": sources[-1]["task_ids"], "new_environment_episodes": 0})

    excluded = set().union(*(set(s["task_ids"]) for s in sources if s["kind"] != "synthetic_not_environment_evidence"))
    real01to08 = set().union(*(set(s["task_ids"]) for s in sources if s["kind"] == "real_execution_archive" and s["experiment"] in ARTIFACT_ROOTS))
    real_with_prior = set().union(*(set(s["task_ids"]) for s in sources if s["kind"] == "real_execution_archive"))
    eligible = sorted((t for t in tasks if t["id"] not in excluded), key=lambda t: (rank(t), t["id"]))
    pool_checks = []
    for task in tasks:
        game = data_root / task["gamefile"]
        trajectory_data = game.with_name("traj_data.json")
        entry = {**task, "game_exists": game.is_file(), "traj_data_exists": trajectory_data.is_file()}
        if game.is_file():
            game_bytes = game.read_bytes()
            game_json = json.loads(game_bytes)
            # Parse only to establish the static game format. Never instantiate
            # TextWorld or consume the walkthrough/solvability for selection.
            entry.update(game_sha256=digest(game_bytes), game_json_parseable=True,
                         pddl_domain_and_problem_present=all(isinstance(game_json.get(k), str) and game_json[k] for k in ("pddl_domain", "pddl_problem")))
        if trajectory_data.is_file():
            traj_bytes = trajectory_data.read_bytes()
            entry.update(traj_data_sha256=digest(traj_bytes),
                         task_type_matches=json.loads(traj_bytes).get("task_type") == task["task_type"])
        pool_checks.append(entry)

    exposure = []
    for task_id in sorted(task_ids):
        refs = [s["path"] for s in sources if task_id in s["task_ids"] and s["kind"] != "synthetic_not_environment_evidence"]
        exposure.append({"id": task_id, "excluded": task_id in excluded,
                         "real_execution_01_08": task_id in real01to08,
                         "real_execution_including_referenced_prior": task_id in real_with_prior,
                         "source_paths": refs})
    return {
        "schema": "v22.stream_task_inventory.v1", "status": "insufficient_unused_train" if len(eligible) < REQUIRED_TASKS else "eligible_pool_ready_no_final_selection",
        "benchmark_train_source": {"path": str(TRAIN), "sha256": digest((ROOT / TRAIN).read_bytes())},
        "selector_source": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).read_bytes())},
        "selection_rule": {"seed": SEED, "rank": "ascending SHA256(UTF8(seed + newline + id + newline + gamefile + newline)); tie break by id",
                           "eligible": "fixed edition Train minus every real execution or declared/reused historical Train identity in sources", "no_outcome_or_family_selection": True,
                           "required_tasks": REQUIRED_TASKS, "rounds_requested": 2, "tasks_per_round_requested": 10,
                           "insufficient_pool_action": "Freeze inventory and ranking only. No fallback, no task_manifest, no final round assignment; await user boundary decision."},
        "counts": {"fixed_train": len(tasks), "real_execution_01_08_unique": len(real01to08), "real_execution_with_referenced_prior_unique": len(real_with_prior),
                   "excluded_unique": len(excluded), "frozen_or_referenced_only_unique": len(excluded - real_with_prior), "eligible_unique": len(eligible), "shortfall": max(0, REQUIRED_TASKS - len(eligible))},
        "excluded_ids": sorted(excluded), "ranked_unused_candidates": [{**t, "rank_sha256": rank(t)} for t in eligible],
        "operation09": {"new_environment_episodes": 0, "cases": cases09},
        "missing_sources": missing_sources, "source_files": sources, "task_exposure": exposure,
        "data_root": str(data_root.resolve()), "static_task_checks": pool_checks,
        "limitations": ["Archive presence is exposure evidence, not a success/failure label.", "Copies across recovery archives are not independent executions; unique task counts are deduplicated.",
                        "No task outcome is used by the selector. No raw Train expansion or Selection/Test task is used.", "Static JSON parsing and file hashes do not prove an environment reset will succeed."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("/Users/didi/.cache/alfworld"))
    parser.add_argument("--check", action="store_true", help="Read-only comparison with frozen inventory; writes nothing")
    args = parser.parse_args()
    result = inventory(args.data_root)
    target = HERE / "task_inventory.json"
    if args.check:
        assert read(target) == result, "Task inventory differs from frozen source/data identities"
    else:
        if target.exists():
            assert read(target) == result, "Refusing to overwrite a differing frozen inventory"
        else:
            write(target, result)
    print(json.dumps({"status": result["status"], "counts": result["counts"], "inventory": str(target), "read_only_check": args.check}, ensure_ascii=False))


if __name__ == "__main__":
    main()
