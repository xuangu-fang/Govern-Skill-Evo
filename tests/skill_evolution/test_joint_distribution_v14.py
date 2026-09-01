from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest

from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14
from src.skill_evolution import joint_distribution_v14 as joint

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_DIR = ROOT / "experiments/campaigns/autonomous_gse_v14"
MANIFEST = CAMPAIGN_DIR / "campaign_manifest.json"
BATCH_MAP = CAMPAIGN_DIR / "batch_map.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def campaign():
    return _load(MANIFEST)


@pytest.fixture
def batch_map():
    return _load(BATCH_MAP)


def _outcomes(code: str) -> tuple[bool, bool]:
    return {
        "CS": (True, True), "CF": (False, True),
        "VS": (True, False), "VF": (False, False),
    }[code]


def _monitor_result(
    batch_map: dict, *, skill_id: str, skill_version: str,
    states: list[str] | None = None, seed_offset: int = 0,
) -> dict:
    task_ids = copy.deepcopy(batch_map["monitor"]["task_ids"])
    codes = states or [joint.STATE_CODES[index % 4] for index in range(60)]
    rows = []
    position = 0
    for domain_task in task_ids:
        domain, task_id = domain_task.split(":", 1)
        for rollout_index, seed in enumerate((200, 201, 202), start=1):
            code = codes[position]
            success, compliant = _outcomes(code)
            rows.append({
                "source_id": f"monitor_{skill_id}_{domain}_{task_id}_{rollout_index}",
                "domain": domain, "task_id": task_id, "rollout_index": rollout_index,
                "rollout_seed": seed + seed_offset,
                "skill_id": skill_id, "skill_version": skill_version,
                "task_success": success, "compliant": compliant,
                "state": joint.STATE_NAMES[code], "state_code": code,
                "trajectory_artifact_path": f"/tmp/{skill_id}_{domain}_{task_id}_{rollout_index}.json",
            })
            position += 1
    result = {
        "schema_version": "autonomous_gse_monitor_result_0.14.0",
        "campaign_id": "autonomous_gse_v14", "monitor_id": "fixed_monitor_m",
        "skill_artifact_contract": "immutable_identity",
        "skill": {
            "skill_id": skill_id, "skill_version": skill_version,
            "skill_path": f"skills/{skill_id}.md",
        },
        "task_ids": task_ids, "rollouts_per_task": 3, "rows": rows,
    }
    result["summary"] = joint.distribution(rows)
    return result


class FakeMonitorBackend:
    def __init__(self, root: Path, states: list[str] | None = None):
        self.root = root
        self.states = states or [joint.STATE_CODES[index % 4] for index in range(60)]
        self.calls = 0

    def run_batch(self, *, units, skill):
        self.calls += 1
        paths = []
        for position, unit in enumerate(units):
            code = self.states[position]
            success, compliant = _outcomes(code)
            path = self.root / skill["skill_id"] / (
                f"{unit['domain']}_{unit['task_id']}_{unit['rollout_index']}.json"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "domain": unit["domain"], "task_id": unit["task_id"],
                "phase": "monitor", "skill_version": skill["skill_version"],
                "rollout_index": unit["rollout_index"], "rollout_seed": unit["rollout_seed"],
                "task_evaluation": {"success": success},
                "compliance_evaluation": {"compliant": compliant},
                "state": joint.STATE_NAMES[code],
                "governed_evidence": {
                    "source_id": f"monitor_{skill['skill_id']}_{position:02d}"
                },
            }), encoding="utf-8")
            paths.append(path)
        return paths


def test_monitor_plan_is_balanced_k3_and_deterministic(campaign, batch_map):
    first = v14.build_monitor_plan(campaign, batch_map)
    second = v14.build_monitor_plan(campaign, batch_map)
    assert first == second
    assert len(first["task_ids"]) == 20
    assert len(first["units"]) == 60
    assert first["rollouts_per_task"] == 3
    assert sum(value.startswith("airline:") for value in first["task_ids"]) == 10
    assert sum(value.startswith("retail:") for value in first["task_ids"]) == 10
    for task_id in first["task_ids"]:
        units = [unit for unit in first["units"] if f"{unit['domain']}:{unit['task_id']}" == task_id]
        assert [unit["rollout_index"] for unit in units] == [1, 2, 3]
        assert [unit["rollout_seed"] for unit in units] == [200, 201, 202]


@pytest.mark.parametrize(
    ("success", "compliant", "expected"),
    ((True, True, "CS"), (True, False, "VS"), (False, True, "CF"), (False, False, "VF")),
)
def test_state_mapping_is_deterministic(success, compliant, expected):
    assert joint.state_code(success, compliant) == expected


def test_distribution_counts_probabilities_and_marginals(batch_map):
    result = _monitor_result(batch_map, skill_id="S0", skill_version="S0")
    measured = result["summary"]
    assert sum(measured["counts"].values()) == 60
    assert sum(measured["probabilities"].values()) == pytest.approx(1.0)
    probabilities = measured["probabilities"]
    assert measured["success_rate"] == probabilities["CS"] + probabilities["VS"]
    assert measured["compliance_rate"] == probabilities["CS"] + probabilities["CF"]
    assert measured["cup_rate"] == probabilities["CS"]


