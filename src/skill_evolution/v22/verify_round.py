"""Offline artifact consistency checks; no model calls or semantic certification."""

import argparse
import difflib
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import digest, load_skill, object_digest
from src.adapters.alfworld.verify_skill_run import compare_records, require, verify_record
from src.adapters.alfworld.response_archive import verify_response_archive
from .diagnosis_editor import (
    diagnosis_messages, editor_messages, parse_json_response, validate_diagnosis, validate_editor,
)
from .evidence import load_prior_parent_attempts, prepare_evidence, verify_sources
from .run_round import cost_summary, validate_plan
from .observation_plan import observation_plan
from .model_call import request_profile


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_call(path, stage, model, messages, document, *, max_tokens=16384, timeout_seconds=300,
                transport_policy="legacy"):
    profile = request_profile(stage, max_tokens, timeout_seconds, transport_policy=transport_policy)
    call = read(path)
    require(call["schema_version"] == "v22_semantic_call_v1" and call["stage"] == stage
            and call["model"] == model and len(call["steps"]) == 1, "Semantic call identity mismatch.")
    event = call["steps"][0]
    require(event["messages"] == messages and call["messages_sha256"] == object_digest(messages),
            "Semantic call input differs from frozen evidence/requirements.")
    require(call.get("request_profile", {"max_tokens": 16384, "timeout_seconds": 300}) == profile,
            "Semantic request profile differs from the declared budget.")
    require(call.get("transport_policy", "legacy") == transport_policy,
            "Semantic transport policy differs from the declared protocol.")
    parameters = {"model": model, "temperature": 1.0, "max_tokens": max_tokens,
                  "reasoning_effort": "medium", "thinking": {"type": "enabled"}, "stream": False}
    attempts = event.get("transport_attempts", [])
    maximum = 1 if transport_policy == "single_attempt" else 6
    require(len(attempts) <= maximum and (document is None or bool(attempts)), "Missing/excess semantic HTTP attempts.")
    if transport_policy == "single_attempt" and attempts:
        require(call.get("response_archival") == "raw_http_body_v1" and event.get("response_archive") is True,
                "Single-attempt call lacks response archival identity.")
    response = event.get("model_response")
    for number, attempt in enumerate(attempts, 1):
        if transport_policy == "single_attempt":
            verify_response_archive(path, attempt)
        require(attempt["attempt"] == number, "Semantic transport order mismatch.")
        require(attempt["request_parameters"] == parameters
                and attempt["request_sha256"] == object_digest({**parameters, "messages": messages}),
                "Semantic HTTP request parameters/body mismatch.")
        require(attempt["status"] in {"requesting", "responded", "error", "interrupted"}, "Unknown semantic transport state.")
        if number < len(attempts):
            require(attempt["status"] == "responded" and attempt.get("http_status") in {429, 500, 502, 503, 504},
                    "Unexpected semantic transport retry.")
        if attempt["status"] == "requesting":
            require(number == len(attempts) and response is None and document is None, "Unfinished semantic transport has output.")
    if response is not None:
        require(bool(attempts) and attempts[-1]["status"] == "responded"
                and 200 <= attempts[-1].get("http_status", 0) < 400, "Semantic response lacks successful HTTP attempt.")
        require(response.get("api_attempts") == len(attempts)
                and response.get("transport_retries") == len(attempts) - 1, "Semantic transport response count mismatch.")
        if document is not None or attempts[-1].get("usage") is not None:
            require(attempts[-1].get("usage") == response.get("usage"), "Semantic transport usage mismatch.")
    if document is not None:
        require(call["status"] == "responded" and event["phase"] == "responded", "Unfinished semantic call.")
        response = event["model_response"]
        require(response.get("finish_reason") != "length"
                and parse_json_response(response["content"]) == document, "Saved semantic output differs from response.")


