"""One bounded, source-bound compact learning -> update -> feedback cycle.

The existing staged round is immutable. Its No Skill Parent is reused, not adopted.
No formal Gate, continual scheduler, automatic semantic repair, or deployment.
"""

import argparse
from copy import deepcopy
import difflib
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.adapters.alfworld.run_task import REPO_ROOT
from src.adapters.alfworld.run_task_skill import timestamp
from src.adapters.alfworld.skill_runtime import digest, load_skill, object_digest, write_record
from src.adapters.alfworld.verify_skill_run import compare_records, require, verify_record
from .compact_learning import (apply_memory, build_learning_payload, learning_messages,
                               prepare_legacy, validate_learning)
from .compact_learning_view import learning_messages_scoped, scoped_learning_payload
from .compact_update import (apply_fusion, diagnosis_messages, editor_messages,
                             fusion_messages, validate_diagnosis, validate_editor)
from .diagnosis_editor import parse_json_response
from .evidence import verify_sources
from .model_call import semantic_call
from .run_round import cost_summary, execute_with_adapter
from .verify_round import verify_call


DEFAULT_PLAN = REPO_ROOT / "experiments/methods/v22/03_compact_cycle/config/plan_scoped.json"
STAGES = ("learn_initial", "diagnosis", "fusion", "editor", "fusion_revision",
          "editor_revision", "learn_final")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_plan(plan, parents):
    require(plan["schema_version"] == "v22.compact_cycle_plan.v1", "Unknown compact cycle plan.")
    require(plan.get("evidence_view", "legacy") in {"legacy", "scoped_v1"}, "Unknown evidence consumption view.")
    require(plan["actor_model"] == "deepseek-v4-flash" and plan["evolution_model"] == "deepseek-v4-pro",
            "Keep trajectory and evolution model roles explicit.")
    require(plan["parent"] == "reuse_source_no_skill" and plan["adoption"] == "staging_only",
            "This path reuses the unadopted round's No Skill Parent.")
    require(plan["task_ids"] == [p["task"]["id"] for p in parents], "Task list changed from declared source.")
    require(type(plan["max_steps_per_episode"]) is int and 1 <= plan["max_steps_per_episode"] <= 50
            and plan["candidate_episodes_max"] == len(parents),
            "Candidate budget must match the fixed source task list.")
    require(plan["semantic_calls_max"] == 7 and plan["construction_revision_pairs_max"] == 1
            and plan["semantic_retries"] == 0 and plan["candidate_retries"] == 0,
            "Unexpected retry or method-call budget.")
    for p in parents:
        require(p["skill"] == load_skill() and p["purpose"] == "learning" and p["split"] == "train"
                and p["model"] == plan["actor_model"] and p["protocol"]["max_steps"] == plan["max_steps_per_episode"],
                "Source Parent differs from the declared execution protocol.")


SCOPED_UPDATE_INSTRUCTIONS = """
CURRENT/HISTORY BOUNDARY: runs, sources, plan and current_run_facts are current.
Historical evidence belongs to H1::/H2:: namespaces in historical_contexts; matching
task IDs or bare event aliases do not make it current. Memory is fallible and its
limits/counterevidence still apply. Historical repeated action lists are omitted;
do not infer missing actions from that omission. Compare actual run/Skill identities.
Use only current sources keys or unchanged Memory effect IDs in output basis, never
H1:: historical aliases. Historical observations may justify a scoped change or
identity; they do not require a transformation or prove its benefit.
"""


def stage_messages(plan, stage, payload):
    """Choose a versioned read-only view; old plans reconstruct original messages."""
    builders = {"learn_initial": learning_messages, "learn_final": learning_messages,
                "diagnosis": diagnosis_messages, "fusion": fusion_messages,
                "fusion_revision": fusion_messages, "editor": editor_messages,
                "editor_revision": editor_messages}
    require(stage in builders, "Unknown semantic stage.")
    profile = plan.get("evidence_view", "legacy")
    require(profile in {"legacy", "scoped_v1"}, "Unknown evidence consumption view.")
    if profile == "legacy" or stage == "diagnosis":
        return builders[stage](payload)
    if stage in {"learn_initial", "learn_final"}:
        return learning_messages_scoped(payload)
    messages = builders[stage](scoped_learning_payload(payload))
    messages[0]["content"] += SCOPED_UPDATE_INSTRUCTIONS
    return messages


