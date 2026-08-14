"""Semantic tests for the S0 -> Candidate S1 experiment manifest."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    REPO_ROOT
    / "experiments"
    / "manifests"
    / "stweb_suitecrm_poc_v02.json"
)


def resolve(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    return path


def split_task_ids(manifest: dict, split: str) -> set[int]:
    return {
        task_id
        for template in manifest["splits"][split]["templates"]
        for task_id in template["task_ids"]
    }


def test_evolution_manifest_records_candidate_and_parent_split() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    parent_path = resolve(manifest["parent_manifest"]["path"])
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    candidate = manifest["skill_evolution"]["candidate"]

    assert manifest["status"] == "completed"
    assert manifest["manifest_id"] == "stweb_suitecrm_poc_v02"
    assert manifest["research_scope"]["primary_evaluation_unit"] == "task_id"
    assert manifest["research_scope"]["split_unit"] == "intent_template_id"
    assert manifest["research_scope"]["grouping_unit"] == "intent_template_id"
    assert manifest["splits"] == parent["splits"]
    assert resolve(candidate["skill_path"]).is_file()
    assert resolve(candidate["provenance_path"]).is_file()

    assert manifest["planned_rollouts"]["selection"]["methods"] == [
        "no_skill",
        "governed_candidate_s1",
    ]
    assert manifest["expected_counts"]["planned_selection_trajectories"] == 36
    assert manifest["planned_rollouts"]["test"]["status"] == (
        "locked_until_selection_decision"
    )


def test_evolution_manifest_records_reset_and_selection_runtime() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    reset = manifest["environment"]["database_reset_policy"]
    runtime = manifest["selection_runtime"]
    agent = runtime["agent"]
    runner = runtime["runner"]

    assert reset["timing"] == "before_every_trial"
    assert reset["shared_database_state_between_trials"] is False
    assert reset["execution_must_be_sequential"] is True
    assert resolve(reset["reset_script"]).is_file()
    assert resolve(reset["snapshot"]).is_file()

    assert runtime["status"] == "inherited_configuration"
    assert agent["requested_model"] == "openai/gpt-5.6-terra"
    assert agent["resolved_model"] == "gpt-5.6-terra"
    assert agent["api_parameters"] == {
        "temperature": 0.1,
        "max_tokens": 512,
    }
    assert agent["action_set"]["multiaction"] is False
    assert resolve(agent["implementation_path"]).is_file()
    assert resolve(runner["path"]).is_file()
    assert runner["headless"] is False
    assert runner["trials_per_task"] == 1
    assert runner["execution"] == "sequential"
    assert runner["database_reset_before_every_trial"] is True


def test_evolution_manifest_keeps_splits_disjoint_and_complete() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    train_ids = split_task_ids(manifest, "train")
    selection_ids = split_task_ids(manifest, "selection")
    test_ids = split_task_ids(manifest, "test")

    assert len(train_ids) == 51
    assert len(selection_ids) == 18
    assert len(test_ids) == 18
    assert not train_ids & selection_ids
    assert not train_ids & test_ids
    assert not selection_ids & test_ids