def test_joint_report_transition_deltas_task_effects_and_overall_consistency(batch_map):
    parent_codes = ["CF", "VS", "VF", "CF", "VS", "CS"] + ["VF"] * 54
    candidate_codes = ["CS", "CS", "CS", "VS", "CF", "VF"] + ["VF"] * 54
    parent = _monitor_result(
        batch_map, skill_id="parent", skill_version="S0", states=parent_codes,
    )
    candidate = _monitor_result(
        batch_map, skill_id="candidate", skill_version="candidate_001", states=candidate_codes,
    )
    report = joint.build_joint_distribution_report(parent, candidate)
    pairs = report["matched_pairs"]
    assert [(item["delta_success"], item["delta_compliance"]) for item in pairs[:6]] == [
        (1, 0), (0, 1), (1, 1), (1, -1), (-1, 1), (-1, -1),
    ]
    matrix = report["transition_matrix"]
    assert set(matrix["counts"]) == set(joint.STATE_CODES)
    assert all(set(row) == set(joint.STATE_CODES) for row in matrix["counts"].values())
    assert matrix["total_pairs"] == 60
    assert sum(sum(row.values()) for row in matrix["counts"].values()) == 60
    assert "probabilities" not in matrix
    assert sum(sum(row.values()) for row in matrix["joint_probabilities"].values()) == pytest.approx(1.0)
    for before in joint.STATE_CODES:
        for after in joint.STATE_CODES:
            assert matrix["joint_probabilities"][before][after] == pytest.approx(
                matrix["counts"][before][after] / matrix["total_pairs"]
            )
    assert len(report["task_level_effects"]) == 20
    assert all(item["matched_rollouts"] == 3 for item in report["task_level_effects"])
    first_task = report["task_level_effects"][0]
    assert first_task["mean_delta_success"] == pytest.approx(2 / 3)
    assert first_task["mean_delta_compliance"] == pytest.approx(2 / 3)
    assert report["overall_shift"]["delta_success"] == pytest.approx(
        report["candidate_distribution"]["success_rate"]
        - report["parent_distribution"]["success_rate"]
    )
    assert report["overall_shift"]["delta_compliance"] == pytest.approx(
        report["candidate_distribution"]["compliance_rate"]
        - report["parent_distribution"]["compliance_rate"]
    )


def test_parent_candidate_seed_mismatch_fails_closed(batch_map):
    parent = _monitor_result(batch_map, skill_id="parent", skill_version="S0")
    candidate = _monitor_result(
        batch_map, skill_id="candidate", skill_version="candidate_001", seed_offset=1,
    )
    with pytest.raises(joint.JointDistributionContractError, match="lineage"):
        joint.build_joint_distribution_report(parent, candidate)


def test_task_without_three_pairs_fails_closed(batch_map):
    parent = _monitor_result(batch_map, skill_id="parent", skill_version="S0")
    candidate = _monitor_result(batch_map, skill_id="candidate", skill_version="candidate_001")
    candidate["rows"][0]["task_id"] = candidate["rows"][3]["task_id"]
    candidate["summary"] = joint.distribution(candidate["rows"])
    with pytest.raises(joint.JointDistributionContractError):
        joint.build_joint_distribution_report(parent, candidate)


@pytest.mark.parametrize(("field", "invalid"), (("source_id", "  "), ("source_id", None), ("trajectory_artifact_path", ""), ("trajectory_artifact_path", None)))
def test_monitor_result_rejects_empty_trajectory_lineage(batch_map, field, invalid):
    result = _monitor_result(batch_map, skill_id="S0", skill_version="S0")
    result["rows"][0][field] = invalid
    with pytest.raises(joint.JointDistributionContractError, match="trajectory lineage"):
        joint.validate_monitor_result(result)


def test_monitor_runtime_writes_rows_and_reuses_valid_cache(tmp_path, campaign, batch_map):
    backend = FakeMonitorBackend(tmp_path / "rollouts")
    skill = {
        "skill_id": "S0", "skill_version": "S0",
        "skill_path": "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md",
    }
    first = v14.run_fixed_monitor(
        campaign, batch_map, skill=skill, backend=backend, artifact_root=tmp_path / "artifacts",
    )
    second = v14.run_fixed_monitor(
        campaign, batch_map, skill=skill, backend=backend, artifact_root=tmp_path / "artifacts",
    )
    assert first == second
    assert backend.calls == 1
    assert len(first["rows"]) == 60
    assert first["summary"]["total_rollouts"] == 60
    assert (tmp_path / "artifacts/monitor_results/S0.json").is_file()


@pytest.mark.parametrize("field", ("skill_id", "skill_version", "skill_path"))
def test_any_skill_identity_change_invalidates_monitor_cache(tmp_path, campaign, batch_map, field):
    backend = FakeMonitorBackend(tmp_path / "rollouts")
    skill = {
        "skill_id": "S0", "skill_version": "S0",
        "skill_path": "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md",
    }
    result = v14.run_fixed_monitor(
        campaign, batch_map, skill=skill, backend=backend, artifact_root=tmp_path / "artifacts",
    )
    changed = copy.deepcopy(skill)
    changed[field] += "_new"
    plan = v14.build_monitor_plan(campaign, batch_map)
    assert not v14._cached_monitor_result_valid(
        result, campaign=campaign, plan=plan, skill=changed,
    )


def test_monitor_runtime_never_invokes_learner(tmp_path, campaign, batch_map, monkeypatch):
    backend = FakeMonitorBackend(tmp_path / "rollouts")
    monkeypatch.setattr(
        v14.V13_PROPOSAL_OPERATOR, "propose",
        lambda *args, **kwargs: pytest.fail("Monitor must not enter Proposal Operator"),
    )
    result = v14.run_fixed_monitor(
        campaign, batch_map,
        skill={
            "skill_id": "S0", "skill_version": "S0",
            "skill_path": "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md",
        },
        backend=backend, artifact_root=tmp_path / "artifacts",
    )
    assert len(result["rows"]) == 60


def test_phase3_measurement_module_contains_no_decision_semantics():
    source = inspect.getsource(joint)
    for forbidden in (
        "bootstrap", "confidence_interval", "confidence threshold",
        "evolution_gate_v14", '"ACCEPT"', '"RETAIN"',
    ):
        assert forbidden not in source