def diagnosis_input(initial, parents):
    """Only current Parent feedback. No Candidate, historical plan or Memory leak."""
    runs = {alias: deepcopy(run) for alias, run in initial["runs"].items() if alias.startswith("P")}
    commands = {run["initial_commands"] for run in runs.values()}
    commands.update(event["commands"] for run in runs.values() for event in run["steps"])
    return {"parent": deepcopy(initial["parent"]), "capabilities": initial["capabilities"],
            "base_protocol": {k: parents[0]["protocol"][k] for k in
                              ("system_prompt", "initial_template", "history_template")},
            "runs": runs, "command_sets": {key: deepcopy(initial["command_sets"][key]) for key in sorted(commands)},
            "sources": {k: deepcopy(v) for k, v in initial["sources"].items()
                        if k.startswith("P") or k in {"skill:parent", "capabilities"}}
                       | {"base_protocol": {"kind": "base_protocol"}}}


def fusion_input(current, plan, memory, editor_feedback=None):
    result = {**deepcopy(current), "plan": deepcopy(plan), "memory": deepcopy(memory)}
    if editor_feedback is not None:
        result["editor_feedback"] = deepcopy(editor_feedback)
    return result


def editor_input(current, plan, memory):
    used = {ref for row in plan["requirements"] for ref in row["basis"]}
    return {**deepcopy(current), "plan": deepcopy(plan),
            "memory": [deepcopy(row) for row in memory if row["id"] in used]}


def updated_memory(payload, output):
    return apply_memory(payload["memory"], output, object_digest(payload), payload=payload)


def candidate_records(root):
    return [read(p) for p in sorted((root / "candidate_runs").glob("*/skill_*/trajectory.json"))]


def cycle_cost(root):
    result = cost_summary([], candidate_records(root), root)
    result["scope"] = "Only this cycle's recorded semantic calls and new Candidate executions. Reused source executions are not charged again. Unknown usage is not zero."
    return result


def make_diff(parent, candidate):
    parent_label = "parent/NoSkill" if parent["mode"] == "none" else "parent/SKILL.md"
    return "".join(difflib.unified_diff((parent["text"] or "").splitlines(keepends=True),
        candidate["text"].splitlines(keepends=True), fromfile=parent_label, tofile="candidate/SKILL.md"))


def execution_comparisons(root, parents):
    by_task = {p["task"]["id"]: p for p in parents}
    rows = []
    for path in sorted((root / "candidate_runs").glob("*/skill_*/trajectory.json")):
        record = read(path)
        require(record["task"]["id"] in by_task, "Undeclared execution task.")
        parent = by_task[record["task"]["id"]]
        audit = verify_record(record)
        rows.append({"task_id": parent["task"]["id"], "trajectory": str(path.resolve()),
            "parent_run_id": parent["run_id"], "candidate_run_id": record["run_id"],
            "conditions": compare_records(parent, record), "candidate_audit": audit,
            "parent_actions": sum(e["phase"] == "executed" for e in parent["steps"]),
            "candidate_actions": audit["steps_executed"], "parent_success": parent["won"],
            "candidate_success": audit["native_success"]})
    order = {p["task"]["id"]: i for i, p in enumerate(parents)}
    return sorted(rows, key=lambda row: order[row["task_id"]])


def change_summary(root, initial_plan, effective, memory):
    ids = {row["id"] for row in memory}
    cited = set()
    for stage in ("fusion", "fusion_revision"):
        path = root / "outputs" / f"{stage}.json"
        if path.exists():
            cited.update(ref for change in read(path)["changes"] for ref in change["basis"] if ref in ids)
    return {"memory_presented_ids": sorted(ids), "history_ids_cited_in_changes": sorted(cited),
            "requirements_changed": initial_plan["requirements"] != effective["requirements"],
            "requirement_text_changed": [r["text"] for r in initial_plan["requirements"]]
                                        != [r["text"] for r in effective["requirements"]]}


