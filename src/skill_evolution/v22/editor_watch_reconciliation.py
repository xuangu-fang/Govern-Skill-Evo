"""Offline deduplication of exactly echoed inherited Editor watch questions.

This does not retry a model, repair semantics, execute a Candidate, or change the
original operation's status. The original call and every other field stay intact.
"""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import digest, load_skill, object_digest, write_record
from src.adapters.alfworld.verify_skill_run import require
from . import consume_fixed_plan as consumption
from .compact_cycle import editor_input, make_diff, read
from .compact_update import validate_editor
from .diagnosis_editor import parse_json_response
from .effective_update import editor_messages_effective
from .evidence import verify_sources
from .verify_round import verify_call


NORMALIZATION = "v22.editor_identical_inherited_watch.v1"


def normalize_inherited_watch(value, payload):
    """Remove only exact inherited-question echoes; all other validation remains."""
    require(isinstance(value, dict) and isinstance(value.get("watch"), list), "Editor watch must be an array.")
    inherited = {row["id"]: row for row in payload["plan"]["watch"]}
    normalized = deepcopy(value)
    normalized["watch"] = []
    for row in value["watch"]:
        require(isinstance(row, dict) and isinstance(row.get("id"), str), "Editor watch must contain identified question objects.")
        previous = inherited.get(row.get("id"))
        if previous is not None:
            require(row == previous, "Inherited watch differs; semantic changes cannot be normalized.")
        else:
            normalized["watch"].append(deepcopy(row))
    return validate_editor(normalized, payload)


def _source(source_operation, branch):
    source = Path(source_operation).resolve()
    require(branch in consumption.BRANCHES, "Unknown comparison branch.")
    checked = consumption.verify(source)
    require(checked["status"] in {"consumption_checked", "comparison_incomplete", "error", "interrupted"},
            "Only a terminal source operation can be reconciled.")
    report, plan = read(source / "report.json"), read(source / "plan.json")
    stage = branch + "_editor"
    require(stage in report["stages"], "Source branch has no recorded Editor call.")
    current, effective = read(source / "current.json"), read(source / f"{branch}_plan.json")
    memory = [] if branch == "current" else read(source / "memory_effective.json")
    payload = editor_input(current, effective, memory)
    require(read(source / "inputs" / f"{stage}.json") == payload, "Source Editor input differs from the effective Plan.")
    call_path = source / "calls" / f"{stage}.json"
    call = read(call_path)
    response = call["steps"][0].get("model_response")
    require(isinstance(response, dict), "Source Editor has no complete model response.")
    raw = parse_json_response(response.get("content"))
    verify_call(call_path, stage, plan["evolution_model"], editor_messages_effective(payload), raw)
    require(response.get("response_model") == plan["evolution_model"], "Source Editor response model mismatch.")
    normalized = normalize_inherited_watch(raw, payload)
    bindings = [{"path": str(path.resolve()), "sha256": digest(path.read_bytes())}
                for path in sorted(source.rglob("*")) if path.is_file()]
    derived = {"source_operation": str(source), "source_status": report["status"], "branch": branch,
               "call_path": str(call_path), "call_sha256": digest(call_path.read_bytes()),
               "raw_editor_sha256": object_digest(raw), "normalization": NORMALIZATION,
               "removed_inherited_watch": [row["id"] for row in raw["watch"]
                                            if row["id"] in {old["id"] for old in effective["watch"]}]}
    return source, payload, normalized, bindings, derived


def _lineage(payload, normalized, candidate, diff, derived):
    return {"parent": payload["parent"], "candidate": candidate,
            "effective_plan_sha256": object_digest(payload["plan"]),
            "editor_input_sha256": object_digest(payload), "normalized_editor_sha256": object_digest(normalized),
            "diff_sha256": digest(diff.encode("utf-8")), "mappings": normalized["mappings"],
            "derived_from": derived, "state": "staging_only", "executed": False,
            "semantic_preservation": "not_certified"}


def _report(normalized, derived):
    return {"schema_version": NORMALIZATION, "status": "offline_reconciled", "decision": normalized["decision"],
            "derived_from": derived, "adoption": "staging_only", "model_calls": 0, "environment_executions": 0,
            "scope": "Exact inherited-watch deduplication only. Original operation status is unchanged; semantic correctness and behavior remain unverified."}


def recover(source_operation, branch, output_dir):
    source, payload, normalized, bindings, derived = _source(source_operation, branch)
    root = Path(output_dir).resolve()
    require(root != source and source not in root.parents, "Output must be outside the source operation.")
    require(not root.exists(), "Recovery output already exists.")
    verify_sources(bindings)
    root.mkdir(parents=True)
    write_record(root / "manifest.json", {"source_operation": str(source), "branch": branch,
                                        "source_files": bindings, "normalization": NORMALIZATION})
    write_record(root / "input.json", payload)
    write_record(root / "editor.json", normalized)
    if normalized["decision"] == "candidate":
        path = root / "SKILL.md"
        path.write_bytes(normalized["candidate_text"].encode("utf-8"))
        candidate = load_skill(path)
        diff = make_diff(payload["parent"], candidate)
        (root / "actual.diff").write_text(diff, encoding="utf-8")
        write_record(root / "lineage.json", _lineage(payload, normalized, candidate, diff, derived))
    report = _report(normalized, derived)
    write_record(root / "report.json", report)
    verify_sources(bindings)
    return report


def verify(output_dir):
    root = Path(output_dir).resolve()
    manifest = read(root / "manifest.json")
    require(manifest["normalization"] == NORMALIZATION, "Unknown normalization version.")
    verify_sources(manifest["source_files"])
    _, payload, normalized, bindings, derived = _source(manifest["source_operation"], manifest["branch"])
    require(bindings == manifest["source_files"], "Source snapshot inventory changed.")
    require(read(root / "input.json") == payload, "Recovery input changed.")
    require(read(root / "editor.json") == normalized, "Recovery Editor differs beyond exact watch normalization.")
    require(read(root / "report.json") == _report(normalized, derived), "Recovery report/provenance changed.")
    if normalized["decision"] == "candidate":
        candidate = load_skill(root / "SKILL.md")
        require(candidate["text"] == normalized["candidate_text"], "Candidate text differs from the original Editor response.")
        diff = make_diff(payload["parent"], candidate)
        require((root / "actual.diff").read_text(encoding="utf-8") == diff, "Recovery diff changed.")
        require(read(root / "lineage.json") == _lineage(payload, normalized, candidate, diff, derived), "Recovery lineage changed.")
    else:
        require(not any((root / name).exists() for name in ("SKILL.md", "actual.diff", "lineage.json")),
                "Semantic stop cannot publish a Candidate.")
    return {"artifact_valid": True, "decision": normalized["decision"], "normalization": NORMALIZATION,
            "original_status": derived["source_status"], "executed": False, "semantic_preservation": "not_certified"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    recovery = commands.add_parser("recover")
    recovery.add_argument("source_operation", type=Path)
    recovery.add_argument("branch", choices=consumption.BRANCHES)
    recovery.add_argument("--output-dir", type=Path, required=True)
    audit = commands.add_parser("verify")
    audit.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    result = (verify(args.output_dir) if args.command == "verify"
              else recover(args.source_operation, args.branch, args.output_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
