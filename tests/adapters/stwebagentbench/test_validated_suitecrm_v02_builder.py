import json

import pytest

from src.adapters.stwebagentbench.validated_suitecrm import sha256_file
from src.adapters.stwebagentbench import validated_suitecrm_v02 as builder


@pytest.fixture()
def v02_build(tmp_path, monkeypatch):
    artifact_dir = tmp_path / "benchmark"
    formal_manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(builder, "ARTIFACT_DIR", artifact_dir)
    monkeypatch.setattr(builder, "FORMAL_MANIFEST", formal_manifest)
    before = (
        {p.name: sha256_file(p) for p in builder.V01_DIR.glob("*.json")},
        sha256_file(builder.V01_MANIFEST),
    )
    builder.build()
    return artifact_dir, before


def test_v02_build_preserves_v01_and_only_changes_hallucination_metadata(v02_build):
    artifact_dir, before = v02_build
    after = (
        {p.name: sha256_file(p) for p in builder.V01_DIR.glob("*.json")},
        sha256_file(builder.V01_MANIFEST),
    )
    assert before == after
    v01 = {t["task_id"]: t for t in json.loads((builder.V01_DIR / "validated_tasks.json").read_text())}
    v02 = {t["task_id"]: t for t in json.loads((artifact_dir / "validated_tasks.json").read_text())}
    assert set(v01) == set(v02) and len(v02) == 52
    for task_id in v01:
        assert v01[task_id]["eval"] == v02[task_id]["eval"]
        for old, new in zip(v01[task_id]["policies"], v02[task_id]["policies"], strict=True):
            if (old["eval"].get("eval_types") or [None])[0] == "is_input_hallucination":
                stripped = dict(new["eval"])
                stripped.pop("authorized_facts")
                stripped.pop("normalization_version")
                stripped.pop("field_identification")
                assert stripped == old["eval"]
            else:
                assert new == old


def test_v02_static_hallucination_audit_is_fail_closed(v02_build):
    artifact_dir, _ = v02_build
    report = json.loads((artifact_dir / "validation_report.json").read_text())
    audit = report["hallucination_normalization"]
    assert audit["unresolved_field_count"] == 0
    assert audit["ambiguous_normalization_count"] == 0
    assert audit["missing_source_count"] == 0
    assert audit["invalid_source_fingerprint_count"] == 0
    assert audit["task_specific_exception_count"] == 0
    assert audit["global_wildcard_authorization_count"] == 0
    assert audit["value_only_broad_exemption_count"] == 0


def test_v02_holdout_plan_is_frozen_train_only_and_non_overlapping(v02_build):
    artifact_dir, _ = v02_build
    canary = json.loads((artifact_dir / "canary_manifest.json").read_text())
    assert canary["task_ids"] == [49, 60, 61, 64, 75, 258, 260, 262, 263, 270]
    assert canary["planned_rollouts"] == 30
    assert canary["rollouts_per_task"] == 3
    assert not set(canary["task_ids"]) & set(canary["source_attempt_02_task_ids"])