def run_cycle(source_round, output_dir, plan, generate, execute_candidate):
    """generate(stage, messages, path); execute_candidate(parent, skill_path, root)."""
    source, root = Path(source_round).resolve(), Path(output_dir).resolve()
    require(root != source and source not in root.parents, "Output must be outside the source round.")
    initial, bindings, parents = prepare_legacy(source)
    validate_plan(plan, parents)
    root.mkdir(parents=True, exist_ok=False)
    for directory in ("inputs", "outputs", "calls"):
        (root / directory).mkdir()
    manifest = {"schema_version": "v22.compact_cycle_manifest.v1", "source_round": str(source),
                "source_files": bindings, "plan_sha256": object_digest(plan),
                "implementation": {p.name: digest(p.read_bytes()) for p in Path(__file__).parent.glob("*.py")}}
    write_record(root / "manifest.json", manifest)
    write_record(root / "plan.json", plan)
    report = {"schema_version": "v22.compact_cycle_report.v1", "started_at": timestamp(),
              "status": "running", "active_stage": None, "stages": [], "comparisons": [],
              "adoption": "staging_only", "parent_skill_id": "none",
              "source_cost_reference": read(source / "report.json").get("cost"),
              "limitations": ["Same-task Train evidence; not independent generalization or isolated edit effects.",
                              "Memory and requirement changes are fallible model judgments; structural checks are not semantic proof.",
                              "Original-revision Candidate was not executed as a controlled baseline.",
                              "No active Skill or global Memory publication; operation-local Memory snapshots only."]}

    def save_report():
        write_record(root / "report.json", report)

    def invoke(stage, payload, validator):
        require(stage in STAGES and stage not in report["stages"] and len(report["stages"]) < plan["semantic_calls_max"],
                "Duplicate or excess semantic stage.")
        verify_sources(bindings)
        report.update(active_stage=stage)
        report["stages"].append(stage)
        save_report()
        write_record(root / "inputs" / f"{stage}.json", payload)
        messages = stage_messages(plan, stage, payload)
        raw = generate(stage, messages, root / "calls" / f"{stage}.json")
        value = parse_json_response(raw)
        validator(value, payload)
        verify_call(root / "calls" / f"{stage}.json", stage, plan["evolution_model"], messages, value)
        call = read(root / "calls" / f"{stage}.json")
        require(call["steps"][0]["model_response"]["response_model"] == plan["evolution_model"],
                "Evolution response model differs from the declared model.")
        verify_sources(bindings)
        write_record(root / "outputs" / f"{stage}.json", value)
        return value

    save_report()
    try:
        learned = invoke("learn_initial", initial, validate_learning)
        memory = updated_memory(initial, learned)
        write_record(root / "memory_initial.json", memory)
        report["initial_memory_count"] = len(memory)
        current = diagnosis_input(initial, parents)
        diagnosis = invoke("diagnosis", current, validate_diagnosis)
        if diagnosis["decision"] != "revise":
            report.update(status=diagnosis["decision"], stop_reason=diagnosis["reason"])
            return report
        write_record(root / "initial_plan.json", diagnosis["plan"])
        f_input = fusion_input(current, diagnosis["plan"], memory)
        fusion = invoke("fusion", f_input, apply_fusion)
        effective = apply_fusion(fusion, f_input)
        write_record(root / "effective_plan.json", effective)
        if fusion["decision"] != "ready" or effective["open"]:
            report.update(status="needs_revision", stop_reason=fusion["reason"])
            return report
        editor = invoke("editor", editor_input(current, effective, memory), validate_editor)
        if editor["decision"] == "needs_revision":
            # One explicitly budgeted upstream correction; never a JSON repair retry.
            f_input = fusion_input(current, effective, memory, editor)
            fusion = invoke("fusion_revision", f_input, apply_fusion)
            effective = apply_fusion(fusion, f_input)
            write_record(root / "effective_plan_revision.json", effective)
            if fusion["decision"] != "ready" or effective["open"]:
                report.update(status="needs_revision", stop_reason=fusion["reason"])
                return report
            editor = invoke("editor_revision", editor_input(current, effective, memory), validate_editor)
        if editor["decision"] != "candidate":
            report.update(status=editor["decision"], stop_reason=editor["reason"])
            return report

        directory = root / "candidate"
        directory.mkdir()
        skill_path = directory / "SKILL.md"
        skill_path.write_bytes(editor["candidate_text"].encode("utf-8"))
        candidate = load_skill(skill_path)
        diff = make_diff(initial["parent"], candidate)
        require(bool(diff), "Candidate must contain an actual change.")
        (directory / "actual.diff").write_text(diff, encoding="utf-8")
        execution_plan = deepcopy(effective)
        execution_plan["watch"].extend(editor["watch"])
        require(len({w["id"] for w in execution_plan["watch"]}) == len(execution_plan["watch"]),
                "Editor observation IDs collide with existing questions.")
        write_record(root / "execution_plan.json", execution_plan)
        lineage = {"parent": initial["parent"], "candidate": candidate,
                   "initial_plan_sha256": object_digest(diagnosis["plan"]),
                   "effective_plan_sha256": object_digest(effective),
                   "execution_plan_sha256": object_digest(execution_plan),
                   "memory_sha256": object_digest(memory), "editor_sha256": object_digest(editor),
                   "diff_sha256": digest(diff.encode("utf-8")), "mappings": editor["mappings"],
                   "created_at": timestamp(), "state": "staging_only", "semantic_preservation": "not_certified"}
        write_record(directory / "lineage.json", lineage)
        report.update(active_stage="candidate_execution", status="executing_candidate")
        save_report()
        new_records = []
        for parent in parents:
            verify_sources(bindings)
            require(load_skill(skill_path) == candidate, "Staged Skill changed.")
            task_root = root / "candidate_runs" / parent["task"]["id"].replace(":", "_")
            path = Path(execute_candidate(parent, skill_path, task_root)).resolve()
            record = read(path)
            new_records.append(record)
            verify_record(record)
            require(record["skill"] == candidate, "Executed Skill differs from the staged version.")
            report["comparisons"] = execution_comparisons(root, parents)
            save_report()
        require(load_skill(skill_path) == candidate, "Candidate changed during execution.")
        final_input = build_learning_payload(initial["parent"], candidate, diff, execution_plan,
                                            parents, new_records, memory=memory, origin="saved_before_execution")
        final_output = invoke("learn_final", final_input, validate_learning)
        write_record(root / "memory_final.json", updated_memory(final_input, final_output))
        matched = all(p["conditions"]["recorded_conditions_match"] and p["candidate_audit"]["episode_complete"]
                      for p in report["comparisons"])
        report.update(status="cycle_complete" if matched else "evaluation_incomplete",
                      final_memory_count=len(read(root / "memory_final.json")),
                      initial_plan_sha256=object_digest(diagnosis["plan"]),
                      effective_plan_sha256=object_digest(effective),
                      **change_summary(root, diagnosis["plan"], effective, memory))
        return report
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "error",
                      error_type=type(exc).__name__)
        if isinstance(exc, ValueError):
            report["validation_error"] = str(exc)
        return report
    finally:
        # Persist facts for partial executions too, even if the adapter process failed.
        report["comparisons"] = execution_comparisons(root, parents)
        report.update(finished_at=timestamp(), cost=cycle_cost(root))
        if report["status"] not in {"error", "interrupted"}:
            report["active_stage"] = None
        save_report()


