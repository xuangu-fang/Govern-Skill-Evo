import gzip
import json
from pathlib import Path


ROOT = (
    Path(__file__).resolve().parents[2]
    / "benchmarks/tau2_governed_evolution/complex_workflow/pilot/base_calibration"
)
EXPECTED_DECLARATIONS = "b99fd6f37b571b762a23dcd9eade57f1a2af33a3e5259b89cdb718f268183e08"
EXPECTED_BUNDLES = "06f7209589867feeb5608b49d1c64976bf18049deaabaa97c50afeee07d96a1f"


def _rows() -> list[dict]:
    return [json.loads(line) for line in (ROOT / "rollout_results.jsonl").read_text().splitlines()]


def test_cw3_has_exactly_three_valid_rollouts_per_frozen_task() -> None:
    rows = _rows()
    assert len(rows) == 45
    assert len({row["task_id"] for row in rows}) == 15
    for task_id in {row["task_id"] for row in rows}:
        task_rows = [row for row in rows if row["task_id"] == task_id]
        assert {row["rollout_seed"] for row in task_rows} == {200, 201, 202}
        assert all(row["runtime_status"] == "COMPLETED" for row in task_rows)


def test_cw3_freeze_and_base_runtime_are_unchanged() -> None:
    summary = json.loads((ROOT / "base_calibration_summary.json").read_text())
    assert summary["freeze_verification"] == {
        "declarations_sha256": EXPECTED_DECLARATIONS,
        "compiled_bundle_sha256": EXPECTED_BUNDLES,
        "passed": True,
    }
    config = summary["run_configuration"]
    assert config["agent"]["model"] == "openai/deepseek-v4-flash"
    assert config["agent"]["temperature"] == 0.2
    assert config["user_simulator"]["temperature"] == 0.0
    assert config["rollout_seeds"] == [200, 201, 202]
    assert config["base_skill"]["version"] == "S0"
    assert config["base_skill"]["injection"] == "none"
    assert config["diagnosis_editor_candidate_gate_calls"] == 0
    assert config["reference_skill_calls"] == 0


def test_cw3_preserves_complete_evidence_and_final_state() -> None:
    for row in _rows():
        assert row["trajectory"]
        assert row["tool_actions"]
        assert row["reward_detail"] is not None
        assert row["component_compliance"] is not None
        assert row["behavior_state"] in {"CS", "CF", "VS", "VF"}
        assert row["protected_state_audit"]["all_protected_invariants_unchanged"]
        db_path = Path(row["final_db_state"]["path"])
        with gzip.open(db_path, "rt") as handle:
            db = json.load(handle)
        assert {"users", "reservations", "flights"} <= set(db)


def test_cw3_staged_goals_were_introduced_and_acted_on() -> None:
    staged = [
        evidence
        for row in _rows()
        for evidence in row["staged_goal_evidence"]
    ]
    assert len(staged) == 9
    assert all(item["secondary_goal_introduced"] for item in staged)
    assert all(item["agent_acted_on_goal"] for item in staged)


def test_cw3_summary_and_manual_attribution_are_complete() -> None:
    summary = json.loads((ROOT / "base_calibration_summary.json").read_text())
    assert summary["overall"] == {
        "rollouts": 45,
        "valid_rollouts": 45,
        "runtime_errors": 0,
        "task_success_count": 28,
        "compliance_count": 31,
        "CS": 19,
        "CF": 12,
        "VS": 9,
        "VF": 5,
    }
    assert summary["strong_headroom_clusters"] == [
        "latest_complete_transaction_reconfirmation"
    ]
    assert summary["weak_headroom_clusters"] == []
    assert summary["workflow_headroom_judgment"] == "PARTIALLY_SUPPORTED"
    assert summary["hypothesis_a_judgment"] == "PARTIALLY_SUPPORTED"
    assert summary["hypothesis_b_judgment"] == "PARTIALLY_SUPPORTED"
    assert summary["next_decision"] == "HOLD"

    annotations = json.loads((ROOT / "trajectory_attributions.json").read_text())
    non_cs = [row for row in _rows() if row["behavior_state"] != "CS"]
    assert len(annotations) == len(non_cs) == 26
    assert all(item["note"] for item in annotations)


def test_initial_network_failure_is_excluded_from_behavior_metrics() -> None:
    attempt = json.loads((ROOT / "infrastructure_attempt_01.json").read_text())
    assert attempt["status"] == "INVALID_INFRASTRUCTURE_ATTEMPT"
    assert attempt["runtime_errors"] == 45
    assert attempt["valid_behavior_rollouts"] == 0
    assert attempt["included_in_behavior_metrics"] is False
