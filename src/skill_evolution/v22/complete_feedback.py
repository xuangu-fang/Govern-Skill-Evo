"""One source-bound completion of failed final feedback, without new execution.

The failed cycle and its raw response remain immutable. This explicit operation
uses a separate scoped evidence view; it is not an automatic semantic retry.
"""

import argparse
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.adapters.alfworld.run_task import REPO_ROOT
from src.adapters.alfworld.run_task_skill import timestamp
from src.adapters.alfworld.skill_runtime import digest, object_digest, write_record
from src.adapters.alfworld.verify_skill_run import require
from .compact_cycle import read, updated_memory, verify_cycle
from .compact_learning import validate_learning
from .compact_learning_view import learning_messages_scoped
from .diagnosis_editor import parse_json_response
from .evidence import verify_sources
from .model_call import semantic_call
from .run_round import cost_summary
from .verify_round import verify_call


STAGE = "learn_final_scoped"


def prepare(source, plan):
    source = Path(source).resolve()
    verify_cycle(source)
    report = read(source / "report.json")
    require(report["status"] == "error" and report["active_stage"] == "learn_final",
            "Completion requires a failed final learning stage, not a new search.")
    require(not (source / "memory_final.json").exists(), "Source already has final Memory.")
    require(all(row["conditions"]["recorded_conditions_match"] and row["candidate_audit"]["episode_complete"]
                for row in report["comparisons"]) and len(report["comparisons"]) == 2,
            "This completion reuses two complete comparable executions.")
    require(plan["schema_version"] == "v22.feedback_completion_plan.v1"
            and plan["source_cycle"] == str(source.relative_to(REPO_ROOT))
            and plan["semantic_calls_max"] == 1 and plan["new_environment_episodes"] == 0
            and plan["semantic_retries"] == 0 and plan["evolution_model"] == "deepseek-v4-pro",
            "Unexpected completion scope/budget.")
    bindings = {str(p.resolve()): digest(p.read_bytes()) for p in source.rglob("*") if p.is_file()}
    paths = [(REPO_ROOT / item["path"]).resolve() for item in plan["prior_reports"]]
    require(len(set(paths)) == len(paths) and source / "report.json" in paths,
            "Cumulative cost must include this cycle exactly once.")
    for item in plan["prior_reports"]:
        path = (REPO_ROOT / item["path"]).resolve()
        require(digest(path.read_bytes()) == item["sha256"], "Prior cost report changed.")
        bindings[str(path)] = item["sha256"]
    require(sum(read(path)["cost"]["semantic_calls"] for path in paths) + 1 <= plan["cumulative_semantic_calls_max"],
            "Completion exceeds the declared cumulative semantic budget.")
    return read(source / "inputs/learn_final.json"), [
        {"path": path, "sha256": sha} for path, sha in sorted(bindings.items())]


