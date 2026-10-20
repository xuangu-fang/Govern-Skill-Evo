"""Bounded, fixed-draft consumption check: reconcile Memory, then two branches.

No Diagnosis regeneration, Actor execution, adoption, automatic retry or branch
selection. Old reports and prompts remain immutable. Semantic decisions are not
certified by this source and structure verifier.
"""

import argparse
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.adapters.alfworld.run_task import REPO_ROOT
from src.adapters.alfworld.run_task_skill import timestamp
from src.adapters.alfworld.skill_runtime import digest, load_skill, object_digest, write_record
from src.adapters.alfworld.verify_skill_run import require
from .compact_cycle import read, fusion_input, editor_input, make_diff
from .compact_update import apply_fusion, validate_editor
from .complete_feedback import verify_completion
from .diagnosis_editor import parse_json_response
from .effective_memory import (learning_messages_effective, validate_effective_learning,
                               apply_effective_memory)
from .effective_update import fusion_messages_effective, editor_messages_effective
from .evidence import verify_sources
from .model_call import semantic_call
from .run_round import cost_summary
from .verify_round import verify_call


DEFAULT_PLAN = REPO_ROOT / "experiments/methods/v22/04_fixed_consumption/config/plan.json"
BRANCHES = ("current", "history")
STAGES = ("memory", "current_fusion", "current_editor", "history_fusion", "history_editor")


def prepare(source, plan):
    source = Path(source).resolve()
    require(verify_completion(source)["feedback_ready"], "Source feedback is not ready.")
    require(plan["schema_version"] == "v22.fixed_consumption_plan.v1"
            and plan["source_completion"] == str(source.relative_to(REPO_ROOT))
            and plan["evolution_model"] == "deepseek-v4-pro"
            and plan["semantic_calls_max"] == 5 and plan["semantic_retries"] == 0
            and plan["new_environment_episodes"] == 0 and plan["branch_order"] == list(BRANCHES),
            "Plan differs from the bounded fixed-draft comparison.")
    cycle = Path(read(source / "manifest.json")["source_cycle"])
    current = read(cycle / "inputs/diagnosis.json")
    initial = read(cycle / "initial_plan.json")
    payload = read(source / "input.json")
    payload["memory"] = read(source / "memory_final.json")
    payload["reconciliation"] = "Re-read the same executions to correct knowledge and scope; no new execution or independent support."
    roots = [source, cycle]
    if plan.get("recovery_of"):
        failed = (REPO_ROOT / plan["recovery_of"]).resolve()
        checked = verify(failed)
        failed_report = read(failed / "report.json")
        require(checked["status"] == "error" and checked["stages_checked"] == ["memory"]
                and failed_report.get("validation_error") == "Semantic output was truncated; it cannot become a valid proposal."
                and not (failed / "memory_effective.json").exists(), "Recovery source is not the declared failed learning.")
        roots.append(failed)
    files = {str(p.resolve()): digest(p.read_bytes()) for root in roots
             for p in root.rglob("*") if p.is_file()}
    bindings = [{"path": path, "sha256": sha} for path, sha in sorted(files.items())]
    return payload, current, initial, bindings


def memory_contract(plan):
    profile = plan.get("memory_profile", "full_v1")
    if profile == "revision_only_v1":
        from .effective_reconciliation import (messages_reconciliation, validate_reconciliation,
                                                apply_reconciled_memory)
        return messages_reconciliation, validate_reconciliation, apply_reconciled_memory
    require(profile == "full_v1", "Unknown Memory profile.")
    return learning_messages_effective, validate_effective_learning, apply_effective_memory


def new_memory(payload, output, plan):
    return memory_contract(plan)[2](payload["memory"], output, object_digest(payload), payload)


def cost(root):
    value = cost_summary([], [], root)
    value["scope"] = "Only this consumption operation's semantic calls; zero new environment executions. Prior executions and learning are reused, not charged again. Unknown usage is not zero."
    return value


