from __future__ import annotations

import ast
import copy
import json
import re
from pathlib import Path

from src.adapters.tau2 import tau3_compliance_judge_v13 as compliance_v13
from src.learners.stwebagentbench import generate_governed_skill_v13 as editor_v13
from src.learners.stwebagentbench import generate_governed_skill_v14 as editor_v14
from src.skill_evolution import autonomous_gse_v13_proposal as proposal_v13
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as runtime_v14
from src.skill_evolution import autonomous_gse_v14_proposal as proposal_v14
from src.skill_evolution import diagnosis_contract_v13 as contract_v13
from src.skill_evolution import diagnosis_contract_v14 as contract_v14
from src.skill_evolution import diagnosis_v13
from src.skill_evolution import diagnosis_v14
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from tests.skill_evolution.test_autonomous_gse_v13 import (
    _diagnosis, _domain_contexts, _edit, _experience, _group, _tag,
)


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
S0 = ROOT / "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md"


def _normalize_version_identity(value: str) -> str:
    return re.sub(r"v0\.(?:13|14)", "v0.X", value).replace(
        "v13_dual_axis_mechanism_preserving_bounded_edit",
        "vX_dual_axis_mechanism_preserving_bounded_edit",
    ).replace(
        "v14_dual_axis_mechanism_preserving_bounded_edit",
        "vX_dual_axis_mechanism_preserving_bounded_edit",
    )


def _parent_skill() -> str:
    return S0.read_text(encoding="utf-8").replace(
        "# Operational Skill", "# SuiteCRM Operational Skill", 1,
    )


def _request_pair(diagnoses: tuple[dict, ...]):
    common = {
        "candidate_id": "candidate_001",
        "current_parent_skill": _parent_skill(),
        "eligible_diagnoses": diagnoses,
        "domain_contexts": ({
            "domain": "airline",
            "original_domain_policy": "# Airline policy\nFollow applicable requirements.",
        },),
    }
    return proposal_v13.DiagnosisEditorRequest(**common), proposal_v14.DiagnosisEditorRequest(**common)


def _twenty_task_evidence() -> tuple[dict, ...]:
    return tuple(
        _experience(domain, str(task), rollout_index)
        for domain in ("airline", "retail")
        for task in range(1, 11)
        for rollout_index in (1, 2, 3)
    )


def _update_diagnoser(request) -> str:
    value = _diagnosis(
        relevance="update", action="add", category="skill_issue",
        update_axis="both", evidence_pattern="recurrent",
        problem="a stable decision mechanism is missing",
        repair_operator="apply the bounded mechanism at the decision opportunity",
    )
    value["behavior_analysis"]["support_evidence_refs"] = [{
        "source_id": request.rollouts[0]["source_id"], "step_ids": [2],
    }]
    return _tag(value)


def _no_update_diagnoser(request) -> str:
    value = _diagnosis()
    value["behavior_analysis"]["support_evidence_refs"] = []
    return _tag(value)


def _merged_editor(request) -> str:
    return "<CANONICAL_EDITS_JSON>" + json.dumps([
        _edit([item["patch_id"] for item in request.eligible_diagnoses])
    ]) + "</CANONICAL_EDITS_JSON>"


def test_diagnosis_contract_snapshot_equivalence_for_valid_invalid_and_repair():
    experiences = _group()
    sections = {"Planning and navigation": []}
    valid = _diagnosis(
        relevance="update", action="add", category="skill_issue",
        update_axis="both", evidence_pattern="recurrent",
        problem="missing decision mechanism", repair_operator="apply bounded repair",
    )
    assert contract_v13.validate_diagnosis(
        copy.deepcopy(valid), experiences=experiences, skill_sections=sections,
    ) == contract_v14.validate_diagnosis(
        copy.deepcopy(valid), experiences=experiences, skill_sections=sections,
    ) == ()

    invalid = copy.deepcopy(valid)
    invalid["update_axis"] = "none"
    errors13 = contract_v13.validate_diagnosis(
        copy.deepcopy(invalid), experiences=experiences, skill_sections=sections,
    )
    errors14 = contract_v14.validate_diagnosis(
        copy.deepcopy(invalid), experiences=experiences, skill_sections=sections,
    )
    assert errors13 == errors14
    assert contract_v13.repair_diagnosis_contract_fields(invalid, errors13) == (
        contract_v14.repair_diagnosis_contract_fields(invalid, errors14)
    )
    response = _tag(valid)
    assert contract_v13.parse_and_validate_diagnosis(
        "diagnosis_001", response, experiences=experiences, skill_sections=sections,
    ).as_dict() == contract_v14.parse_and_validate_diagnosis(
        "diagnosis_001", response, experiences=experiences, skill_sections=sections,
    ).as_dict()


def test_diagnosis_prompt_and_configuration_are_semantically_identical():
    assert diagnosis_v14.LEARNER_MODEL == diagnosis_v13.LEARNER_MODEL
    assert diagnosis_v14.EMPTY_RESPONSE_RETRIES == diagnosis_v13.EMPTY_RESPONSE_RETRIES
    assert _normalize_version_identity(diagnosis_v14.DIAGNOSIS_SYSTEM_PROMPT) == (
        _normalize_version_identity(diagnosis_v13.DIAGNOSIS_SYSTEM_PROMPT)
    )