def costs(root, plan):
    incremental = cost_summary([], [], root)
    prior = [read(REPO_ROOT / item["path"])["cost"] for item in plan["prior_reports"]]
    rows = prior + [incremental]
    counters = ("environment_requests", "semantic_calls", "http_attempts", "requests_with_unknown_usage",
                "http_attempts_with_unknown_usage")
    cumulative = {key: sum(row[key] for row in rows) for key in counters}
    cumulative["reported_usage"] = {key: sum(row["reported_usage"].get(key, 0) for row in rows)
                                    for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    cumulative["scope"] = "All compact-cycle attempts plus this completion; reused pre-cycle source costs excluded. Unknown usage is not zero."
    return {"incremental": incremental, "cumulative": cumulative}


def run_completion(source, output_dir, plan, generate):
    payload, bindings = prepare(source, plan)
    source, root = Path(source).resolve(), Path(output_dir).resolve()
    require(root != source and source not in root.parents, "Completion must not alter source cycle.")
    root.mkdir(parents=True, exist_ok=False)
    (root / "calls").mkdir()
    write_record(root / "plan.json", plan)
    write_record(root / "input.json", payload)
    write_record(root / "manifest.json", {"source_cycle": str(source), "source_files": bindings,
        "plan_sha256": object_digest(plan), "implementation": {
            p.name: digest(p.read_bytes()) for p in Path(__file__).parent.glob("*.py")}})
    report = {"schema_version": "v22.feedback_completion_report.v1", "started_at": timestamp(),
              "status": "requesting", "adoption": "staging_only", "stage": STAGE,
              "scope": "Completion of final feedback only; the original error and identity Fusion remain unchanged."}
    write_record(root / "report.json", report)
    try:
        messages = learning_messages_scoped(payload)
        raw = generate(STAGE, messages, root / "calls" / f"{STAGE}.json")
        output = parse_json_response(raw)
        validate_learning(output, payload)
        verify_call(root / "calls" / f"{STAGE}.json", STAGE, plan["evolution_model"], messages, output)
        call = read(root / "calls" / f"{STAGE}.json")
        require(call["steps"][0]["model_response"]["response_model"] == plan["evolution_model"],
                "Evolution response model mismatch.")
        verify_sources(bindings)
        write_record(root / "output.json", output)
        memory = updated_memory(payload, output)
        write_record(root / "memory_final.json", memory)
        report.update(status="feedback_ready", final_memory_count=len(memory))
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "error", error_type=type(exc).__name__)
        if isinstance(exc, ValueError):
            report["validation_error"] = str(exc)
    finally:
        report.update(finished_at=timestamp(), cost=costs(root, plan))
        write_record(root / "report.json", report)
    return report


def verify_completion(output_dir):
    root = Path(output_dir).resolve()
    manifest, plan, report = [read(root / f"{name}.json") for name in ("manifest", "plan", "report")]
    payload, bindings = prepare(manifest["source_cycle"], plan)
    require(manifest["source_files"] == bindings and manifest["plan_sha256"] == object_digest(plan), "Completion bindings changed.")
    verify_sources(bindings)
    require(read(root / "input.json") == payload, "Completion input differs from frozen final feedback input.")
    require(report["adoption"] == "staging_only" and report["stage"] == STAGE, "Completion scope changed.")
    path = root / "calls" / f"{STAGE}.json"
    require(list((root / "calls").glob("*.json")) == [path], "Unexpected completion call count.")
    output_path = root / "output.json"
    output = read(output_path) if output_path.exists() else None
    verify_call(path, STAGE, plan["evolution_model"], learning_messages_scoped(payload), output)
    if output is not None:
        validate_learning(output, payload)
        require(read(path)["steps"][0]["model_response"]["response_model"] == plan["evolution_model"], "Response model mismatch.")
        memory = updated_memory(payload, output)
        require(read(root / "memory_final.json") == memory and report["final_memory_count"] == len(memory), "Final Memory differs from learning.")
        require(report["status"] == "feedback_ready", "Validated completion has wrong status.")
    else:
        require(report["status"] in {"error", "interrupted"} and not (root / "memory_final.json").exists(), "Unvalidated completion cannot publish Memory.")
    require(report["cost"] == costs(root, plan), "Completion cost differs from calls and all prior attempts.")
    return {"artifact_valid": True, "feedback_ready": output is not None,
            "scope": "Frozen sources, calls, references, Memory derivation and cumulative cost; not semantic certification."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("source_cycle", type=Path)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    verify = sub.add_parser("verify")
    verify.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "verify":
        print(json.dumps(verify_completion(args.output_dir), ensure_ascii=False, indent=2))
        return 0
    plan = read(args.plan)
    prepare(args.source_cycle, plan)
    load_dotenv(args.env_file, override=False)
    key, base = os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    if not key or not base:
        parser.error("OPENAI_API_KEY and OPENAI_BASE_URL are required.")
    with requests.Session() as session:
        if ".intra." in base:
            session.trust_env = False
        generate = lambda stage, messages, path: semantic_call(stage, messages, session=session,
            endpoint=base + "/chat/completions", key=key, model=plan["evolution_model"], output=path)
        result = run_completion(args.source_cycle, args.output_dir, plan, generate)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "feedback_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
