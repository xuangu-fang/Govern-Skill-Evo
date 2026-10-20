"""Bounded operation 07: real Train response learning, then one shared-memory update.

This experiment wrapper reuses V22 contracts; it does not introduce a new learner.
Run with PYTHONPATH=. and the ALFWorld environment. Each stage refuses repetition.
"""

import argparse
from copy import deepcopy
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.adapters.alfworld.run_task import REPO_ROOT
from src.adapters.alfworld.skill_runtime import digest, load_skill, write_record
from src.adapters.alfworld.verify_skill_run import require, verify_record
from src.skill_evolution.v22.bounded_evaluation import execute_batch
from src.skill_evolution.v22.compact_cycle import diagnosis_input, make_diff, read
from src.skill_evolution.v22.compact_learning import build_learning_payload
from src.skill_evolution.v22.conditional_trial import bindings
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v22.effective_memory import (
    apply_effective_memory, learning_messages_effective, validate_effective_learning,
)
from src.skill_evolution.v22.evidence import verify_sources
from src.skill_evolution.v22.model_call import semantic_call
from src.skill_evolution.v22.verify_round import verify_call


ROOT = REPO_ROOT / "artifacts/methods/v22/train_response_20261015"
PLAN = ROOT / "plan.json"


def check_inputs():
    verify_sources(read(ROOT / "source_manifest.json"))
    verify_sources(read(ROOT / "continuation_implementation.json"))
    require(read(PLAN) == read(Path(__file__).with_name("plan.json")), "Copied plan differs from declaration.")


def generate(stage, messages, output):
    check_inputs()
    load_dotenv(REPO_ROOT / ".env", override=False)
    base = os.environ["OPENAI_BASE_URL"].rstrip("/")
    with requests.Session() as session:
        if ".intra." in base:
            session.trust_env = False
        return semantic_call(stage, messages, session=session, endpoint=base + "/chat/completions",
                             key=os.environ["OPENAI_API_KEY"], model=read(PLAN)["evolution_model"], output=output)


def learn():
    plan = read(PLAN)
    verify_sources(read(ROOT / "source_manifest.json"))
    directory = ROOT / "learning"
    directory.mkdir(exist_ok=False)
    for name in ("inputs", "raw_outputs", "outputs", "calls"):
        (directory / name).mkdir()
    parents = [read(p) for p in plan["parent_trajectories"]]
    rows = read(ROOT / "original_replay.json")
    require(len(rows) == 4, "All original Replay attempts must be accounted for.")
    source_paths = [PLAN, ROOT / "source_manifest.json", ROOT / "original_replay.json"]
    source_paths.extend(row["trajectory"] for row in rows if row.get("trajectory"))
    write_record(directory / "sources.json", bindings(source_paths))
    result, merged = {}, []
    for arm in plan["learning"]["order"]:
        entry = result[arm] = {"status": "preparing", "context_id": plan["learning"]["context_ids"][arm]}
        write_record(directory / "report.json", result)
        try:
            source = plan["arms"][arm]
            skill = load_skill(source["skill_path"])
            require(digest(Path(source["skill_path"]).read_bytes()) == source["skill_sha256"], "Candidate changed.")
            records = [read(row["trajectory"]) for row in rows if row["arm"] == arm and row.get("trajectory")]
            require(any(verify_record(r)["episode_complete"] for r in records), "No complete Candidate behavior to learn.")
            execution_plan = deepcopy(read(source["plan_path"]))
            execution_plan["watch"] = read(source["observation_plan_path"])["watch"]
            payload = build_learning_payload(load_skill(), skill, make_diff(load_skill(), skill), execution_plan,
                parents, records, memory=[], origin="frozen_06_requirements_and_watch_before_new_train_replay")
            entry.update(candidate_skill_id=skill["skill_id"], trajectories=[row["trajectory"] for row in rows
                         if row["arm"] == arm and row.get("trajectory")])
            write_record(directory / "inputs" / f"{arm}.json", payload)
            messages = learning_messages_effective(payload)
            stage = f"learn_{arm}"
            raw = generate(stage, messages, directory / "calls" / f"{stage}.json")
            value = parse_json_response(raw)
            write_record(directory / "raw_outputs" / f"{arm}.json", value)
            verify_call(directory / "calls" / f"{stage}.json", stage, plan["evolution_model"], messages, value)
            require(read(directory / "calls" / f"{stage}.json")["steps"][0]["model_response"]["response_model"]
                    == plan["evolution_model"], "Unexpected response model.")
            validate_effective_learning(value, payload)
            effects = apply_effective_memory([], value, entry["context_id"], payload)
            write_record(directory / "outputs" / f"{arm}.json", value)
            write_record(directory / f"memory_{arm}.json", effects)
            merged.extend(effects)
            entry.update(status="learned", effect_ids=[e["id"] for e in effects])
        except Exception as exc:
            entry.update(status="error", error_type=type(exc).__name__)
            if isinstance(exc, ValueError):
                entry["validation_error"] = str(exc)
        write_record(directory / "report.json", result)
    require(len({e["id"] for e in merged}) == len(merged), "Effect identities collide.")
    write_record(directory / "memory.json", merged)
    verify_sources(read(directory / "sources.json"))
    verify_sources(read(ROOT / "source_manifest.json"))
    files = [p for p in directory.rglob("*") if p.is_file()]
    write_record(directory / "freeze.json", {"files": bindings(files), "effect_count": len(merged),
        "shared_parents_are_not_independent_replications": True,
        "old_memory": plan["old_memory_archive"], "candidate_provenance": result})
    print(result, flush=True)


