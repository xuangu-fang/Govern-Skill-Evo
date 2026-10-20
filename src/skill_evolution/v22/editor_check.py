"""One isolated v1 Editor construction check; no Candidate execution or adoption."""

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
from .diagnosis_editor import diagnosis_messages, editor_messages, parse_json_response, validate_diagnosis, validate_editor
from .editor_preservation import EDITOR_SCHEMA_V1
from .evidence import prepare_evidence, verify_sources
from .model_call import semantic_call
from .run_round import cost_summary
from .verify_round import verify_call


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def prepare_check(source_round):
    """Read only the old pre-execution inputs; no old Candidate or outcomes."""
    root = Path(source_round).resolve()
    names = ("plan.json", "parent.json", "diagnosis.json", "evidence.json", "sources.json", "calls/diagnosis.json")
    plan, parent, diagnosis, evidence, sources = [read(root / name) for name in names[:5]]
    require(parent == load_skill(), "This check uses a No Skill Parent.")
    _, rebuilt_sources, rebuilt_evidence = prepare_evidence([s["path"] for s in sources], plan)
    require(sources == rebuilt_sources and evidence == rebuilt_evidence, "Pre-execution source reconstruction mismatch.")
    validate_diagnosis(diagnosis, parent, evidence)
    verify_call(root / "calls/diagnosis.json", "diagnosis", plan["model"], diagnosis_messages(parent, evidence), diagnosis)
    payload = {"parent": parent, "diagnosis": diagnosis, "evidence": evidence}
    paths = [root / name for name in names] + [Path(s["path"]) for s in sources]
    bindings = [{"path": str(p.resolve()), "sha256": digest(p.read_bytes())} for p in paths]
    return payload, bindings, plan["model"]


def messages(payload):
    return editor_messages(payload["parent"], payload["diagnosis"], payload["evidence"], schema_version=EDITOR_SCHEMA_V1)


def check_cost(output):
    cost = cost_summary([], [], output)
    cost["scope"] = "Isolated Editor construction check only; zero environment requests. Original round costs are not repeated."
    return cost


def run_check(source_round, output_dir, generate):
    root, output = Path(source_round).resolve(), Path(output_dir).resolve()
    require(output != root and root not in output.parents, "Check must be outside the source round.")
    payload, bindings, model = prepare_check(root)
    output.mkdir(parents=True, exist_ok=False)
    (output / "calls").mkdir()
    write_record(output / "input.json", payload)
    write_record(output / "manifest.json", {"schema_version": "v22.editor_check_manifest.v1",
        "source_round": str(root), "source_files": bindings, "input_sha256": object_digest(payload),
        "model": model, "editor_schema": EDITOR_SCHEMA_V1,
        "budget": {"editor_calls": 1, "semantic_retries": 0, "environment_calls": 0},
        "implementation": {p.name: digest(p.read_bytes()) for p in Path(__file__).parent.glob("*.py")}})
    report = {"schema_version": "v22.editor_check.v1", "started_at": timestamp(), "status": "running",
              "scope": "New isolated construction, never retrospective approval of the old executed Candidate."}
    write_record(output / "report.json", report)
    try:
        raw = generate("editor", messages(payload), output / "calls/editor.json")
        value = validate_editor(parse_json_response(raw), payload["parent"], payload["diagnosis"], payload["evidence"])
        require(value["schema_version"] == EDITOR_SCHEMA_V1, "Editor check cannot downgrade to v0.")
        verify_sources(bindings)
        write_record(output / "editor.json", value)
        report.update(status={"candidate": "candidate_unexecuted", "needs_revision": "needs_revision", "no_change": "no_change"}[value["decision"]])
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "error", error_type=type(exc).__name__)
        if isinstance(exc, ValueError):
            report["validation_error"] = str(exc)
    finally:
        report.update(finished_at=timestamp(), incremental_cost=check_cost(output))
        write_record(output / "report.json", report)
    return report


def verify_check(output_dir):
    output = Path(output_dir)
    manifest, payload, report = [read(output / f"{n}.json") for n in ("manifest", "input", "report")]
    require(manifest["schema_version"] == "v22.editor_check_manifest.v1"
            and manifest["editor_schema"] == EDITOR_SCHEMA_V1
            and manifest["budget"] == {"editor_calls": 1, "semantic_retries": 0, "environment_calls": 0}, "Check scope mismatch.")
    verify_sources(manifest["source_files"])
    rebuilt, bindings, model = prepare_check(manifest["source_round"])
    require(rebuilt == payload and bindings == manifest["source_files"] and model == manifest["model"]
            and object_digest(payload) == manifest["input_sha256"], "Check input differs from pre-execution source.")
    value = read(output / "editor.json") if (output / "editor.json").exists() else None
    calls = list((output / "calls").glob("*.json"))
    require(len(calls) <= 1 and all(p.name == "editor.json" for p in calls), "Extra Editor check call.")
    if value is not None:
        validate_editor(value, payload["parent"], payload["diagnosis"], payload["evidence"])
        require(value["schema_version"] == EDITOR_SCHEMA_V1 and bool(calls), "Missing v1 check call.")
    if calls:
        verify_call(calls[0], "editor", model, messages(payload), value)
    expected = {"candidate": "candidate_unexecuted", "needs_revision": "needs_revision", "no_change": "no_change"}
    require(report["schema_version"] == "v22.editor_check.v1" and report["incremental_cost"] == check_cost(output), "Check report/cost mismatch.")
    if value is not None:
        require(report["status"] == expected[value["decision"]], "Check decision mismatch.")
    else:
        require(report["status"] in {"error", "interrupted"}, "Missing output for completed check.")
    require(not (output / "candidate_runs").exists() and not (output / "candidate").exists(), "Isolated check cannot execute or release a Candidate.")
    return {"artifact_valid": True, "check_complete": value is not None, "status": report["status"],
            "scope": "New Editor input/output and preservation declarations only; not semantic proof or retrospective approval."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("source_round", type=Path)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    run.add_argument("--dry-run", action="store_true")
    verify = sub.add_parser("verify")
    verify.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "verify":
        result = verify_check(args.output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["check_complete"] else 1
    payload, _, model = prepare_check(args.source_round)
    if args.dry_run:
        print(json.dumps({"verified": True, "editor_schema": EDITOR_SCHEMA_V1,
                          "proposals": len(payload["diagnosis"]["proposals"]), "environment_calls": 0}))
        return 0
    load_dotenv(args.env_file, override=False)
    key, base = os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    if not key or not base:
        parser.error("OPENAI_API_KEY and OPENAI_BASE_URL are required.")
    with requests.Session() as session:
        if ".intra." in base:
            session.trust_env = False
        generate = lambda stage, request, output: semantic_call(stage, request, session=session,
            endpoint=base + "/chat/completions", key=key, model=model, output=output)
        report = run_check(args.source_round, args.output_dir, generate)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] in {"error", "interrupted"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