def test_editor_prompt_configuration_and_synthetic_call_are_equivalent():
    diagnoses = ({"patch_id": "diagnosis_001", "objective": "bounded repair"},)
    request13, request14 = _request_pair(diagnoses)
    system13, user13 = editor_v13.build_editor_prompts(request13)
    system14, user14 = editor_v14.build_editor_prompts(request14)
    assert editor_v14.LEARNER_MODEL == editor_v13.LEARNER_MODEL
    assert _normalize_version_identity(system14) == _normalize_version_identity(system13)
    assert user14 == user13

    response = "<CANONICAL_EDITS_JSON>[]</CANONICAL_EDITS_JSON>"
    learner = lambda model, system, user: (response, "", None)
    assert editor_v13.call_governed_editor(request13, learner_call=learner) == (
        editor_v14.call_governed_editor(request14, learner_call=learner)
    )


def test_proposal_signal_snapshot_equivalence():
    experiences = _group()
    diagnosis = _diagnosis(
        relevance="update", action="add", category="skill_issue",
        update_axis="both", evidence_pattern="recurrent",
        problem="missing mechanism", repair_operator="apply bounded repair",
    )
    validation13 = contract_v13.parse_and_validate_diagnosis(
        "diagnosis_001", _tag(diagnosis), experiences=experiences,
        skill_sections={"Planning and navigation": []},
    )
    validation14 = contract_v14.parse_and_validate_diagnosis(
        "diagnosis_001", _tag(diagnosis), experiences=experiences,
        skill_sections={"Planning and navigation": []},
    )
    assert proposal_v13._signal(validation13, ("airline", "1")) == (
        proposal_v14._signal(validation14, ("airline", "1"))
    )


def test_proposal_end_to_end_twenty_task_snapshot_equivalence():
    context = ProposalContext(
        "candidate_001", _parent_skill(), _twenty_task_evidence(),
    )
    decision13 = proposal_v13.MultiRolloutDiagnosisProposalOperator().propose(
        context, _update_diagnoser, _merged_editor, domain_contexts=_domain_contexts(),
    )
    decision14 = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        context, _update_diagnoser, _merged_editor, domain_contexts=_domain_contexts(),
    )
    assert decision14.__dict__ == decision13.__dict__
    assert decision14.proposal_status == "CANDIDATE"
    assert len(decision14.eligible_diagnosis_ids) == 20
    assert decision14.editor_calls == 1


def test_no_candidate_snapshot_equivalence():
    context = ProposalContext(
        "candidate_001", _parent_skill(), _twenty_task_evidence(),
    )
    decision13 = proposal_v13.MultiRolloutDiagnosisProposalOperator().propose(
        context, _no_update_diagnoser, _merged_editor, domain_contexts=_domain_contexts(),
    )
    decision14 = proposal_v14.MultiRolloutDiagnosisProposalOperator().propose(
        context, _no_update_diagnoser, _merged_editor, domain_contexts=_domain_contexts(),
    )
    assert decision14.__dict__ == decision13.__dict__
    assert decision14.proposal_status == "NO_CANDIDATE"
    assert decision14.editor_calls == 0


def test_v14_semantic_modules_do_not_import_v13_learner_modules():
    paths = (
        ROOT / "src/skill_evolution/diagnosis_contract_v14.py",
        ROOT / "src/skill_evolution/diagnosis_v14.py",
        ROOT / "src/skill_evolution/autonomous_gse_v14_proposal.py",
        ROOT / "src/learners/stwebagentbench/generate_governed_skill_v14.py",
        ROOT / "src/skill_evolution/autonomous_gse_v14_benchmark_runtime.py",
    )
    forbidden = {
        "src.skill_evolution.diagnosis_v13",
        "src.skill_evolution.diagnosis_contract_v13",
        "src.skill_evolution.autonomous_gse_v13_proposal",
        "src.learners.stwebagentbench.generate_governed_skill_v13",
    }
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        assert not imported & forbidden, (path, imported & forbidden)


def test_manifest_and_runtime_own_v14_learner_but_share_frozen_judge():
    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    assert campaign["learner_stack"] == {
        "diagnosis": "src.skill_evolution.diagnosis_v14",
        "diagnosis_contract": "src.skill_evolution.diagnosis_contract_v14",
        "proposal_operator": (
            "src.skill_evolution.autonomous_gse_v14_proposal."
            "MultiRolloutDiagnosisProposalOperator"
        ),
        "editor": (
            "src.learners.stwebagentbench.generate_governed_skill_v14."
            "call_governed_editor"
        ),
        "semantics_snapshot_from": "autonomous_gse_v13",
    }
    assert campaign["compliance_judge"] == {
        "implementation": "src.adapters.tau2.tau3_compliance_judge_v13",
        "model": compliance_v13.JUDGE_MODEL,
        "temperature": compliance_v13.JUDGE_TEMPERATURE,
        "prompt_version": compliance_v13.JUDGE_PROMPT_VERSION,
        "frozen_from": "autonomous_gse_v13",
        "fallback": "forbidden",
    }
    runtime_v14.validate_campaign_contract(campaign)
    assert runtime_v14.call_diagnosis is diagnosis_v14.call_diagnosis
    assert runtime_v14.call_governed_editor is editor_v14.call_governed_editor
    assert runtime_v14.judge_compliance is compliance_v13.judge_compliance