def screen():
    plan = read(PLAN)
    verify_sources(read(ROOT / "source_manifest.json"))
    verify_sources(read(ROOT / "learning/freeze.json")["files"])
    require(bool(read(ROOT / "learning/memory.json")), "No learned response effects; do not advance.")
    jobs = [{"key": task.replace(":", "_"), "task_id": task, "split": "train", "purpose": "learning",
             "skill_path": None} for task in plan["screen_task_ids"]]
    rows = execute_batch(jobs, ROOT / "runs/screen", plan, REPO_ROOT / ".env")
    write_record(ROOT / "screen.json", rows)
    failures = [row for row in rows if row.get("audit") and row["audit"]["episode_complete"] and row["success"] is False]
    write_record(ROOT / "selected_failures.json", failures)
    write_record(ROOT / "screen_sources.json", bindings([ROOT / "screen.json", ROOT / "selected_failures.json"] +
                                                       [r["trajectory"] for r in rows if r.get("trajectory")]))
    print([{k: r.get(k) for k in ("task_id", "success", "steps", "status")} for r in rows], flush=True)


def construct():
    from src.skill_evolution.v22.train_response_update import construct as build
    verify_sources(read(ROOT / "source_manifest.json"))
    verify_sources(read(ROOT / "screen_sources.json"))
    verify_sources(read(ROOT / "learning/freeze.json")["files"])
    rows = read(ROOT / "selected_failures.json")
    require(bool(rows), "No complete No Skill failures; stop without replacement.")
    parents = [read(r["trajectory"]) for r in rows]
    blank = {"intent": "No update yet", "requirements": [], "watch": [], "open": []}
    payload = build_learning_payload(load_skill(), load_skill(), "", blank, parents, [])
    current = diagnosis_input(payload, parents)
    memory = read(ROOT / "learning/memory.json")
    report = build(ROOT / "next_update", current, memory, generate, model=read(PLAN)["evolution_model"])
    paths = [p for p in (ROOT / "next_update").rglob("*") if p.is_file()]
    paths.extend((REPO_ROOT / "src/skill_evolution/v22").glob("*.py"))
    paths += [Path(__file__).resolve(), PLAN, ROOT / "screen_sources.json", ROOT / "learning/freeze.json"]
    write_record(ROOT / "next_freeze.json", {"files": bindings(paths), "ready_arms": report["ready_arms"],
        "task_ids": [r["task_id"] for r in rows], "scope": "One Replay per frozen arm on these failed Train; no revisions."})
    print(report, flush=True)


def replay():
    plan, frozen = read(PLAN), read(ROOT / "next_freeze.json")
    verify_sources(frozen["files"])
    verify_sources(read(ROOT / "screen_sources.json"))
    verify_sources(read(ROOT / "learning/freeze.json")["files"])
    jobs = []
    for index, task in enumerate(frozen["task_ids"]):
        order = [arm for arm in ("direct", "conditioned") if arm in frozen["ready_arms"]]
        if index % 2:
            order.reverse()
        for arm in order:
            item = frozen["ready_arms"][arm]
            path = ROOT / "next_update" / item["skill_file"] if item["skill_file"] else None
            require(load_skill(path)["skill_id"] == item["skill_id"], "Frozen Skill identity differs.")
            jobs.append({"key": task.replace(":", "_") + "_" + arm, "arm": arm, "task_id": task,
                         "split": "train", "purpose": "learning", "skill_path": str(path) if path else None})
    require(bool(jobs), "No frozen executable arm; stop without substituting a candidate.")
    rows = execute_batch(jobs, ROOT / "runs/next_replay", plan, REPO_ROOT / ".env")
    write_record(ROOT / "next_replay.json", rows)
    verify_sources(frozen["files"])
    print([{k: r.get(k) for k in ("arm", "task_id", "success", "steps", "status")} for r in rows], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("learn", "screen", "construct", "replay"))
    args = parser.parse_args()
    check_inputs()
    globals()[args.stage]()
