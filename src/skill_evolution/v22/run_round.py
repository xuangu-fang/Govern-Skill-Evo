"""One no-history Diagnosis -> Editor -> staged Candidate execution round."""

from __future__ import annotations

import argparse
from collections import Counter
import difflib
import json
import os
from pathlib import Path
import subprocess
import sys

import requests
from dotenv import load_dotenv

from src.adapters.alfworld.run_task import REPO_ROOT
from src.adapters.alfworld.run_task_skill import timestamp
from src.adapters.alfworld.skill_runtime import digest, execution_protocol, load_skill, object_digest, write_record
from src.adapters.alfworld.verify_skill_run import compare_records, verify_record
from .diagnosis_editor import (
    diagnosis_messages, editor_messages, parse_json_response, validate_diagnosis, validate_editor,
)
from .evidence import load_prior_parent_attempts, prepare_evidence, verify_sources
from .editor_preservation import EDITOR_SCHEMA_V1
from .model_call import semantic_call
from .observation_plan import observation_plan

DEFAULT_PLAN = REPO_ROOT / "experiments/methods/v22/01_no_history/config/plan.json"


def validate_plan(plan):
    if plan.get("editor_schema", EDITOR_SCHEMA_V1) not in {"v22.editor.v0", EDITOR_SCHEMA_V1}:
        raise ValueError("Unknown Editor protocol in plan.")
    if (plan["parent_skill"] != "none" or plan["split"] != "train" or plan["purpose"] != "learning"
            or plan["fusion"] != "identity" or plan["memory"] != "empty"
            or plan["adoption"] != "staging_only_no_formal_gate"):
        raise ValueError("This runner only implements a no-history Train round with a staged Candidate.")
    tasks = plan["task_ids"]
    if not tasks or len(set(tasks)) != len(tasks) or any(not task.startswith("train:") for task in tasks):
        raise ValueError("Declare distinct Train tasks before running the Parent.")
    if plan["method_calls"] != {"diagnosis": 1, "editor_max": 1} or plan["semantic_retries"] != 0:
        raise ValueError("This minimal path permits one Diagnosis and at most one Editor, without semantic retry.")
    if plan["parent_episodes"] != len(tasks) or plan["candidate_episodes_max"] != len(tasks):
        raise ValueError("Declared episode budget must match the fixed task list.")
    protocol = execution_protocol(plan["max_steps_per_episode"])
    fixed = {"max_tokens_per_request": protocol["max_tokens"],
             "environment_seed": protocol["environment_seed"],
             "temperature_request": protocol["temperature"], "thinking": protocol["thinking"],
             "reasoning_effort": protocol["reasoning_effort"], "transport_attempts_per_request_max": 6}
    if any(plan.get(key) != value for key, value in fixed.items()):
        raise ValueError("Declared request configuration differs from the fixed execution client.")


def cost_summary(parents, candidates, run_dir):
    usage = Counter()
    counts = {"environment_requests": 0, "semantic_calls": 0, "http_attempts": 0,
              "requests_with_unknown_usage": 0, "http_attempts_with_unknown_usage": 0}
    streams = [("environment_requests", r["steps"]) for r in parents + candidates]
    for path in sorted((run_dir / "calls").glob("*.json")):
        streams.append(("semantic_calls", json.loads(path.read_text(encoding="utf-8"))["steps"]))
    for kind, events in streams:
        counts[kind] += len(events)
        for event in events:
            attempts = event.get("transport_attempts", [])
            counts["http_attempts"] += len(attempts)
            counts["http_attempts_with_unknown_usage"] += sum(a.get("usage") is None for a in attempts)
            keys = ("prompt_tokens", "completion_tokens", "total_tokens")
            if event.get("response_archive") is True:
                # Every received attempt may have billed usage, including failed HTTP
                # responses. The final response is already one of these attempts.
                reported_items = [a.get("usage") or {} for a in attempts]
                counts["requests_with_unknown_usage"] += (not attempts or any(
                    not all(isinstance(item.get(k), int) for k in keys) for item in reported_items))
            else:
                reported_items = [event.get("model_response", {}).get("usage") or {}]
                counts["requests_with_unknown_usage"] += not all(
                    isinstance(reported_items[0].get(k), int) for k in keys)
            for reported in reported_items:
                usage.update({key: reported[key] for key in keys if isinstance(reported.get(key), int)})
                if event.get("response_archive") is True:
                    reasoning = (reported.get("completion_tokens_details") or {}).get("reasoning_tokens")
                    if isinstance(reasoning, int):
                        usage["reasoning_tokens"] += reasoning  # A subset of completion_tokens, not additional tokens.
    return {**counts, "reported_usage": dict(usage),
            "scope": "Includes source and declared failed Parent attempts, Candidate executions and all recorded method calls; unknown usage is not zero."}


