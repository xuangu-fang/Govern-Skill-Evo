"""Integrity tests for the v03 implementation binding."""

from __future__ import annotations

import json
from pathlib import Path

from src.learners.stwebagentbench.generate_governed_s2 import (
    MAX_ADDS,
    MAX_DELETES,
    MAX_EDITS,
    MAX_REPLACES,
)
from src.skill_evolution.implementation_binding import (
    require_implementation_binding,
    sha256_file,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    REPO_ROOT / "experiments/manifests/stweb_suitecrm_poc_v03.json"
)
FREEZE_PATH = (
    REPO_ROOT
    / "experiments/results/stweb_suitecrm_poc_v03/preregistration/"
    "implementation_freeze.json"
)


def test_v03_implementation_binding_matches_all_bound_files() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    freeze = require_implementation_binding(MANIFEST_PATH, manifest)

    assert freeze is not None
    assert freeze["status"] == "bound_for_formal_execution"
    assert freeze["scope"]["formal_rollouts_started_before_binding"] is False
    assert freeze["scope"]["test_remains_sealed"] is True


def test_v03_freezes_exact_incremental_edit_bound() -> None:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    assert freeze["edit_bound"] == {
        "maximum_total": MAX_EDITS,
        "maximum_add": MAX_ADDS,
        "maximum_replace": MAX_REPLACES,
        "maximum_delete": MAX_DELETES,
        "every_edit_requires_fresh_s1_train_source": True,
        "repair_requires_violated_policy_source": True,
        "replace_or_delete_requires_exact_parent_clause": True,
        "duplicate_candidate_rules_forbidden": True,
        "empty_valid_patch_result": "no_candidate",
    }


def test_v03_manifest_and_parent_skill_are_bitwise_frozen() -> None:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    assert sha256_file(MANIFEST_PATH) == freeze["manifest"]["sha256"]
    parent = freeze["immutable_inputs"]["parent_skill"]
    assert sha256_file(REPO_ROOT / parent["path"]) == parent["sha256"]
