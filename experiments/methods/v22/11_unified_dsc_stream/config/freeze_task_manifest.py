#!/usr/bin/env python3
"""Freeze the user-approved eight-plus-eight allocation without any episode.

The preceding 20-task shortage inventory stays byte-identical.  This separate
protocol amendment takes its existing hash-ranked 16 unused Train tasks in
order, first eight then last eight; it does not resample or inspect outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import inventory_tasks


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
APPROVED_INVENTORY_SHA256 = "823a9df387b77ff3ff9a9ec0f7271e257102ae60b6dcb6ddf9ed866e48848a5f"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def object_digest(value) -> str:
    # Matches src.adapters.alfworld.skill_runtime.object_digest without imports
    # that could initialize an environment or a live model client.
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8"))


def binding(path: Path) -> dict:
    return {"path": str(path.resolve().relative_to(ROOT)), "sha256": digest(path.read_bytes())}


def build_manifest() -> dict:
    inventory_path = HERE / "task_inventory.json"
    raw = inventory_path.read_bytes()
    assert digest(raw) == APPROVED_INVENTORY_SHA256, "Original task inventory changed"
    frozen = json.loads(raw)
    assert frozen == inventory_tasks.inventory(Path(frozen["data_root"])), "Task pool or historical sources changed"
    native = json.loads((ROOT / frozen["benchmark_train_source"]["path"]).read_bytes())
    native_by_id = {row["id"]: row for row in native}
    ranked_ids = [row["id"] for row in frozen["ranked_unused_candidates"]]
    assert len(ranked_ids) == len(set(ranked_ids)) == 16
    assert not set(ranked_ids) & set(frozen["excluded_ids"])
    round_ids = {"round1": ranked_ids[:8], "round2": ranked_ids[8:]}
    return {
        "protocol": "v22.grouped_continual.v4",
        "status": "frozen_before_live_execution",
        "benchmark_train_source": frozen["benchmark_train_source"],
        "authorization": {
            "date": "2026-10-16",
            "source": "Human task-scope clarification in the current experiment preparation conversation",
            "approved_scope": "两轮各 8 项，全部使用此前未接触的 Train；沿用已冻结 hash 排名，前 8 项为第一轮，后 8 项为第二轮。",
            "supersedes": "The initial provisional request for two rounds of ten tasks; no dataset expansion or old-task supplementation.",
            "execution_authorized": False,
        },
        "selection_policy": {
            "rule": frozen["selection_rule"],
            "amendment": "Keep the precomputed ranking unchanged and allocate first eight to round 1 and last eight to round 2. The original inventory records the rejected 20-task request and is not overwritten.",
            "inventory": binding(inventory_path),
            "inventory_generator": binding(HERE / "inventory_tasks.py"),
            "manifest_generator": binding(Path(__file__).resolve()),
            "historical_exclusion_ids_canonical_sha256": object_digest(frozen["excluded_ids"]),
            "historical_source_files_canonical_sha256": object_digest(frozen["source_files"]),
            "selected_historical_intersection": [],
            "pool_size": 39,
            "excluded_count": 23,
            "unused_count": 16,
            "outcome_based_selection": False,
            "family_quotas": False,
        },
        "learner_visibility": "Only runtime task requests and observed interactions. This manifest, gamefile names, native task_type, old outcomes, selection inventory and exclusion reasons are not learner inputs.",
        "rounds": [{"round": number, "task_ids": round_ids[f"round{number}"],
                    "tasks": [native_by_id[task_id] for task_id in round_ids[f"round{number}"]]}
                   for number in (1, 2)],
        "unique_tasks": 16,
        "strict_streaming_train": True,
        "task_ids_canonical_sha256": object_digest(round_ids),
        "environment_episodes_started_during_preparation": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--select-eights", action="store_true", help="Write the approved 8+8 manifest once; refuse a differing existing file")
    mode.add_argument("--check", action="store_true", help="Read-only exact reconstruction check")
    args = parser.parse_args()
    manifest = build_manifest()
    target = HERE / "task_manifest.json"
    encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check or target.exists():
        assert target.read_bytes() == encoded, "Manifest is missing or differs from the authorized frozen allocation"
    else:
        target.write_bytes(encoded)
    print(json.dumps({"manifest": str(target), "sha256": digest(encoded),
                      "round1": manifest["rounds"][0]["task_ids"], "round2": manifest["rounds"][1]["task_ids"],
                      "selected_historical_intersection": [], "read_only_check": args.check}, ensure_ascii=False))


if __name__ == "__main__":
    main()
