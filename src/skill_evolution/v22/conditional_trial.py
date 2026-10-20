"""Predeclared fresh-Train construction and frozen Selection evaluation.

No adoption, semantic retries, held-out feedback learning, or Test access. The two
construction arms share evidence, a serious draft, Memory, and a faithful Editor.
"""

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess

import requests
from dotenv import load_dotenv

from src.adapters.alfworld.run_task import REPO_ROOT, SPLIT_ROOT
from src.adapters.alfworld.run_task_skill import timestamp
from src.adapters.alfworld.skill_runtime import digest, load_skill, object_digest, write_record
from src.adapters.alfworld.verify_skill_run import compare_records, require, verify_record
from .compact_cycle import diagnosis_input, fusion_input, make_diff, read
from .compact_learning import build_learning_payload
from .compact_update import apply_fusion, validate_diagnosis
from .diagnosis_editor import parse_json_response
from .editor_watch_reconciliation import normalize_inherited_watch
from .evidence import verify_sources
from .model_call import semantic_call
from .run_round import cost_summary
from .verify_round import verify_call


ARMS = ("direct", "conditioned")
STAGES = ("diagnosis", "direct_proposal", "direct_editor", "conditioned_proposal", "conditioned_editor")


def bindings(paths):
    return [{"path": str(Path(p).resolve()), "sha256": digest(Path(p).read_bytes())}
            for p in sorted(set(Path(p) for p in paths))]


def validate_plan(plan):
    require(plan["schema_version"] == "v22.conditional_trial.v1", "Unknown trial protocol.")
    require(plan["actor_model"] == "deepseek-v4-flash" and plan["evolution_model"] == "deepseek-v4-pro",
            "Model roles differ from protocol.")
    for field, split in (("train_task_ids", "train"), ("selection_task_ids", "val")):
        ids = plan[field]
        available = {row["id"] for row in read(SPLIT_ROOT / split / "items.json")}
        require(ids and len(ids) == len(set(ids)) and set(ids) <= available, "Unknown or duplicate tasks.")
    require(not {"train:0000", "train:0012"} & set(plan["train_task_ids"]), "Old development tasks are excluded.")
    require(plan["semantic_calls_max"] == 5 and plan["semantic_retries"] == 0
            and plan["episode_retries"] == 0 and plan["adoption"] == "staging_only", "Unexpected trial scope.")
    require(type(plan["max_steps_per_episode"]) is int and 1 <= plan["max_steps_per_episode"] <= 50
            and type(plan["actor_workers"]) is int and 1 <= plan["actor_workers"] <= 3, "Invalid bounded actor budget.")
    require(plan["evaluation_repeats"] == 1 and plan["branch_order"] == list(ARMS), "Unexpected repetitions/order.")
    require(plan["profile"] == "v22.conditional_update.v1" and plan["transport_attempts_per_request_max"] == 6
            and plan["request_parameters"] == {"temperature": 1.0, "max_tokens": 16384,
                "reasoning_effort": "medium", "thinking": {"type": "enabled"}, "stream": False},
            "Declared client/profile parameters differ from the fixed implementation.")
    require(plan["environment_episodes_max"] == len(plan["train_task_ids"]) + 3 * len(plan["selection_task_ids"]),
            "Episode budget mismatch.")


