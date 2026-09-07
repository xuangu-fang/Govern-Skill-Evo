import json

from benchmarks.tau2_governed_evolution.intent_dynamics.run_airline_phase_a_empty_rollouts import (
    CAMPAIGN_PATH,
    MANIFEST_PATH,
    _load_task,
    validate_audit_contract,
)


def test_phase_a_headroom_manifest_contract() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    campaign = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))

    validate_audit_contract(manifest, campaign)

    eligible = [
        item
        for item in manifest["tasks"]
        if not item.get("phase_a_conformance", "").startswith("excluded_posthoc")
    ]
    assert len(eligible) == 10
    assert sum(item["layer"] == "c1_upfront_seed" for item in eligible) == 4
    assert sum(item["layer"] == "broader_native" for item in eligible) == 6
    assert manifest["selection_amendment"]["replacement_outcome_used_for_selection"] is False


def test_phase_a_headroom_tasks_resolve() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    for spec in manifest["tasks"]:
        task = _load_task(spec)
        assert str(task.id) == str(spec["source_task_id"] if spec["source_kind"] == "official_native_task" else spec["audit_task_id"])


def test_progressive_native_task_is_not_counted_as_phase_a() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    specs = {item["audit_task_id"]: item for item in manifest["tasks"]}

    assert specs["native_airline_42"]["phase_a_conformance"] == (
        "excluded_posthoc_progressive_disclosure"
    )
    assert specs["native_airline_34"]["phase_a_conformance"] == (
        "excluded_posthoc_feedback_conditioned_budget"
    )
    assert specs["native_airline_41"]["phase_a_conformance"] == (
        "eligible_structural_replacement"
    )
