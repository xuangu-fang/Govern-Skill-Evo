from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as old_v14
from src.skill_evolution import autonomous_gse_v14_tge_v1_runtime as runtime
from src.skill_evolution.distributional_gate_v14 import (
    build_distributional_gate_decision,
)
from src.skill_evolution.joint_distribution_v14 import (
    build_joint_distribution_report,
    distribution,
)


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_DIR = ROOT / "experiments/campaigns/autonomous_gse_v14_tge_v1"
CAMPAIGN_PATH = CAMPAIGN_DIR / "campaign_manifest.json"
BATCH_MAP_PATH = CAMPAIGN_DIR / "batch_map.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def campaign() -> dict:
    return _load(CAMPAIGN_PATH)


@pytest.fixture
def batch_map() -> dict:
    return _load(BATCH_MAP_PATH)


def test_frozen_splits_batches_and_family_integrity(campaign, batch_map):
    validated = runtime.validate_batch_map(batch_map, campaign)
    split_ids = validated["split_ids"]
    assert {name: len(ids) for name, ids in split_ids.items()} == {
        "train": 48,
        "monitor": 20,
        "test": 48,
    }
    batches = [
        {value.split(":", 1)[1] for value in batch["task_ids"]}
        for batch in batch_map["batches"]
    ]
    assert [len(ids) for ids in batches] == [16, 16, 16]
    assert set.union(*batches) == split_ids["train"]
    assert not any(left & right for index, left in enumerate(batches) for right in batches[index + 1 :])
    assert not set.union(*batches) & split_ids["monitor"]
    assert not set.union(*batches) & split_ids["test"]

    family_batches: dict[str, set[int]] = {}
    metadata = validated["metadata"]
    for index, ids in enumerate(batches, start=1):
        for task_id in ids:
            family_batches.setdefault(metadata[task_id]["family_id"], set()).add(index)
    assert all(len(indices) == 1 for indices in family_batches.values())


@pytest.mark.parametrize(
    ("operation", "allowed", "denied"),
    (
        ("rollout_for_evolution", "train", ("monitor", "test")),
        ("diagnosis", "train", ("monitor", "test")),
        ("targeted_replay", "train", ("monitor", "test")),
        ("selection", "monitor", ("train", "test")),
        ("bootstrap_gate", "monitor", ("train", "test")),
        ("final_evaluation", "test", ("train", "monitor")),
    ),
)
def test_split_access_fails_closed(operation, allowed, denied):
    runtime.assert_split_access(operation, allowed)
    for split in denied:
        with pytest.raises(runtime.TGEV1RuntimeContractError, match="cannot access"):
            runtime.assert_split_access(operation, split)


def test_all_frozen_evaluator_routes_resolve(campaign):
    _, metadata, _, split_ids = runtime.load_frozen_assets(campaign)
    routes = {split: [] for split in split_ids}
    for split, task_ids in split_ids.items():
        routes[split] = [runtime.evaluator_route(metadata[task_id]) for task_id in task_ids]
        assert all(route["task_success"] == "tge_v1" for route in routes[split])
    assert any(route["compliance"] == "ordering" for route in routes["train"])
    assert any(route["compliance"] == "ordering" for route in routes["monitor"])
    assert all(route["compliance"] != "composition" for route in routes["train"])
    assert all(route["compliance"] != "composition" for route in routes["monitor"])
    assert sum(route["compliance"] == "composition" for route in routes["test"]) == 16


def test_campaign_contract_and_frozen_hashes(campaign, batch_map):
    runtime.validate_campaign_contract(campaign)
    assert runtime.validate_frozen_hashes(campaign) == campaign["frozen_hashes"]
    assert runtime.validate_batch_map(batch_map, campaign)["split_ids"]
    assert campaign["test_policy"]["held_out"] is True
    assert campaign["test_policy"]["allowed_during_evolution"] is False
    assert campaign["test_policy"]["allowed_for_selection"] is False
    assert campaign["test_policy"]["allowed_for_diagnosis"] is False


def test_hash_and_batch_map_drift_fail_closed(campaign, batch_map, tmp_path):
    drifted_campaign = copy.deepcopy(campaign)
    drifted_campaign["frozen_hashes"]["split_manifest"] = "0" * 64
    with pytest.raises(runtime.TGEV1RuntimeContractError, match="hashes"):
        runtime.validate_frozen_hashes(drifted_campaign)

    batch_path = tmp_path / "batch_map.json"
    drifted_map = copy.deepcopy(batch_map)
    drifted_map["batches"][0]["task_ids"][0] = drifted_map["batches"][1]["task_ids"][0]
    batch_path.write_text(json.dumps(drifted_map), encoding="utf-8")
    drifted_campaign = copy.deepcopy(campaign)
    drifted_campaign["evolution"]["batch_map"] = str(batch_path)
    drifted_campaign["frozen_hashes"]["batch_map"] = runtime._sha256(batch_path)
    with pytest.raises(runtime.TGEV1RuntimeContractError):
        runtime.validate_batch_map(drifted_map, drifted_campaign)


