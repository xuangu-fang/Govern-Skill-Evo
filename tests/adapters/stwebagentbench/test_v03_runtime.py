"""Tests for manifest-driven v03 runtime resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.adapters.stwebagentbench import skill_runtime
from src.adapters.stwebagentbench.run_evolution_train import load_train_tasks
from src.adapters.stwebagentbench.skill_runtime import load_method_skill
from src.adapters.stwebagentbench.summarize_evolution_selection import (
    _resolve_methods,
    build_report,
    render_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    REPO_ROOT / "experiments/manifests/stweb_suitecrm_poc_v03.json"
)


def make_row(method: str, task_success: bool, compliant: bool) -> dict:
    return {
        "task_id": 1,
        "method": method,
        "task_success": task_success,
        "compliant": compliant,
        "cup": task_success and compliant,
        "successful_but_violating": task_success and not compliant,
        "violation_count": 0 if compliant else 1,
        "violation_categories": {} if compliant else {"strict_execution": 1},
        "steps": 2,
    }


def test_v03_train_resolves_frozen_s1() -> None:
    manifest, tasks, method = load_train_tasks(MANIFEST_PATH)
    skill = load_method_skill(manifest, method)

    assert method == "governed_candidate_s1"
    assert len(tasks) == 51
    assert skill["version"] == "S1"
    assert skill["sha256"] == manifest["skill_evolution"]["parent"][
        "skill_sha256"
    ]
    assert skill["available"] is True


def test_v03_candidate_can_be_missing_before_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(skill_runtime, "REPO_ROOT", tmp_path)
    manifest = {
        "skill_evolution": {
            "candidate": {
                "method": "governed_candidate_s2",
                "skill_version": "S2",
                "candidate_id": "governed_candidate_s2",
                "skill_path": "skills/governed_candidate_s2_skill.md",
                "skill_sha256": None,
                "freeze_record_path": (
                    "skills/governed_candidate_s2_freeze.json"
                ),
            }
        }
    }
    skill = load_method_skill(
        manifest,
        "governed_candidate_s2",
        allow_missing=True,
    )
    assert skill["version"] == "S2"
    assert skill["available"] is False


def test_parent_candidate_summary_uses_s1_to_s2_labels() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert _resolve_methods(manifest, None, None) == (
        "governed_candidate_s1",
        "governed_candidate_s2",
    )
    report = build_report(
        [make_row("governed_candidate_s1", False, False)],
        [make_row("governed_candidate_s2", True, False)],
        "governed_candidate_s1",
        "governed_candidate_s2",
    )
    markdown = render_markdown(report)
    assert "# S1→S2 Selection结果汇总" in markdown
    assert "S2完成了任务" in markdown
