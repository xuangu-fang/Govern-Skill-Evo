import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = (
    ROOT
    / "benchmarks/tau2_governed_evolution/v2/pilot/base_calibration"
)


def _rows() -> list[dict]:
    return [
        json.loads(line)
        for line in (ARTIFACTS / "rollout_results.jsonl").read_text().splitlines()
    ]


def test_base_calibration_contains_exactly_three_valid_rollouts_per_task() -> None:
    rows = _rows()
    by_task: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_task[row["task_id"]].append(row)

    assert len(rows) == 84
    assert len(by_task) == 28
    assert all(len(task_rows) == 3 for task_rows in by_task.values())
    assert all(
        {row["rollout_index"] for row in task_rows} == {1, 2, 3}
        for task_rows in by_task.values()
    )
    assert all(row["runtime_status"] == "COMPLETED" for row in rows)
    assert all(row["runtime_error"] is None for row in rows)
    assert {row["rollout_seed"] for row in rows} == {200, 201, 202}
    assert {row["skill_version"] for row in rows} == {"S0"}


def test_behavior_states_and_interaction_component_labels_are_preserved() -> None:
    rows = _rows()
    expected_state = {
        (True, True): "CS",
        (False, True): "CF",
        (True, False): "VS",
        (False, False): "VF",
    }
    assert all(
        row["behavior_state"]
        == expected_state[(row["task_success"], row["target_compliance"])]
        for row in rows
    )

    i1 = [row for row in rows if row["component"] == "I1"]
    i2 = [row for row in rows if row["component"] == "I2"]
    assert all(
        set(row["component_compliance"])
        == {
            "airline.book.baggage_allowance",
            "airline.action.explicit_confirmation",
        }
        for row in i1
    )
    assert all(
        set(row["component_compliance"])
        == {
            "airline.cancel.reason_required",
            "airline.compensation.delayed_flight_sequence",
        }
        for row in i2
    )


def test_saved_summary_records_observed_structural_judgments() -> None:
    summary = json.loads(
        (ARTIFACTS / "base_calibration_summary.json").read_text()
    )

    assert summary["overall"] == {
        "rollouts": 84,
        "valid_rollouts": 84,
        "runtime_errors": 0,
        "success": 57,
        "compliance": 71,
        "CS": 44,
        "CF": 27,
        "VS": 13,
        "VF": 0,
    }
    assert summary["h1_base_prerequisite"]["judgment"] == "MIXED"
    assert {
        key: value["status"]
        for key, value in summary["h1_base_prerequisite"]["mechanisms"].items()
    } == {
        "A": "WEAK_HEADROOM",
        "B": "SATURATED",
        "C": "WEAK_HEADROOM",
    }
    assert summary["h2"]["overall"] == "NOT_SUPPORTED"
    assert summary["h3"]["I1"]["judgment"] == "MIXED"
    assert summary["h3"]["I2"]["judgment"] == "NOT_SUPPORTED"
    assert summary["h3"]["overall"] == "MIXED"
    assert summary["pilot_decision"] == "STOP"

    assert Counter(row["component"] for row in _rows()) == {
        "A": 18,
        "B": 18,
        "C": 12,
        "I1": 12,
        "I2": 12,
        "confirmation_control": 6,
        "reason_control": 6,
    }
