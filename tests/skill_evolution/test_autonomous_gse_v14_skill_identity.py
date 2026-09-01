from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as runtime
from src.skill_evolution.autonomous_gse_v14_orchestrator import (
    EvolutionServices, resolve_skill_artifact_path, resume_campaign, run_campaign,
)

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
BATCH_MAP_PATH = ROOT / "experiments/campaigns/autonomous_gse_v14/batch_map.json"
S0_RESULT_PATH = ROOT / "artifacts/autonomous_gse_v14/formal/monitor_results/S0.json"
S0_IDENTITY = "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class NoRolloutBackend:
    def __init__(self):
        self.calls = 0

    def run_batch(self, **kwargs):
        self.calls += 1
        raise AssertionError("A valid Monitor cache must not execute rollout API work.")


def _copy_cached_result(root: Path, *, skill: dict[str, str]) -> None:
    result = copy.deepcopy(_load(S0_RESULT_PATH))
    result["skill"] = copy.deepcopy(skill)
    for row in result["rows"]:
        row["skill_id"] = skill["skill_id"]
        row["skill_version"] = skill["skill_version"]
    path = root / "monitor_results" / f"{skill['skill_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result), encoding="utf-8")


def _noop_services(campaign, batch_map, artifact_root, monitor):
    def rows(batch):
        values = []
        for tagged in batch["task_ids"]:
            domain, task_id = tagged.split(":", 1)
            for rollout_index in (1, 2, 3):
                values.append({
                    "source_id": f"{domain}_{task_id}_{rollout_index}",
                    "domain": domain, "task_id": task_id,
                    "rollout_index": rollout_index,
                    "rollout_seed": 199 + rollout_index,
                    "state": "compliant_success", "trajectory": [],
                })
        return values

    return EvolutionServices(
        parent_rollouts=lambda step, batch, skill: {
            "rows": rows(batch), "evidence": rows(batch),
        },
        propose=lambda context, step: SimpleNamespace(
            proposal_status="NO_CANDIDATE",
            proposal_reason={"code": "NO_UPDATE_ELIGIBLE_DIAGNOSIS"},
            candidate_skill=None, diagnoses=[], applied_edits=[],
        ),
        candidate_monitor=monitor,
        candidate_replay=lambda *args: pytest.fail("No-op must not replay Candidate."),
    )


@pytest.mark.skipif(not S0_RESULT_PATH.is_file(), reason="Frozen S0 Monitor artifact unavailable")
def test_manifest_and_real_s0_cache_use_same_canonical_identity():
    campaign = _load(CAMPAIGN_PATH)
    cached = _load(S0_RESULT_PATH)
    assert campaign["initial_parent"]["path"] == S0_IDENTITY
    assert cached["skill"] == {
        "skill_id": "S0", "skill_version": "S0", "skill_path": S0_IDENTITY,
    }


def test_repo_relative_identity_resolves_independently_of_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resolved = resolve_skill_artifact_path(S0_IDENTITY)
    assert resolved == ROOT / S0_IDENTITY
    assert resolved.is_file()
    assert S0_IDENTITY == "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md"


@pytest.mark.skipif(not S0_RESULT_PATH.is_file(), reason="Frozen S0 Monitor artifact unavailable")
def test_real_s0_monitor_cache_returns_without_backend_rollouts():
    campaign, batch_map = _load(CAMPAIGN_PATH), _load(BATCH_MAP_PATH)
    backend = NoRolloutBackend()
    result = runtime.run_fixed_monitor(
        campaign, batch_map,
        skill={"skill_id": "S0", "skill_version": "S0", "skill_path": S0_IDENTITY},
        backend=backend, artifact_root=ROOT / "artifacts/autonomous_gse_v14/formal",
    )
    assert backend.calls == 0
    assert len(result["rows"]) == 60
    assert result["summary"]["counts"] == {"CS": 48, "CF": 4, "VS": 6, "VF": 2}


