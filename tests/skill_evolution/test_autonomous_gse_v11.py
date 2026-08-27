from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import src.learners.stwebagentbench.generate_governed_skill_v11 as editor_v11
import src.skill_evolution.diagnosis_v11 as diagnosis_v11
import src.skill_evolution.regression_diagnosis_v11 as regression_v11
import src.skill_evolution.targeted_fix_v11 as targeted_v11

from src.adapters.tau2.tau3_task_split_v11 import (
    _load_official_splits,
    build_frozen_split,
    validate_frozen_split,
)
from src.learners.stwebagentbench.generate_governed_skill_v11 import build_editor_prompts
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v11_benchmark_runtime import (
    build_campaign_dry_plan,
    build_holdout_plan,
    derive_rollout_seeds,
    evaluate_holdout,
    matched_replay_plan,
    run_v11_campaign,
    validate_campaign_contract,
)
from src.skill_evolution.autonomous_gse_v11_proposal import (
    DiagnosisDrivenProposalOperator,
    DiagnosisEditorRequest,
)
from src.skill_evolution.diagnosis_contract_v11 import validate_diagnosis
from src.skill_evolution.diagnosis_v11 import DIAGNOSIS_SYSTEM_PROMPT
from src.skill_evolution.evolution_gate_v11 import build_evolution_decision
from src.skill_evolution.regression_diagnosis_v11 import (
    REGRESSION_TRANSITIONS,
    RegressionDiagnosisResponseError,
    SYSTEM_PROMPT as REGRESSION_PROMPT,
    build_regression_transition_report,
    parse_regression_diagnosis_response,
)
from src.skill_evolution.targeted_fix_v11 import (
    SYSTEM_PROMPT as TARGETED_PROMPT,
    parse_targeted_fix_response,
)

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_DIR = ROOT / "experiments/campaigns/autonomous_gse_v11"
MANIFEST = CAMPAIGN_DIR / "campaign_manifest.json"
BATCH_MAP = CAMPAIGN_DIR / "batch_map.json"
TAU2 = ROOT / "external/tau2-bench"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence(state="compliant_failure", source_id="source_1"):
    success = state.endswith("success")
    compliant = state.startswith("compliant")
    violations = [] if compliant else [{"policy_template_id": "policy_x"}]
    return {
        "source_id": source_id,
        "state": state,
        "task_success": success,
        "process_feedback": {"compliant": compliant, "violated_policies": violations},
        "actions": [
            {"step": 1, "actor": "user", "event_type": "message", "content": "help"},
            {"step": 2, "actor": "agent", "event_type": "message", "content": "done"},
        ],
    }


def _diagnosis(category, relevance, action, section=None, rule_id=None):
    return {
        "behavior_summary": "summary",
        "task_analysis": {"status": "failure", "reason": "reason", "evidence_steps": [2]},
        "policy_analysis": {
            "status": "compliant", "reason": "reason", "policy_ids": [], "evidence_steps": [2]
        },
        "root_cause": {"category": category, "explanation": "explanation"},
        "skill_update_relevance": relevance,
        "update_recommendation": {
            "action": action,
            "target_section": section,
            "target_rule_id": rule_id,
            "objective": "general objective",
            "description": "general method",
        },
    }


def _tag(value):
    return "<DIAGNOSIS_JSON>" + json.dumps(value) + "</DIAGNOSIS_JSON>"


def _row(domain, task_id, state):
    return {
        "domain": domain,
        "task_id": str(task_id),
        "rollout_index": 1,
        "state": state,
        "task_success": state.endswith("success"),
        "compliant": state.startswith("compliant"),
    }


def test_frozen_dataset_contract_matches_official_splits() -> None:
    frozen = _load(BATCH_MAP)
    official = _load_official_splits(TAU2)
    validate_frozen_split(frozen, official)
    rebuilt = build_frozen_split(TAU2, 200)
    assert rebuilt == frozen
    evolution = frozen["assignment"]["evolution"]
    holdout = frozen["assignment"]["holdout"]
    assert {domain: len(values) for domain, values in evolution.items()} == {
        "airline": 30, "retail": 30
    }
    assert {domain: len(values) for domain, values in holdout.items()} == {
        "airline": 20, "retail": 20
    }
    assert all(set(evolution[d]) <= set(official[d]["train"]) for d in evolution)
    assert all(set(holdout[d]) <= set(official[d]["test"]) for d in holdout)
    batches = frozen["batches"]
    assert all(len(batch["task_ids"]) == 20 for batch in batches)
    assert len({item for batch in batches for item in batch["task_ids"]}) == 60