def verify_round(run_dir):
    root = Path(run_dir).resolve()
    plan, parent, sources, evidence, report = [read(root / f"{name}.json")
                                              for name in ("plan", "parent", "sources", "evidence", "report")]
    validate_plan(plan)
    require(parent == load_skill() and report["parent_skill_id"] == "none", "Parent is not No Skill.")
    require(report["schema_version"] == "v22_no_history_round_v1"
            and report["fusion"] == "identity" and report["memory"] == "empty"
            and report["adoption"]["decision"] == "staging_only", "Round scope/adoption mismatch.")
    require(report["plan_sha256"] == object_digest(plan)
            and report["evidence_sha256"] == object_digest(evidence), "Plan/evidence hash mismatch.")
    verify_sources(sources)
    parents, rebuilt_sources, rebuilt_evidence = prepare_evidence([s["path"] for s in sources], plan)
    require(sources == rebuilt_sources and evidence == rebuilt_evidence, "Source/evidence reconstruction mismatch.")
    prior = load_prior_parent_attempts(plan, parents)
    require(report.get("prior_parent_attempts", []) == plan.get("prior_parent_attempts", []),
            "Prior Parent attempts differ from the recovery plan.")
    status = report["status"]
    editor_schema = report.get("editor_schema", "v22.editor.v0")
    require(editor_schema in {"v22.editor.v0", "v22.editor.v1"}, "Unknown declared Editor schema.")
    if "editor_schema" in plan:
        require(editor_schema == plan["editor_schema"], "Editor schema differs from plan.")
    terminal = {"candidate_evaluated", "no_change", "needs_evidence", "needs_revision"}
    require(status in terminal | {"evaluation_incomplete", "error", "interrupted", "constructing", "executing_candidate"},
            "Unknown round status.")
    diagnosis = read(root / "diagnosis.json") if (root / "diagnosis.json").exists() else None
    editor = read(root / "editor.json") if (root / "editor.json").exists() else None
    requirements = None
    if diagnosis is not None:
        validate_diagnosis(diagnosis, parent, evidence)
        if diagnosis["decision"] == "revise":
            requirements = {"mode": "identity", "diagnosis_sha256": object_digest(diagnosis),
                            **{key: diagnosis[key] for key in ("goals", "preserve", "proposals", "interactions", "boundary_checks")}}
            if (root / "requirements.json").exists():
                require(read(root / "requirements.json") == requirements, "Identity requirements changed.")
            else:
                require(status not in terminal and editor is None, "Missing effective requirements.")
        else:
            require(editor is None and not (root / "requirements.json").exists(), "Diagnosis stop released requirements/Editor.")
    if editor is not None:
        require(requirements is not None, "Editor lacks a revising Diagnosis.")
        validate_editor(editor, parent, diagnosis, evidence)
        require(editor["schema_version"] == editor_schema, "Editor protocol was downgraded.")
    calls = {p.stem for p in (root / "calls").glob("*.json")}
    require(calls <= {"diagnosis", "editor"}, "Unexpected semantic call or retry.")
    for stage, document in (("diagnosis", diagnosis), ("editor", editor)):
        if stage in calls:
            messages = diagnosis_messages(parent, evidence) if stage == "diagnosis" else editor_messages(parent, diagnosis, evidence, schema_version=editor_schema)
            verify_call(root / "calls" / f"{stage}.json", stage, plan["model"], messages, document)
        else:
            require(document is None, "Saved output has no recorded semantic call.")
    if status in terminal:
        require(diagnosis is not None and "finished_at" in report, "Completed round lacks Diagnosis/finish record.")
    expected_stop = ({"no_change": "no_change", "need_evidence": "needs_evidence"}.get(diagnosis["decision"])
                     if diagnosis else None)
    if editor and editor["decision"] != "candidate":
        expected_stop = {"no_change": "no_change", "needs_revision": "needs_revision"}[editor["decision"]]
    if status in terminal and status != "candidate_evaluated":
        require(status == expected_stop, "Reported semantic stop differs from actual decision.")
    paths = sorted((root / "candidate_runs").glob("*/skill_*/trajectory.json"))
    candidate = None
    if expected_stop or editor is None or editor["decision"] != "candidate":
        require(not (root / "candidate").exists() and not paths and not report["comparisons"]
                and "candidate_skill_id" not in report, "No-candidate branch contains execution artifacts.")
    elif (root / "candidate/lineage.json").exists():
        candidate = load_skill(root / "candidate/SKILL.md")
        require(candidate["text"] == editor["candidate_text"], "Candidate differs from Editor text.")
        actual_diff = "".join(difflib.unified_diff([], candidate["text"].splitlines(keepends=True),
                                                fromfile="parent/NoSkill", tofile="candidate/SKILL.md"))
        require((root / "candidate/actual.diff").read_bytes() == actual_diff.encode("utf-8"), "Actual diff mismatch.")
        lineage = read(root / "candidate/lineage.json")
        expected = {"parent": parent, "candidate": candidate, "sources": sources,
                    "evidence_sha256": object_digest(evidence), "diagnosis_sha256": object_digest(diagnosis),
                    "requirements_sha256": object_digest(requirements), "editor_sha256": object_digest(editor),
                    "diff_sha256": digest(actual_diff.encode("utf-8")), "mappings": editor["mappings"],
                    "decision": "staged_for_execution"}
        require(all(lineage.get(k) == v for k, v in expected.items()), "Lineage mismatch.")
        if "editor_schema" in report:
            observation = observation_plan(parent, diagnosis, requirements, editor, candidate, actual_diff)
            require(read(root / "observation_plan.json") == observation
                    and lineage.get("observation_plan_sha256") == object_digest(observation),
                    "Pre-execution observation questions differ from actual requirements/Skill.")
        require(report["candidate_skill_id"] == candidate["skill_id"]
                and Path(report["candidate_path"]).resolve() == root / "candidate/SKILL.md", "Candidate report identity mismatch.")
    require(candidate is not None or not paths, "Executions lack staged Candidate lineage.")
    records = {str(path.resolve()): read(path) for path in paths}
    seen = set()
    for record in records.values():
        verify_record(record)
        require(record["skill"] == candidate and record["task"]["id"] in plan["task_ids"]
                and record["task"]["id"] not in seen, "Candidate execution identity/task mismatch or duplicate.")
        seen.add(record["task"]["id"])
    rows = report["comparisons"]
    require(len(rows) <= len(parents), "Too many comparisons.")
    for parent_record, row in zip(parents, rows):
        path = str(Path(row["candidate_trajectory"]).resolve())
        require(path in records, "Comparison references an unrecorded Candidate trajectory.")
        result = records[path]
        audit = verify_record(result)
        expected = {"task_id": parent_record["task"]["id"], "parent_run_id": parent_record["run_id"],
                    "candidate_run_id": result["run_id"], "candidate_audit": audit,
                    "conditions": compare_records(parent_record, result), "parent_native_success": parent_record["won"],
                    "candidate_native_success": audit["native_success"],
                    "parent_actions": sum(e["phase"] == "executed" for e in parent_record["steps"]),
                    "candidate_actions": audit["steps_executed"]}
        require(result["task"]["id"] == row["task_id"] and all(row.get(k) == v for k, v in expected.items()), "Comparison report mismatch.")
    if status == "candidate_evaluated":
        require(candidate is not None and len(rows) == len(records) == len(parents)
                and all(r["candidate_audit"]["episode_complete"] and r["conditions"]["recorded_conditions_match"] for r in rows),
                "Candidate evaluation is incomplete or conditions differ.")
    if "cost" in report:
        require(report["cost"] == cost_summary(prior + parents, list(records.values()), root), "Cost report mismatch.")
    return {"schema_version": "v22_round_audit_v1", "artifact_valid": True, "round_status": status,
            "round_complete": status in terminal, "candidate_executions": len(records),
            "scope": "Saved evidence, calls, identity requirements, diff, lineage and recorded execution consistency only; not semantic correctness, behavioral benefit or causal evidence."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    result = verify_round(args.run_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["round_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
