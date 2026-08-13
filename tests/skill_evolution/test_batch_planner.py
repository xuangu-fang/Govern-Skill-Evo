from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from src.skill_evolution.batch_planner import (
    assignment_sha256,
    build_batch_map,
    build_from_campaign_manifest,
    canonical_json_bytes,
    write_frozen_batch_map,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_MANIFEST_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
)
SOURCE_MANIFEST_PATH = (
    PROJECT_ROOT / "experiments/manifests/stweb_suitecrm_poc_v01.json"
)
FROZEN_BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v01/batch_map.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_actual_batch_map(source_manifest: dict | None = None) -> dict:
    campaign = load_json(CAMPAIGN_MANIFEST_PATH)
    source = source_manifest or load_json(SOURCE_MANIFEST_PATH)
    binding = campaign["train"]["source_manifest"]
    return build_batch_map(
        source,
        campaign_id=campaign["campaign_id"],
        seed=campaign["train"]["assignment_seed"],
        source_path=binding["path"],
        source_sha256=binding["sha256"],
    )


def test_actual_train_split_becomes_three_balanced_batches() -> None:
    batch_map = build_actual_batch_map()
    source = load_json(SOURCE_MANIFEST_PATH)
    expected_task_ids = {
        task_id
        for template in source["splits"]["train"]["templates"]
        for task_id in template["task_ids"]
    }
    observed_task_ids: list[int] = []

    assert batch_map["status"] == "frozen"
    assert batch_map["assignment"]["algorithm"] == "sha256_rank_v01"
    assert len(batch_map["batches"]) == 3

    for expected_rank, batch in enumerate(batch_map["batches"], start=1):
        assert batch["batch_id"] == f"batch_{expected_rank:03d}"
        assignments = batch["assignments"]
        task_ids = [item["task_id"] for item in assignments]
        template_ids = [item["intent_template_id"] for item in assignments]
        assert len(task_ids) == len(set(task_ids)) == 17
        assert len(template_ids) == len(set(template_ids)) == 17
        observed_task_ids.extend(task_ids)

    assert len(observed_task_ids) == len(set(observed_task_ids)) == 51
    assert set(observed_task_ids) == expected_task_ids


def test_frozen_batch_map_matches_bound_planner_and_manifest_hash() -> None:
    campaign = load_json(CAMPAIGN_MANIFEST_PATH)
    regenerated = build_from_campaign_manifest(CAMPAIGN_MANIFEST_PATH)
    frozen_bytes = FROZEN_BATCH_MAP_PATH.read_bytes()
    digest = hashlib.sha256(frozen_bytes).hexdigest()

    assert frozen_bytes == canonical_json_bytes(regenerated)
    assert digest == campaign["train"]["batch_map"]["sha256"]
    assert not FROZEN_BATCH_MAP_PATH.with_suffix(".sha256").exists()


def test_assignment_uses_frozen_digest_material() -> None:
    seed = "campaign-seed"
    expected = hashlib.sha256(b"campaign-seed\n2000\n47").hexdigest()

    assert assignment_sha256(seed, 2000, 47) == expected


def test_same_semantic_input_is_byte_stable_despite_source_order() -> None:
    source = load_json(SOURCE_MANIFEST_PATH)
    reordered = copy.deepcopy(source)
    reordered["splits"]["train"]["templates"].reverse()
    for template in reordered["splits"]["train"]["templates"]:
        template["task_ids"].reverse()

    original_bytes = canonical_json_bytes(build_actual_batch_map(source))
    reordered_bytes = canonical_json_bytes(build_actual_batch_map(reordered))

    assert reordered_bytes == original_bytes


def test_result_fields_cannot_influence_assignment() -> None:
    source = load_json(SOURCE_MANIFEST_PATH)
    with_results = copy.deepcopy(source)
    for index, template in enumerate(
        with_results["splits"]["train"]["templates"]
    ):
        template.update(
            {
                "task_success": index % 2 == 0,
                "compliance": index % 3 == 0,
                "cup": index,
                "historical_gate_decision": "accept" if index else "reject",
                "violations": ["synthetic"],
            }
        )

    assert canonical_json_bytes(build_actual_batch_map(with_results)) == (
        canonical_json_bytes(build_actual_batch_map(source))
    )


def test_different_seed_changes_assignment() -> None:
    source = load_json(SOURCE_MANIFEST_PATH)
    campaign = load_json(CAMPAIGN_MANIFEST_PATH)
    binding = campaign["train"]["source_manifest"]
    changed = build_batch_map(
        source,
        campaign_id=campaign["campaign_id"],
        seed="different-campaign-seed",
        source_path=binding["path"],
        source_sha256=binding["sha256"],
    )

    original_pairs = [
        [item["task_id"] for item in batch["assignments"]]
        for batch in build_actual_batch_map(source)["batches"]
    ]
    changed_pairs = [
        [item["task_id"] for item in batch["assignments"]]
        for batch in changed["batches"]
    ]
    assert changed_pairs != original_pairs


@pytest.mark.parametrize(
    "mutation",
    [
        lambda train: train.update({"template_count": 16}),
        lambda train: train.update({"task_count": 50}),
        lambda train: train["templates"].pop(),
        lambda train: train["templates"][0]["task_ids"].pop(),
        lambda train: train["templates"][1]["task_ids"].__setitem__(
            0, train["templates"][0]["task_ids"][0]
        ),
    ],
)
def test_rejects_malformed_train_split(mutation) -> None:
    source = load_json(SOURCE_MANIFEST_PATH)
    mutation(source["splits"]["train"])

    with pytest.raises(ValueError):
        build_actual_batch_map(source)


def test_campaign_binding_verifies_source_manifest_hash(tmp_path: Path) -> None:
    campaign = load_json(CAMPAIGN_MANIFEST_PATH)
    campaign["train"]["source_manifest"]["sha256"] = "0" * 64
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        build_from_campaign_manifest(campaign_path)


def test_frozen_output_has_matching_hash_and_cannot_be_overwritten(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "batch_map.json"
    payload = build_actual_batch_map()
    expected_bytes = canonical_json_bytes(payload)
    expected_digest = hashlib.sha256(expected_bytes).hexdigest()

    digest = write_frozen_batch_map(output_path, payload)

    assert digest == expected_digest
    assert output_path.read_bytes() == expected_bytes
    assert not output_path.with_suffix(".sha256").exists()
    with pytest.raises(FileExistsError):
        write_frozen_batch_map(output_path, payload)