def test_manifest_and_dry_plan_have_no_selection_and_exact_budget() -> None:
    campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
    validate_campaign_contract(campaign)
    assert "selection" not in campaign
    plan = build_campaign_dry_plan(campaign, batch_map)
    assert plan["selection_workload"] is None
    assert plan["computed_budget"] == campaign["budget"]
    assert [step["parent_trajectories"] for step in plan["steps"]] == [20, 20, 20]
    assert all(step["matched_seed_lineage"] for step in plan["steps"])
    assert plan["holdout"]["included_in_evolution_run"] is False


def test_single_rollout_matched_replay_lineage() -> None:
    assert derive_rollout_seeds(200, 1000) == (1200,)
    replay = matched_replay_plan(["airline:1", "retail:2"], 200)
    assert replay["parent"] == replay["candidate"]
    assert {unit["rollout_index"] for unit in replay["parent"]} == {1}


@pytest.mark.parametrize(
    ("category", "relevance", "action", "valid"),
    [
        ("skill_issue", "update", "add", True),
        ("skill_issue", "none", "none", False),
        ("execution_issue", "none", "none", True),
        ("execution_issue", "update", "add", False),
        ("external_issue", "none", "none", True),
        ("uncertain", "uncertain", "none", True),
        (None, "none", "none", True),
        (None, "preserve", "none", False),
    ],
)
def test_diagnosis_root_cause_relevance_bijection(category, relevance, action, valid) -> None:
    section = "Planning and navigation" if action == "add" else None
    errors = validate_diagnosis(
        _diagnosis(category, relevance, action, section),
        evidence=_evidence(),
        skill_sections={"Planning and navigation": []},
    )
    assert (not errors) is valid


def test_diagnosis_forbids_preserve_fields_and_missing_steps() -> None:
    diagnosis = _diagnosis(None, "none", "none")
    diagnosis["preserve_constraints"] = []
    assert "INVALID_DIAGNOSIS_FIELDS" in validate_diagnosis(
        diagnosis, evidence=_evidence(), skill_sections={"Planning and navigation": []}
    )
    diagnosis.pop("preserve_constraints")
    diagnosis["task_analysis"]["evidence_steps"] = [999]
    assert "TASK_EVIDENCE_STEP_NOT_FOUND" in validate_diagnosis(
        diagnosis, evidence=_evidence(), skill_sections={"Planning and navigation": []}
    )
    assert "preserve_constraints" not in DIAGNOSIS_SYSTEM_PROMPT
    assert (
        'task_analysis.status must be exactly "success" when task_success is true and\n'
        '  exactly "failure" when task_success is false.'
        in DIAGNOSIS_SYSTEM_PROMPT
    )
    assert (
        'policy_analysis.status must be exactly "compliant" or "violated".'
        in DIAGNOSIS_SYSTEM_PROMPT
    )
    assert (
        'root_cause.category must be exactly "skill_issue", "execution_issue",\n'
        '  "external_issue", "uncertain", or JSON null.'
        in DIAGNOSIS_SYSTEM_PROMPT
    )


def test_no_update_diagnosis_skips_editor() -> None:
    parent = (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text(encoding="utf-8")
    calls = []
    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext(
            candidate_id="candidate_001",
            parent_skill=parent.replace("# Operational Skill", "# SuiteCRM Operational Skill"),
            current_batch_governed_evidence=(_evidence(),),
        ),
        lambda request: _tag(_diagnosis("execution_issue", "none", "none")),
        lambda request: calls.append(request) or "",
    )
    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.editor_calls == 0
    assert calls == []


