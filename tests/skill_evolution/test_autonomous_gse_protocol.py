from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from src.skill_evolution.two_dimensional_gate import analyze_candidate


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas/autonomous_gse_v01_campaign.schema.json"
)
STEP_SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v01_step.schema.json"
MANIFEST_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
)
FROZEN_FREEZE_TOOL_PATH = (
    PROJECT_ROOT
    / "experiments/results/autonomous_gse_v01/frozen_sources/"
    "autonomous_gse_freeze.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(instance: dict, schema: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(schema)
    validator.check_schema(schema)
    validator.validate(instance)


def artifact(kind: str, version: str) -> dict[str, str]:
    return {
        "kind": kind,
        "version": version,
        "path": f"artifacts/{version}.json",
        "sha256": "a" * 64,
    }


def gate_rows_for_deltas(
    task_success: int,
    compliance: int,
    cup: int,
    *,
    severity_status: str = "passed",
) -> list[dict]:
    """Build paired rows whose aggregate deltas match a golden case."""

    if (task_success, compliance, cup) == (1, 0, 0):
        states = [((False, False), (True, False))]
    elif (task_success, compliance, cup) == (0, 1, 0):
        states = [((False, False), (False, True))]
    elif (task_success, compliance, cup) == (0, 0, 1):
        states = [
            ((False, True), (True, True)),
            ((True, False), (False, False)),
            ((False, False), (False, True)),
            ((False, True), (False, False)),
        ]
    elif (task_success, compliance, cup) == (0, 0, 0):
        states = [((False, False), (False, False))]
    elif (task_success, compliance, cup) == (1, -1, 1):
        states = [
            ((False, True), (True, True)),
            ((False, True), (False, False)),
        ]
    else:
        raise ValueError("Unsupported golden delta case")

    severe_value = None if severity_status == "not_evaluated" else False
    rows = []
    for task_id, (before, after) in enumerate(states, start=1):
        for method, state in (("parent", before), ("candidate", after)):
            row = {
                "method": method,
                "task_id": task_id,
                "task_success": state[0],
                "compliant": state[1],
            }
            if severe_value is not None:
                row["severe_violation"] = severe_value
            rows.append(row)
    return rows


def step_manifest(*, parent_kind: str, parent_version: str, operator: str) -> dict:
    return {
        "schema_version": "autonomous_gse_step_0.1.0",
        "protocol_version": "autonomous_gse_v01",
        "campaign_id": "autonomous_gse_v01",
        "epoch": 1,
        "step": 1,
        "status": "STEP_REGISTERED",
        "batch": {
            "batch_id": "batch_001",
            "batch_map_path": "artifacts/batch_map.json",
            "batch_map_sha256": "b" * 64,
            "task_ids": list(range(1, 18)),
        },
        "parent": artifact(parent_kind, parent_version),
        "proposal_operator": operator,
        "candidate_id": "epoch_001_step_001_candidate",
        "parent_checkpoint": artifact("selection_checkpoint", parent_version),
        "budget_reservation": {
            "train_trajectories": 17,
            "maximum_candidate_selection_trajectories": 18,
            "maximum_learner_calls": 1,
        },
        "data_isolation": {
            "current_batch_only": True,
            "selection_for_learning": "forbidden",
            "test_for_learning": "forbidden",
        },
    }


def test_protocol_json_files_are_valid_json() -> None:
    campaign_schema = load_json(CAMPAIGN_SCHEMA_PATH)
    step_schema = load_json(STEP_SCHEMA_PATH)
    manifest = load_json(MANIFEST_PATH)

    assert campaign_schema["$schema"].endswith("draft/2020-12/schema")
    assert step_schema["$schema"].endswith("draft/2020-12/schema")
    assert manifest["status"] == "frozen"
    assert "frozen_at" in manifest


def test_frozen_manifest_preserves_core_campaign_invariants() -> None:
    manifest = load_json(MANIFEST_PATH)

    assert manifest["initial_parent"]["kind"] == "no_skill"
    assert manifest["initial_parent"]["version"] == "S0"
    assert manifest["schedule"] == {
        "epochs": 1,
        "steps_per_epoch": 3,
        "scheduled_steps": 3,
    }
    assert manifest["train"]["total_tasks"] == 51
    assert manifest["train"]["batches"] == 3
    assert manifest["train"]["tasks_per_batch"] == 17
    assert manifest["selection"]["protocol"] == "accepted_parent_checkpoint"
    assert manifest["proposal"]["maximum_learner_calls"] == 3
    assert manifest["test"]["authorized"] is False
    assert manifest["budget"]["maximum_total_trajectories"] == 51 + 18 + 54


def test_bound_artifact_hashes_match_files() -> None:
    manifest = load_json(MANIFEST_PATH)
    bound_artifacts = [
        manifest["initial_parent"],
        manifest["train"]["source_manifest"],
        manifest["train"]["batch_map"],
        manifest["gate"]["implementation"],
        manifest["implementation_bindings"]["batch_planner"],
        manifest["implementation_bindings"]["controller"],
        manifest["implementation_bindings"]["bootstrap_operator"],
        manifest["implementation_bindings"]["incremental_operator"],
        manifest["implementation_bindings"]["bootstrap_prompt"],
        manifest["implementation_bindings"]["incremental_prompt"],
        manifest["implementation_bindings"]["train_runner"],
        manifest["implementation_bindings"]["experience_builder"],
        manifest["implementation_bindings"]["selection_runner"],
        manifest["implementation_bindings"]["benchmark_runtime_adapter"],
        manifest["implementation_bindings"]["runtime_orchestrator"],
        manifest["implementation_bindings"]["learner_adapter"],
        manifest["implementation_bindings"]["learner_client"],
        manifest["implementation_bindings"]["campaign_schema"],
        manifest["implementation_bindings"]["benchmark_agent"],
        manifest["benchmark_runtime"]["database_snapshot"],
        manifest["benchmark_runtime"]["database_reset"],
        manifest["benchmark_runtime"]["compose_file"],
    ]

    for bound in bound_artifacts:
        path = PROJECT_ROOT / bound["path"]
        assert path.is_file(), bound["path"]
        assert sha256_file(path) == bound["sha256"], bound["path"]

    frozen_freeze_tool = manifest["implementation_bindings"]["freeze_tool"]
    assert FROZEN_FREEZE_TOOL_PATH.is_file()
    assert sha256_file(FROZEN_FREEZE_TOOL_PATH) == frozen_freeze_tool["sha256"]


def test_frozen_manifest_validates_against_campaign_schema() -> None:
    validate(load_json(MANIFEST_PATH), load_json(CAMPAIGN_SCHEMA_PATH))


@pytest.mark.parametrize(
    ("field_path", "invalid_value"),
    [
        (("initial_parent", "version"), "S1"),
        (("schedule", "scheduled_steps"), 4),
        (("budget", "maximum_total_trajectories"), 124),
        (("proposal", "maximum_learner_calls"), 4),
        (("selection", "selection_data_for_learning"), "allowed"),
        (("test", "authorized"), True),
    ],
)
def test_campaign_schema_rejects_protocol_drift(
    field_path: tuple[str, str], invalid_value: object
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    manifest = load_json(MANIFEST_PATH)
    manifest[field_path[0]][field_path[1]] = invalid_value

    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, load_json(CAMPAIGN_SCHEMA_PATH))


def test_frozen_campaign_rejects_pending_runtime_bindings() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    manifest = load_json(MANIFEST_PATH)
    manifest["implementation_bindings"]["train_runner"] = {
        "kind": "runner",
        "version": "autonomous_train_runner_v01",
        "status": "pending_binding",
    }

    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, load_json(CAMPAIGN_SCHEMA_PATH))


