"""Replay existing Train traces once, without changing the executed round."""

import argparse
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.adapters.alfworld.run_task import REPO_ROOT
from src.adapters.alfworld.run_task_skill import timestamp
from src.adapters.alfworld.skill_runtime import digest, object_digest, write_record
from src.adapters.alfworld.verify_skill_run import compare_records, learning_feedback, require, verify_record
from .diagnosis_editor import parse_json_response
from .evidence import verify_sources
from .model_call import semantic_call
from .observation_plan import observation_plan
from .replay_contract import replay_messages, validate_assessment
from .run_round import cost_summary
from .verify_round import verify_call, verify_round


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def visible_run(record):
    feedback = learning_feedback(record)
    require(feedback["split"] == "train" and feedback["purpose"] == "learning", "Replay requires learning-purpose Train traces.")
    before = feedback["initial_observation"]
    steps = []
    for event in feedback["steps"]:
        steps.append({"observation_before": before, **{key: event[key] for key in (
            "step", "phase", "admissible_commands", "action", "action_in_admissible_commands",
            "observation", "reward", "done", "won") if key in event}})
        before = event.get("observation", before)
    return {key: feedback[key] for key in ("run_id", "task_id", "initial_observation", "execution_context",
            "status", "error_stage", "error_type", "native_success", "episode_complete")} | {"steps": steps}


def run_facts(record):
    audit = verify_record(record)
    executed = [e for e in record["steps"] if e["phase"] == "executed"]
    return {"run_id": record["run_id"], "status": record["status"],
            "episode_complete": audit["episode_complete"], "native_success": audit["native_success"],
            "action_count": len(executed), "reported_usage": audit["reported_usage"],
            "requests_with_unknown_usage": audit["requests_with_unknown_usage"],
            "non_admissible_action_steps": [e["step"] for e in executed if not e["action_in_admissible_commands"]],
            "look_action_steps": [e["step"] for e in executed if e["action"] == "look"],
            "literal_nothing_happens_steps": [e["step"] for e in executed if e["observation"].strip() == "Nothing happens."]}


def prepare_feedback(source_round):
    root = Path(source_round).resolve()
    audit = verify_round(root)
    report, plan, parent, diagnosis, requirements, editor = [read(root / f"{n}.json")
        for n in ("report", "plan", "parent", "diagnosis", "requirements", "editor")]
    require(editor["decision"] == "candidate", "No executed Candidate is available for Replay.")
    lineage = read(root / "candidate/lineage.json")
    candidate = lineage["candidate"]
    diff = (root / "candidate/actual.diff").read_text(encoding="utf-8")
    observation = observation_plan(parent, diagnosis, requirements, editor, candidate, diff)
    preplan = root / "observation_plan.json"
    if preplan.exists():
        require(read(preplan) == observation and "editor_schema" in report
                and lineage.get("observation_plan_sha256") == object_digest(observation),
                "Saved observation questions lack pre-execution lineage binding.")
    sources = read(root / "sources.json")
    parents = {s["task_id"]: read(s["path"]) for s in sources}
    candidates = [read(p) for p in sorted((root / "candidate_runs").glob("*/skill_*/trajectory.json"))]
    require(bool(candidates), "No Candidate execution exists; do not synthesize Replay.")
    by_task = {r["task"]["id"]: r for r in candidates}
    pairs, runs = [], []
    for task_id in plan["task_ids"]:
        if task_id not in by_task:
            continue
        before, after = parents[task_id], by_task[task_id]
        comparison = compare_records(before, after)
        pairs.append({"task_id": task_id, "parent_run_id": before["run_id"], "candidate_run_id": after["run_id"],
                      "comparison_eligible": comparison["recorded_conditions_match"],
                      "comparison": comparison, "parent": run_facts(before), "candidate": run_facts(after)})
        runs.extend([visible_run(before), visible_run(after)])
    facts = {"pairs": pairs, "unexecuted_tasks": [t for t in plan["task_ids"] if t not in by_task],
             "source_round_cost": report.get("cost"), "source_round_audit": audit,
             "scope": "Mechanical native outcomes and event counts; action-list membership is not task correctness. Unknown usage is not zero."}
    payload = {"schema_version": "v22.replay_input.v1", "parent": parent,
               "candidate": {k: v for k, v in candidate.items() if k != "source"},
               "actual_diff": diff, "requirements": requirements, "observation_plan": observation,
               "observation_plan_origin": "saved_before_execution" if preplan.exists() else "reconstructed_from_frozen_pre_execution_artifacts",
               "editor_preservation": {"schema": editor["schema_version"],
                                       "status": "recorded_self_check" if "requirement_checks" in editor else "not_recorded_legacy",
                                       "checks": editor.get("requirement_checks", [])},
               "facts": facts, "runs": runs}
    # These absolute provenance paths never enter the model's evidence view.
    files = {p.resolve() for p in root.rglob("*") if p.is_file()}
    files.update(Path(s["path"]).resolve() for s in sources + plan.get("prior_parent_attempts", []))
    bindings = [{"path": str(p), "sha256": digest(p.read_bytes())} for p in sorted(files)]
    return payload, bindings, plan["model"]


def incremental_cost(output):
    result = cost_summary([], [], output)
    result["scope"] = "This feedback operation only; source round cost is separately referenced, not charged again. No environment execution."
    return result


