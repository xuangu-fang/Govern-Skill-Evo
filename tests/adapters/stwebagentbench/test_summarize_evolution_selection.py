"""Tests for the paired S0 -> S1 Selection summarizer."""

from __future__ import annotations

import pytest

from src.adapters.stwebagentbench.summarize_evolution_selection import (
    build_report,
    render_markdown,
)


def make_row(
    task_id: int,
    method: str,
    task_success: bool,
    compliant: bool,
    violation_count: int,
    category: str | None,
    steps: int,
) -> dict:
    return {
        "task_id": task_id,
        "method": method,
        "task_success": task_success,
        "compliant": compliant,
        "cup": task_success and compliant,
        "successful_but_violating": task_success and not compliant,
        "violation_count": violation_count,
        "violation_categories": (
            {category: violation_count} if category else {}
        ),
        "steps": steps,
    }


def test_build_report_computes_requested_metrics_and_transitions() -> None:
    reference = [
        make_row(1, "no_skill", False, False, 2, "strict_execution", 10),
        make_row(2, "no_skill", True, False, 1, "user_consent", 8),
        make_row(
            3,
            "no_skill",
            False,
            False,
            1,
            "hierarchy_adherence",
            6,
        ),
        make_row(4, "no_skill", False, False, 1, "user_consent", 12),
        make_row(5, "no_skill", True, True, 0, None, 9),
    ]
    candidate = [
        make_row(
            1,
            "governed_candidate_s1",
            True,
            False,
            1,
            "strict_execution",
            9,
        ),
        make_row(
            2,
            "governed_candidate_s1",
            False,
            False,
            1,
            "strict_execution",
            10,
        ),
        make_row(3, "governed_candidate_s1", True, True, 0, None, 5),
        make_row(4, "governed_candidate_s1", False, True, 0, None, 11),
        make_row(5, "governed_candidate_s1", True, True, 0, None, 9),
    ]

    report = build_report(
        reference,
        candidate,
        "no_skill",
        "governed_candidate_s1",
    )

    aggregate = report["aggregate"]
    assert aggregate["reference"]["task_success"]["count"] == 2
    assert aggregate["candidate"]["task_success"]["count"] == 3
    assert aggregate["reference"]["total_violation_instances"] == 5
    assert aggregate["candidate"]["total_violation_instances"] == 2
    assert aggregate["deltas"]["task_success"] == 1
    assert aggregate["deltas"]["compliance"] == 2
    assert aggregate["deltas"]["cup"] == 1
    assert aggregate["deltas"]["total_violation_instances"] == -3

    assert report["state_distribution"] == {
        "reference": {"VF": 3, "VS": 1, "CF": 0, "CS": 1},
        "candidate": {"VF": 1, "VS": 1, "CF": 1, "CS": 2},
        "deltas": {"VF": -2, "VS": 0, "CF": 1, "CS": 1},
    }

    transitions = report["task_evolution_transitions"]
    assert transitions["paired_task_count"] == 5
    assert transitions["stable_task_count"] == 1
    assert transitions["changed_task_count"] == 4
    assert [
        (task["task_id"], task["from_state"], task["to_state"])
        for task in transitions["changed_tasks"]
    ] == [
        (1, "VF", "VS"),
        (2, "VS", "VF"),
        (3, "VF", "CS"),
        (4, "VF", "CF"),
    ]

    assert report["violation_categories"] == {
        "reference": {
            "hierarchy_adherence": 1,
            "strict_execution": 2,
            "user_consent": 2,
        },
        "candidate": {
            "hierarchy_adherence": 0,
            "strict_execution": 2,
            "user_consent": 0,
        },
        "deltas": {
            "hierarchy_adherence": -1,
            "strict_execution": 0,
            "user_consent": -2,
        },
    }

    markdown = render_markdown(report)
    assert "5个Task中有1个保持在原状态，4个发生状态变化" in markdown
    assert "| 1 | VF → VS |" in markdown
    assert "| Strict Execution | 2 | 2 | 0 |" in markdown


def test_build_report_rejects_unpaired_task_ids() -> None:
    reference = [
        make_row(1, "no_skill", False, False, 1, "strict_execution", 2)
    ]
    candidate = [
        make_row(
            2,
            "governed_candidate_s1",
            False,
            False,
            1,
            "strict_execution",
            2,
        )
    ]

    with pytest.raises(ValueError, match="task IDs do not match"):
        build_report(
            reference,
            candidate,
            "no_skill",
            "governed_candidate_s1",
        )