def test_frozen_campaign_accepts_fully_bound_runtime_artifacts() -> None:
    manifest = load_json(MANIFEST_PATH)
    manifest["train"]["batch_map"] = artifact(
        "batch_map", "autonomous_gse_batch_map_0.1.0"
    )
    for name, binding in manifest["implementation_bindings"].items():
        manifest["implementation_bindings"][name] = artifact(
            binding["kind"], binding["version"]
        )

    validate(manifest, load_json(CAMPAIGN_SCHEMA_PATH))


def test_step_schema_dispatches_s0_to_bootstrap() -> None:
    manifest = step_manifest(
        parent_kind="no_skill", parent_version="S0", operator="bootstrap"
    )
    validate(manifest, load_json(STEP_SCHEMA_PATH))


def test_step_schema_dispatches_accepted_skill_to_incremental() -> None:
    manifest = step_manifest(
        parent_kind="accepted_skill", parent_version="S1", operator="incremental"
    )
    validate(manifest, load_json(STEP_SCHEMA_PATH))


@pytest.mark.parametrize(
    ("parent_kind", "parent_version", "invalid_operator"),
    [
        ("no_skill", "S0", "incremental"),
        ("accepted_skill", "S1", "bootstrap"),
    ],
)
def test_step_schema_rejects_wrong_operator_dispatch(
    parent_kind: str, parent_version: str, invalid_operator: str
) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    manifest = step_manifest(
        parent_kind=parent_kind,
        parent_version=parent_version,
        operator=invalid_operator,
    )

    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, load_json(STEP_SCHEMA_PATH))


