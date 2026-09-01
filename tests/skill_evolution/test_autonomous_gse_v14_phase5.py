from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.skill_evolution.autonomous_gse_v14_orchestrator import (
    EvolutionServices, _analysis_edits, run_campaign, run_evolution_step,
)
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as runtime
from src.skill_evolution import autonomous_gse_v14_orchestrator as orchestrator
from src.skill_evolution.regression_analysis_v14 import (
    RegressionAnalysisRequest, analyze_regressions, select_adverse_pairs,
)
from src.skill_evolution.target_behavior_analysis_v14 import (
    analyze_target_behaviors,
)


def _batches():
    return [{
        "batch_id": f"batch_{step}",
        "task_ids": [
            *(f"airline:{step}_{index}" for index in range(10)),
            *(f"retail:{step}_{index}" for index in range(10)),
        ],
    } for step in (1, 2, 3)]


def _rows(batch, *, state="compliant_success", seed_shift=0):
    rows = []
    for tagged in batch["task_ids"]:
        domain, task_id = tagged.split(":", 1)
        for rollout_index in (1, 2, 3):
            rows.append({
                "source_id": f"{domain}_{task_id}_{rollout_index}",
                "domain": domain, "task_id": task_id, "rollout_index": rollout_index,
                "rollout_seed": 199 + rollout_index + seed_shift, "state": state,
                "trajectory": [{"step": 1, "event_type": "assistant"}],
            })
    return rows


def _candidate(step):
    diagnosis = {
        "diagnosis_id": "diagnosis_001",
        "source_ids": [f"airline_{step}_0_{index}" for index in (1, 2, 3)],
    }
    edit = {
        "canonical_edit_id": "canonical_edit_001",
        "derived_from_diagnosis_ids": ["diagnosis_001"],
        "verification_target": {
            "problem": "problem", "trigger_condition": "trigger",
            "expected_behavior": "expected",
        },
    }
    return SimpleNamespace(
        proposal_status="CANDIDATE", proposal_reason={"code": "UPDATE"},
        candidate_skill=f"# candidate {step}\n", diagnoses=[diagnosis], applied_edits=[edit],
    )


def _noop():
    return SimpleNamespace(
        proposal_status="NO_CANDIDATE",
        proposal_reason={"code": "NO_UPDATE_ELIGIBLE_DIAGNOSIS"},
        candidate_skill=None, diagnoses=[], applied_edits=[],
    )


def _campaign(skill_path):
    return {
        "campaign_id": "autonomous_gse_v14",
        "initial_parent": {"version": "S0", "path": str(skill_path)},
    }


def _services(decisions, calls, *, proposal=None, replay_error=None, target=None, regression=None):
    iterator = iter(decisions)

    def monitor(skill):
        calls["monitor"].append(skill["skill_id"])
        return {"skill": copy.deepcopy(skill), "monitor_id": "fixed_monitor_m"}

    def parent_rollouts(step, batch, skill):
        calls["parent"].append((step, skill["skill_id"]))
        rows = _rows(batch)
        return {"rows": rows, "evidence": copy.deepcopy(rows)}

    def candidate_replay(step, batch, skill):
        calls["replay"].append((step, skill["skill_id"]))
        if replay_error:
            raise replay_error
        return {"rows": _rows(batch), "evidence": []}

    def gate(_report):
        decision = next(iterator)
        return {
            "bootstrap": {"positive_probability": 0.9 if decision == "ACCEPT" else 0.2},
            "gate": {"decision": decision, "positive_probability_threshold": 0.8},
        }

    return EvolutionServices(
        parent_rollouts=parent_rollouts,
        propose=proposal or (lambda context, step: _candidate(step)),
        candidate_monitor=monitor, candidate_replay=candidate_replay,
        joint_report=lambda parent, candidate: {"parent": parent, "candidate": candidate},
        gate=gate,
        target_behavior=target or (lambda *args: {"role": "logging_only", "results": []}),
        regression=regression or (lambda *args: {"role": "logging_only", "adverse_pairs": []}),
    )


def _calls():
    return {"monitor": [], "parent": [], "replay": []}


