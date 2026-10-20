"""Evaluate unchanged Editor texts after exact numbered-list span reconciliation.

This separate operation preserves the original structural failure. It performs no
semantic calls, requirement changes, text repair, adoption, or feedback learning.
"""

import argparse
import json
from pathlib import Path

from src.adapters.alfworld.run_task import REPO_ROOT
from src.adapters.alfworld.run_task_skill import timestamp
from src.adapters.alfworld.skill_runtime import digest, load_skill, write_record
from src.adapters.alfworld.verify_skill_run import require, verify_record
from . import conditional_trial as trial
from .bounded_evaluation import execute_batch, selection_jobs, summarize_selection
from .compact_cycle import make_diff, read
from .editor_span_reconciliation import normalize_numbered_spans
from .evidence import verify_sources
from .run_round import cost_summary


def check(root):
    manifest = read(root / "manifest.json")
    verify_sources(manifest["sources"] + manifest["implementation"])
    frozen = read(root / "freeze.json")
    require(digest((root / "freeze.json").read_bytes()) == read(root / "report.json")["freeze_sha256"], "Freeze changed.")
    verify_sources(frozen["files"])
    return read(root / "execution_plan.json"), frozen


def prepare(config_path, output_dir):
    config_path, root = Path(config_path).resolve(), Path(output_dir).resolve()
    config = read(config_path)
    require(config["schema_version"] == "v22.reconciled_selection.v1"
            and config["semantic_calls"] == 0 and config["episode_retries"] == 0, "Unexpected recovery scope.")
    source = (REPO_ROOT / config["source_run"]).resolve()
    verified = trial.verify(source)
    original, plan = read(source / "report.json"), read(source / "plan.json")
    require(verified["status"] == "frozen" and not original["selection"]
            and not (source / "selection_schedule.json").exists(), "Only pre-evaluation frozen construction can be reconciled.")
    require(config["selection_task_ids"] == plan["selection_task_ids"]
            and config["environment_episodes_max"] == 3 * len(plan["selection_task_ids"]), "Evaluation set/budget changed.")
    originals = [p for p in source.rglob("*") if p.is_file()]
    code = [Path(__file__), Path(__file__).with_name("editor_span_reconciliation.py"),
            Path(__file__).with_name("bounded_evaluation.py")]
    root.mkdir(parents=True, exist_ok=False)
    write_record(root / "config.json", config)
    write_record(root / "execution_plan.json", plan)
    write_record(root / "manifest.json", {"sources": trial.bindings(originals + [config_path]),
                                         "implementation": trial.bindings(code), "prepared_at": timestamp()})
    arms = {"parent": {"skill_file": None, "skill_id": "none"}}
    alignment = {}
    for arm in trial.ARMS:
        require(read(source / "outputs" / f"{arm}_proposal.json")["decision"] == "ready", "Proposal was not ready.")
        payload = read(source / "inputs" / f"{arm}_editor.json")
        raw = read(source / "raw_outputs" / f"{arm}_editor.json")
        normalized = normalize_numbered_spans(raw, payload)
        require(normalized["decision"] == "candidate" and not payload["plan"]["open"], "No executable Candidate.")
        require(normalized["candidate_text"] == raw["candidate_text"], "Candidate text changed.")
        directory = root / "candidates" / arm
        directory.mkdir(parents=True)
        write_record(directory / "editor_normalized.json", normalized)
        (directory / "SKILL.md").write_text(raw["candidate_text"], encoding="utf-8")
        skill = load_skill(directory / "SKILL.md")
        (directory / "actual.diff").write_text(make_diff(load_skill(), skill), encoding="utf-8")
        write_record(directory / "observation_plan.json", {"watch": payload["plan"]["watch"] + normalized["watch"],
                                                           "origin": "before_selection"})
        arms[arm] = {"skill_file": str((directory / "SKILL.md").relative_to(root)), "skill_id": skill["skill_id"]}
        alignment[arm] = {"raw_mapping_count": len(raw["mappings"]), "normalized_mapping_count": len(normalized["mappings"]),
                          "candidate_text_unchanged": True, "source_status": original["branches"][arm]["status"]}
    write_record(root / "alignment.json", alignment)
    write_record(root / "freeze.json", {"frozen_at": timestamp(), "arms": arms,
        "files": trial.bindings([p for p in root.rglob("*") if p.is_file()]),
        "semantic_preservation": "not_certified", "scope": "Numbered-list quote alignment only; no Skill or requirement changes."})
    report = {"status": "frozen", "source_status": verified["status"], "source_cost": verified["cost"],
              "selection": [], "adoption": "staging_only", "freeze_sha256": digest((root / "freeze.json").read_bytes())}
    write_record(root / "report.json", report)
    return verify(root)