def test_v11_editor_request_has_no_preserve_constraints() -> None:
    parent = (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text(encoding="utf-8")
    request = DiagnosisEditorRequest(
        "candidate",
        parent.replace("# Operational Skill", "# SuiteCRM Operational Skill"),
        ({"patch_id": "p"},),
    )
    assert "preserve_constraints" not in request.__dict__
    system, user = build_editor_prompts(request)
    assert "PRESERVE_CONSTRAINTS" not in system + user
    assert "SuiteCRM" not in system + user


@pytest.mark.parametrize(
    "module", [diagnosis_v11, editor_v11, targeted_v11, regression_v11]
)
def test_real_v11_learner_paths_freeze_temperature_zero(monkeypatch, module) -> None:
    calls = []

    def fake(model, system, user, **kwargs):
        calls.append((model, system, user, kwargs))
        return "response", model, None

    monkeypatch.setattr(module, "call_learner", fake)
    module._default_learner_call("openai/gpt-5.6-luna", "system", "user")
    assert calls == [
        (
            "openai/gpt-5.6-luna",
            "system",
            "user",
            {"temperature": 0.0},
        )
    ]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("drift", "DIAGNOSIS_TARGET_DRIFT"),
        ("recipe", "TASK_SPECIFIC_RULE"),
        ("policy", "POLICY_ID_LEAKAGE"),
    ],
)
def test_editor_guards_target_recipe_and_policy_leakage(mode, expected) -> None:
    parent = (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text(encoding="utf-8")
    evidence = _evidence("violating_failure" if mode == "policy" else "compliant_failure")
    diagnosis = _diagnosis(
        "skill_issue", "update", "add", "Planning and navigation"
    )
    if mode == "policy":
        diagnosis["policy_analysis"].update(
            {"status": "violated", "policy_ids": ["policy_x"]}
        )
    edit = {
        "derived_from_patch_ids": ["diagnosis_001"],
        "operation": "add",
        "section": "Execution patterns" if mode == "drift" else "Planning and navigation",
        "target_rule_id": "",
        "text": (
            "Enter the first field then second field."
            if mode == "recipe"
            else "Always follow policy_x."
            if mode == "policy"
            else "Verify the applicable operating constraint before acting."
        ),
        "reason": "reason",
        "source_ids": [evidence["source_id"]],
        "repair_policy_ids": diagnosis["policy_analysis"]["policy_ids"],
    }
    decision = DiagnosisDrivenProposalOperator().propose(
        ProposalContext(
            candidate_id="candidate_001",
            parent_skill=parent.replace("# Operational Skill", "# SuiteCRM Operational Skill"),
            current_batch_governed_evidence=(evidence,),
        ),
        lambda request: _tag(diagnosis),
        lambda request: "<CANONICAL_EDITS_JSON>" + json.dumps([edit]) + "</CANONICAL_EDITS_JSON>",
    )
    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.canonical_edits[0]["v11_validation_error"] == expected


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ("compliant_success", "violating_success", "compliance_regression"),
        ("compliant_failure", "violating_failure", "compliance_regression"),
        ("compliant_success", "compliant_failure", "task_regression"),
        ("violating_success", "violating_failure", "task_regression"),
        ("compliant_success", "violating_failure", "dual_regression"),
        ("violating_success", "compliant_failure", None),
        ("compliant_failure", "violating_success", None),
        ("compliant_success", "compliant_success", None),
        ("violating_failure", "compliant_success", None),
    ],
)
def test_deterministic_regression_set(before, after, expected) -> None:
    report = build_regression_transition_report(
        [_row("airline", "1", before)], [_row("airline", "1", after)]
    )
    assert (report["regression_set"][0]["regression_type"] if report["regression_set"] else None) == expected


def test_regression_diagnosis_and_targeted_fix_closed_vocabularies() -> None:
    targeted = parse_targeted_fix_response(
        '<TARGETED_FIX_JSON>{"status":"FIXED","reason":"target gone","parent_evidence_steps":[2],"candidate_evidence_steps":[2]}</TARGETED_FIX_JSON>'
    )
    assert targeted["status"] == "FIXED"
    with pytest.raises(ValueError):
        parse_targeted_fix_response(
            '<TARGETED_FIX_JSON>{"status":"PARTIALLY_FIXED","reason":"","parent_evidence_steps":[],"candidate_evidence_steps":[]}</TARGETED_FIX_JSON>'
        )
    regression = parse_regression_diagnosis_response(
        '<REGRESSION_DIAGNOSIS_JSON>{"first_meaningful_divergence":"step 2","key_behavior_difference":"stopped","attribution":"UNRELATED_VARIATION","reason":"insufficient","parent_evidence_steps":[2],"candidate_evidence_steps":[2]}</REGRESSION_DIAGNOSIS_JSON>'
    )
    assert regression["attribution"] == "UNRELATED_VARIATION"
    assert "post-hoc attribution is forbidden" in REGRESSION_PROMPT
    assert (
        "parent_evidence_steps and candidate_evidence_steps must each be JSON arrays\n"
        "containing only positive integer trajectory step IDs."
        in REGRESSION_PROMPT
    )
    assert "task still fails" in TARGETED_PROMPT