@pytest.mark.skipif(not S0_RESULT_PATH.is_file(), reason="Frozen S0 Monitor artifact unavailable")
def test_full_campaign_initialization_reuses_s0_cache_with_relative_identity(tmp_path):
    campaign, batch_map = _load(CAMPAIGN_PATH), _load(BATCH_MAP_PATH)
    artifact_root = tmp_path / "formal"
    skill = {"skill_id": "S0", "skill_version": "S0", "skill_path": S0_IDENTITY}
    _copy_cached_result(artifact_root, skill=skill)
    backend = NoRolloutBackend()
    requested = []

    def monitor(identity):
        requested.append(copy.deepcopy(identity))
        return runtime.run_fixed_monitor(
            campaign, batch_map, skill=identity, backend=backend,
            artifact_root=artifact_root,
        )

    services = _noop_services(campaign, batch_map, artifact_root, monitor)
    services = EvolutionServices(**{
        **services.__dict__,
        "parent_rollouts": lambda *args: (_ for _ in ()).throw(RuntimeError("stop after init")),
    })
    with pytest.raises(RuntimeError, match="stop after init"):
        runtime.run_v14_campaign(
            campaign, batch_map, artifact_root=artifact_root, services=services,
        )
    assert requested == [skill]
    assert backend.calls == 0
    state = _load(artifact_root / "campaign_state.json")
    assert state["current_parent"]["skill_path"] == S0_IDENTITY


def test_campaign_state_and_resume_preserve_relative_identity_across_cwd(tmp_path, monkeypatch):
    campaign, batch_map = _load(CAMPAIGN_PATH), _load(BATCH_MAP_PATH)
    artifact_root = tmp_path / "formal"
    requested = []

    def monitor(identity):
        requested.append(copy.deepcopy(identity))
        return {"skill": copy.deepcopy(identity)}

    services = _noop_services(campaign, batch_map, artifact_root, monitor)
    other_cwd = tmp_path / "other"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    state = run_campaign(
        campaign, batch_map, services, artifact_root=artifact_root,
    )
    assert state["current_parent"]["skill_path"] == S0_IDENTITY
    assert state["final_skill"]["skill_path"] == S0_IDENTITY
    resumed = resume_campaign(
        campaign, batch_map, services, artifact_root=artifact_root,
    )
    assert resumed["current_parent"]["skill_path"] == S0_IDENTITY
    assert requested == [
        {"skill_id": "S0", "skill_version": "S0", "skill_path": S0_IDENTITY},
        {"skill_id": "S0", "skill_version": "S0", "skill_path": S0_IDENTITY},
    ]


@pytest.mark.parametrize("kind", ("S0", "candidate"))
def test_resume_monitor_cache_reuse_uses_exact_saved_parent_identity(tmp_path, kind):
    campaign, batch_map = _load(CAMPAIGN_PATH), _load(BATCH_MAP_PATH)
    artifact_root = tmp_path / "formal"
    if kind == "S0":
        skill = {"skill_id": "S0", "skill_version": "S0", "skill_path": S0_IDENTITY}
    else:
        candidate_path = tmp_path / "candidate_step_01.md"
        candidate_path.write_text("# candidate\n", encoding="utf-8")
        skill = {
            "skill_id": "candidate_step_01", "skill_version": "candidate_step_01",
            "skill_path": candidate_path.as_posix(),
        }
    _copy_cached_result(artifact_root, skill=skill)
    (artifact_root / "campaign_state.json").write_text(json.dumps({
        "schema_version": "autonomous_gse_campaign_state_0.14.0",
        "campaign_id": campaign["campaign_id"], "current_step": 3,
        "current_parent": skill,
        "current_parent_monitor_result_path": (
            artifact_root / "monitor_results" / f"{skill['skill_id']}.json"
        ).as_posix(),
        "completed_steps": [{}, {}, {}], "final_skill": skill,
    }), encoding="utf-8")
    backend = NoRolloutBackend()
    services = _noop_services(
        campaign, batch_map, artifact_root,
        lambda identity: runtime.run_fixed_monitor(
            campaign, batch_map, skill=identity, backend=backend,
            artifact_root=artifact_root,
        ),
    )
    state = resume_campaign(
        campaign, batch_map, services, artifact_root=artifact_root,
    )
    assert backend.calls == 0
    assert state["current_parent"] == skill