def test_step_schema_rejects_batch_or_candidate_id_from_wrong_step() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json(STEP_SCHEMA_PATH)
    manifest = step_manifest(
        parent_kind="no_skill", parent_version="S0", operator="bootstrap"
    )
    manifest["batch"]["batch_id"] = "batch_002"

    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, schema)

    manifest["batch"]["batch_id"] = "batch_001"
    manifest["candidate_id"] = "epoch_001_step_002_candidate"
    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, schema)


def test_completed_step_requires_outcome_and_next_parent() -> None:
    schema = load_json(STEP_SCHEMA_PATH)
    manifest = step_manifest(
        parent_kind="accepted_skill", parent_version="S1", operator="incremental"
    )
    manifest.update(
        {
            "status": "STEP_COMPLETED",
            "outcome": "REJECT",
            "candidate": artifact("candidate_skill", "candidate_001"),
            "next_parent": copy.deepcopy(manifest["parent"]),
        }
    )
    validate(manifest, schema)

    jsonschema = pytest.importorskip("jsonschema")
    manifest.pop("outcome")
    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, schema)


@pytest.mark.parametrize("outcome", ["NO_CANDIDATE", "INVALID_PROPOSAL"])
def test_no_candidate_outcomes_forbid_candidate_artifact(outcome: str) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json(STEP_SCHEMA_PATH)
    manifest = step_manifest(
        parent_kind="no_skill", parent_version="S0", operator="bootstrap"
    )
    manifest.update(
        {
            "status": "STEP_COMPLETED",
            "outcome": outcome,
            "next_parent": copy.deepcopy(manifest["parent"]),
            "candidate": artifact("candidate_skill", "candidate_001"),
        }
    )

    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, schema)


def test_nonterminal_step_forbids_outcome() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json(STEP_SCHEMA_PATH)
    manifest = step_manifest(
        parent_kind="no_skill", parent_version="S0", operator="bootstrap"
    )
    manifest["outcome"] = "NO_CANDIDATE"

    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, schema)


def test_invalid_step_requires_integrity_failure_without_next_parent() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json(STEP_SCHEMA_PATH)
    manifest = step_manifest(
        parent_kind="no_skill", parent_version="S0", operator="bootstrap"
    )
    manifest.update({"status": "STEP_INVALID", "outcome": "INTEGRITY_FAILURE"})
    validate(manifest, schema)

    manifest["outcome"] = "REJECT"
    with pytest.raises(jsonschema.ValidationError):
        validate(manifest, schema)


@pytest.mark.parametrize(
    ("deltas", "expected_outcome"),
    [
        ((1, 0, 0), "ACCEPT"),
        ((0, 1, 0), "ACCEPT"),
        ((0, 0, 1), "ACCEPT"),
        ((0, 0, 0), "REJECT"),
        ((1, -1, 1), "REJECT"),
    ],
)
def test_manifest_gate_semantic_golden_cases(
    deltas: tuple[int, int, int], expected_outcome: str
) -> None:
    manifest = load_json(MANIFEST_PATH)
    gate_contract = manifest["gate"]
    metric_keys = gate_contract["implementation_metric_keys"]
    result = analyze_candidate(
        gate_rows_for_deltas(*deltas), "parent", "candidate"
    )

    actual_deltas = result["aggregate"]["deltas"]
    assert tuple(
        actual_deltas[metric_keys[metric]]
        for metric in gate_contract["aggregate_metrics"]
    ) == deltas
    implementation_decision = result["evolution_gate"]["decision"]
    assert gate_contract["decision_mapping"][implementation_decision] == (
        expected_outcome
    )


def test_manifest_gate_allows_progress_when_severity_not_evaluated() -> None:
    manifest = load_json(MANIFEST_PATH)
    result = analyze_candidate(
        gate_rows_for_deltas(1, 0, 0, severity_status="not_evaluated"),
        "parent",
        "candidate",
    )

    assert result["hard_constraint"]["status"] == "not_evaluated"
    assert manifest["gate"]["severity_policy"]["not_evaluated"] == (
        "allow_aggregate_gate_evaluation"
    )
    implementation_decision = result["evolution_gate"]["decision"]
    assert manifest["gate"]["decision_mapping"][implementation_decision] == (
        "ACCEPT"
    )


def test_manifest_gate_rejects_detected_severe_violation() -> None:
    manifest = load_json(MANIFEST_PATH)
    rows = gate_rows_for_deltas(1, 0, 0)
    candidate_row = next(row for row in rows if row["method"] == "candidate")
    candidate_row["severe_violation"] = True
    result = analyze_candidate(rows, "parent", "candidate")

    assert result["hard_constraint"]["status"] == "failed"
    assert manifest["gate"]["severity_policy"]["severe_violation_detected"] == (
        "REJECT"
    )
    implementation_decision = result["evolution_gate"]["decision"]
    assert manifest["gate"]["decision_mapping"][implementation_decision] == (
        "REJECT"
    )