def invoke(root, report, plan, bindings, stage, payload, messages, validator, generate):
    require(stage in STAGES and stage not in report["stages"] and len(report["stages"]) < plan["semantic_calls_max"],
            "Duplicate or excess semantic stage.")
    verify_sources(bindings)
    report["stages"].append(stage)
    report["active_stage"] = stage
    write_record(root / "report.json", report)
    write_record(root / "inputs" / f"{stage}.json", payload)
    raw = generate(stage, messages, root / "calls" / f"{stage}.json")
    value = parse_json_response(raw)
    validator(value, payload)
    path = root / "calls" / f"{stage}.json"
    verify_call(path, stage, plan["evolution_model"], messages, value)
    require(read(path)["steps"][0]["model_response"]["response_model"] == plan["evolution_model"], "Response model mismatch.")
    verify_sources(bindings)
    write_record(root / "outputs" / f"{stage}.json", value)
    return value


def error_fields(exc):
    fields = {"status": "interrupted" if isinstance(exc, KeyboardInterrupt) else "error", "error_type": type(exc).__name__}
    if isinstance(exc, ValueError):
        fields["validation_error"] = str(exc)
    return fields


def learn(source, output_dir, plan, generate):
    payload, current, initial, bindings = prepare(source, plan)
    source, root = Path(source).resolve(), Path(output_dir).resolve()
    cycle = Path(read(source / "manifest.json")["source_cycle"]).resolve()
    protected_roots = [source, cycle]
    if plan.get("recovery_of"):
        protected_roots.append((REPO_ROOT / plan["recovery_of"]).resolve())
    require(all(root != protected and protected not in root.parents for protected in protected_roots),
            "Output must be outside all source operations.")
    root.mkdir(parents=True, exist_ok=False)
    for directory in ("inputs", "calls", "outputs"):
        (root / directory).mkdir()
    write_record(root / "plan.json", plan)
    write_record(root / "current.json", current)
    write_record(root / "initial_plan.json", initial)
    write_record(root / "manifest.json", {"source_completion": str(source), "source_files": bindings,
        "plan_sha256": object_digest(plan), "initial_plan_sha256": object_digest(initial),
        "current_sha256": object_digest(current), "implementation": {
            p.name: digest(p.read_bytes()) for p in Path(__file__).parent.glob("*.py")}})
    report = {"schema_version": "v22.fixed_consumption_report.v1", "started_at": timestamp(),
        "status": "learning", "active_stage": None, "stages": [], "branches": {},
        "adoption": "staging_only", "environment_executions": 0,
        "limitations": ["Single semantic sample per branch; no causal estimate of Memory benefit.",
                        "No new execution: requirement/text changes are not behavioral gain.",
                        "Some relevant knowledge is already in Parent; a Memory citation alone is not historical increment.",
                        "Source checks do not certify semantic truth or preservation."]}
    try:
        messages, validator, _ = memory_contract(plan)
        output = invoke(root, report, plan, bindings, "memory", payload, messages(payload), validator, generate)
        memory = new_memory(payload, output, plan)
        write_record(root / "memory_effective.json", memory)
        report.update(status="memory_ready", active_stage=None, memory_sha256=object_digest(memory))
    except (Exception, KeyboardInterrupt) as exc:
        report.update(error_fields(exc))
    report.update(updated_at=timestamp(), cost=cost(root))
    write_record(root / "report.json", report)
    return report


def branch_summary(initial, effective, fusion, memory, editor=None):
    ids = {row["id"] for row in memory}
    cited = sorted({ref for row in fusion["changes"] for ref in row["basis"] if ref in ids})
    return {"status": fusion["decision"] if editor is None else editor["decision"],
            "requirements_changed": initial["requirements"] != effective["requirements"],
            "requirement_text_changed": [r["text"] for r in initial["requirements"]] != [r["text"] for r in effective["requirements"]],
            "history_ids_cited_in_changes": cited, "effective_plan_sha256": object_digest(effective)}