def test_invalid_regression_response_preserves_raw_model_output() -> None:
    raw = (
        '<REGRESSION_DIAGNOSIS_JSON>{"first_meaningful_divergence":"x",'
        '"key_behavior_difference":"y","attribution":"UNRELATED_VARIATION",'
        '"reason":"z","parent_evidence_steps":["2"],'
        '"candidate_evidence_steps":[2]}</REGRESSION_DIAGNOSIS_JSON>'
    )
    with pytest.raises(RegressionDiagnosisResponseError) as captured:
        parse_regression_diagnosis_response(raw)
    assert captured.value.code == "INVALID_REGRESSION_DIAGNOSIS_EVIDENCE"
    assert captured.value.raw_response == raw


def _gate(fixed=1, attribution=None, parent_states=None, candidate_states=None):
    parent_states = parent_states or ["compliant_success"] * 20
    candidate_states = candidate_states or ["compliant_success"] * 20
    return build_evolution_decision(
        targeted_fix_results=[{"status": "FIXED"}] * fixed
        + ([{"status": "NOT_FIXED"}] if fixed == 0 else []),
        regression_diagnoses=[] if attribution is None else [{"attribution": attribution}],
        parent_rows=[_row("airline" if i < 10 else "retail", i, state) for i, state in enumerate(parent_states)],
        candidate_rows=[_row("airline" if i < 10 else "retail", i, state) for i, state in enumerate(candidate_states)],
    )


def test_gate_order_and_catastrophic_threshold() -> None:
    assert _gate(fixed=0)["primary_reason"] == "NO_TARGETED_FIX"
    assert _gate(attribution="CHANGE_CAUSED")["primary_reason"] == "CHANGE_CAUSED_REGRESSION"
    assert _gate(
        attribution="UNRELATED_VARIATION",
        candidate_states=["compliant_failure"] * 2 + ["compliant_success"] * 18,
    )["decision"] == "ACCEPT"
    collapse = _gate(
        candidate_states=["compliant_failure"] * 3 + ["compliant_success"] * 17
    )
    assert collapse["primary_reason"] == "AGGREGATE_COLLAPSE"
    assert collapse["aggregate"]["delta"]["task_success"] == -3


def test_holdout_plan_is_explicit_matched_and_learning_free() -> None:
    plan = build_holdout_plan(
        _load(MANIFEST), _load(BATCH_MAP),
        {"kind": "candidate_skill", "version": "S3", "path": "memory://s3"},
    )
    assert plan["source_split"] == "official_test"
    assert plan["trajectory_count"] == 80
    assert plan["learning_calls"] == 0
    assert plan["s0_units"] == plan["s_final_units"]


