from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as runtime
from src.skill_evolution.autonomous_gse_v14_orchestrator import (
    OrchestrationContractError, _validate_rollout_bundle,
)
from src.skill_evolution.autonomous_gse_v14_proposal import group_task_evidence


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
BATCH_MAP = ROOT / "experiments/campaigns/autonomous_gse_v14/batch_map.json"
S0_PATH = "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md"
LINEAGE_FIELDS = (
    "source_id", "domain", "task_id", "rollout_index", "rollout_seed", "state",
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_cached_parent_artifacts(
    artifact_root: Path, task_ids: list[str], *, skill_path: str = S0_PATH,
) -> list[Path]:
    paths = []
    for tagged in task_ids:
        domain, task_id = tagged.split(":", 1)
        for rollout_index, rollout_seed in enumerate((200, 201, 202), start=1):
            source_id = f"step_01_parent_{domain}_{task_id}_rollout_{rollout_index:02d}"
            path = artifact_root / "rollouts/train/step_01_parent" / (
                f"{domain}_{task_id}_rollout_{rollout_index:02d}.json"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            value = {
                "domain": domain, "task_id": task_id, "phase": "train",
                "skill_version": "S0", "rollout_index": rollout_index,
                "rollout_seed": rollout_seed, "state": "compliant_success",
                "provenance": {"skill_id": "S0", "skill_path": skill_path},
                "governed_evidence": {
                    "source_id": source_id,
                    "trajectory": [{"step": 1, "event_type": "assistant"}],
                    "actions": [{"step": 1, "actor": "agent", "content": "done"}],
                    "task_success": True,
                    "process_feedback": {"compliant": True, "violated_policies": []},
                    "task_evaluation": {"reward": 1},
                    "compliance_evaluation": {"compliant": True},
                },
            }
            path.write_text(json.dumps(value), encoding="utf-8")
            paths.append(path)
    return paths


def test_cached_run_batch_enriches_evidence_and_preserves_rows_lineage(tmp_path, monkeypatch):
    campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
    batch = batch_map["batches"][0]
    artifact_root = tmp_path / "artifacts"
    paths = _write_cached_parent_artifacts(artifact_root, batch["task_ids"])
    before = {path: path.read_bytes() for path in paths}
    backend = runtime.EvolutionRolloutBackendV14(campaign, artifact_root=artifact_root)
    calls = 0

    def unexpected_rollout(**_kwargs):
        nonlocal calls
        calls += 1
        pytest.fail("Complete cached B1 artifacts must not trigger rollout execution")

    monkeypatch.setattr(backend, "_run_one", unexpected_rollout)
    bundle = backend.run_batch(
        step=1, task_ids=batch["task_ids"],
        skill={"skill_id": "S0", "skill_version": "S0", "skill_path": S0_PATH},
        role="parent",
    )

    assert calls == 0
    assert len(bundle["rows"]) == len(bundle["evidence"]) == 60
    for row, evidence in zip(bundle["rows"], bundle["evidence"], strict=True):
        assert {field: evidence[field] for field in LINEAGE_FIELDS} == {
            field: row[field] for field in LINEAGE_FIELDS
        }
        assert "trajectory_artifact_path" in row
        assert "trajectory_artifact_path" not in evidence
        assert {
            "source_id", "domain", "task_id", "rollout_index", "rollout_seed",
            "state", "trajectory", "task_success", "process_feedback",
        } <= set(evidence)
    assert {path: path.read_bytes() for path in paths} == before

    runtime.validate_learner_evidence(
        tuple(bundle["evidence"]), batch_task_ids=batch["task_ids"],
        protected_task_ids=runtime._protected_task_ids(batch_map),
    )
    _validate_rollout_bundle(bundle, batch=batch, require_evidence=True)
    groups = group_task_evidence(tuple(bundle["evidence"]))
    assert len(groups) == 20
    for (domain, task_id), group in groups:
        assert len(group) == 3
        assert {(item["domain"], item["task_id"]) for item in group} == {(domain, task_id)}
        assert [item["rollout_index"] for item in group] == [1, 2, 3]
        assert len({item["source_id"] for item in group}) == 3


@pytest.mark.parametrize("missing", ("domain", "task_id"))
def test_missing_task_identity_still_fails_closed(missing):
    batch_map = _load(BATCH_MAP)
    batch = batch_map["batches"][0]
    domain, task_id = batch["task_ids"][0].split(":", 1)
    evidence = {
        "source_id": "source_1", "domain": domain, "task_id": task_id,
        "rollout_index": 1, "rollout_seed": 200, "state": "compliant_success",
    }
    evidence.pop(missing)
    with pytest.raises(runtime.RuntimeContractError, match="outside the current Evolution batch"):
        runtime.validate_learner_evidence(
            (evidence,), batch_task_ids=batch["task_ids"],
            protected_task_ids=runtime._protected_task_ids(batch_map),
        )


@pytest.mark.parametrize("indexes", ((1, 2), (1, 1, 3)))
def test_missing_or_duplicate_rollout_index_fails_diagnosis_group_contract(indexes):
    evidence = tuple({
        "source_id": f"source_{position}", "domain": "airline", "task_id": "1",
        "rollout_index": rollout_index,
    } for position, rollout_index in enumerate(indexes, start=1))
    with pytest.raises(ValueError, match=(
        "TASK_GROUP_MUST_HAVE_EXACTLY_THREE_ROLLOUTS"
        if len(indexes) != 3 else "INVALID_OR_DUPLICATE_ROLLOUT_INDEX"
    )):
        group_task_evidence(evidence)


def test_bundle_contract_rejects_rows_evidence_lineage_drift():
    batch = {
        "batch_id": "batch_1",
        "task_ids": [
            *(f"airline:{index}" for index in range(10)),
            *(f"retail:{index}" for index in range(10)),
        ],
    }
    rows = []
    for tagged in batch["task_ids"]:
        domain, task_id = tagged.split(":", 1)
        for rollout_index in (1, 2, 3):
            rows.append({
                "source_id": f"{domain}_{task_id}_{rollout_index}",
                "domain": domain, "task_id": task_id, "rollout_index": rollout_index,
                "rollout_seed": 199 + rollout_index, "state": "compliant_success",
            })
    evidence = [dict(row) for row in rows]
    evidence[0]["task_id"] = "drifted"
    with pytest.raises(OrchestrationContractError, match="rows/evidence lineage drifted"):
        _validate_rollout_bundle(
            {"rows": rows, "evidence": evidence}, batch=batch, require_evidence=True,
        )