def construct(output_dir, generate):
    root = Path(output_dir).resolve()
    require(verify(root)["status"] == "memory_ready", "Construct is a one-time continuation after valid Memory reconciliation.")
    manifest, plan, report = [read(root / f"{name}.json") for name in ("manifest", "plan", "report")]
    _, current, initial, bindings = prepare(manifest["source_completion"], plan)
    memory = read(root / "memory_effective.json")
    manifest["construction_implementation"] = {
        p.name: digest(p.read_bytes()) for p in Path(__file__).parent.glob("*.py")}
    write_record(root / "manifest.json", manifest)
    report["status"] = "constructing"
    for branch in BRANCHES:
        selected = [] if branch == "current" else memory
        try:
            payload = fusion_input(current, initial, selected)
            fusion = invoke(root, report, plan, bindings, branch + "_fusion", payload,
                            fusion_messages_effective(payload), apply_fusion, generate)
            effective = apply_fusion(fusion, payload)
            write_record(root / f"{branch}_plan.json", effective)
            result = branch_summary(initial, effective, fusion, selected)
            report["branches"][branch] = result
            if fusion["decision"] == "ready" and not effective["open"]:
                payload = editor_input(current, effective, selected)
                editor = invoke(root, report, plan, bindings, branch + "_editor", payload,
                                editor_messages_effective(payload), validate_editor, generate)
                result = branch_summary(initial, effective, fusion, selected, editor)
                report["branches"][branch] = result
                if editor["decision"] == "candidate":
                    directory = root / branch
                    directory.mkdir()
                    (directory / "SKILL.md").write_bytes(editor["candidate_text"].encode("utf-8"))
                    candidate = load_skill(directory / "SKILL.md")
                    diff = make_diff(current["parent"], candidate)
                    (directory / "actual.diff").write_text(diff, encoding="utf-8")
                    write_record(directory / "lineage.json", {"parent": current["parent"], "candidate": candidate,
                        "initial_plan_sha256": object_digest(initial), "effective_plan_sha256": object_digest(effective),
                        "memory_sha256": object_digest(selected), "editor_sha256": object_digest(editor),
                        "diff_sha256": digest(diff.encode("utf-8")), "mappings": editor["mappings"],
                        "state": "staging_only", "executed": False, "semantic_preservation": "not_certified"})
        except (Exception, KeyboardInterrupt) as exc:
            report["branches"][branch] = error_fields(exc)
            if isinstance(exc, KeyboardInterrupt):
                break
        finally:
            report.update(updated_at=timestamp(), cost=cost(root))
            write_record(root / "report.json", report)
    complete = len(report["branches"]) == 2 and all(r["status"] not in {"error", "interrupted"} for r in report["branches"].values())
    report.update(status="consumption_checked" if complete else "comparison_incomplete", active_stage=None,
                  updated_at=timestamp(), cost=cost(root))
    write_record(root / "report.json", report)
    return report