class NoCandidateBackend:
    def __init__(self, root: Path, campaign: dict):
        self.root, self.campaign, self.calls = root, campaign, []

    def run_batch(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        paths = []
        for domain_task in kwargs["task_ids"]:
            domain, task_id = domain_task.split(":", 1)
            path = self.root / kwargs["execution_phase"] / f"{domain}_{task_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            evidence = _evidence(source_id="unused")
            path.write_text(json.dumps({
                "domain": domain, "task_id": task_id, "rollout_seed": 200,
                "state": evidence["state"],
                "task_evaluation": {"success": False},
                "compliance_evaluation": {"compliant": True},
                "governed_evidence": evidence,
            }), encoding="utf-8")
            paths.append(path)
        return paths


class CandidateBackend(NoCandidateBackend):
    def __init__(self, root: Path, campaign: dict, scenario: str):
        super().__init__(root, campaign)
        self.scenario = scenario

    def run_batch(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        candidate = "candidate_replay" in kwargs["execution_phase"]
        paths = []
        for index, domain_task in enumerate(kwargs["task_ids"]):
            domain, task_id = domain_task.split(":", 1)
            state = "compliant_failure"
            if candidate and self.scenario in {"accept", "no_targeted_fix"}:
                state = "compliant_success"
            elif candidate and self.scenario == "change_caused":
                state = "violating_failure" if index == 0 else "compliant_success"
            elif candidate and self.scenario == "aggregate_collapse":
                state = "violating_failure" if index < 3 else "compliant_failure"
            path = self.root / kwargs["execution_phase"] / f"{domain}_{task_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            evidence = _evidence(state, source_id="unused")
            path.write_text(json.dumps({
                "domain": domain,
                "task_id": task_id,
                "rollout_seed": 200,
                "state": state,
                "task_evaluation": {"success": state.endswith("success")},
                "compliance_evaluation": {"compliant": state.startswith("compliant")},
                "governed_evidence": evidence,
            }), encoding="utf-8")
            paths.append(path)
        return paths


def _mock_editor(request):
    edit = {
        "derived_from_patch_ids": [item["patch_id"] for item in request.eligible_diagnoses],
        "operation": "add",
        "section": "Planning and navigation",
        "target_rule_id": "",
        "text": (
            f"At refinement stage {request.candidate_id[-1]}, verify applicable "
            "constraints before acting and confirm the result afterward."
        ),
        "reason": "Apply the validated reusable intervention.",
        "source_ids": [
            source_id
            for item in request.eligible_diagnoses
            for source_id in item["source_ids"]
        ],
        "repair_policy_ids": [],
    }
    return "<CANONICAL_EDITS_JSON>" + json.dumps([edit]) + "</CANONICAL_EDITS_JSON>"


@pytest.mark.parametrize(
    ("scenario", "decision", "reason", "promoted"),
    [
        ("accept", "ACCEPT", "ACCEPTED", True),
        ("no_targeted_fix", "REJECT", "NO_TARGETED_FIX", False),
        ("change_caused", "REJECT", "CHANGE_CAUSED_REGRESSION", False),
        ("aggregate_collapse", "REJECT", "AGGREGATE_COLLAPSE", False),
    ],
)
def test_candidate_mock_end_to_end_paths(
    tmp_path: Path, scenario: str, decision: str, reason: str, promoted: bool
) -> None:
    campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
    backend = CandidateBackend(tmp_path / "rollouts", campaign, scenario)

    def targeted(request):
        status = "NOT_FIXED" if scenario == "no_targeted_fix" else "FIXED"
        return {
            "diagnosis_id": request.diagnosis_id,
            "source_id": request.source_id,
            "status": status,
            "reason": "mock paired evidence",
            "parent_evidence_steps": [2],
            "candidate_evidence_steps": [2],
        }

    def regression(request):
        attribution = (
            "CHANGE_CAUSED" if scenario == "change_caused" else "UNRELATED_VARIATION"
        )
        return {
            "pair_id": request.pair_id,
            "domain": request.domain,
            "parent_state": request.parent_state,
            "candidate_state": request.candidate_state,
            "regression_type": request.regression_type,
            "first_meaningful_divergence": "step 2",
            "key_behavior_difference": "mock divergence",
            "attribution": attribution,
            "reason": "mock causal analysis",
            "parent_evidence_steps": [2],
            "candidate_evidence_steps": [2],
        }

    report = run_v11_campaign(
        campaign,
        batch_map,
        backend=backend,
        diagnoser=lambda request: _tag(
            _diagnosis(
                "skill_issue", "update", "add", "Planning and navigation"
            )
        ),
        editor=_mock_editor,
        targeted_fix_judge=targeted,
        regression_judge=regression,
        artifact_root=tmp_path / "artifacts",
    )

    assert [step["decision"] for step in report["steps"]] == [decision] * 3
    assert [step["primary_reason"] for step in report["steps"]] == [reason] * 3
    assert len(backend.calls) == 6
    assert all(len(call["task_ids"]) == 20 for call in backend.calls)
    assert report["final_skill"]["version"] == ("S3" if promoted else "S0")
    required = {
        "diagnoses.json",
        "proposal.json",
        "candidate_edits.json",
        "candidate_skill.md",
        "targeted_fix_report.json",
        "regression_transition_report.json",
        "regression_diagnoses.json",
        "aggregate_metrics.json",
        "evolution_decision.json",
    }
    for step in range(1, 4):
        step_root = tmp_path / "artifacts/steps" / f"step_{step:03d}"
        assert required <= {path.name for path in step_root.iterdir()}
        candidate_edits = _load(step_root / "candidate_edits.json")
        assert candidate_edits[0]["derived_from_diagnosis_ids"]
        assert candidate_edits[0]["source_ids"]
        assert candidate_edits[0]["final_text"]


def test_campaign_persists_invalid_regression_raw_response(tmp_path: Path) -> None:
    campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
    backend = CandidateBackend(tmp_path / "rollouts", campaign, "change_caused")
    raw = "<REGRESSION_DIAGNOSIS_JSON>{invalid evidence}</REGRESSION_DIAGNOSIS_JSON>"

    def invalid_regression(request):
        raise RegressionDiagnosisResponseError(
            "INVALID_REGRESSION_DIAGNOSIS_EVIDENCE", raw
        )

    with pytest.raises(
        RegressionDiagnosisResponseError,
        match="INVALID_REGRESSION_DIAGNOSIS_EVIDENCE",
    ):
        run_v11_campaign(
            campaign,
            batch_map,
            backend=backend,
            diagnoser=lambda request: _tag(
                _diagnosis(
                    "skill_issue", "update", "add", "Planning and navigation"
                )
            ),
            editor=_mock_editor,
            targeted_fix_judge=lambda request: {
                "diagnosis_id": request.diagnosis_id,
                "source_id": request.source_id,
                "status": "FIXED",
                "reason": "mock paired evidence",
                "parent_evidence_steps": [2],
                "candidate_evidence_steps": [2],
            },
            regression_judge=invalid_regression,
            artifact_root=tmp_path / "artifacts",
        )

    error = _load(
        tmp_path
        / "artifacts/steps/step_001/regression_diagnosis_error.json"
    )
    assert error["pair_id"] == "airline:5:rollout_01"
    assert error["error_code"] == "INVALID_REGRESSION_DIAGNOSIS_EVIDENCE"
    assert error["raw_response"] == raw
    assert error["completed_regression_diagnoses"] == 0


def test_mock_campaign_no_candidate_runs_only_parent_batches(tmp_path: Path) -> None:
    campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
    backend = NoCandidateBackend(tmp_path / "rollouts", campaign)
    editor_calls = []
    report = run_v11_campaign(
        campaign, batch_map, backend=backend,
        diagnoser=lambda request: _tag(_diagnosis("execution_issue", "none", "none")),
        editor=lambda request: editor_calls.append(request) or "",
        targeted_fix_judge=lambda request: pytest.fail("Targeted Fix must be skipped"),
        regression_judge=lambda request: pytest.fail("Regression must be skipped"),
        artifact_root=tmp_path / "artifacts",
    )
    assert [step["decision"] for step in report["steps"]] == ["NO_CANDIDATE"] * 3
    assert len(backend.calls) == 3
    assert all(call["phase"] == "train" for call in backend.calls)
    assert editor_calls == []
    assert report["disabled_phases"] == {"official_test_holdout": True}
    resume = _load(tmp_path / "artifacts/resume_state.json")
    assert resume["completed_steps"] == 3
    assert len(resume["steps"]) == 3

    resumed_backend = NoCandidateBackend(tmp_path / "resumed_rollouts", campaign)
    resumed = run_v11_campaign(
        campaign, batch_map, backend=resumed_backend,
        resume_state=resume, artifact_root=tmp_path / "artifacts"
    )
    assert resumed_backend.calls == []
    assert resumed["steps"] == report["steps"]


def test_explicit_holdout_runs_only_s0_and_final_without_learning(tmp_path: Path) -> None:
    campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
    backend = NoCandidateBackend(tmp_path / "holdout_rollouts", campaign)
    report = evaluate_holdout(
        campaign,
        batch_map,
        {"kind": "candidate_skill", "version": "S3", "path": str(CAMPAIGN_DIR / "skills/S0_empty_skill.md")},
        backend=backend,
        artifact_root=tmp_path / "holdout",
    )
    assert report["trajectory_count"] == 80
    assert report["learning_calls"] == 0
    assert [(call["phase"], call["skill_version"]) for call in backend.calls] == [
        ("test", "S0"), ("test", "S3")
    ]
