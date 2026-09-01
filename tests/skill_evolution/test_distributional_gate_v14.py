from __future__ import annotations

import copy
import inspect
import json
import random
from pathlib import Path

import pytest

from src.skill_evolution import distributional_gate_v14 as gate
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as runtime


def _synthetic_report(
    effects: dict[tuple[str, str], list[tuple[int, int]]] | None = None,
) -> dict:
    effects = effects or {}
    matched_pairs = []
    task_level_effects = []
    success_count = compliance_count = 0
    for domain in ("airline", "retail"):
        for task_number in range(10):
            task_id = f"{domain}_{task_number}"
            deltas = effects.get((domain, task_id), [(0, 0), (0, 0), (0, 0)])
            assert len(deltas) == 3
            task_success = sum(value[0] for value in deltas)
            task_compliance = sum(value[1] for value in deltas)
            success_count += task_success
            compliance_count += task_compliance
            for rollout_index, (delta_success, delta_compliance) in enumerate(deltas, start=1):
                matched_pairs.append({
                    "domain": domain,
                    "task_id": task_id,
                    "rollout_index": rollout_index,
                    "rollout_seed": 199 + rollout_index,
                    "parent_state": "VF",
                    "candidate_state": "CS",
                    "delta_success": delta_success,
                    "delta_compliance": delta_compliance,
                })
            task_level_effects.append({
                "domain": domain,
                "task_id": task_id,
                "matched_rollouts": 3,
                "mean_delta_success": task_success / 3,
                "mean_delta_compliance": task_compliance / 3,
            })
    return {
        "schema_version": "autonomous_gse_joint_distribution_report_0.14.0",
        "campaign_id": "synthetic_v14",
        "monitor_id": "fixed_monitor_m",
        "parent_skill": {
            "skill_id": "parent", "skill_version": "S0", "skill_path": "parent.md",
        },
        "candidate_skill": {
            "skill_id": "candidate", "skill_version": "S1", "skill_path": "candidate.md",
        },
        "matched_pairs": matched_pairs,
        "task_level_effects": task_level_effects,
        "overall_shift": {
            "delta_success": success_count / 60,
            "delta_compliance": compliance_count / 60,
        },
    }


def _all_tasks(effect: list[tuple[int, int]]) -> dict:
    return {
        (domain, f"{domain}_{task_number}"): effect
        for domain in ("airline", "retail")
        for task_number in range(10)
    }


@pytest.mark.parametrize(
    ("delta_success", "delta_compliance", "expected"),
    (
        (3, 0, True), (0, 3, True), (3, 2, True),
        (3, -1, True), (-1, 3, True),
        (3, -2, False), (-2, 3, False),
        (0, 0, False), (-1, -1, False), (-3, 0, False), (0, -3, False),
    ),
)
def test_epsilon_pareto_positive_region_boundaries(
    delta_success, delta_compliance, expected,
):
    assert gate.is_epsilon_pareto_positive(delta_success, delta_compliance) is expected


def test_obviously_positive_candidate_is_accepted():
    result = gate.build_distributional_gate_decision(
        _synthetic_report(_all_tasks([(1, 0), (0, 0), (0, 0)])),
    )
    assert result["bootstrap"]["positive_probability"] == 1.0
    assert result["gate"]["decision"] == "ACCEPT"


def test_zero_shift_is_retained():
    result = gate.build_distributional_gate_decision(_synthetic_report())
    assert result["bootstrap"]["positive_probability"] == 0.0
    assert result["gate"]["decision"] == "RETAIN"


def test_obviously_negative_candidate_is_retained():
    result = gate.build_distributional_gate_decision(
        _synthetic_report(_all_tasks([(-1, 0), (0, 0), (0, 0)])),
    )
    assert result["bootstrap"]["positive_probability"] == 0.0
    assert result["gate"]["decision"] == "RETAIN"


def test_systematic_tradeoff_beyond_epsilon_is_retained():
    result = gate.build_distributional_gate_decision(
        _synthetic_report(_all_tasks([(1, -1), (0, -1), (0, 0)])),
    )
    assert result["bootstrap"]["positive_probability"] == 0.0
    assert result["gate"]["decision"] == "RETAIN"


