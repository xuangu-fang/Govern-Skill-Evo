import json
import tempfile
from pathlib import Path

import pytest

from src.adapters.stwebagentbench import validated_suitecrm as builder
from src.adapters.stwebagentbench.validated_suitecrm import (
    ARTIFACT_DIR,
    FORMAL_MANIFEST,
    SOURCE_SCENARIOS,
    SOURCE_SPLIT_MANIFEST,
    SOURCE_TASKS,
    audit_constraint_model,
    build,
    sha256_file,
)
from src.adapters.stwebagentbench.validated_suitecrm_spec import (
    DROP_TASK_IDS,
    RETAINED_TASK_IDS,
    SELECTION_TASK_IDS,
    TEST_TASK_IDS,
    TRAIN_TASK_IDS,
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_is_ready_and_source_files_are_unchanged(monkeypatch):
    with tempfile.TemporaryDirectory(dir=builder.REPO_ROOT / "artifacts") as directory:
        root = Path(directory)
        artifact_dir = root / "benchmark"
        formal_manifest = root / "manifest.json"
        monkeypatch.setattr(builder, "ARTIFACT_DIR", artifact_dir)
        monkeypatch.setattr(builder, "FORMAL_MANIFEST", formal_manifest)
        before = (sha256_file(SOURCE_TASKS), sha256_file(SOURCE_SCENARIOS))
        manifest = build()
        after = (sha256_file(SOURCE_TASKS), sha256_file(SOURCE_SCENARIOS))
        assert manifest["status"] == "ready"
        assert before == after
        report = _load(artifact_dir / "validation_report.json")
        assert report["critical_count"] == 0
        assert report["quarantine_count"] == 0
        assert report["retained_task_count"] == 52


def test_exact_drop_and_split_contract():
    tasks = _load(ARTIFACT_DIR / "validated_tasks.json")
    retained = {task["task_id"] for task in tasks}
    assert retained == set(RETAINED_TASK_IDS)
    assert retained.isdisjoint(DROP_TASK_IDS)

    manifest = _load(FORMAL_MANIFEST)
    actual = {
        split: tuple(
            task_id
            for template in manifest["splits"][split]["templates"]
            for task_id in template["task_ids"]
        )
        for split in ("train", "selection", "test")
    }
    assert actual == {
        "train": TRAIN_TASK_IDS,
        "selection": SELECTION_TASK_IDS,
        "test": TEST_TASK_IDS,
    }
    assert tuple(map(len, (actual["train"], actual["selection"], actual["test"]))) == (32, 10, 10)
    assert not (set(actual["train"]) & set(actual["selection"]))
    assert not (set(actual["train"]) & set(actual["test"]))
    assert not (set(actual["selection"]) & set(actual["test"]))


def test_retained_template_assignments_match_v03_and_do_not_cross_splits():
    old = _load(SOURCE_SPLIT_MANIFEST)
    new = _load(FORMAL_MANIFEST)
    old_assignment = {
        task_id: split
        for split in ("train", "selection", "test")
        for template in old["splits"][split]["templates"]
        for task_id in template["task_ids"]
    }
    template_splits = {}
    for split in ("train", "selection", "test"):
        for template in new["splits"][split]["templates"]:
            template_splits.setdefault(template["intent_template_id"], set()).add(split)
            assert all(old_assignment[task_id] == split for task_id in template["task_ids"])
    assert all(len(splits) == 1 for splits in template_splits.values())


def test_scenarios_are_exact_filtered_copies_with_separate_authorized_layer():
    source = _load(SOURCE_SCENARIOS)
    validated = _load(ARTIFACT_DIR / "validated_scenarios.json")
    assert set(map(int, validated["scenarios"])) == set(RETAINED_TASK_IDS)
    for task_id in RETAINED_TASK_IDS:
        assert validated["scenarios"][str(task_id)] == source["scenarios"][str(task_id)]
    assert "authorized_task_values" in validated


def test_patch_and_audit_counts_are_frozen():
    patches = _load(ARTIFACT_DIR / "task_patches.json")
    audit = _load(ARTIFACT_DIR / "task_audit.json")
    assert patches["polarity_patch_count"] == 27
    assert patches["only_fill_expansion_count"] > 0
    rows = {row["task_id"]: row for row in audit["tasks"]}
    assert len(rows) == 87
    assert all(rows[task_id]["status"] == "DROP" for task_id in DROP_TASK_IDS)
    assert all(rows[task_id]["reason"] == "SEMANTIC_UNSAT" for task_id in DROP_TASK_IDS)


def test_train_batches_are_non_overlapping_11_11_10():
    batches = _load(FORMAL_MANIFEST)["train_batch_plan"]["batches"]
    task_ids = [task_id for batch in batches for task_id in batch["task_ids"]]
    assert [len(batch["task_ids"]) for batch in batches] == [11, 11, 10]
    assert len(task_ids) == len(set(task_ids)) == 32
    assert set(task_ids) == set(TRAIN_TASK_IDS)


def test_normalized_constraint_audit_detects_required_conflict_and_forbidden_action():
    issues = audit_constraint_model(
        {
            "T": {
                "required_fields": {"status": "Closed"},
                "required_actions": ["delete"],
                "final_fields": {"status": "Closed"},
            },
            "P": {
                "required_fields": [
                    {"field": "status", "value": "Pending Input", "priority": "organization"},
                    {"field": "status", "value": "Recycled", "priority": "organization"},
                ],
                "forbidden_actions": ["delete"],
                "temporal": [
                    {
                        "first_field": "status",
                        "first_value": "Pending Input",
                        "final_field": "status",
                        "final_value": "Closed",
                        "evaluator_requires_first_as_final": True,
                    }
                ],
            },
            "E": {
                "required": [{"target": "status", "value": "Pending Input"}],
                "forbidden": [{"target": "status", "value": "Pending Input"}],
                "only_fill": ["Closed"],
            },
            "task_values": ["Closed"],
            "scenario_values": ["John"],
            "policy_values": ["Pending Input"],
        }
    )
    codes = {issue["code"] for issue in issues}
    assert {
        "TASK_POLICY_FINAL_STATE_CONFLICT",
        "POLICY_POLICY_CONFLICT",
        "OPPOSITE_EVALUATOR_POLARITY",
        "REQUIRED_ACTION_FORBIDDEN",
        "TEMPORAL_REQUIREMENT_ENCODED_AS_FINAL_STATE",
        "ONLY_FILL_EXCLUDES_SCENARIO_VALUES",
        "ONLY_FILL_EXCLUDES_POLICY_VALUES",
    } <= codes
