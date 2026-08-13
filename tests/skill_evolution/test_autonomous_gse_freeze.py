"""Fail-closed Campaign preflight and freeze record contracts."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import src.skill_evolution.autonomous_gse_freeze as freeze_module
from src.skill_evolution.autonomous_gse_freeze import (
    CampaignPreflightError,
    build_freeze_record,
    freeze_campaign,
    require_campaign_freeze,
    run_preflight,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
)


@pytest.fixture(autouse=True)
def isolate_formal_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep preflight tests independent of completed local Campaign runs."""

    monkeypatch.setattr(freeze_module, "FORMAL_ROOT", tmp_path / "formal")


def load_campaign() -> dict:
    campaign = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
    freeze_tool = PROJECT_ROOT / "src/skill_evolution/autonomous_gse_freeze.py"
    campaign["implementation_bindings"]["freeze_tool"]["sha256"] = (
        hashlib.sha256(freeze_tool.read_bytes()).hexdigest()
    )
    return campaign


def environment_fixture(campaign: dict) -> dict:
    return {
        "python": {"executable": "fixture", "version": "3.12"},
        "required_modules": "passed",
        "learner_configuration_present": [
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
        ],
        "benchmark_commit": campaign["benchmark_runtime"]["benchmark"][
            "commit"
        ],
        "docker_server_version": "fixture",
        "compose_images": {"fixture": "sha256:fixture"},
        "suitecrm_readiness": {
            "url": "http://127.0.0.1:8080/public",
            "http_status": 200,
            "database_reset": "passed",
            "expected_active_counts": {
                "contacts": 10,
                "accounts": 9,
                "leads": 10,
            },
        },
    }


def draft_path(tmp_path: Path) -> Path:
    campaign = load_campaign()
    campaign["status"] = "draft"
    campaign.pop("frozen_at", None)
    path = tmp_path / "campaign_manifest.json"
    path.write_text(json.dumps(campaign), encoding="utf-8")
    return path


def test_preflight_builds_a_frozen_manifest_without_mutating_draft(
    tmp_path: Path,
) -> None:
    path = draft_path(tmp_path)
    before = path.read_bytes()

    final_manifest, preflight = run_preflight(
        path, environment_probe=environment_fixture
    )

    assert path.read_bytes() == before
    assert json.loads(path.read_text())["status"] == "draft"
    assert final_manifest["status"] == "frozen"
    assert final_manifest["frozen_at"].endswith("+00:00")
    assert preflight["schema_validation"] == "passed"
    assert preflight["formal_artifacts_absent_before_freeze"] is True
    assert preflight["budget_and_batch_plan"] == {
        "initial_selection": 18,
        "train_batches": [17, 17, 17],
        "maximum_candidate_selection": [18, 18, 18],
        "maximum_total_trajectories": 123,
        "maximum_learner_calls": 3,
    }
    assert preflight["test_lock"]["authorized"] is False


def test_preflight_rejects_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = freeze_module._sha256_file

    def drift(path: Path) -> str:
        if path.name == "S0_no_skill.json":
            return "0" * 64
        return original(path)

    monkeypatch.setattr(freeze_module, "_sha256_file", drift)
    with pytest.raises(CampaignPreflightError, match="SHA-256 drifted"):
        run_preflight(
            draft_path(tmp_path), environment_probe=environment_fixture
        )


def test_preflight_rejects_existing_formal_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    formal_root = tmp_path / "formal"
    formal_root.mkdir()
    (formal_root / "trajectory.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(freeze_module, "FORMAL_ROOT", formal_root)

    with pytest.raises(CampaignPreflightError, match="retrospective freeze"):
        run_preflight(
            draft_path(tmp_path), environment_probe=environment_fixture
        )


def test_freeze_is_single_write_and_record_hashes_final_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign_path = tmp_path / "campaign_manifest.json"
    campaign_path = draft_path(tmp_path)
    monkeypatch.setattr(freeze_module, "REPO_ROOT", tmp_path)

    original_resolve = freeze_module._resolve
    monkeypatch.setattr(
        freeze_module,
        "_resolve",
        lambda relative: PROJECT_ROOT / relative,
    )
    monkeypatch.setattr(
        freeze_module,
        "CAMPAIGN_SCHEMA_PATH",
        PROJECT_ROOT / "schemas/autonomous_gse_v01_campaign.schema.json",
    )
    monkeypatch.setattr(freeze_module, "FORMAL_ROOT", tmp_path / "formal")

    record = freeze_campaign(
        campaign_path, environment_probe=environment_fixture
    )

    frozen = json.loads(campaign_path.read_text(encoding="utf-8"))
    freeze_path = tmp_path / "campaign_freeze.json"
    assert frozen["status"] == "frozen"
    assert freeze_path.is_file()
    assert record["campaign"]["sha256"] == hashlib.sha256(
        campaign_path.read_bytes()
    ).hexdigest()
    assert record["campaign"]["path"] == "campaign_manifest.json"

    with pytest.raises(FileExistsError, match="freeze already exists"):
        freeze_campaign(campaign_path, environment_probe=environment_fixture)

    monkeypatch.setattr(freeze_module, "_resolve", original_resolve)


def test_formal_execution_requires_freeze_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = load_campaign()
    campaign["status"] = "frozen"
    campaign["frozen_at"] = "2026-08-13T00:00:00+00:00"
    path = tmp_path / "campaign_manifest.json"
    path.write_text(json.dumps(campaign), encoding="utf-8")
    monkeypatch.setattr(freeze_module, "REPO_ROOT", tmp_path)

    with pytest.raises(CampaignPreflightError, match="record is missing"):
        require_campaign_freeze(path, campaign)


def test_freeze_record_has_one_way_manifest_reference(tmp_path: Path) -> None:
    path = draft_path(tmp_path)
    final_manifest, preflight = run_preflight(
        path, environment_probe=environment_fixture
    )
    monkey_root = freeze_module.REPO_ROOT
    freeze_module.REPO_ROOT = tmp_path
    try:
        record = build_freeze_record(path, final_manifest, preflight)
    finally:
        freeze_module.REPO_ROOT = monkey_root

    assert "freeze" not in final_manifest
    assert record["campaign"]["path"].endswith("campaign_manifest.json")
    assert record["change_policy"]["freeze_record_must_not_be_overwritten"]