def test_artifact_root_isolated_and_resume_is_locked(campaign, tmp_path):
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    artifact_root = tmp_path / "formal"
    runtime.prepare_artifact_root(
        mode="run",
        artifact_root=artifact_root,
        campaign_path=campaign_path,
        campaign=campaign,
    )
    assert (artifact_root / "runtime_lock.json").is_file()
    with pytest.raises(runtime.TGEV1RuntimeContractError, match="not empty"):
        runtime.prepare_artifact_root(
            mode="run",
            artifact_root=artifact_root,
            campaign_path=campaign_path,
            campaign=campaign,
        )
    (artifact_root / "campaign_state.json").write_text("{}", encoding="utf-8")
    runtime.prepare_artifact_root(
        mode="resume",
        artifact_root=artifact_root,
        campaign_path=campaign_path,
        campaign=campaign,
    )
    lock = _load(artifact_root / "runtime_lock.json")
    lock["runtime_version"] = "drifted"
    (artifact_root / "runtime_lock.json").write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(runtime.TGEV1RuntimeContractError, match="mismatch"):
        runtime.prepare_artifact_root(
            mode="resume",
            artifact_root=artifact_root,
            campaign_path=campaign_path,
            campaign=campaign,
        )


def test_plan_is_static_and_does_not_create_formal_state(campaign, batch_map, tmp_path, monkeypatch):
    monkeypatch.setattr(
        runtime,
        "_run_task",
        lambda *args, **kwargs: pytest.fail("plan attempted a rollout"),
    )
    plan = runtime.build_campaign_dry_plan(campaign, batch_map)
    assert plan["validation"] == {
        "status": "PASS",
        "train_tasks": 48,
        "monitor_tasks": 20,
        "test_tasks": 48,
        "batch_sizes": [16, 16, 16],
        "batch_union_is_train": True,
        "batch_intersection_empty": True,
        "test_held_out": True,
        "test_denied_to_evolution": True,
        "test_denied_to_selection": True,
        "all_evaluator_routes_resolve": True,
        "frozen_hashes_match": True,
        "llm_calls": 0,
        "rollouts": 0,
        "formal_run_state_created": False,
    }
    assert [step["parent_trajectories"] for step in plan["steps"]] == [48, 48, 48]
    assert plan["evaluators"]["route_counts"] == {
        "atomic": 70,
        "ordering": 30,
        "composition": 16,
    }
    assert not (tmp_path / "formal" / "campaign_state.json").exists()


def _airline_monitor(skill_id: str, state: str = "CS") -> dict:
    success, compliant = {
        "CS": (True, True), "VS": (True, False),
        "CF": (False, True), "VF": (False, False),
    }[state]
    task_ids = [f"airline:task_{index:02d}" for index in range(20)]
    rows = []
    for tagged in task_ids:
        task_id = tagged.split(":", 1)[1]
        for rollout_index, seed in enumerate((200, 201, 202), start=1):
            rows.append({
                "source_id": f"{skill_id}_{task_id}_{rollout_index}",
                "domain": "airline",
                "task_id": task_id,
                "rollout_index": rollout_index,
                "rollout_seed": seed,
                "skill_id": skill_id,
                "skill_version": skill_id,
                "task_success": success,
                "compliant": compliant,
                "state": {
                    "CS": "compliant_success", "VS": "violating_success",
                    "CF": "compliant_failure", "VF": "violating_failure",
                }[state],
                "state_code": state,
                "trajectory_artifact_path": f"/tmp/{skill_id}_{task_id}_{rollout_index}.json",
            })
    result = {
        "schema_version": "autonomous_gse_monitor_result_0.14.0",
        "campaign_id": "autonomous_gse_v14_tge_v1",
        "monitor_id": "fixed_monitor_m",
        "skill_artifact_contract": "immutable_identity",
        "skill": {"skill_id": skill_id, "skill_version": skill_id, "skill_path": f"{skill_id}.md"},
        "task_ids": task_ids,
        "rollouts_per_task": 3,
        "rows": rows,
    }
    result["summary"] = distribution(rows)
    return result


def test_single_airline_stratum_preserves_v14_gate_semantics():
    parent = _airline_monitor("parent")
    candidate = _airline_monitor("candidate")
    report = build_joint_distribution_report(parent, candidate)
    decision = build_distributional_gate_decision(report)
    assert decision["bootstrap"]["domain_tasks_per_replicate"] == {"airline": 20}
    assert decision["bootstrap"]["replicates"] == 10_000
    assert decision["bootstrap"]["seed"] == 200
    assert decision["gate"]["positive_probability_threshold"] == 0.8
    assert decision["gate"]["decision"] == "RETAIN"


def test_old_v14_runtime_and_campaign_still_validate():
    old_campaign = _load(ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json")
    old_batch_map = _load(ROOT / "experiments/campaigns/autonomous_gse_v14/batch_map.json")
    old_v14.validate_campaign_contract(old_campaign)
    old_v14.validate_batch_map(old_batch_map, old_campaign)