def initialize(plan_path, output_dir):
    plan_path, root = Path(plan_path).resolve(), Path(output_dir).resolve()
    plan = read(plan_path)
    validate_plan(plan)
    memory_path = REPO_ROOT / plan["memory_source"]
    memory = read(memory_path)
    require(digest(memory_path.read_bytes()) == plan["memory_sha256"], "Memory source changed.")
    sources = [plan_path, memory_path, SPLIT_ROOT / "train/items.json", SPLIT_ROOT / "val/items.json"]
    code = [p for directory in (REPO_ROOT / "src/skill_evolution/v22", REPO_ROOT / "src/adapters/alfworld")
            for p in directory.glob("*.py")]
    root.mkdir(parents=True, exist_ok=False)
    for directory in ("inputs", "raw_outputs", "outputs", "calls", "candidates"):
        (root / directory).mkdir()
    write_record(root / "plan.json", plan)
    write_record(root / "memory.json", memory)
    write_record(root / "manifest.json", {"created_at": timestamp(), "plan_path": str(plan_path), "sources": bindings(sources),
        "implementation": bindings(code), "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "working_tree": "Pre-existing uncommitted V22 work; source hashes, not HEAD alone, identify implementation."})
    report = {"status": "initialized", "started_at": timestamp(), "stages": [], "branches": {},
              "adoption": "staging_only", "train": [], "selection": []}
    write_record(root / "report.json", report)
    return report


def check_sources(root):
    manifest = read(root / "manifest.json")
    verify_sources(manifest["sources"] + manifest["implementation"])
    plan = read(root / "plan.json")
    require(plan == read(manifest["plan_path"]), "Trial plan differs from declaration.")
    require(read(root / "memory.json") == read(REPO_ROOT / plan["memory_source"]), "Copied Memory changed.")
    validate_plan(plan)
    return plan


def save(root, report):
    records = [read(p) for p in sorted((root / "runs").glob("**/trajectory.json"))]
    report["cost"] = cost_summary(records, [], root)
    report["cost"]["scope"] = "This operation only: all new Train/Selection requests and semantic calls, including failures. Reused historical evidence is not charged again. Unknown usage is not zero."
    write_record(root / "report.json", report)


def collect(root, env_file, execute_batch=None):
    if execute_batch is None:
        from .bounded_evaluation import execute_batch
    root = Path(root).resolve()
    plan, report = check_sources(root), read(root / "report.json")
    require(report["status"] == "initialized", "Train collection is single-use.")
    report.update(status="collecting_train", train_started_at=timestamp())
    save(root, report)
    jobs = [{"key": task.replace(":", "_"), "task_id": task, "split": "train", "purpose": "learning",
             "skill_path": None} for task in plan["train_task_ids"]]
    report["train"] = execute_batch(jobs, root / "runs/train", plan, env_file)
    paths = [row.get("trajectory") for row in report["train"]]
    records = [read(path) for path in paths if path]
    complete = len(records) == len(jobs) and all(verify_record(r)["episode_complete"] for r in records)
    report.update(status="train_ready" if complete else "train_incomplete", train_finished_at=timestamp())
    write_record(root / "train_sources.json", bindings([p for p in paths if p]))
    save(root, report)
    return report


def current_input(root):
    plan = read(root / "plan.json")
    verify_sources(read(root / "train_sources.json"))
    rows = read(root / "report.json")["train"]
    records = [read(row["trajectory"]) for row in rows]
    require([r["task"]["id"] for r in records] == plan["train_task_ids"], "Train order differs from plan.")
    for record in records:
        audit = verify_record(record)
        require(audit["episode_complete"] and record["model"] == plan["actor_model"]
                and record["protocol"]["max_steps"] == plan["max_steps_per_episode"]
                and record["skill"] == load_skill(), "Current Train is incomplete or protocol differs.")
    blank = {"intent": "No update yet", "requirements": [], "watch": [], "open": []}
    initial = build_learning_payload(load_skill(), load_skill(), "", blank, records, [])
    return diagnosis_input(initial, records)


def messages_for(stage, payload):
    from .conditional_update import diagnosis_messages_conditional, proposal_messages, realization_messages
    if stage == "diagnosis":
        return diagnosis_messages_conditional(payload)
    if stage.endswith("_proposal"):
        return proposal_messages(payload, stage.removesuffix("_proposal"))
    require(stage.endswith("_editor"), "Unknown construction stage.")
    return realization_messages(payload)


def invoke(root, report, plan, stage, payload, generate):
    require(stage in STAGES and stage not in report["stages"] and len(report["stages"]) < 5, "Duplicate/excess semantic call.")
    check_sources(root)
    report["stages"].append(stage)
    report["active_stage"] = stage
    save(root, report)
    write_record(root / "inputs" / f"{stage}.json", payload)
    messages = messages_for(stage, payload)
    raw = generate(stage, messages, root / "calls" / f"{stage}.json")
    value = parse_json_response(raw)
    write_record(root / "raw_outputs" / f"{stage}.json", value)
    verify_call(root / "calls" / f"{stage}.json", stage, plan["evolution_model"], messages, value)
    call = read(root / "calls" / f"{stage}.json")
    require(call["steps"][0]["model_response"]["response_model"] == plan["evolution_model"], "Response model mismatch.")
    return value


def construct(root, generate):
    root = Path(root).resolve()
    plan, report = check_sources(root), read(root / "report.json")
    require(report["status"] == "train_ready", "Construction requires completed fresh Train and is single-use.")
    report["status"] = "constructing"
    current, memory = current_input(root), read(root / "memory.json")
    write_record(root / "current.json", current)
    try:
        raw = invoke(root, report, plan, "diagnosis", current, generate)
        diagnosis = validate_diagnosis(raw, current)
        write_record(root / "outputs/diagnosis.json", diagnosis)
        if diagnosis["decision"] != "revise":
            report.update(status=diagnosis["decision"], stop_reason=diagnosis["reason"])
            return report
        initial = diagnosis["plan"]
        write_record(root / "initial_plan.json", initial)
        for arm in ARMS:
            branch = report["branches"][arm] = {"status": "constructing"}
            try:
                payload = fusion_input(current, initial, memory)
                raw = invoke(root, report, plan, arm + "_proposal", payload, generate)
                effective = apply_fusion(raw, payload)
                write_record(root / "outputs" / f"{arm}_proposal.json", raw)
                write_record(root / f"{arm}_plan.json", effective)
                branch.update(requirements_changed=effective["requirements"] != initial["requirements"],
                              history_cited=sorted({ref for change in raw["changes"] for ref in change["basis"]
                                                    if ref in {m["id"] for m in memory}}))
                if raw["decision"] != "ready" or effective["open"]:
                    branch.update(status="needs_revision", reason=raw["reason"])
                    continue
                # Both realization arms receive the same complete Memory information.
                editor_payload = fusion_input(current, effective, memory)
                raw_editor = invoke(root, report, plan, arm + "_editor", editor_payload, generate)
                editor = normalize_inherited_watch(raw_editor, editor_payload)
                write_record(root / "outputs" / f"{arm}_editor.json", editor)
                branch["removed_exact_watch_echoes"] = len(raw_editor["watch"]) - len(editor["watch"])
                if editor["decision"] != "candidate":
                    branch.update(status=editor["decision"], reason=editor["reason"])
                    continue
                directory = root / "candidates" / arm
                directory.mkdir()
                skill_path = directory / "SKILL.md"
                skill_path.write_text(editor["candidate_text"], encoding="utf-8")
                skill = load_skill(skill_path)
                (directory / "actual.diff").write_text(make_diff(load_skill(), skill), encoding="utf-8")
                watch = deepcopy(effective["watch"]) + deepcopy(editor["watch"])
                write_record(directory / "observation_plan.json", {"watch": watch, "origin": "before_selection"})
                branch.update(status="candidate", skill_file=str(skill_path.relative_to(root)),
                              skill_id=skill["skill_id"])
            except Exception as exc:
                branch.update(status="error", error_type=type(exc).__name__)
                if isinstance(exc, ValueError):
                    branch["validation_error"] = str(exc)
            finally:
                save(root, report)
        freeze(root, report)
    except Exception as exc:
        report.update(status="construction_error", error_type=type(exc).__name__)
        if isinstance(exc, ValueError):
            report["validation_error"] = str(exc)
    finally:
        report.update(active_stage=None, construction_finished_at=timestamp())
        save(root, report)
    return report


def freeze(root, report):
    require(not (root / "freeze.json").exists(), "Freeze already exists.")
    check_sources(root)
    arms = {"parent": {"skill_file": None, "skill_id": "none"}}
    for arm, branch in report["branches"].items():
        if branch["status"] == "candidate":
            arms[arm] = {key: branch[key] for key in ("skill_file", "skill_id")}
        elif branch["status"] == "no_change":
            arms[arm] = {"skill_file": None, "skill_id": "none"}
    paths = [p for p in root.rglob("*") if p.is_file() and p.name != "report.json"]
    write_record(root / "freeze.json", {"frozen_at": timestamp(), "arms": arms, "files": bindings(paths),
        "evaluation": "Fixed Selection only; no construction calls or feedback learning after freeze.",
        "semantic_preservation": "not_certified_by_structural_validation"})
    report.update(status="frozen", freeze_sha256=digest((root / "freeze.json").read_bytes()))


def check_freeze(root):
    plan = check_sources(root)
    frozen, report = read(root / "freeze.json"), read(root / "report.json")
    require(digest((root / "freeze.json").read_bytes()) == report["freeze_sha256"], "Freeze record changed.")
    verify_sources(frozen["files"])
    require(set(frozen["arms"]) <= {"parent", *ARMS} and "parent" in frozen["arms"], "Invalid evaluation arms.")
    for arm in frozen["arms"].values():
        skill = load_skill(root / arm["skill_file"] if arm["skill_file"] else None)
        require(skill["skill_id"] == arm["skill_id"], "Frozen Skill differs.")
    return plan, frozen


def evaluate(root, env_file, execute_batch=None):
    from .bounded_evaluation import selection_jobs
    if execute_batch is None:
        from .bounded_evaluation import execute_batch
    root = Path(root).resolve()
    plan, frozen = check_freeze(root)
    report = read(root / "report.json")
    require(report["status"] == "frozen", "Selection is single-use and requires frozen candidates.")
    jobs = selection_jobs(plan, frozen, root)
    write_record(root / "selection_schedule.json", jobs)
    report.update(status="evaluating", selection_started_at=timestamp())
    save(root, report)
    report["selection"] = execute_batch(jobs, root / "runs/selection", plan, env_file)
    check_freeze(root)
    report.update(status="evaluated", selection_finished_at=timestamp())
    save(root, report)
    write_record(root / "evaluation_summary.json", evaluation_summary(root))
    return report


def evaluation_summary(root):
    report, frozen = read(root / "report.json"), read(root / "freeze.json")
    rows, by_task, totals = [], {}, {}
    for entry in report["selection"]:
        # The explicit schedule, rather than naming conventions, identifies each arm.
        job = next(j for j in read(root / "selection_schedule.json") if j["key"] == entry["key"])
        arm = job["arm"]
        row = {"task_id": job["task_id"], "arm": arm, "trajectory": entry.get("trajectory"),
               "success": None, "steps": None, "invalid_actions": None, "status": entry.get("status")}
        if entry.get("trajectory"):
            record = read(entry["trajectory"])
            audit = verify_record(record)
            row.update(success=audit["native_success"], steps=audit["steps_executed"], status=record["status"],
                       invalid_actions=sum(e.get("phase") == "executed" and e.get("action_in_admissible_commands") is False
                                           for e in record["steps"]))
            by_task.setdefault(row["task_id"], {})[arm] = record
        rows.append(row)
    comparisons = []
    for task, records in by_task.items():
        for arm in ARMS:
            if arm in records and "parent" in records:
                comparisons.append({"task_id": task, "left": "parent", "right": arm,
                                    **compare_records(records["parent"], records[arm])})
        if all(a in records for a in ARMS):
            comparisons.append({"task_id": task, "left": "direct", "right": "conditioned",
                                **compare_records(records["direct"], records["conditioned"])})
    for arm in frozen["arms"]:
        subset = [r for r in rows if r["arm"] == arm]
        totals[arm] = {"episodes": len(subset), "successes": sum(r["success"] is True for r in subset),
                       "failures": sum(r["success"] is False for r in subset),
                       "unknown": sum(r["success"] is None for r in subset),
                       "executed_steps": sum(r["steps"] or 0 for r in subset),
                       "invalid_actions": sum(r["invalid_actions"] or 0 for r in subset)}
    return {"rows": rows, "totals": totals, "comparisons": comparisons,
            "complete_three_arm_comparison": set(frozen["arms"]) == {"parent", *ARMS}
                and len(rows) == 3 * len(read(root / "plan.json")["selection_task_ids"])
                and all(r["success"] is not None for r in rows),
            "interpretation": "One stochastic sample per task/arm, metadata-stratified Selection subset; exploratory only. Step totals mix successes and failures and are not an efficiency gain estimate. No isolated edit causality or final Test result."}


def verify(root):
    root = Path(root).resolve()
    plan, report = check_sources(root), read(root / "report.json")
    stages = report["stages"]
    require(len(stages) == len(set(stages)) and set(stages) <= set(STAGES), "Unknown/repeated semantic stages.")
    require({p.stem for p in (root / "calls").glob("*.json")} <= set(stages), "Undeclared semantic call.")
    if (root / "current.json").exists():
        current, memory = current_input(root), read(root / "memory.json")
        require(read(root / "current.json") == current, "Current input differs from new Train evidence.")
        initial = read(root / "initial_plan.json") if (root / "initial_plan.json").exists() else None
        for stage in stages:
            if stage == "diagnosis":
                expected = current
            elif stage.endswith("_proposal"):
                expected = fusion_input(current, initial, memory)
            else:
                arm = stage.removesuffix("_editor")
                expected = fusion_input(current, read(root / f"{arm}_plan.json"), memory)
            require(read(root / "inputs" / f"{stage}.json") == expected, "Semantic input routing mismatch.")
            raw_path = root / "raw_outputs" / f"{stage}.json"
            raw = read(raw_path) if raw_path.exists() else None
            call_path = root / "calls" / f"{stage}.json"
            if call_path.exists():
                verify_call(call_path, stage, plan["evolution_model"], messages_for(stage, expected), raw)
            output_path = root / "outputs" / f"{stage}.json"
            if output_path.exists():
                saved = read(output_path)
                if stage == "diagnosis":
                    require(saved == validate_diagnosis(raw, expected), "Diagnosis output changed.")
                    if initial is not None:
                        require(saved["plan"] == initial, "Initial Plan differs from Diagnosis.")
                elif stage.endswith("_proposal"):
                    arm = stage.removesuffix("_proposal")
                    require(saved == raw and apply_fusion(raw, expected) == read(root / f"{arm}_plan.json"),
                            "Requirement construction differs.")
                else:
                    require(saved == normalize_inherited_watch(raw, expected), "Editor normalization differs.")
                    arm = stage.removesuffix("_editor")
                    if saved["decision"] == "candidate":
                        skill = load_skill(root / f"candidates/{arm}/SKILL.md")
                        require(skill["text"] == saved["candidate_text"], "Skill differs from Editor.")
    if (root / "freeze.json").exists():
        _, frozen = check_freeze(root)
        from .bounded_evaluation import selection_jobs
        jobs = selection_jobs(plan, frozen, root)
        if (root / "selection_schedule.json").exists():
            require(read(root / "selection_schedule.json") == jobs, "Selection schedule differs from declaration.")
        require(len(report["selection"]) in (0, len(jobs)), "Missing or extra Selection rows.")
        if report["selection"]:
            require([row["key"] for row in report["selection"]] == [job["key"] for job in jobs],
                    "Selection task/arm order differs from declaration.")
        for row in report["selection"]:
            if row.get("trajectory"):
                job = next(job for job in jobs if job["key"] == row["key"])
                record = read(row["trajectory"])
                verify_record(record)
                require(record["split"] == "val" and record["purpose"] == "selection"
                        and record["task"]["id"] == job["task_id"]
                        and record["skill"]["skill_id"] == frozen["arms"][job["arm"]]["skill_id"]
                        and record["model"] == plan["actor_model"]
                        and record["protocol"]["max_steps"] == plan["max_steps_per_episode"]
                        and record["started_at"] >= frozen["frozen_at"], "Evaluation boundary/freeze violation.")
        if (root / "evaluation_summary.json").exists():
            require(read(root / "evaluation_summary.json") == evaluation_summary(root), "Summary differs from raw executions.")
    records = [read(p) for p in sorted((root / "runs").glob("**/trajectory.json"))]
    require(len(records) <= plan["environment_episodes_max"], "Episode budget exceeded.")
    actual_cost = cost_summary(records, [], root)
    require(all(report["cost"][k] == v for k, v in actual_cost.items() if k != "scope"), "Cost accounting mismatch.")
    return {"status": report["status"], "checks": "source, input, call, output, freeze, trajectory and cost consistency",
            "semantic_preservation": "not_certified", "adoption": "staging_only", "cost": report["cost"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "collect", "construct", "evaluate", "verify"])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    args = parser.parse_args(argv)
    if args.command == "init":
        require(args.plan is not None, "Initialization needs a protocol file.")
        result = initialize(args.plan, args.run_dir)
    elif args.command == "collect":
        result = collect(args.run_dir, args.env_file)
    elif args.command == "evaluate":
        result = evaluate(args.run_dir, args.env_file)
    elif args.command == "verify":
        result = verify(args.run_dir)
    else:
        load_dotenv(args.env_file, override=False)
        base, key = os.environ.get("OPENAI_BASE_URL", "").rstrip("/"), os.environ.get("OPENAI_API_KEY")
        require(bool(base and key), "Model connection configuration is missing.")
        with requests.Session() as session:
            if ".intra." in base:
                session.trust_env = False
            plan = read(args.run_dir / "plan.json")
            def generate(stage, messages, path):
                return semantic_call(stage, messages, session=session, endpoint=base + "/chat/completions",
                                     key=key, model=plan["evolution_model"], output=path)
            result = construct(args.run_dir, generate)
    print(json.dumps({k: result[k] for k in ("status", "cost", "branches") if k in result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