def run_round(plan, parent_paths, run_dir, generate, execute_candidate):
    """Dependencies are explicit so all stop/failure branches can be tested offline.

    generate(stage, messages, output_path) -> raw JSON text
    execute_candidate(parent_record, skill_path, output_root) -> trajectory path
    """
    validate_plan(plan)
    parents, sources, evidence = prepare_evidence(parent_paths, plan)
    prior_parents = load_prior_parent_attempts(plan, parents)
    run_dir = Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "calls").mkdir()
    parent = load_skill()
    editor_schema = plan.get("editor_schema", EDITOR_SCHEMA_V1)
    write_record(run_dir / "plan.json", plan)
    write_record(run_dir / "parent.json", parent)
    write_record(run_dir / "sources.json", sources)
    write_record(run_dir / "evidence.json", evidence)
    implementation = {p.name: digest(p.read_bytes()) for p in Path(__file__).parent.glob("*.py")}
    report = {"schema_version": "v22_no_history_round_v1", "started_at": timestamp(),
              "status": "constructing", "active_stage": "diagnosis", "parent_skill_id": "none",
              "plan_sha256": object_digest(plan), "evidence_sha256": object_digest(evidence),
              "method_implementation": implementation, "fusion": "identity", "memory": "empty",
              "editor_schema": editor_schema,
              "prior_parent_attempts": plan.get("prior_parent_attempts", []),
              "adoption": {"decision": "staging_only", "reason": "Formal Gate is not implemented; no active Skill is replaced."},
              "comparisons": [], "limitations": [
                  "Same-task Train re-execution is a construction check, not held-out generalization or a causal effect estimate.",
                  "Reference and text checks do not prove semantic correctness or behavioral compliance.",
                  "Behavioral feedback is a separate source-bound operation; Fusion transforms, Memory and cross-round publication are not implemented.",
              ]}
    write_record(run_dir / "report.json", report)
    candidates = []
    try:
        raw = generate("diagnosis", diagnosis_messages(parent, evidence), run_dir / "calls/diagnosis.json")
        diagnosis = validate_diagnosis(parse_json_response(raw), parent, evidence)
        write_record(run_dir / "diagnosis.json", diagnosis)
        if diagnosis["decision"] != "revise":
            report.update(status="no_change" if diagnosis["decision"] == "no_change" else "needs_evidence",
                          stop_reason=diagnosis["rationale"], active_stage=None)
            return report
        requirements = {"mode": "identity", "diagnosis_sha256": object_digest(diagnosis),
                        "goals": diagnosis["goals"], "preserve": diagnosis["preserve"],
                        "proposals": diagnosis["proposals"], "interactions": diagnosis["interactions"],
                        "boundary_checks": diagnosis["boundary_checks"]}
        write_record(run_dir / "requirements.json", requirements)
        report["active_stage"] = "editor"
        write_record(run_dir / "report.json", report)
        raw = generate("editor", editor_messages(parent, diagnosis, evidence, schema_version=editor_schema), run_dir / "calls/editor.json")
        editor = validate_editor(parse_json_response(raw), parent, diagnosis, evidence)
        if editor["schema_version"] != editor_schema:
            raise ValueError("Editor output cannot downgrade the declared pre-execution protocol.")
        write_record(run_dir / "editor.json", editor)
        if editor["decision"] != "candidate":
            report.update(status="no_change" if editor["decision"] == "no_change" else "needs_revision",
                          stop_reason=editor["rationale"], active_stage=None)
            return report
        candidate_dir = run_dir / "candidate"
        candidate_dir.mkdir()
        skill_path = candidate_dir / "SKILL.md"
        skill_path.write_bytes(editor["candidate_text"].encode("utf-8"))
        candidate = load_skill(skill_path)
        actual_diff = "".join(difflib.unified_diff(
            (parent["text"] or "").splitlines(keepends=True),
            candidate["text"].splitlines(keepends=True), fromfile="parent/NoSkill", tofile="candidate/SKILL.md"))
        if not actual_diff:
            raise ValueError("Candidate has no actual change.")
        (candidate_dir / "actual.diff").write_text(actual_diff, encoding="utf-8")
        observation = observation_plan(parent, diagnosis, requirements, editor, candidate, actual_diff)
        # New rounds bind questions before any Candidate action; legacy artifacts remain untouched.
        write_record(run_dir / "observation_plan.json", observation)
        lineage = {"parent": parent, "candidate": candidate, "sources": sources,
                   "evidence_sha256": object_digest(evidence), "diagnosis_sha256": object_digest(diagnosis),
                   "requirements_sha256": object_digest(requirements), "editor_sha256": object_digest(editor),
                   "diff_sha256": digest(actual_diff.encode("utf-8")), "mappings": editor["mappings"],
                   "decision": "staged_for_execution", "created_at": timestamp()}
        lineage["observation_plan_sha256"] = object_digest(observation)
        write_record(candidate_dir / "lineage.json", lineage)
        report.update(status="executing_candidate", active_stage="candidate_execution",
                      candidate_skill_id=candidate["skill_id"], candidate_path=str(skill_path))
        write_record(run_dir / "report.json", report)
        for parent_record in parents:
            verify_sources(sources)
            if load_skill(skill_path) != candidate:
                raise ValueError("Candidate changed after staging.")
            task_root = run_dir / "candidate_runs" / parent_record["task"]["id"].replace(":", "_")
            path = Path(execute_candidate(parent_record, skill_path, task_root))
            result = json.loads(path.read_text(encoding="utf-8"))
            candidates.append(result)
            audit = verify_record(result)
            if result["skill"] != candidate:
                raise ValueError("Executed Skill differs from the staged Candidate.")
            comparison = compare_records(parent_record, result)
            report["comparisons"].append({"task_id": parent_record["task"]["id"],
                "parent_run_id": parent_record["run_id"], "candidate_run_id": result["run_id"],
                "candidate_trajectory": str(path.resolve()), "candidate_audit": audit, "conditions": comparison,
                "parent_native_success": parent_record["won"], "candidate_native_success": audit["native_success"],
                "parent_actions": sum(e["phase"] == "executed" for e in parent_record["steps"]),
                "candidate_actions": audit["steps_executed"]})
            write_record(run_dir / "report.json", report)
        verify_sources(sources)
        verify_sources(plan.get("prior_parent_attempts", []))
        if load_skill(skill_path) != candidate:
            raise ValueError("Candidate changed during execution.")
        complete = all(row["candidate_audit"]["episode_complete"] for row in report["comparisons"])
        matched = all(row["conditions"]["recorded_conditions_match"] for row in report["comparisons"])
        report["status"] = "candidate_evaluated" if complete and matched else "evaluation_incomplete"
        report["active_stage"] = None
        return report
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "error",
                      error_type=type(exc).__name__,
                      error="Round stopped; saved calls and prior artifacts remain available. No semantic retry or adoption occurred.")
        if isinstance(exc, ValueError):
            report["validation_error"] = str(exc)
        return report
    finally:
        # Include any persisted partial Candidate if a process failed before return.
        seen = {r["run_id"] for r in candidates}
        for path in (run_dir / "candidate_runs").glob("*/skill_*/trajectory.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["run_id"] not in seen:
                candidates.append(record)
                seen.add(record["run_id"])
        report["cost"] = cost_summary(prior_parents + parents, candidates, run_dir)
        report["finished_at"] = timestamp()
        write_record(run_dir / "report.json", report)


def execute_with_adapter(parent, skill_path, output_root, env_file):
    output_root.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-m", "src.adapters.alfworld.run_task_skill", "--purpose", "learning",
               "--split", "train", "--task-id", parent["task"]["id"], "--model", parent["model"],
               "--max-steps", str(parent["protocol"]["max_steps"]), "--skill-file", str(skill_path),
               "--env-file", str(env_file), "--output-root", str(output_root)]
    with (output_root / "run.log").open("w", encoding="utf-8") as log:
        process = subprocess.run(command, cwd=REPO_ROOT, stdout=log, stderr=subprocess.STDOUT)
    paths = list(output_root.glob("skill_*/trajectory.json"))
    if len(paths) != 1:
        raise RuntimeError("Candidate process did not produce exactly one trajectory.")
    write_record(output_root / "process.json", {"command": command, "exit_code": process.returncode})
    return paths[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-trajectories", type=Path, nargs="+", required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    validate_plan(plan)
    parents, _, _ = prepare_evidence(args.parent_trajectories, plan)
    load_prior_parent_attempts(plan, parents)
    if args.dry_run:
        print("Inputs verified: No Skill Train evidence; at most one Diagnosis and one Editor; no calls or outputs.")
        return 0
    load_dotenv(args.env_file, override=False)
    key = os.environ.get("OPENAI_API_KEY")
    base = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    if not key or not base:
        parser.error("OPENAI_API_KEY and OPENAI_BASE_URL are required.")
    with requests.Session() as session:
        if ".intra." in base:
            session.trust_env = False
        generate = lambda stage, messages, output: semantic_call(
            stage, messages, session=session, endpoint=base + "/chat/completions", key=key,
            model=plan["model"], output=output)
        execute = lambda parent, skill, output: execute_with_adapter(parent, skill, output, args.env_file.resolve())
        report = run_round(plan, args.parent_trajectories, args.run_dir, generate, execute)
    print(json.dumps({"status": report["status"], "report": str(args.run_dir.resolve() / "report.json"),
                      "cost": report["cost"]}, ensure_ascii=False, indent=2))
    return 1 if report["status"] in {"error", "interrupted", "evaluation_incomplete"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