def evaluate(root, env_file):
    plan, frozen = check(root)
    report = read(root / "report.json")
    require(report["status"] == "frozen", "Evaluation is single-use.")
    report.update(status="evaluating", started_at=timestamp())
    write_record(root / "report.json", report)
    jobs = selection_jobs(plan, frozen, root)
    write_record(root / "schedule.json", jobs)
    report["selection"] = execute_batch(jobs, root / "runs", plan, env_file)
    check(root)
    records = [read(p) for p in sorted((root / "runs").glob("**/trajectory.json"))]
    report.update(status="evaluated", finished_at=timestamp(), cost=cost_summary(records, [], root))
    report["cost"]["scope"] = "Selection requests only. Source Train and five semantic calls are reported separately once. No recovery model call."
    write_record(root / "report.json", report)
    write_record(root / "evaluation_summary.json", summarize_selection(report["selection"]))
    return verify(root)


def verify(root):
    plan, frozen = check(root)
    report, config = read(root / "report.json"), read(root / "config.json")
    source = REPO_ROOT / config["source_run"]
    for arm in trial.ARMS:
        raw = read(source / "raw_outputs" / f"{arm}_editor.json")
        payload = read(source / "inputs" / f"{arm}_editor.json")
        require(read(root / f"candidates/{arm}/editor_normalized.json") == normalize_numbered_spans(raw, payload), "Alignment differs.")
        skill = load_skill(root / frozen["arms"][arm]["skill_file"])
        require(skill["text"] == raw["candidate_text"] and skill["skill_id"] == frozen["arms"][arm]["skill_id"], "Skill changed.")
    jobs = selection_jobs(plan, frozen, root)
    if (root / "schedule.json").exists():
        require(read(root / "schedule.json") == jobs, "Evaluation schedule changed.")
    rows = report["selection"]
    require(not (root / "calls").exists(), "Recovery cannot call an updater.")
    require((not rows and report["status"] != "evaluated")
            or [r["key"] for r in rows] == [j["key"] for j in jobs], "Evaluation order/count differs.")
    for row, job in zip(rows, jobs):
        require(all(row.get(key) == job[key] for key in ("key", "arm", "task_id", "split", "purpose", "skill_path")),
                "Saved evaluation identity differs from scheduled job.")
        if row.get("trajectory"):
            record = read(row["trajectory"])
            audit = verify_record(record)
            require(record["task"]["id"] == job["task_id"] and record["split"] == "val" and record["purpose"] == "selection"
                    and record["skill"]["skill_id"] == frozen["arms"][job["arm"]]["skill_id"]
                    and record["model"] == plan["actor_model"] and record["protocol"]["max_steps"] == plan["max_steps_per_episode"]
                    and record["started_at"] >= frozen["frozen_at"], "Frozen task/Skill/protocol boundary violation.")
            if row.get("audit") is not None:
                require(row["audit"] == audit, "Saved audit differs from trajectory.")
                expected = {"status": audit["status"], "steps": audit["steps_executed"],
                            "executed": audit["steps_executed"] > 0, "success": audit["native_success"],
                            "invalid_action_count": sum(event.get("action_in_admissible_commands") is False
                                                        for event in record["steps"] if event["phase"] == "executed")}
                require(all(row.get(k) == v for k, v in expected.items()), "Saved outcome differs from trajectory.")
            else:
                require(row["status"] == "error" and row["success"] is None,
                        "An unaudited execution must remain unknown.")
        else:
            require(row["status"] == "error" and row["success"] is None and row.get("audit") is None,
                    "A missing trajectory must remain unknown.")
    records = [read(p) for p in sorted((root / "runs").glob("**/trajectory.json"))]
    require(len(records) <= config["environment_episodes_max"], "Episode budget exceeded.")
    if report["status"] == "evaluated":
        actual = cost_summary(records, [], root)
        require(all(report["cost"][k] == v for k, v in actual.items() if k != "scope"), "Cost mismatch.")
        require(read(root / "evaluation_summary.json") == summarize_selection(rows), "Evaluation summary differs.")
    return {"status": report["status"], "source_status": report["source_status"], "adoption": "staging_only",
            "semantic_calls": 0, "candidate_texts_unchanged": True, "selection_episodes": len(records),
            "semantic_preservation": "not_certified", "cost": report.get("cost")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "evaluate", "verify"])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    args = parser.parse_args(argv)
    root = args.run_dir.resolve()
    if args.command == "prepare":
        result = prepare(args.config, root)
    elif args.command == "evaluate":
        result = evaluate(root, args.env_file)
    else:
        result = verify(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
