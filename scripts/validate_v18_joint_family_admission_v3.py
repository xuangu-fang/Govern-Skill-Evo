#!/usr/bin/env python3
"""Validate the frozen one-seed Joint Family Admission Contract v3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO / "experiments/configs/v18_joint_family_admission_003"
CONTRACT = CONFIG_DIR / "admission_contract.json"
MANIFEST = CONFIG_DIR / "manifest.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    design = contract["replication_design"]
    if contract["contract_id"] != "v18-joint-family-admission-3":
        raise ValueError("Unexpected contract id")
    if design["splits"] != ["train", "monitor"]:
        raise ValueError("Train and Monitor must remain separate")
    if design["fresh_task_variants_per_split"] != 4 or design["seeds_per_task"] != 1:
        raise ValueError("Contract v3 requires four variants and one seed per split")
    if len(design["predeclared_seeds"]) != 1:
        raise ValueError("Exactly one seed must be predeclared")
    expected = len(design["splits"]) * design["fresh_task_variants_per_split"] * design["seeds_per_task"] * len(design["conditions"])
    if expected != design["total_rollouts"] or expected != 32:
        raise ValueError("Planned rollout count must be 32")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["admission_contract_sha256"] != digest(CONTRACT):
        raise ValueError("Admission contract digest drift")
    if manifest["validator_sha256"] != digest(Path(__file__)):
        raise ValueError("Admission validator digest drift")
    print(json.dumps({"status": "PASS", "contract_id": contract["contract_id"], "planned_rollouts": expected}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