def test_one_lucky_positive_task_does_not_pass():
    effects = {("airline", "airline_0"): [(1, 0), (0, 0), (0, 0)]}
    result = gate.build_distributional_gate_decision(_synthetic_report(effects))
    assert 0.62 < result["bootstrap"]["positive_probability"] < 0.68
    assert result["gate"]["decision"] == "RETAIN"


def test_two_positive_tasks_provide_enough_support():
    effects = {
        ("airline", "airline_0"): [(1, 0), (0, 0), (0, 0)],
        ("airline", "airline_1"): [(1, 0), (0, 0), (0, 0)],
    }
    result = gate.build_distributional_gate_decision(_synthetic_report(effects))
    assert 0.87 < result["bootstrap"]["positive_probability"] < 0.92
    assert result["gate"]["decision"] == "ACCEPT"


@pytest.mark.parametrize(
    ("probability", "expected"),
    ((0.7999, "RETAIN"), (0.8000, "ACCEPT"), (0.9000, "ACCEPT")),
)
def test_gate_threshold_is_inclusive(probability, expected):
    assert gate.gate_decision(probability) == expected


def test_bootstrap_is_deterministic():
    effects = {
        ("airline", "airline_0"): [(1, 0), (0, 0), (0, 0)],
        ("retail", "retail_0"): [(0, 1), (0, 0), (0, 0)],
    }
    report = _synthetic_report(effects)
    assert gate.build_distributional_gate_decision(report) == (
        gate.build_distributional_gate_decision(report)
    )


def test_each_replicate_draws_ten_tasks_from_each_domain():
    clusters = gate.build_task_clusters(_synthetic_report())
    by_domain = {
        domain: [cluster for cluster in clusters if cluster["domain"] == domain]
        for domain in gate.EXPECTED_DOMAINS
    }
    for seed in range(10):
        replicate = gate._draw_stratified_replicate(by_domain, random.Random(seed))
        assert replicate["domain_draw_counts"] == {"airline": 10, "retail": 10}


def test_gate_bootstraps_task_clusters_not_rollout_rows():
    result = gate.build_distributional_gate_decision(_synthetic_report())
    assert result["bootstrap"]["unit"] == "task"
    assert result["bootstrap"]["cluster_rollouts"] == 3
    assert result["bootstrap"]["airline_tasks_per_replicate"] == 10
    assert result["bootstrap"]["retail_tasks_per_replicate"] == 10
    assert result["bootstrap"]["replicates"] == 10000
    assert result["bootstrap"]["seed"] == 200


def test_cluster_contract_fails_closed_on_incomplete_task():
    report = _synthetic_report()
    report["matched_pairs"].pop()
    with pytest.raises(gate.DistributionalGateContractError):
        gate.build_distributional_gate_decision(report)


def test_observed_shift_count_consistency_fails_closed():
    report = _synthetic_report()
    report["overall_shift"]["delta_success"] = 1 / 60
    with pytest.raises(gate.DistributionalGateContractError, match="overall_shift"):
        gate.build_distributional_gate_decision(report)


def test_fixed_gate_config_rejects_outcome_tuning():
    config = copy.deepcopy(gate.DEFAULT_GATE_CONFIG)
    config["positive_probability_threshold"] = 0.79
    with pytest.raises(gate.DistributionalGateContractError, match="config drifted"):
        gate.build_distributional_gate_decision(_synthetic_report(), config)


def test_gate_cli_consumes_report_without_rollout(tmp_path, capsys):
    report_path = tmp_path / "joint.json"
    output_path = tmp_path / "gate.json"
    report_path.write_text(json.dumps(_synthetic_report()), encoding="utf-8")
    exit_code = runtime.main([
        "gate", "--joint-report", str(report_path), "--output", str(output_path),
    ])
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == result
    assert result["bootstrap"]["positive_probability"] == 0.0


def test_gate_has_no_scalar_or_legacy_veto_inputs():
    source = inspect.getsource(gate).casefold()
    for forbidden in (
        "targeted_fix", "regression_diagnosis", "weighted score",
        "headroom", "confidence_interval", "cup gate",
    ):
        assert forbidden not in source