def verify_cycle(output_dir):
    """Rebuild semantic inputs, deltas, actual versions and cost without calls."""
    root = Path(output_dir).resolve()
    manifest, plan, report = [read(root / f"{n}.json") for n in ("manifest", "plan", "report")]
    verify_sources(manifest["source_files"])
    initial, bindings, parents = prepare_legacy(manifest["source_round"])
    validate_plan(plan, parents)
    require(bindings == manifest["source_files"] and manifest["plan_sha256"] == object_digest(plan),
            "Source bindings or cycle plan changed.")
    require(report["adoption"] == "staging_only" and report["parent_skill_id"] == "none", "Adoption scope changed.")
    require(report["source_cost_reference"] == read(Path(manifest["source_round"]) / "report.json").get("cost"),
            "Source cost reference changed.")
    require(report["comparisons"] == execution_comparisons(root, parents), "Reported comparisons differ from actual runs.")
    require(report["stages"] == [s for s in STAGES if s in report["stages"]], "Invalid/repeated stage order.")
    require({p.stem for p in (root / "calls").glob("*.json")} <= set(report["stages"]), "Undeclared semantic call.")
    seen = []
    terminal = None
    final_valid = False

    def check(stage, expected, validator):
        if stage not in report["stages"]:
            return None
        seen.append(stage)
        require(read(root / "inputs" / f"{stage}.json") == expected, "Stage input differs from source/previous stage: " + stage)
        outpath = root / "outputs" / f"{stage}.json"
        value = read(outpath) if outpath.exists() else None
        path = root / "calls" / f"{stage}.json"
        if value is not None:
            validator(value, expected)
            require(path.exists(), "Validated output lacks a call.")
        if path.exists():
            verify_call(path, stage, plan["evolution_model"], stage_messages(plan, stage, expected), value)
            call = read(path)
            if value is not None:
                require(call["steps"][0]["model_response"]["response_model"] == plan["evolution_model"],
                        "Evolution response model mismatch.")
        return value

    first = check("learn_initial", initial, validate_learning)
    memory = updated_memory(initial, first) if first is not None else None
    if memory is not None:
        require(read(root / "memory_initial.json") == memory, "Initial Memory differs from validated learning.")
        require(report.get("initial_memory_count") == len(memory), "Initial Memory count mismatch.")
        current = diagnosis_input(initial, parents)
        diagnosis = check("diagnosis", current, validate_diagnosis)
        if diagnosis is not None and diagnosis["decision"] != "revise":
            terminal = diagnosis["decision"]
        if diagnosis is not None and diagnosis["decision"] == "revise":
            require(read(root / "initial_plan.json") == diagnosis["plan"], "Initial Plan changed.")
            f_input = fusion_input(current, diagnosis["plan"], memory)
            fusion = check("fusion", f_input, apply_fusion)
            if fusion is not None:
                effective = apply_fusion(fusion, f_input)
                require(read(root / "effective_plan.json") == effective, "Effective Plan differs from Fusion delta.")
                if fusion["decision"] != "ready" or effective["open"]:
                    terminal = "needs_revision"
                if fusion["decision"] == "ready" and not effective["open"]:
                    editor = check("editor", editor_input(current, effective, memory), validate_editor)
                    if editor is not None and editor["decision"] == "needs_revision":
                        revised = fusion_input(current, effective, memory, editor)
                        editor = None
                        fusion2 = check("fusion_revision", revised, apply_fusion)
                        if fusion2 is not None:
                            effective = apply_fusion(fusion2, revised)
                            require(read(root / "effective_plan_revision.json") == effective, "Revised Plan mismatch.")
                            if fusion2["decision"] == "ready" and not effective["open"]:
                                editor = check("editor_revision", editor_input(current, effective, memory), validate_editor)
                            else:
                                editor = None
                                terminal = "needs_revision"
                    if editor is not None and editor["decision"] != "candidate":
                        terminal = editor["decision"]
                    if editor is not None and editor["decision"] == "candidate":
                        skill = load_skill(root / "candidate/SKILL.md")
                        require(skill["text"] == editor["candidate_text"], "Candidate differs from Editor output.")
                        diff = make_diff(initial["parent"], skill)
                        require((root / "candidate/actual.diff").read_text() == diff, "Actual diff changed.")
                        execution = deepcopy(effective)
                        execution["watch"].extend(editor["watch"])
                        require(read(root / "execution_plan.json") == execution, "Execution questions changed.")
                        lineage = read(root / "candidate/lineage.json")
                        expected = {"parent": initial["parent"], "candidate": skill,
                            "initial_plan_sha256": object_digest(diagnosis["plan"]),
                            "effective_plan_sha256": object_digest(effective),
                            "execution_plan_sha256": object_digest(execution),
                            "memory_sha256": object_digest(memory), "editor_sha256": object_digest(editor),
                            "diff_sha256": digest(diff.encode("utf-8")), "mappings": editor["mappings"],
                            "created_at": lineage["created_at"], "state": "staging_only", "semantic_preservation": "not_certified"}
                        require(lineage == expected, "Candidate lineage mismatch.")
                        records = candidate_records(root)
                        by_task = {p["task"]["id"]: p for p in parents}
                        require(len(records) <= len(parents) and len({r["task"]["id"] for r in records}) == len(records),
                                "Unexpected Candidate retry or task count.")
                        for record in records:
                            verify_record(record)
                            require(record["task"]["id"] in by_task and record["skill"] == skill, "Wrong Candidate task/Skill.")
                        if "learn_final" in report["stages"]:
                            require(len(records) == len(parents), "Final feedback is missing declared task executions.")
                            order = {r["task"]["id"]: r for r in records}
                            records = [order[p["task"]["id"]] for p in parents]
                            payload = build_learning_payload(initial["parent"], skill, diff, execution,
                                                             parents, records, memory=memory, origin="saved_before_execution")
                            final = check("learn_final", payload, validate_learning)
                            if final is not None:
                                require(read(root / "memory_final.json") == updated_memory(payload, final), "Final Memory mismatch.")
                                final_valid = True
                                matched = all(compare_records(by_task[r["task"]["id"]], r)["recorded_conditions_match"]
                                              and verify_record(r)["episode_complete"] for r in records)
                                terminal = "cycle_complete" if matched else "evaluation_incomplete"
                                require(report.get("initial_plan_sha256") == object_digest(diagnosis["plan"])
                                        and report.get("effective_plan_sha256") == object_digest(effective)
                                        and report.get("final_memory_count") == len(read(root / "memory_final.json")),
                                        "Reported plan/Memory summary differs from actual artifacts.")
                                require(all(report.get(key) == value for key, value in
                                            change_summary(root, diagnosis["plan"], effective, memory).items()),
                                        "Reported history/requirement changes differ from actual increments.")
    require(seen == report["stages"], "Stage ran without validated predecessor.")
    require(report["cost"] == cycle_cost(root), "Incremental cost mismatch.")
    require(report["status"] == terminal if terminal is not None else report["status"] in {"error", "interrupted"},
            "Terminal status is unsupported by validated stage outcomes.")
    require(not (root / "memory_final.json").exists() or final_valid, "Final Memory has no validated final learning call.")
    if report["status"] in {"error", "interrupted"}:
        require(not (root / "memory_final.json").exists(), "Failed cycle cannot publish final Memory.")
    return {"schema_version": "v22.compact_cycle_audit.v1", "artifact_valid": True,
            "cycle_complete": report["status"] == "cycle_complete", "stages_checked": seen,
            "scope": "Source/input/call/delta/diff/cost consistency only; no semantic or causal certification."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("source_round", type=Path)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    run.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    run.add_argument("--dry-run", action="store_true")
    audit = sub.add_parser("verify")
    audit.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "verify":
        print(json.dumps(verify_cycle(args.output_dir), ensure_ascii=False, indent=2))
        return 0
    plan = read(args.plan)
    _, _, parents = prepare_legacy(args.source_round)
    validate_plan(plan, parents)
    if args.dry_run:
        print(json.dumps({"inputs_verified": True, "task_ids": plan["task_ids"],
                          "semantic_calls_max": plan["semantic_calls_max"],
                          "new_parent_episodes": 0, "candidate_episodes_max": len(parents)}))
        return 0
    load_dotenv(args.env_file, override=False)
    key, base = os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    if not key or not base:
        parser.error("OPENAI_API_KEY and OPENAI_BASE_URL are required.")
    with requests.Session() as session:
        if ".intra." in base:
            session.trust_env = False
        generate = lambda stage, messages, output: semantic_call(stage, messages, session=session,
            endpoint=base + "/chat/completions", key=key, model=plan["evolution_model"], output=output)
        execute = lambda parent, skill, output: execute_with_adapter(parent, skill, output, args.env_file.resolve())
        result = run_cycle(args.source_round, args.output_dir, plan, generate, execute)
    print(json.dumps({"status": result["status"], "output": str(args.output_dir.resolve()),
                      "cost": result["cost"], "validation_error": result.get("validation_error")}, ensure_ascii=False, indent=2))
    return 1 if result["status"] in {"error", "interrupted", "evaluation_incomplete"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