def test_three_step_accept_retain_accept_parent_chain(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    calls = _calls()
    state = run_campaign(
        _campaign(skill), {"batches": _batches()},
        _services(["ACCEPT", "RETAIN", "ACCEPT"], calls), artifact_root=tmp_path / "artifacts",
    )
    assert [step["parent_skill"]["skill_id"] for step in state["completed_steps"]] == [
        "S0", "candidate_step_01", "candidate_step_01",
    ]
    assert [step["next_parent"]["skill_id"] for step in state["completed_steps"]] == [
        "candidate_step_01", "candidate_step_01", "candidate_step_03",
    ]
    assert state["final_skill"]["skill_id"] == "candidate_step_03"
    assert calls["monitor"] == ["S0", "candidate_step_01", "candidate_step_02", "candidate_step_03"]


def test_all_retain_reuses_s0_monitor_and_final_skill_is_s0(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    calls = _calls()
    state = run_campaign(
        _campaign(skill), {"batches": _batches()},
        _services(["RETAIN", "RETAIN", "RETAIN"], calls), artifact_root=tmp_path / "artifacts",
    )
    assert state["final_skill"]["skill_id"] == "S0"
    assert [step["parent_skill"]["skill_id"] for step in state["completed_steps"]] == ["S0"] * 3
    assert calls["monitor"].count("S0") == 1


@pytest.mark.parametrize(
    ("decision", "expected_parent"), (("ACCEPT", "candidate_step_01"), ("RETAIN", "S0")),
)
def test_single_step_promotion_and_monitor_cache_object(tmp_path, decision, expected_parent):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    parent = {"skill_id": "S0", "skill_version": "S0", "skill_path": str(skill)}
    parent_monitor = {"identity": "Monitor(S0)"}
    calls = _calls()
    summary, next_parent, next_monitor = run_evolution_step(
        step=1, batch=_batches()[0], parent=parent, parent_monitor=parent_monitor,
        campaign={}, services=_services([decision], calls), artifact_root=tmp_path / "artifacts",
    )
    assert summary["selection"]["decision"] == decision
    assert next_parent["skill_id"] == expected_parent
    assert next_monitor == (
        {"skill": next_parent, "monitor_id": "fixed_monitor_m"}
        if decision == "ACCEPT" else parent_monitor
    )


def test_legal_noop_retains_without_candidate_cost(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    parent = {"skill_id": "S0", "skill_version": "S0", "skill_path": str(skill)}
    calls = _calls()
    services = _services([], calls, proposal=lambda context, step: _noop())
    summary, next_parent, next_monitor = run_evolution_step(
        step=1, batch=_batches()[0], parent=parent, parent_monitor={"S0": True},
        campaign={}, services=services, artifact_root=tmp_path / "artifacts",
    )
    assert summary["selection"] == {
        "gate_executed": False, "decision": "RETAIN", "reason": "no_candidate_update",
    }
    assert next_parent == parent and next_monitor == {"S0": True}
    assert calls["monitor"] == [] and calls["replay"] == []


def test_candidate_monitor_failure_is_execution_error_not_retain(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    parent = {"skill_id": "S0", "skill_version": "S0", "skill_path": str(skill)}
    services = _services(["ACCEPT"], _calls())
    services = EvolutionServices(
        **{**services.__dict__, "candidate_monitor": lambda skill: (_ for _ in ()).throw(RuntimeError("monitor failed"))},
    )
    with pytest.raises(RuntimeError, match="monitor failed"):
        run_evolution_step(
            step=1, batch=_batches()[0], parent=parent, parent_monitor={}, campaign={},
            services=services, artifact_root=tmp_path / "artifacts",
        )
    error = json.loads((tmp_path / "artifacts/steps/step_01/selection/selection_error.json").read_text())
    assert error["stage"] == "selection_path"


def test_invalid_proposal_status_is_execution_failure_not_retain(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    parent = {"skill_id": "S0", "skill_version": "S0", "skill_path": str(skill)}
    invalid = SimpleNamespace(
        proposal_status="INVALID_PROPOSAL", proposal_reason={"code": "ERROR"},
        candidate_skill=None, diagnoses=[], applied_edits=[],
    )
    with pytest.raises(Exception, match="legal no-op"):
        run_evolution_step(
            step=1, batch=_batches()[0], parent=parent, parent_monitor={}, campaign={},
            services=_services([], _calls(), proposal=lambda context, step: invalid),
            artifact_root=tmp_path / "artifacts",
        )
    assert not (tmp_path / "artifacts/steps/step_01/step_summary.json").exists()


@pytest.mark.parametrize("analysis", ("target", "regression"))
def test_logging_analysis_cannot_veto_accept(tmp_path, analysis):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    parent = {"skill_id": "S0", "skill_version": "S0", "skill_path": str(skill)}
    target = lambda *args: {"role": "logging_only", "results": [{"label": "WORSENED"}]}
    regression = lambda *args: {
        "role": "logging_only", "adverse_pairs": [{"causal_assessment": "CHANGE_CAUSED"}],
    }
    services = _services(["ACCEPT"], _calls(), target=target, regression=regression)
    summary, next_parent, _ = run_evolution_step(
        step=1, batch=_batches()[0], parent=parent, parent_monitor={}, campaign={},
        services=services, artifact_root=tmp_path / "artifacts",
    )
    assert summary["selection"]["decision"] == "ACCEPT"
    assert summary["promotion_source"] == "distributional_gate_only"
    assert next_parent["skill_id"] == "candidate_step_01"


def test_analysis_error_does_not_change_saved_accept(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    parent = {"skill_id": "S0", "skill_version": "S0", "skill_path": str(skill)}
    services = _services(
        ["ACCEPT"], _calls(),
        regression=lambda *args: (_ for _ in ()).throw(RuntimeError("analysis failed")),
    )
    summary, next_parent, _ = run_evolution_step(
        step=1, batch=_batches()[0], parent=parent, parent_monitor={}, campaign={},
        services=services, artifact_root=tmp_path / "artifacts",
    )
    selection = json.loads((
        tmp_path / "artifacts/steps/step_01/selection/selection_decision.json"
    ).read_text())
    assert selection["gate_decision"] == "ACCEPT"
    assert summary["explanation"]["regression_analysis_status"] == "error"
    assert next_parent["skill_id"] == "candidate_step_01"


def test_candidate_replay_lineage_error_is_logging_only(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    parent = {"skill_id": "S0", "skill_version": "S0", "skill_path": str(skill)}
    services = _services(["ACCEPT"], _calls())
    original = services.candidate_replay
    services = EvolutionServices(**{
        **services.__dict__,
        "candidate_replay": lambda step, batch, candidate: {
            **original(step, batch, candidate),
            "rows": _rows(batch, seed_shift=1),
        },
    })
    summary, next_parent, _ = run_evolution_step(
        step=1, batch=_batches()[0], parent=parent, parent_monitor={}, campaign={},
        services=services, artifact_root=tmp_path / "artifacts",
    )
    assert summary["selection"]["decision"] == "ACCEPT"
    assert summary["explanation"]["current_batch_replay_status"] == "error"
    assert next_parent["skill_id"] == "candidate_step_01"


@pytest.mark.parametrize(
    ("before", "after", "selected"),
    (
        ("compliant_failure", "violating_success", True),
        ("violating_success", "compliant_failure", True),
        ("compliant_success", "compliant_success", False),
        ("violating_failure", "compliant_success", False),
    ),
)
def test_regression_selector_covers_any_negative_axis(before, after, selected):
    parent = [{
        "domain": "airline", "task_id": "1", "rollout_index": 1,
        "rollout_seed": 200, "state": before,
    }]
    candidate = [{**parent[0], "state": after}]
    assert bool(select_adverse_pairs(parent, candidate)) is selected


def test_adverse_pair_without_skill_causal_chain_is_unrelated():
    parent = [{
        "domain": "airline", "task_id": "1", "rollout_index": 1,
        "rollout_seed": 200, "state": "compliant_success", "trajectory": [],
    }]
    candidate = [{**parent[0], "state": "compliant_failure"}]
    report = analyze_regressions(
        parent, candidate, [], analyzer=lambda request: {
            "first_behavioral_divergence": "none attributable to skill",
            "causal_assessment": "UNRELATED_VARIATION",
            "evidence_steps": {"parent": [], "candidate": []}, "reason": "no causal chain",
        },
    )
    assert report["adverse_pairs"][0]["causal_assessment"] == "UNRELATED_VARIATION"


def test_target_behavior_schema_has_no_hard_verdict():
    batch = _batches()[0]
    parent = _rows(batch)
    candidate = _rows(batch)
    proposal = _candidate(1)
    report = analyze_target_behaviors(
        proposal.applied_edits, proposal.diagnoses, parent, candidate,
        analyzer=lambda request: {
            "canonical_edit_id": request.canonical_edit_id,
            "verification_target": request.verification_target,
            "analyzed_pairs": [],
            "summary": {"improved": 0, "unchanged_bad": 0, "preserved": 0, "worsened": 0, "not_exercised": 3},
        },
    )
    serialized = json.dumps(report)
    assert report["role"] == "logging_only"
    assert "FIXED" not in serialized and "NOT_FIXED" not in serialized and "targeted_pass" not in serialized


def test_full_campaign_never_calls_final_test(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    calls = _calls()
    state = run_campaign(
        _campaign(skill), {"batches": _batches()},
        _services(["RETAIN"] * 3, calls), artifact_root=tmp_path / "artifacts",
    )
    assert state["current_step"] == 3
    assert "final_test" not in calls


def test_explanation_and_monitor_never_enter_next_step_proposal(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    calls = _calls()

    def propose(context, step):
        serialized = json.dumps(context.current_batch_governed_evidence)
        for forbidden in (
            "target_behavior_analysis", "regression_analysis", "gate rationale",
            "fixed_monitor_m", "selection_decision",
        ):
            assert forbidden not in serialized
        return _candidate(step)

    state = run_campaign(
        _campaign(skill), {"batches": _batches()},
        _services(["ACCEPT", "RETAIN", "RETAIN"], calls, proposal=propose),
        artifact_root=tmp_path / "artifacts",
    )
    assert state["current_step"] == 3


def test_initial_campaign_state_supports_resume_after_execution_failure(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    calls = _calls()
    services = _services(["ACCEPT"], calls)
    services = EvolutionServices(**{
        **services.__dict__,
        "parent_rollouts": lambda *args: (_ for _ in ()).throw(RuntimeError("rollout failed")),
    })
    root = tmp_path / "artifacts"
    with pytest.raises(RuntimeError, match="rollout failed"):
        run_campaign(_campaign(skill), {"batches": _batches()}, services, artifact_root=root)
    state = json.loads((root / "campaign_state.json").read_text())
    assert state["current_step"] == 0
    assert state["current_parent"]["skill_id"] == "S0"
    assert state["completed_steps"] == []


def test_cli_exposes_run_and_resume_without_final_test(monkeypatch, tmp_path, capsys):
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text("{}", encoding="utf-8")
    campaign = {"campaign_id": "v14", "evolution": {"batch_map": "unused"}}
    monkeypatch.setattr(runtime, "_campaign_files", lambda path: (campaign, {"batches": []}))
    calls = []
    monkeypatch.setattr(
        runtime, "run_v14_campaign",
        lambda campaign, batch_map, artifact_root, resume, services=None: calls.append(resume) or {"ok": True},
    )
    assert runtime.main(["run", "--campaign", str(campaign_path), "--artifact-root", str(tmp_path / "run")]) == 0
    assert runtime.main(["resume", "--campaign", str(campaign_path), "--artifact-root", str(tmp_path / "run")]) == 0
    assert calls == [False, True]
    assert capsys.readouterr().out.count('"ok": true') == 2


def test_orchestration_has_only_distributional_promotion_authority():
    source = inspect.getsource(orchestrator)
    assert "evolution_gate_v13" not in source
    assert "targeted_pass" not in source
    assert "regression_pass" not in source
    assert "aggregate_guard" not in source
    assert "weighted" not in source.casefold()
    assert "cup" not in source.casefold()
    assert orchestrator.PROMOTION_SOURCE == "distributional_gate_only"


def test_v13_patch_lineage_is_expanded_for_v14_logging():
    proposal = SimpleNamespace(
        applied_edits=[{
            "canonical_edit_id": "canonical_edit_001",
            "derived_from_patch_ids": ["diagnosis_001"],
        }],
        raw_patches=[{"patch_id": "diagnosis_001", "diagnosis_id": "diagnosis_001"}],
    )
    assert _analysis_edits(proposal)[0]["derived_from_diagnosis_ids"] == ["diagnosis_001"]


def test_saved_proposal_is_reused_without_diagnosis_or_editor_call(tmp_path):
    skill = tmp_path / "S0.md"
    skill.write_text("# S0\n", encoding="utf-8")
    parent = {"skill_id": "S0", "skill_version": "S0", "skill_path": str(skill)}
    calls = _calls()
    proposal_calls = []

    def propose(context, step):
        proposal_calls.append(step)
        return _candidate(step)

    services = _services(["RETAIN", "RETAIN"], calls, proposal=propose)
    kwargs = {
        "step": 1, "batch": _batches()[0], "parent": parent,
        "parent_monitor": {"S0": True}, "campaign": {}, "services": services,
        "artifact_root": tmp_path / "artifacts",
    }
    run_evolution_step(**kwargs)
    run_evolution_step(**kwargs)
    assert proposal_calls == [1]