def make_package(payload, assessment, manifest, cost):
    return {"schema_version": "v22.behavior_feedback_package.v1",
            "input_sha256": object_digest(payload), "manifest_sha256": object_digest(manifest),
            "assessment_sha256": object_digest(assessment),
            "bindings": payload["observation_plan"]["bindings"],
            "observation_plan_origin": payload["observation_plan_origin"],
            "editor_preservation": payload["editor_preservation"], "facts": payload["facts"],
            "interpretation": assessment, "incremental_cost": cost,
            "learning_boundary": {"unit": "actual_candidate_bundle", "causal_attribution": "not_identified",
                                  "memory_written": False, "adoption_changed": False,
                                  "scope": "Source-linked semantic observations on supplied Train tasks; model judgments remain fallible. No isolated edit effects or generalization established."}}


def run_feedback(source_round, output_dir, generate):
    root, output = Path(source_round).resolve(), Path(output_dir).resolve()
    if output == root or root in output.parents:
        raise ValueError("Feedback must be outside the immutable source round.")
    payload, bindings, model = prepare_feedback(root)
    output.mkdir(parents=True, exist_ok=False)
    (output / "calls").mkdir()
    manifest = {"schema_version": "v22.replay_manifest.v1", "source_round": str(root),
                "source_files": bindings, "input_sha256": object_digest(payload), "model": model,
                "budget": {"replay_calls": 1, "semantic_retries": 0, "environment_calls": 0},
                "implementation": {p.name: digest(p.read_bytes()) for p in Path(__file__).parent.glob("*.py")}}
    write_record(output / "manifest.json", manifest)
    write_record(output / "input.json", payload)
    report = {"schema_version": "v22.replay_operation.v1", "started_at": timestamp(), "status": "running"}
    write_record(output / "report.json", report)
    try:
        raw = generate("replay", replay_messages(payload), output / "calls/replay.json")
        assessment = validate_assessment(parse_json_response(raw), payload)
        verify_sources(bindings)
        write_record(output / "assessment.json", assessment)
        cost = incremental_cost(output)
        write_record(output / "package.json", make_package(payload, assessment, manifest, cost))
        report["status"] = "feedback_ready"
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "error", error_type=type(exc).__name__)
        if isinstance(exc, ValueError):
            report["validation_error"] = str(exc)
    finally:
        report.update(finished_at=timestamp(), incremental_cost=incremental_cost(output))
        write_record(output / "report.json", report)
    return report


def verify_feedback(output_dir):
    output = Path(output_dir).resolve()
    manifest, payload, report = [read(output / f"{name}.json") for name in ("manifest", "input", "report")]
    require(manifest["schema_version"] == "v22.replay_manifest.v1"
            and manifest["budget"] == {"replay_calls": 1, "semantic_retries": 0, "environment_calls": 0}, "Replay scope changed.")
    verify_sources(manifest["source_files"])
    rebuilt, bindings, model = prepare_feedback(manifest["source_round"])
    require(payload == rebuilt and bindings == manifest["source_files"] and manifest["model"] == model
            and object_digest(payload) == manifest["input_sha256"], "Replay source/input reconstruction mismatch.")
    calls = list((output / "calls").glob("*.json"))
    require(len(calls) <= 1 and all(p.name == "replay.json" for p in calls), "Unexpected Replay call or semantic retry.")
    assessment = read(output / "assessment.json") if (output / "assessment.json").exists() else None
    if assessment is not None:
        validate_assessment(assessment, payload)
        require(bool(calls), "Assessment has no recorded semantic call.")
    if calls:
        verify_call(calls[0], "replay", model, replay_messages(payload), assessment)
    cost = incremental_cost(output)
    require(report["incremental_cost"] == cost, "Replay incremental cost mismatch.")
    require(report["schema_version"] == "v22.replay_operation.v1"
            and report["status"] in {"feedback_ready", "error", "interrupted"}, "Unknown Replay operation state.")
    if report["status"] == "feedback_ready":
        require(assessment is not None and read(output / "package.json") == make_package(payload, assessment, manifest, cost),
                "Feedback package differs from observed facts/assessment/bindings.")
    else:
        require(not (output / "package.json").exists(), "Failed Replay cannot release a feedback package.")
    return {"schema_version": "v22.replay_audit.v1", "artifact_valid": True,
            "feedback_ready": report["status"] == "feedback_ready", "source_files_checked": len(bindings),
            "scope": "Source identity, coverage, exact quotes and call consistency; not proof of semantic truth or causal attribution."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("source_round", type=Path)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    run.add_argument("--dry-run", action="store_true")
    audit = sub.add_parser("verify")
    audit.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "verify":
        result = verify_feedback(args.output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["feedback_ready"] else 1
    payload, _, model = prepare_feedback(args.source_round)
    if args.dry_run:
        print(json.dumps({"verified": True, "paired_tasks": len(payload["facts"]["pairs"]),
                          "targets": len(payload["observation_plan"]["targets"]),
                          "unexecuted_tasks": payload["facts"]["unexecuted_tasks"],
                          "replay_calls_max": 1, "environment_calls": 0}))
        return 0
    load_dotenv(args.env_file, override=False)
    key, base = os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    if not key or not base:
        parser.error("OPENAI_API_KEY and OPENAI_BASE_URL are required.")
    with requests.Session() as session:
        if ".intra." in base:
            session.trust_env = False
        generate = lambda stage, messages, output: semantic_call(stage, messages, session=session,
            endpoint=base + "/chat/completions", key=key, model=model, output=output)
        result = run_feedback(args.source_round, args.output_dir, generate)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "feedback_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
