import json
from pathlib import Path


REPLAY_ROOT = Path(
    "artifacts/stweb_suitecrm_interactive_validated_v02/offline_replay_attempt_02"
)
FIELD_EVIDENCE_REPLAY_ROOT = Path(
    "artifacts/stweb_suitecrm_interactive_validated_v02/"
    "offline_replay_holdout_attempt_02_field_evidence_fix"
)


def test_frozen_attempt_02_offline_replay_contract():
    summary = json.loads((REPLAY_ROOT / "summary.json").read_text())
    assert summary["status"] == "passed"
    assert summary["shadow_trajectories"] == 36
    assert summary["original_task_success"] == 17
    assert summary["v01_task_success"] == 17
    assert summary["v02_task_success"] == 17
    assert summary["task_success_mismatch_count"] == 0
    assert summary["known_v01_false_hallucination_findings"] == 7
    assert summary["known_v01_false_hallucination_findings_remaining"] == 0
    assert summary["unexplained_delta_count"] == 0


def test_frozen_replay_deltas_are_all_in_the_allowed_mechanisms():
    diff = json.loads((REPLAY_ROOT / "hallucination_diff.json").read_text())
    allowed = {
        "HALLUCINATION_ACTION_FILTER",
        "HALLUCINATION_TIME_NORMALIZATION",
        "HALLUCINATION_DURATION_NORMALIZATION",
        "HALLUCINATION_RECURRENCE_NORMALIZATION",
        "HALLUCINATION_DATE_NORMALIZATION",
    }
    assert diff["remaining_known_finding_count"] == 0
    assert diff["unexplained_deltas"] == []
    assert all(row["reason"] in allowed for row in diff["deltas"])


def test_frozen_holdout_field_evidence_replay_contract():
    summary = json.loads((FIELD_EVIDENCE_REPLAY_ROOT / "summary.json").read_text())
    assert summary["status"] == "passed"
    assert summary["shadow_trajectories"] == 30
    assert summary["task_success_before"] == summary["task_success_after"] == 13
    assert summary["task_success_mismatch_count"] == 0
    assert summary["known_false_positive_count"] == 9
    assert summary["known_false_positive_replayed_count"] == 9
    assert summary["known_false_positive_remaining_count"] == 0
    assert summary["unexplained_delta_count"] == 0
    assert summary["new_hallucination_unresolved_count"] == 0


def test_holdout_field_evidence_deltas_are_only_the_scoped_repair():
    payload = json.loads(
        (FIELD_EVIDENCE_REPLAY_ROOT / "evaluator_diff.json").read_text()
    )
    allowed = {
        "HALLUCINATION_AX_TREE_FIELD_EVIDENCE",
        "HALLUCINATION_LABEL_NORMALIZATION",
        "HALLUCINATION_DATETIME_NORMALIZATION",
    }
    assert len(payload["deltas"]) == 9
    assert {row["change_reason"] for row in payload["deltas"]} <= allowed
    assert all(row["decision"]["authorized"] for row in payload["deltas"])


def test_final_canary_is_frozen_to_the_remaining_train_tasks():
    final = json.loads(
        Path(
            "experiments/benchmarks/stweb_suitecrm_interactive_validated_v02/"
            "final_canary_manifest.json"
        ).read_text()
    )
    formal = json.loads(
        Path("experiments/manifests/stweb_suitecrm_interactive_validated_v02.json").read_text()
    )
    expected = [76, 244, 264, 246, 266, 248, 268, 250, 252, 272]
    train = {
        task_id
        for template in formal["splits"]["train"]["templates"]
        for task_id in template["task_ids"]
    }
    assert final["task_ids"] == expected
    assert final["planned_rollouts"] == 30
    assert final["rollouts_per_task"] == 3
    assert set(expected) <= train
    assert not set(expected) & set(final["prior_canary_task_ids"])


def test_final_canary_results_remain_fail_closed_on_new_false_positives():
    root = Path(
        "artifacts/stweb_suitecrm_interactive_validated_v02/final_canary_attempt_03"
    )
    summary = json.loads((root / "summary.json").read_text())
    review = json.loads((root / "hallucination_review.json").read_text())
    validation = json.loads(
        Path(
            "experiments/benchmarks/stweb_suitecrm_interactive_validated_v02/"
            "validation_report.json"
        ).read_text()
    )
    assert summary["planned_rollouts"] == summary["completed_rollouts"] == 30
    assert summary["failed_rollouts"] == 0
    assert summary["task_success_mismatch_count"] == 0
    assert review["false_positive_count"] == 7
    assert review["unresolved_count"] == 0
    assert review["new_systematic_bugs"]
    assert summary["final_validation_status"] == "needs_review"
    assert validation["status"] == "needs_review"