def verify(output_dir):
    root = Path(output_dir).resolve()
    manifest, plan, report = [read(root / f"{name}.json") for name in ("manifest", "plan", "report")]
    payload, current, initial, bindings = prepare(manifest["source_completion"], plan)
    require(bindings == manifest["source_files"] and object_digest(plan) == manifest["plan_sha256"], "Source/plan bindings changed.")
    verify_sources(bindings)
    require(read(root / "current.json") == current and read(root / "initial_plan.json") == initial, "Fixed current evidence/draft changed.")
    require(manifest["current_sha256"] == object_digest(current) and manifest["initial_plan_sha256"] == object_digest(initial), "Fixed draft/evidence identity changed.")
    require(report["adoption"] == "staging_only" and report["environment_executions"] == 0, "Scope changed.")
    require(report["stages"] == [s for s in STAGES if s in report["stages"]], "Invalid stage order/duplicates.")
    require(set(report["branches"]) <= set(BRANCHES), "Unknown comparison branch.")
    require({p.stem for p in (root / "calls").glob("*.json")} == set(report["stages"]), "Call/stage inventory mismatch.")
    checked = []

    def check(stage, expected, messages, validator):
        if stage not in report["stages"]:
            return None
        checked.append(stage)
        require(read(root / "inputs" / f"{stage}.json") == expected, "Stage input differs: " + stage)
        path = root / "outputs" / f"{stage}.json"
        value = read(path) if path.exists() else None
        verify_call(root / "calls" / f"{stage}.json", stage, plan["evolution_model"], messages, value)
        if value is not None:
            validator(value, expected)
            require(read(root / "calls" / f"{stage}.json")["steps"][0]["model_response"]["response_model"] == plan["evolution_model"], "Response model mismatch.")
        return value

    messages, validator, _ = memory_contract(plan)
    output = check("memory", payload, messages(payload), validator)
    completed_branches = {}
    if output is not None:
        memory = new_memory(payload, output, plan)
        require(read(root / "memory_effective.json") == memory and report.get("memory_sha256") == object_digest(memory), "Memory differs from recorded reconciliation.")
        for branch in BRANCHES:
            selected = [] if branch == "current" else memory
            f_input = fusion_input(current, initial, selected)
            fusion = check(branch + "_fusion", f_input, fusion_messages_effective(f_input), apply_fusion)
            if fusion is None:
                continue
            effective = apply_fusion(fusion, f_input)
            require(read(root / f"{branch}_plan.json") == effective, "Effective plan mismatch.")
            result = branch_summary(initial, effective, fusion, selected)
            if fusion["decision"] == "ready" and not effective["open"]:
                e_input = editor_input(current, effective, selected)
                editor = check(branch + "_editor", e_input, editor_messages_effective(e_input), validate_editor)
                if editor is None:
                    continue
                result = branch_summary(initial, effective, fusion, selected, editor)
                if editor["decision"] == "candidate":
                    candidate = load_skill(root / branch / "SKILL.md")
                    require(candidate["text"] == editor["candidate_text"], "Candidate differs from Editor.")
                    diff = make_diff(current["parent"], candidate)
                    require((root / branch / "actual.diff").read_text() == diff, "Candidate diff changed.")
                    lineage = {"parent": current["parent"], "candidate": candidate,
                        "initial_plan_sha256": object_digest(initial), "effective_plan_sha256": object_digest(effective),
                        "memory_sha256": object_digest(selected), "editor_sha256": object_digest(editor),
                        "diff_sha256": digest(diff.encode("utf-8")), "mappings": editor["mappings"],
                        "state": "staging_only", "executed": False, "semantic_preservation": "not_certified"}
                    require(read(root / branch / "lineage.json") == lineage, "Candidate lineage mismatch.")
            require(report["branches"].get(branch) == result, "Branch report differs from validated decisions.")
            completed_branches[branch] = result
    require(checked == report["stages"], "Stage ran without validated predecessor.")
    if len(completed_branches) == 2:
        require(report["status"] == "consumption_checked", "Complete comparison status mismatch.")
    elif report["status"] == "memory_ready":
        require(output is not None and checked == ["memory"] and not report["branches"], "Premature memory_ready state.")
    else:
        require(report["status"] in {"error", "interrupted", "comparison_incomplete"}, "Incomplete comparison cannot claim completion.")
    if output is None:
        require(not (root / "memory_effective.json").exists(), "Invalid learning published Memory.")
    for branch in BRANCHES:
        if branch not in completed_branches:
            require(not (root / branch / "SKILL.md").exists(), "Unvalidated branch published Candidate.")
            attempted = any(stage.startswith(branch + "_") for stage in report["stages"])
            if attempted:
                result = report["branches"].get(branch, {})
                require(result.get("status") in {"error", "interrupted"} and result.get("error_type"),
                        "Unvalidated branch cannot claim a semantic decision.")
            else:
                require(branch not in report["branches"], "Unattempted branch has a reported result.")
    require(report["cost"] == cost(root), "Cost differs from calls.")
    return {"artifact_valid": True, "status": report["status"], "stages_checked": checked,
            "scope": "Frozen draft/evidence, calls, decisions, revisions and actual text only; no semantic or behavioral certification."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    learning = commands.add_parser("learn")
    learning.add_argument("source_completion", type=Path)
    learning.add_argument("--output-dir", type=Path, required=True)
    learning.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    learning.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    construction = commands.add_parser("construct")
    construction.add_argument("output_dir", type=Path)
    construction.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    audit = commands.add_parser("verify")
    audit.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "verify":
        print(json.dumps(verify(args.output_dir), ensure_ascii=False, indent=2))
        return 0
    plan = read(args.plan if args.command == "learn" else args.output_dir / "plan.json")
    load_dotenv(args.env_file, override=False)
    key, base = os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    if not key or not base:
        parser.error("OPENAI_API_KEY and OPENAI_BASE_URL are required.")
    with requests.Session() as session:
        if ".intra." in base:
            session.trust_env = False
        generate = lambda stage, messages, path: semantic_call(stage, messages, session=session,
            endpoint=base + "/chat/completions", key=key, model=plan["evolution_model"], output=path)
        result = (learn(args.source_completion, args.output_dir, plan, generate) if args.command == "learn"
                  else construct(args.output_dir, generate))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"memory_ready", "consumption_checked"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
