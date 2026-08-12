"""Integrity tests for the frozen S0 -> Candidate S1 experiment."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FREEZE_PATH = (
    REPO_ROOT
    / "experiments"
    / "results"
    / "stweb_suitecrm_poc_v01"
    / "skills"
    / "governed_candidate_s1_freeze.json"
)
MANIFEST_PATH = (
    REPO_ROOT
    / "experiments"
    / "manifests"
    / "stweb_suitecrm_poc_v02.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def test_candidate_freeze_matches_all_frozen_artifacts() -> None:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))

    assert freeze["status"] == "frozen_for_evolution_selection"
    assert freeze["integrity"]["candidate_artifacts"] == "passed"
    assert freeze["integrity"]["generation_source"] == (
        "post_generation_drift_recoverable"
    )

    for artifact_name in ("skill", "governed_experience", "provenance"):
        artifact = freeze[artifact_name]
        assert sha256_file(resolve(artifact["path"])) == artifact["sha256"]

    for artifact in freeze["supporting_artifacts"].values():
        assert sha256_file(resolve(artifact["path"])) == artifact["sha256"]

    for generator_name in ("generator", "shared_generator"):
        generator = freeze["generation"][generator_name]
        current_sha256 = sha256_file(resolve(generator["path"]))
        assert current_sha256 == generator["current_file_sha256_at_freeze"]
        assert generator["current_matches_generation"] is (
            current_sha256 == generator["generation_recorded_sha256"]
        )

    recovery = freeze["reproducibility"]["generation_source_recovery"]
    assert sha256_file(resolve(recovery["path"])) == recovery["sha256"]
    assert recovery["recovery_verified"] is True
    model = freeze["generation"]["model"]
    assert model["recorded_metadata_matches_effective_call"] is False
    assert model["effective_api_parameters_from_recovered_source"] == {
        "reasoning_effort": "low",
        "max_completion_tokens": 8000,
    }


def test_generation_time_sources_can_be_reconstructed(
    tmp_path: Path,
) -> None:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    recovery_ref = freeze["reproducibility"][
        "generation_source_recovery"
    ]
    recovery = json.loads(
        resolve(recovery_ref["path"]).read_text(encoding="utf-8")
    )

    assert recovery["status"] == (
        "source_recoverable_with_pinned_base_and_archived_patch"
    )

    for source_name, source in recovery["sources"].items():
        recipe = source["recovery"]
        patch_path = resolve(recipe["patch_path"])
        assert sha256_file(patch_path) == recipe["patch_sha256"]

        if recipe["type"] == "git_commit_plus_archived_patch":
            result = subprocess.run(
                [
                    "git",
                    "show",
                    f"{recipe['base_commit']}:{recipe['base_path']}",
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
            )
            base_bytes = result.stdout
        else:
            base_bytes = resolve(recipe["base_path"]).read_bytes()

        assert sha256_bytes(base_bytes) == recipe["base_sha256"]
        base_path = tmp_path / f"{source_name}_base.py"
        output_path = tmp_path / f"{source_name}_reconstructed.py"
        base_path.write_bytes(base_bytes)
        subprocess.run(
            [
                "patch",
                "-s",
                "-o",
                str(output_path),
                str(base_path),
                str(patch_path),
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        )
        assert sha256_file(output_path) == recipe["reconstructed_sha256"]
        assert recipe["reconstructed_sha256"] == source[
            "generation_recorded_sha256"
        ]


def test_evolution_manifest_freezes_candidate_and_parent_split() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    parent_path = resolve(manifest["parent_manifest"]["path"])
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    candidate = manifest["skill_evolution"]["candidate"]

    assert manifest["status"] == "frozen"
    assert manifest["manifest_id"] == "stweb_suitecrm_poc_v02"
    assert manifest["research_scope"]["primary_evaluation_unit"] == (
        "task_id"
    )
    assert manifest["research_scope"]["split_unit"] == (
        "intent_template_id"
    )
    assert manifest["research_scope"]["grouping_unit"] == (
        "intent_template_id"
    )
    assert sha256_file(parent_path) == manifest["parent_manifest"]["sha256"]
    assert manifest["splits"] == parent["splits"]

    assert manifest["planned_rollouts"]["selection"]["methods"] == [
        "no_skill",
        "governed_candidate_s1",
    ]
    assert manifest["expected_counts"]["planned_selection_trajectories"] == 36
    assert manifest["planned_rollouts"]["test"]["status"] == (
        "locked_until_selection_decision"
    )

    assert sha256_file(resolve(candidate["skill_path"])) == candidate[
        "skill_sha256"
    ]
    assert sha256_file(resolve(candidate["provenance_path"])) == candidate[
        "provenance_sha256"
    ]
    assert sha256_file(resolve(candidate["freeze_record_path"])) == candidate[
        "freeze_record_sha256"
    ]


def test_evolution_manifest_freezes_reset_and_selection_runtime() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    environment = manifest["environment"]
    reset = environment["database_reset_policy"]
    runtime = manifest["selection_runtime"]
    agent = runtime["agent"]
    runner = runtime["runner"]

    assert reset["timing"] == "before_every_trial"
    assert reset["shared_database_state_between_trials"] is False
    assert reset["execution_must_be_sequential"] is True
    assert sha256_file(resolve(reset["reset_script"])) == reset[
        "reset_script_sha256"
    ]
    assert sha256_file(resolve(reset["snapshot"])) == reset[
        "snapshot_sha256"
    ]
    assert reset["snapshot_sha256"] == environment[
        "database_snapshot_sha256"
    ]

    assert runtime["status"] == "inherited_configuration_and_frozen"
    assert agent["requested_model"] == "openai/gpt-5.6-terra"
    assert agent["resolved_model"] == "gpt-5.6-terra"
    assert agent["api_parameters"] == {
        "temperature": 0.1,
        "max_tokens": 512,
    }
    assert agent["action_set"]["multiaction"] is False
    assert sha256_file(resolve(agent["implementation_path"])) == agent[
        "implementation_sha256"
    ]
    assert sha256_file(resolve(runner["path"])) == runner["sha256"]
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
