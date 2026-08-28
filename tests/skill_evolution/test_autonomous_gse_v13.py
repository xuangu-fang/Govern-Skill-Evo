from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.adapters.tau2.tau3_compliance_judge_v13 import (
    ComplianceJudgeError, JUDGE_SYSTEM_PROMPT, build_judge_payload,
    validate_judgment,
)
from src.learners.stwebagentbench.generate_governed_skill_v13 import EDITOR_SYSTEM_PROMPT
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    Tau3RolloutAdapter, build_campaign_dry_plan, build_holdout_plan, derive_rollout_seeds,
    build_policy_grounded_recovery_plan, load_authoritative_domain_contexts,
    matched_replay_plan, prepare_v13_step1_restart_from_parent,
    resume_v13_target_fix_and_gate, run_v13_campaign,
    _tool_contracts_from_authoritative_source,
)
from src.skill_evolution.autonomous_gse_v13_proposal import MultiRolloutDiagnosisProposalOperator
from src.skill_evolution.diagnosis_contract_v13 import validate_diagnosis
from src.skill_evolution.diagnosis_v13 import (
    DIAGNOSIS_SYSTEM_PROMPT, MultiRolloutDiagnosisRequest, build_diagnosis_prompts,
)
from src.skill_evolution.evolution_gate_v13 import build_evolution_decision
from src.skill_evolution.targeted_fix_v13 import (
    SYSTEM_PROMPT as TARGET_FIX_SYSTEM_PROMPT,
    TargetedFixRequest, build_targeted_fix_prompts, derive_edit_verdict,
    parse_targeted_fix_response,
)
from scripts.run_v13_preformal_canary import _case_checks

ROOT = Path(__file__).resolve().parents[2]
V12_DIR = ROOT / "experiments/campaigns/autonomous_gse_v12"
CAMPAIGN_DIR = ROOT / "experiments/campaigns/autonomous_gse_v13"
MANIFEST = CAMPAIGN_DIR / "campaign_manifest.json"
BATCH_MAP = CAMPAIGN_DIR / "batch_map.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _experience(
    domain: str = "airline", task_id: str = "1", rollout_index: int = 1,
    state: str = "compliant_failure", policy_id: str | None = None,
) -> dict:
    success = state.endswith("success")
    compliant = state.startswith("compliant")
    violations = [] if policy_id is None else [{"policy_template_id": policy_id}]
    return {
        "source_id": f"step_001_{domain}_{task_id}_rollout_{rollout_index:02d}",
        "domain": domain, "task_id": str(task_id), "rollout_index": rollout_index,
        "rollout_seed": 199 + rollout_index, "state": state, "task_success": success,
        "process_feedback": {"compliant": compliant, "violated_policies": violations},
        "actions": [
            {"step": 1, "actor": "user", "content": "help"},
            {"step": 2, "actor": "agent", "content": "done"},
        ],
    }


def _group(states=("compliant_failure", "compliant_failure", "compliant_failure"), domain="airline", task_id="1"):
    return tuple(
        _experience(domain, task_id, index, state)
        for index, state in enumerate(states, start=1)
    )


def _diagnosis(
    *, relevance="none", action="none", category=None, update_axis="none",
    problem="", repair_operator="", stopping_boundary="",
) -> dict:
    return {
        "task_behavior_summary": "summary",
        "cross_rollout_analysis": {
            "stable_behavior": "", "success_contrast": "",
            "compliance_contrast": "", "counterevidence": "",
            "discriminating_behavior": (
                "the rollout uses a different decision predicate before the resulting action"
                if relevance == "update" else ""
            ),
            "evidence_consistency": "supportive" if relevance == "update" else "insufficient",
            "support_evidence_refs": [
                {"source_id": "step_001_airline_1_rollout_01", "step_ids": [2]}
            ],
            "counterevidence_refs": [],
        },
        "root_cause": {"category": category, "explanation": "explanation"},
        "skill_update_relevance": relevance, "update_axis": update_axis,
        "repair_policy_ids": [],
        "target_behavior": {
            "problem": problem, "trigger_condition": "when the mechanism is present",
            "decision_boundary": "distinguish records by stable record identity",
            "repair_operator": repair_operator,
            "stopping_boundary": stopping_boundary,
            "expected_behavior": "preserve the required binding or satisfied boundary",
        },
        "update_recommendation": {
            "action": action, "target_section": None, "target_rule_id": None,
            "objective": "repair the mechanism", "description": "apply the bounded operator",
        },
    }


def _domain_contexts() -> dict:
    return {
        domain: {
            "original_domain_policy": f"# {domain.title()} policy\n\nThe agent must follow applicable requirements.",
            "available_tool_contracts": ({
                "tool_name": "lookup",
                "arguments": ["record_id"],
                "required_arguments": ["record_id"],
                "optional_arguments": [],
                "description": "Look up one record.",
            },),
        }
        for domain in ("airline", "retail")
    }


def _tag(value: dict) -> str:
    return "<DIAGNOSIS_JSON>" + json.dumps(value) + "</DIAGNOSIS_JSON>"


def _edit(patch_ids: list[str], *, record_integrity: bool = True) -> dict:
    if record_integrity:
        text = "Keep each record's ID, attributes, price, and availability bound to that same record."
        target = {
            "problem": "fields from different records form a nonexistent option",
            "trigger_condition": "multiple records expose overlapping record-specific fields",
            "expected_behavior": "reason within one record and preserve its field binding",
        }
    else:
        text = "Before stating fees, eligibility, refund routes, or timelines, verify each fact against policy, tool, or user evidence."
        target = {
            "problem": "unsupported operational facts are asserted",
            "trigger_condition": "a fee, eligibility, refund route, or timeline lacks evidence",
            "expected_behavior": "verify each operational fact before relying on it",
        }
    return {
        "derived_from_patch_ids": patch_ids, "operation": "add",
        "section": "Form entry and verification", "target_rule_id": "", "text": text,
        "reason": "mechanism-preserving canonicalization", "source_ids": [],
        "repair_policy_ids": [], "verification_target": target,
    }


def _row(index: int, state: str = "compliant_success") -> dict:
    return {
        "domain": "airline", "task_id": "1", "rollout_index": index,
        "state": state, "task_success": state.endswith("success"),
        "compliant": state.startswith("compliant"),
    }


def _target_request(*, parent_state="violating_success", candidate_state="compliant_failure") -> TargetedFixRequest:
    parents, candidates = [], []
    for index in (1, 2, 3):
        base = {
            "domain": "airline", "task_id": "1", "rollout_index": index,
            "rollout_seed": 199 + index,
            "trajectory": {"actions": [{"step": 1}, {"step": 2}]},
        }
        parents.append({**copy.deepcopy(base), "source_id": f"p{index}", "state": parent_state})
        candidates.append({**copy.deepcopy(base), "source_id": f"c{index}", "state": candidate_state})
    return TargetedFixRequest(
        canonical_edit={
            "canonical_edit_id": "canonical_edit_001",
            "verification_target": {
                "problem": "cross-record composition",
                "trigger_condition": "multiple candidate records",
                "expected_behavior": "preserve one-record field binding",
            },
        },
        supporting_diagnoses=(),
        matched_replays=({
            "diagnosis_id": "diagnosis_001",
            "parent_rollouts": parents, "candidate_rollouts": candidates,
        },),
    )


def _target_response(transitions: list[str], request: TargetedFixRequest) -> str:
    pairs = []
    for index, transition in enumerate(transitions, start=1):
        exercised = transition != "NOT_EXERCISED"
        pairs.append({
            "diagnosis_id": "diagnosis_001", "domain": "airline", "task_id": "1",
            "rollout_index": index, "transition": transition, "reason": "behavior evidence",
            "parent_evidence_refs": [{"source_id": f"p{index}", "step_ids": [1]}] if exercised else [],
            "candidate_evidence_refs": [{"source_id": f"c{index}", "step_ids": [2]}] if exercised else [],
        })
    value = {
        "canonical_edit_id": "canonical_edit_001",
        "status": derive_edit_verdict(transitions),
        "pair_transitions": pairs, "reason": "deterministic transition verdict",
    }
    return "<TARGETED_FIX_JSON>" + json.dumps(value) + "</TARGETED_FIX_JSON>"


class V13DiagnosisEditorTests(unittest.TestCase):
    def test_diagnosis_request_contains_complete_authoritative_domain_context(self):
        contexts = load_authoritative_domain_contexts(ROOT / "external/tau2-bench")
        request = MultiRolloutDiagnosisRequest(
            candidate_id="candidate", diagnosis_id="diagnosis_001",
            current_parent_skill=(CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text().replace(
                "# Operational Skill", "# SuiteCRM Operational Skill", 1
            ),
            task_context={"domain": "airline", "task_id": "1"},
            original_domain_policy=contexts["airline"]["original_domain_policy"],
            available_tool_contracts=contexts["airline"]["available_tool_contracts"],
            rollouts=_group(("compliant_success", "compliant_success", "violating_success")),
        )
        _, user = build_diagnosis_prompts(request)
        self.assertIn("All passengers must fly the same flights in the same cabin", user)
        self.assertIn('"tool_name": "update_reservation_baggages"', user)

    def test_evidence_sufficiency_contract(self):
        sections = {"Planning and navigation": []}
        update = _diagnosis(
            relevance="update", action="add", category="skill_issue",
            update_axis="compliance", problem="different decision predicate",
            repair_operator="use the Policy-permitted predicate",
        )
        self.assertEqual(validate_diagnosis(update, experiences=_group(), skill_sections=sections), ())

        not_supportive = copy.deepcopy(update)
        not_supportive["cross_rollout_analysis"]["evidence_consistency"] = "insufficient"
        self.assertIn(
            "UPDATE_REQUIRES_SUPPORTIVE_EVIDENCE",
            validate_diagnosis(not_supportive, experiences=_group(), skill_sections=sections),
        )
        empty_mechanism = copy.deepcopy(update)
        empty_mechanism["cross_rollout_analysis"]["discriminating_behavior"] = ""
        self.assertIn(
            "UPDATE_REQUIRES_DISCRIMINATING_BEHAVIOR",
            validate_diagnosis(empty_mechanism, experiences=_group(), skill_sections=sections),
        )
        label_only = copy.deepcopy(update)
        label_only["cross_rollout_analysis"]["discriminating_behavior"] = "CS and VS differ."
        self.assertIn(
            "DISCRIMINATING_BEHAVIOR_IS_ONLY_LABEL_CONTRAST",
            validate_diagnosis(label_only, experiences=_group(), skill_sections=sections),
        )
        conflicting = copy.deepcopy(update)
        conflicting["cross_rollout_analysis"]["evidence_consistency"] = "conflicting"
        self.assertIn(
            "CONFLICTING_EVIDENCE_REQUIRES_UNCERTAIN_NO_UPDATE",
            validate_diagnosis(conflicting, experiences=_group(), skill_sections=sections),
        )

    def test_disproven_allegation_is_insufficient_none(self):
        diagnosis = _diagnosis(relevance="none", category=None)
        diagnosis["task_behavior_summary"] = (
            "Policy and tool evidence disprove the suspected mechanism, with no alternative."
        )
        diagnosis["cross_rollout_analysis"].update({
            "stable_behavior": "the grounded behavior is permitted across all rollouts",
            "compliance_contrast": "no compliance-relevant contrast remains",
            "discriminating_behavior": "",
            "evidence_consistency": "insufficient",
            "counterevidence": "the original allegation is resolved against a Skill problem",
            "support_evidence_refs": [],
        })
        self.assertEqual(validate_diagnosis(
            diagnosis, experiences=_group(), skill_sections={"Planning and navigation": []}
        ), ())
        self.assertIsNone(diagnosis["root_cause"]["category"])
        self.assertEqual(diagnosis["skill_update_relevance"], "none")

    def test_true_conflicting_evidence_is_uncertain_no_update(self):
        diagnosis = _diagnosis(relevance="uncertain", category="uncertain")
        diagnosis["cross_rollout_analysis"].update({
            "discriminating_behavior": "",
            "evidence_consistency": "conflicting",
            "counterevidence": (
                "a still-plausible mechanism has supporting evidence and material counterevidence"
            ),
        })
        self.assertEqual(validate_diagnosis(
            diagnosis, experiences=_group(), skill_sections={"Planning and navigation": []}
        ), ())
        self.assertEqual(diagnosis["update_axis"], "none")
        self.assertEqual(diagnosis["update_recommendation"]["action"], "none")

    def test_conflicting_with_none_remains_invalid(self):
        diagnosis = _diagnosis(relevance="none", category=None)
        diagnosis["cross_rollout_analysis"]["evidence_consistency"] = "conflicting"
        self.assertIn(
            "CONFLICTING_EVIDENCE_REQUIRES_UNCERTAIN_NO_UPDATE",
            validate_diagnosis(
                diagnosis, experiences=_group(), skill_sections={"Planning and navigation": []}
            ),
        )

    def test_passenger_cabin_and_baggage_payment_counterevidence_fixture(self):
        contexts = load_authoritative_domain_contexts(ROOT / "external/tau2-bench")
        policy = contexts["airline"]["original_domain_policy"]
        baggage = next(
            item for item in contexts["airline"]["available_tool_contracts"]
            if item["tool_name"] == "update_reservation_baggages"
        )
        self.assertIn("All passengers must fly the same flights in the same cabin", policy)
        self.assertEqual(
            [
                argument["name"] for argument in baggage["arguments"]
                if argument["required"]
            ],
            ["reservation_id", "total_baggages", "nonfree_baggages", "payment_id"],
        )
        payment = next(
            argument for argument in baggage["arguments"]
            if argument["name"] == "payment_id"
        )
        self.assertTrue(payment["description"])
        diagnosis = _diagnosis(relevance="uncertain", category="uncertain")
        diagnosis["cross_rollout_analysis"].update({
            "stable_behavior": "all rollouts use the same-cabin predicate and supply payment information",
            "compliance_contrast": "CS, CS, and VS labels differ without a behavior contrast",
            "discriminating_behavior": "",
            "evidence_consistency": "conflicting",
            "counterevidence": "the alleged behaviors are present in compliant and violating rollouts",
        })
        self.assertEqual(validate_diagnosis(
            diagnosis,
            experiences=_group(("compliant_success", "compliant_success", "violating_success")),
            skill_sections={"Planning and navigation": []},
        ), ())
        self.assertEqual(diagnosis["update_axis"], "none")
        self.assertEqual(diagnosis["update_recommendation"]["action"], "none")

    def test_cancellation_eligibility_policy_blocked_fixture(self):
        diagnosis = _diagnosis(relevance="none", category="external_issue")
        diagnosis["root_cause"]["explanation"] = (
            "The Policy prohibits cancellation under the current conditions even if no refund is accepted."
        )
        diagnosis["cross_rollout_analysis"]["evidence_consistency"] = "insufficient"
        self.assertEqual(validate_diagnosis(
            diagnosis, experiences=_group(), skill_sections={"Planning and navigation": []}
        ), ())
        self.assertEqual(diagnosis["update_axis"], "none")
        self.assertEqual(diagnosis["update_recommendation"]["action"], "none")
        self.assertIn("Policy explicitly prohibits", DIAGNOSIS_SYSTEM_PROMPT)

    def test_cancellation_canary_accepts_independent_compliance_mechanism(self):
        diagnosis = _diagnosis(
            relevance="update", category="skill_issue", action="add",
            update_axis="compliance", problem="subjective praise in procedural updates",
            repair_operator="communicate policy outcomes neutrally and factually",
        )
        diagnosis["repair_policy_ids"] = ["tau3:airline:no-subjective-comments"]
        diagnosis["cross_rollout_analysis"].update({
            "evidence_consistency": "supportive",
            "discriminating_behavior": (
                "one rollout adds subjective emotional praise while two report facts neutrally"
            ),
        })
        checks = _case_checks("cancellation_eligibility", [], diagnosis, True)
        self.assertTrue(all(checks.values()))

    def test_cancellation_canary_rejects_policy_forbidden_task_success_repair(self):
        diagnosis = _diagnosis(
            relevance="update", category="skill_issue", action="add",
            update_axis="task_success", problem="ineligible cancellation was not completed",
            repair_operator="allow cancellation despite Policy when the user accepts no refund",
        )
        diagnosis["repair_policy_ids"] = ["tau3:airline:cancellation"]
        checks = _case_checks("cancellation_eligibility", [], diagnosis, True)
        self.assertFalse(checks["policy_forbidden_task_success_repair_absent"])
        self.assertFalse(checks["external_no_update_or_independent_compliance_update"])

    def test_gift_card_payment_counterevidence_fixture(self):
        diagnosis = _diagnosis(relevance="none", category=None)
        diagnosis["task_behavior_summary"] = "Every rollout refunds to a gift card; none charges a gift card."
        diagnosis["cross_rollout_analysis"].update({
            "stable_behavior": "all compliant rollouts use the same refund-to-gift-card operation",
            "compliance_contrast": "no compliance-relevant contrast remains",
            "discriminating_behavior": "",
            "evidence_consistency": "insufficient",
            "counterevidence": "refund direction disproves additional-payment sufficiency",
            "support_evidence_refs": [],
        })
        self.assertEqual(validate_diagnosis(
            diagnosis,
            experiences=_group(("compliant_success", "violating_success", "compliant_success"), domain="retail"),
            skill_sections={"Planning and navigation": []},
        ), ())
        self.assertIn("A disproven allegation is not automatically conflicting evidence", DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn("Evidence-consistency decision table", DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn("Never use conflicting + none", DIAGNOSIS_SYSTEM_PROMPT)

    def test_tool_capability_never_overrides_policy_permission_fixture(self):
        diagnosis = _diagnosis(relevance="none", category="external_issue")
        diagnosis["root_cause"]["explanation"] = (
            "The operation is technically available but explicitly prohibited by Policy in this state."
        )
        self.assertEqual(validate_diagnosis(
            diagnosis, experiences=_group(), skill_sections={"Planning and navigation": []}
        ), ())
        self.assertIn("Tool availability alone is not Policy permission", DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn("tool availability alone is not Policy permission", EDITOR_SYSTEM_PROMPT)

    def test_dual_axis_schema_accepts_compliance_and_task_success_updates(self):
        sections = {"Planning and navigation": []}
        compliance = _diagnosis(
            relevance="update", action="add", category="skill_issue",
            update_axis="compliance", problem="policy-scoped behavior",
            repair_operator="apply the local policy requirement",
        )
        self.assertEqual(validate_diagnosis(
            compliance,
            experiences=_group(("compliant_success", "violating_success", "compliant_success")),
            skill_sections=sections,
        ), ())
        task_success = copy.deepcopy(compliance)
        task_success["update_axis"] = "task_success"
        self.assertEqual(validate_diagnosis(
            task_success,
            experiences=_group(("compliant_success", "compliant_failure", "compliant_success")),
            skill_sections=sections,
        ), ())
        task_success["update_axis"] = "none"
        self.assertIn("UPDATE_REQUIRES_ACTIVE_AXIS", validate_diagnosis(
            task_success, experiences=_group(), skill_sections=sections,
        ))

    def test_validator_rejects_and_does_not_normalize_relevance_confusions(self):
        sections = {"Planning and navigation": []}
        for invalid in ("add", "compliance", "high", "skill_issue"):
            diagnosis = _diagnosis(
                relevance="update", action="add", category="skill_issue",
                update_axis="compliance", problem="policy-scoped behavior",
                repair_operator="apply the local policy requirement",
            )
            diagnosis["skill_update_relevance"] = invalid
            self.assertIn(
                "INVALID_SKILL_UPDATE_RELEVANCE",
                validate_diagnosis(
                    diagnosis, experiences=_group(), skill_sections=sections,
                ),
            )
            self.assertEqual(diagnosis["skill_update_relevance"], invalid)

    def test_dual_axis_prompt_and_abstraction_boundary_contract(self):
        for contrast in ("CS vs CF", "VS vs VF", "CS vs VS", "CF vs VF"):
            self.assertIn(contrast, DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn("Task Success and Compliance as independent axes", DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn("Generalize entities and episodes", DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn("preserve decision predicates, repair operators", DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn("limits the strength and scope", DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn('"update_axis":"none"', DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn("one-tool-call-at-a-time requirement is outside v0.13 learning scope", DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn("Do not produce a serialization", DIAGNOSIS_SYSTEM_PROMPT)
        self.assertNotIn("PARTIALLY_FIXED", DIAGNOSIS_SYSTEM_PROMPT)

    def test_diagnosis_prompt_prevents_relevance_field_confusion(self):
        self.assertIn(
            'skill_update_relevance must be exactly one of "update", "none", or "uncertain"',
            DIAGNOSIS_SYSTEM_PROMPT,
        )
        for invalid in (
            '"skill_issue"', '"add"', '"replace"', '"delete"',
            '"task_success"', '"compliance"', '"both"', '"high"',
        ):
            self.assertIn(invalid, DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn(
            '"skill_update_relevance":"update","update_axis":"compliance"',
            DIAGNOSIS_SYSTEM_PROMPT,
        )
        self.assertIn("Before returning, verify all of the following", DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn(
            "root_cause, skill_update_relevance, update_axis, and action",
            DIAGNOSIS_SYSTEM_PROMPT,
        )
        self.assertIn(
            "The pair (evidence_consistency conflicting, skill_update_relevance none) never appears",
            DIAGNOSIS_SYSTEM_PROMPT,
        )

    def test_stopping_boundary_is_optional_and_mechanism_specific(self):
        confirmation = _diagnosis(
            relevance="update", action="add", category="skill_issue", update_axis="compliance",
            problem="confirmation is repeated after it was satisfied",
            repair_operator="obtain confirmation before the action",
            stopping_boundary="existing explicit confirmation remains valid when material facts are unchanged",
        )
        record = _diagnosis(
            relevance="update", action="add", category="skill_issue", update_axis="task_success",
            problem="cross-record field composition",
            repair_operator="preserve fields within one record", stopping_boundary="",
        )
        for value in (confirmation, record):
            self.assertEqual(validate_diagnosis(
                value, experiences=_group(), skill_sections={"Planning and navigation": []}
            ), ())

    def test_editor_keeps_distinct_grounding_mechanisms_separate(self):
        parent = (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text().replace(
            "# Operational Skill", "# SuiteCRM Operational Skill"
        )
        evidence = (*_group(domain="airline", task_id="1"), *_group(domain="retail", task_id="2"))

        def diagnose(request):
            record = request.task_context["domain"] == "airline"
            value = _diagnosis(
                relevance="update", action="add", category="skill_issue", update_axis="both",
                problem="cross-record composition" if record else "unsupported operational inference",
                repair_operator="preserve one-record binding" if record else "verify each operational fact",
            )
            value["cross_rollout_analysis"]["support_evidence_refs"] = [
                {"source_id": request.rollouts[0]["source_id"], "step_ids": [2]}
            ]
            return _tag(value)

        def editor(_request):
            return "<CANONICAL_EDITS_JSON>" + json.dumps([
                _edit(["diagnosis_001"], record_integrity=True),
                _edit(["diagnosis_002"], record_integrity=False),
            ]) + "</CANONICAL_EDITS_JSON>"

        decision = MultiRolloutDiagnosisProposalOperator().propose(
            ProposalContext("candidate", parent, tuple(evidence)), diagnose, editor,
            domain_contexts=_domain_contexts(),
        )
        self.assertEqual(len(decision.applied_edits), 2)
        self.assertEqual(decision.editor_calls, 1)

    def test_editor_merges_equivalent_record_integrity_and_preserves_provenance(self):
        parent = (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text().replace(
            "# Operational Skill", "# SuiteCRM Operational Skill"
        )
        evidence = (*_group(domain="airline", task_id="1"), *_group(domain="retail", task_id="2"))

        def diagnose(request):
            value = _diagnosis(
                relevance="update", action="add", category="skill_issue", update_axis="both",
                problem="cross-record field composition", repair_operator="preserve one-record binding",
            )
            value["cross_rollout_analysis"]["support_evidence_refs"] = [
                {"source_id": request.rollouts[0]["source_id"], "step_ids": [2]}
            ]
            return _tag(value)

        def editor(_request):
            return "<CANONICAL_EDITS_JSON>" + json.dumps([
                _edit(["diagnosis_001", "diagnosis_002"], record_integrity=True)
            ]) + "</CANONICAL_EDITS_JSON>"

        decision = MultiRolloutDiagnosisProposalOperator().propose(
            ProposalContext("candidate", parent, tuple(evidence)), diagnose, editor,
            domain_contexts=_domain_contexts(),
        )
        self.assertEqual(len(decision.applied_edits), 1)
        edit = decision.applied_edits[0]
        self.assertEqual(set(edit["derived_from_patch_ids"]), {"diagnosis_001", "diagnosis_002"})
        self.assertEqual(set(edit["source_ids"]), {item["source_id"] for item in evidence})
        self.assertIn("fields from different records", edit["verification_target"]["problem"])

    def test_editor_prompt_requires_mechanism_equivalence_and_operational_target(self):
        self.assertIn("repair-operator equivalence is required", EDITOR_SYSTEM_PROMPT)
        self.assertIn("Minimality concerns unnecessary behavioral constraints, not wording length", EDITOR_SYSTEM_PROMPT)
        self.assertIn("If a merged edit cannot retain one", EDITOR_SYSTEM_PROMPT)
        self.assertIn("Product-record integrity and unsupported operational inference are distinct", EDITOR_SYSTEM_PROMPT)
        self.assertIn("Parent compliant-success path", EDITOR_SYSTEM_PROMPT)


class V13ComplianceJudgeTests(unittest.TestCase):
    POLICY = "# Modify items\n\nThis action can only be called once.\n\n# Modify address\n\nAddresses may be modified."

    def test_action_local_rule_is_not_expanded_to_sibling_tools(self):
        self.assertIn("Policy provenance and semantic applicability are different", JUDGE_SYSTEM_PROMPT)
        self.assertIn('"this action"', JUDGE_SYSTEM_PROMPT)
        self.assertIn("does not automatically govern modify-address", JUDGE_SYSTEM_PROMPT)
        self.assertIn("Tool affordance is not policy permission", JUDGE_SYSTEM_PROMPT)
        self.assertIn("outside this Judge's evaluation scope", JUDGE_SYSTEM_PROMPT)
        self.assertIn("Never output a violation whose policy_clause", JUDGE_SYSTEM_PROMPT)
        trajectory = [
            {"step": 1, "event_type": "tool_call", "tool_name": "modify_address"},
            {"step": 2, "event_type": "tool_call", "tool_name": "modify_items"},
        ]
        payload = build_judge_payload(
            "retail", self.POLICY, {"domain": "retail"}, trajectory,
            [{
                "tool_name": "modify_items", "arguments": [],
                "description": "Modify items.", "raises": [],
            }],
        )
        self.assertEqual(
            [item["tool_name"] for item in payload["full_trajectory"]],
            ["modify_address", "modify_items"],
        )
        self.assertEqual(payload["available_tool_contracts"][0]["tool_name"], "modify_items")

    def test_passenger_same_cabin_constraint_remains_cross_flow_grounding(self):
        self.assertIn(
            "All passengers must fly the same flights in the same cabin",
            JUDGE_SYSTEM_PROMPT,
        )
        self.assertIn(
            "remains grounding when a later Modify-flight action changes that reservation",
            JUDGE_SYSTEM_PROMPT,
        )

    def test_clause_must_come_from_original_policy(self):
        valid = {
            "compliant": False,
            "violations": [{
                "policy_clause": "This action can only be called once.",
                "evidence_steps": [2], "reason": "modify_items was called twice",
            }],
        }
        judgment = validate_judgment(valid, {1, 2}, original_policy=self.POLICY)
        self.assertEqual(judgment.violations[0].policy_section, "Modify items")
        broadened = copy.deepcopy(valid)
        broadened["violations"][0]["policy_clause"] = "All modification tools can only be called once per order."
        with self.assertRaisesRegex(ComplianceJudgeError, "policy clause not found"):
            validate_judgment(broadened, {1, 2}, original_policy=self.POLICY)

    def test_policy_section_is_derived_as_canonical_heading_path(self):
        policy = "## Modify pending order\n\n### Modify items\n\nClause A."
        raw = {
            "compliant": False,
            "violations": [{
                "policy_clause": "Clause A.",
                "evidence_steps": [1], "reason": "One alleged behavior.",
            }],
        }
        judgment = validate_judgment(raw, {1}, original_policy=policy)
        self.assertEqual(
            judgment.violations[0].policy_section,
            "Modify pending order > Modify items",
        )

    def test_non_heading_label_uses_nearest_markdown_heading(self):
        policy = "## Modify flight\n\nChange cabin:\nClause B."
        raw = {
            "compliant": False,
            "violations": [{
                "policy_clause": "Clause B.", "evidence_steps": [1],
                "reason": "One alleged behavior.",
            }],
        }
        judgment = validate_judgment(raw, {1}, original_policy=policy)
        self.assertEqual(judgment.violations[0].policy_section, "Modify flight")

    def test_ambiguous_policy_clause_location_fails_closed(self):
        policy = "## A\n\nSame clause.\n\n## B\n\nSame clause."
        raw = {
            "compliant": False,
            "violations": [{
                "policy_clause": "Same clause.", "evidence_steps": [1],
                "reason": "One alleged behavior.",
            }],
        }
        with self.assertRaises(ComplianceJudgeError) as caught:
            validate_judgment(raw, {1}, original_policy=policy)
        self.assertEqual(
            caught.exception.validation_code,
            "AMBIGUOUS_POLICY_CLAUSE_LOCATION",
        )

    def test_atomic_violation_and_complete_unsupported_claim_contract(self):
        self.assertIn("Each violation item must describe one coherent behavioral allegation", JUDGE_SYSTEM_PROMPT)
        self.assertIn("Do not bundle independent issues", JUDGE_SYSTEM_PROMPT)
        self.assertIn("check the entire original Policy", JUDGE_SYSTEM_PROMPT)
        self.assertIn("every relevant tool-level and argument-level contract", JUDGE_SYSTEM_PROMPT)

    def test_one_tool_call_clause_is_deterministically_excluded(self):
        policy = (
            "# General requirements\n\nYou should only make one tool call at a time.\n\n"
            "The user must confirm cancellation."
        )
        excluded = {
            "compliant": False,
            "violations": [{
                "policy_clause": "You should only make one tool call at a time.",
                "evidence_steps": [1, 2],
                "reason": "Two calls appeared before their results.",
            }],
        }
        judgment = validate_judgment(excluded, {1, 2}, original_policy=policy)
        self.assertTrue(judgment.compliant)
        self.assertEqual(judgment.violations, ())

    def test_one_tool_exclusion_precedes_policy_exact_match(self):
        raw = {
            "compliant": False,
            "violations": [{
                "policy_clause": (
                    "You should only make one tool call at a time, including lookup calls."
                ),
                "evidence_steps": [1, 2],
                "reason": "Two calls appeared before their results.",
            }],
        }
        judgment = validate_judgment(
            raw, {1, 2},
            original_policy="You should only make one tool call at a time.",
        )
        self.assertTrue(judgment.compliant)
        self.assertEqual(judgment.violations, ())

    def test_clause_validation_error_preserves_judge_context(self):
        raw = {
            "compliant": False,
            "violations": [{
                "policy_clause": "All modification tools can only be called once.",
                "evidence_steps": [1], "reason": "A modification was repeated.",
            }],
        }
        with self.assertRaises(ComplianceJudgeError) as caught:
            validate_judgment(raw, {1}, original_policy=self.POLICY)
        self.assertEqual(caught.exception.validation_code, "POLICY_CLAUSE_NOT_FOUND")
        self.assertEqual(
            caught.exception.failed_policy_clause,
            "All modification tools can only be called once.",
        )
        self.assertEqual(caught.exception.raw_judge_response, raw)

    def test_rollout_error_report_preserves_compliance_judge_context(self):
        campaign = _load(MANIFEST)
        raw_response = '{"compliant": false, "violations": []}'
        failure = ComplianceJudgeError(
            "COMPLIANCE_JUDGE_ERROR: policy clause not found",
            validation_code="POLICY_CLAUSE_NOT_FOUND",
            raw_judge_response=raw_response,
            failed_policy_clause="Broadened policy clause.",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "retail_89_rollout_01.json"
            adapter = Tau3RolloutAdapter(
                campaign, repo_root=ROOT, judge_caller=lambda *_: "",
            )
            with patch(
                "src.skill_evolution.autonomous_gse_v13_benchmark_runtime.v09.run_official_rollout",
                side_effect=failure,
            ):
                with self.assertRaises(ComplianceJudgeError):
                    adapter.run(
                        domain="retail", task_id="89", phase="train",
                        skill_version="S0", skill_path=None, rollout_index=1,
                        rollout_seed=200, output_path=output,
                    )
            report = _load(output.with_name("retail_89_rollout_01_error.json"))
            self.assertEqual(report["validation_code"], "POLICY_CLAUSE_NOT_FOUND")
            self.assertEqual(report["raw_judge_response"], raw_response)
            self.assertEqual(report["failed_policy_clause"], "Broadened policy clause.")

    def test_exclusion_preserves_other_policy_violations(self):
        policy = (
            "# Generic action rules\n\n"
            "You should at most make one tool call at a time, and if you take a tool call, "
            "you should not respond to the user at the same time.\n\n"
            "The user must confirm cancellation."
        )
        raw = {
            "compliant": False,
            "violations": [
                {
                    "policy_clause": (
                        "You should at most make one tool call at a time, and if you take a tool call, "
                        "you should not respond to the user at the same time."
                    ),
                    "evidence_steps": [1, 2], "reason": "Two tool calls were listed.",
                },
                {
                    "policy_clause": "The user must confirm cancellation.",
                    "evidence_steps": [3], "reason": "Cancellation occurred without confirmation.",
                },
            ],
        }
        judgment = validate_judgment(raw, {1, 2, 3}, original_policy=policy)
        self.assertFalse(judgment.compliant)
        self.assertEqual(
            [item.policy_clause for item in judgment.violations],
            ["The user must confirm cancellation."],
        )

    def test_tool_contract_preserves_argument_and_raises_semantics(self):
        source = '''
def is_tool(value):
    return value

@is_tool("write")
def exchange_item(payment_method_id: str, note: str | None = None):
    """Exchange an item.

    Args:
        payment_method_id: The payment method used to pay or receive
            refund for the price difference.
        note: An optional audit note.

    Raises:
        InsufficientBalanceError: If the gift card cannot cover a positive
            price difference.
    """
'''
        with tempfile.TemporaryDirectory() as directory:
            tools_path = Path(directory) / "tools.py"
            tools_path.write_text(source, encoding="utf-8")
            contract = _tool_contracts_from_authoritative_source(tools_path)[0]
        self.assertEqual(contract["description"], "Exchange an item.")
        self.assertEqual(contract["arguments"], [
            {
                "name": "payment_method_id", "required": True,
                "description": (
                    "The payment method used to pay or receive refund for the price difference."
                ),
            },
            {"name": "note", "required": False, "description": "An optional audit note."},
        ])
        self.assertEqual(contract["raises"], [{
            "type": "InsufficientBalanceError",
            "description": "If the gift card cannot cover a positive price difference.",
        }])

    def test_gift_card_positive_difference_is_payment_direction(self):
        self.assertIn("positive price difference paid by the customer", JUDGE_SYSTEM_PROMPT)

    def test_gift_card_negative_difference_is_refund_direction(self):
        self.assertIn("negative price difference returned to the customer", JUDGE_SYSTEM_PROMPT)
        self.assertIn("gift card receiving that refund need not already contain", JUDGE_SYSTEM_PROMPT)

    def test_unsupported_information_is_fallback_after_complete_grounding_check(self):
        self.assertIn("unsupported-information clause only as a fallback", JUDGE_SYSTEM_PROMPT)
        self.assertIn("Absence from the current subsection is not evidence", JUDGE_SYSTEM_PROMPT)

    def test_judge_output_schema_forbids_free_form_policy_section(self):
        raw = {
            "compliant": False,
            "violations": [{
                "policy_section": "Modify flight — Change cabin",
                "policy_clause": "This action can only be called once.",
                "evidence_steps": [1], "reason": "One alleged behavior.",
            }],
        }
        with self.assertRaises(ComplianceJudgeError) as caught:
            validate_judgment(raw, {1}, original_policy=self.POLICY)
        self.assertEqual(caught.exception.validation_code, "INVALID_VIOLATION_SCHEMA")


class V13TargetFixTests(unittest.TestCase):
    def test_all_pair_transition_types_and_evidence_contract(self):
        request = _target_request()
        for transition in ("IMPROVED", "UNCHANGED_BAD", "PRESERVED", "WORSENED", "NOT_EXERCISED"):
            response = _target_response([transition] * 3, request)
            value = parse_targeted_fix_response(response, request=request)
            self.assertEqual({item["transition"] for item in value["pair_transitions"]}, {transition})
        _, user = build_targeted_fix_prompts(request)
        payload = json.loads(user.split("\n", 1)[1])
        self.assertEqual(payload["matched_replays"][0]["parent_rollouts"][0]["valid_step_ids"], [1, 2])
        self.assertEqual(payload["matched_replays"][0]["candidate_rollouts"][0]["valid_step_ids"], [1, 2])

    def test_edit_level_verdicts(self):
        self.assertEqual(derive_edit_verdict(["IMPROVED", "UNCHANGED_BAD", "UNCHANGED_BAD"]), "FIXED")
        self.assertEqual(derive_edit_verdict(["UNCHANGED_BAD", "UNCHANGED_BAD"]), "NOT_FIXED")
        self.assertEqual(derive_edit_verdict(["PRESERVED", "NOT_EXERCISED"]), "NOT_EXERCISED")
        self.assertEqual(derive_edit_verdict(["IMPROVED", "WORSENED"]), "NOT_FIXED")

    def test_behavior_is_decoupled_from_four_state_transition(self):
        request = _target_request(parent_state="violating_success", candidate_state="compliant_failure")
        value = parse_targeted_fix_response(
            _target_response(["IMPROVED", "UNCHANGED_BAD", "UNCHANGED_BAD"], request),
            request=request,
        )
        self.assertEqual(value["status"], "FIXED")
        self.assertEqual(request.matched_replays[0]["parent_rollouts"][0]["state"], "violating_success")
        self.assertEqual(request.matched_replays[0]["candidate_rollouts"][0]["state"], "compliant_failure")

    def test_prompt_forbids_candidate_only_and_four_state_shortcuts(self):
        self.assertIn("matched Parent-to-Candidate behavior change", TARGET_FIX_SYSTEM_PROMPT)
        self.assertIn("It is not Task Success, Compliance, CS/VS/CF/VF", TARGET_FIX_SYSTEM_PROMPT)
        self.assertIn("IMPROVED + UNCHANGED_BAD remains FIXED", TARGET_FIX_SYSTEM_PROMPT)
        self.assertIn("one-tool-call-at-a-time requirement is outside v0.13 evaluation scope", TARGET_FIX_SYSTEM_PROMPT)
        self.assertIn("classify every pair NOT_EXERCISED", TARGET_FIX_SYSTEM_PROMPT)
        self.assertNotIn("PARTIALLY_FIXED", TARGET_FIX_SYSTEM_PROMPT)

    def test_prompt_forbids_cross_side_step_copy_when_source_ids_match(self):
        self.assertIn(
            "may intentionally have the same source_id string",
            TARGET_FIX_SYSTEM_PROMPT,
        )
        self.assertIn(
            "copy steps only from that pair's parent_rollout.valid_step_ids",
            TARGET_FIX_SYSTEM_PROMPT,
        )
        self.assertIn(
            "copy steps only from that pair's candidate_rollout.valid_step_ids",
            TARGET_FIX_SYSTEM_PROMPT,
        )
        self.assertIn(
            "Never copy a Parent step into Candidate evidence",
            TARGET_FIX_SYSTEM_PROMPT,
        )


class V13GateCampaignTests(unittest.TestCase):
    def _decision(self, status="FIXED", transitions=None, regression=None, candidate=None):
        transitions = transitions or ["IMPROVED"]
        target = [{
            "canonical_edit_id": "canonical_edit_001", "status": status,
            "pair_transitions": [{"transition": value} for value in transitions],
        }]
        parent = [_row(index) for index in (1, 2, 3)]
        return build_evolution_decision(
            applied_canonical_edits=[{"canonical_edit_id": "canonical_edit_001"}],
            targeted_fix_results=target, regression_diagnoses=regression or [],
            parent_rows=parent, candidate_rows=candidate or copy.deepcopy(parent),
        )

    def test_gate_accept_and_rejection_reasons(self):
        self.assertEqual(self._decision()["decision"], "ACCEPT")
        self.assertIn("TARGET_NOT_FIXED", self._decision("NOT_FIXED", ["UNCHANGED_BAD"])["all_reasons"])
        self.assertIn("TARGET_NOT_EXERCISED", self._decision("NOT_EXERCISED", ["PRESERVED"])["all_reasons"])
        worsened = self._decision("NOT_FIXED", ["IMPROVED", "WORSENED"])
        self.assertEqual(worsened["primary_reason"], "TARGET_WORSENED")
        regression = self._decision(regression=[{"attribution": "CHANGE_CAUSED"}])
        self.assertIn("CHANGE_CAUSED_REGRESSION", regression["all_reasons"])
        parent20 = [_row(index) for index in range(1, 21)]
        candidate17 = [
            _row(index, "compliant_failure" if index <= 3 else "compliant_success")
            for index in range(1, 21)
        ]
        collapsed = build_evolution_decision(
            applied_canonical_edits=[{"canonical_edit_id": "canonical_edit_001"}],
            targeted_fix_results=[{
                "canonical_edit_id": "canonical_edit_001", "status": "FIXED",
                "pair_transitions": [{"transition": "IMPROVED"}],
            }], regression_diagnoses=[], parent_rows=parent20, candidate_rows=candidate17,
        )
        self.assertIn("AGGREGATE_COLLAPSE", collapsed["all_reasons"])

    def test_campaign_is_v12_identity_matched_and_k3(self):
        v12_manifest, v13_manifest = _load(V12_DIR / "campaign_manifest.json"), _load(MANIFEST)
        v12_map, v13_map = _load(V12_DIR / "batch_map.json"), _load(BATCH_MAP)
        self.assertEqual(v12_map["assignment"], v13_map["assignment"])
        self.assertEqual(v12_map["batches"], v13_map["batches"])
        self.assertEqual(v12_manifest["campaign_seed"], v13_manifest["campaign_seed"])
        self.assertEqual(v12_manifest["agent"], v13_manifest["agent"])
        self.assertEqual(v12_manifest["user_simulator"], v13_manifest["user_simulator"])
        self.assertEqual(v12_manifest["official_evaluator"], v13_manifest["official_evaluator"])
        self.assertEqual(v12_manifest["evolution"]["rollouts_per_task"], 3)
        self.assertEqual(v13_manifest["evolution"]["rollouts_per_task"], 3)
        self.assertEqual(
            (V12_DIR / "skills/S0_empty_skill.md").read_text(),
            (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text(),
        )
        self.assertEqual(derive_rollout_seeds(200, 1000), (1200, 1201, 1202))
        replay = matched_replay_plan(["airline:1", "retail:2"], 200)
        self.assertEqual(replay["parent"], replay["candidate"])
        self.assertEqual(len(replay["parent"]), 6)

    def test_dry_plan_and_holdout_match_v12_scale(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        plan = build_campaign_dry_plan(campaign, batch_map)
        self.assertEqual([len(step["parent_units"]) for step in plan["steps"]], [60, 60, 60])
        self.assertEqual([step["maximum_parent_diagnosis_calls"] for step in plan["steps"]], [20, 20, 20])
        self.assertEqual(plan["computed_budget"], campaign["budget"])
        holdout = build_holdout_plan(campaign, batch_map, campaign["initial_parent"])
        self.assertEqual(len(holdout["s0_units"]), 120)
        self.assertEqual(holdout["s0_units"], holdout["s_final_units"])
        self.assertEqual(holdout["trajectory_count"], 240)

    def test_policy_grounded_recovery_pauses_step3_and_branches_step2_reuse(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        plan = build_policy_grounded_recovery_plan(campaign, batch_map, {
            "protocol_version": "autonomous_gse_v13", "completed_steps": 2,
            "current_parent": {"version": "S0"}, "steps": [{}, {}],
        })
        self.assertTrue(plan["step_3_paused"])
        self.assertFalse(plan["formal_execution_authorized"])
        self.assertTrue(plan["preserve_existing_artifacts"])
        self.assertIn("rerun_compliance_judge", plan["step_2_parent_rule"]["if_new_step_1_rejects"]["then"])
        self.assertFalse(
            plan["step_2_parent_rule"]["if_new_step_1_accepts"]
            ["reuse_old_step_2_s0_parent_trajectories"]
        )


class _FakeBackend:
    def __init__(self, root: Path):
        self.root = root
        self.calls = []

    def run_batch(self, *, task_ids, phase, skill_version, skill_path, execution_phase, execution_seed_offset=0):
        self.calls.append((execution_phase, len(task_ids) * 3))
        paths = []
        for domain_task in task_ids:
            domain, task_id = domain_task.split(":", 1)
            for index, seed in enumerate(derive_rollout_seeds(200, execution_seed_offset), start=1):
                path = self.root / execution_phase / f"{domain}_{task_id}_rollout_{index:02d}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                governed = {
                    "state": "compliant_failure", "task_success": False,
                    "process_feedback": {"compliant": True, "violated_policies": []},
                    "actions": [{"step": 1, "actor": "agent", "content": "done"}],
                }
                path.write_text(json.dumps({
                    "domain": domain, "task_id": task_id, "rollout_index": index,
                    "rollout_seed": seed, "state": "compliant_failure",
                    "task_evaluation": {"success": False},
                    "compliance_evaluation": {"compliant": True},
                    "governed_evidence": governed,
                }))
                paths.append(path)
        return paths


class V13OfflineIntegrationTests(unittest.TestCase):
    def test_step1_restart_archives_derived_outputs_and_rescores_saved_parent(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = _FakeBackend(root / "rollouts" / "train")
            task_ids = batch_map["batches"][0]["task_ids"]
            parent_paths = backend.run_batch(
                task_ids=task_ids, phase="train", skill_version="S0", skill_path=None,
                execution_phase="step_001_parent",
            )
            backend.run_batch(
                task_ids=task_ids, phase="train", skill_version="S1",
                skill_path=root / "steps/step_001/candidate_skill.md",
                execution_phase="step_001_candidate_replay",
            )
            for path in parent_paths:
                value = _load(path)
                value["compliance_evaluation"] = {
                    "compliant": True, "judge_model": "openai/gpt-5.6-luna",
                    "judge_temperature": 0,
                    "judge_prompt_version": "tau3_policy_scope_grounded_judge_v13",
                    "violations": [],
                }
                value["governed_evidence"]["compliance_evaluation"] = copy.deepcopy(
                    value["compliance_evaluation"]
                )
                value["provenance"] = {
                    "judge_config": {"prompt_version": "tau3_policy_scope_grounded_judge_v13"}
                }
                path.write_text(json.dumps(value), encoding="utf-8")
            first = _load(parent_paths[0])
            violation = {
                "policy_section": "General requirements",
                "policy_clause": "You should only make one tool call at a time",
                "evidence_steps": [1], "reason": "Multiple calls were listed.",
            }
            first["compliance_evaluation"] = {
                "compliant": False, "judge_model": "openai/gpt-5.6-luna",
                "judge_temperature": 0,
                "judge_prompt_version": "tau3_policy_scope_grounded_judge_v13",
                "violations": [violation],
            }
            first["state"] = "violating_failure"
            first["governed_evidence"]["state"] = "violating_failure"
            first["governed_evidence"]["process_feedback"] = {
                "compliant": False, "violated_policies": [violation],
            }
            first["governed_evidence"]["compliance_evaluation"] = copy.deepcopy(
                first["compliance_evaluation"]
            )
            first["provenance"] = {
                "judge_config": {"prompt_version": "tau3_policy_scope_grounded_judge_v13"}
            }
            parent_paths[0].write_text(json.dumps(first), encoding="utf-8")
            step_root = root / "steps" / "step_001"
            step_root.mkdir(parents=True)
            (step_root / "candidate_skill.md").write_text("# candidate\n", encoding="utf-8")
            (root / "resume_state.json").write_text(json.dumps({
                "protocol_version": "autonomous_gse_v13", "completed_steps": 1,
                "current_parent": campaign["initial_parent"], "steps": [{}],
            }), encoding="utf-8")

            report = prepare_v13_step1_restart_from_parent(
                campaign, batch_map, artifact_root=root,
            )
            archive = root / "invalidated" / "step_001_before_one_tool_scope_exclusion"
            self.assertEqual(report["reused_parent_rollouts"], 60)
            self.assertEqual(report["removed_one_tool_call_violations"], 1)
            self.assertEqual(report["parent_rollouts_rerun"], 0)
            self.assertTrue((archive / "step_001/candidate_skill.md").is_file())
            self.assertTrue((archive / "step_001_candidate_replay").is_dir())
            self.assertTrue((archive / "root_reports/resume_state.json").is_file())
            self.assertFalse((root / "resume_state.json").exists())
            rescored = _load(parent_paths[0])
            original = _load(archive / "parent_rollouts_before_scope_exclusion" / parent_paths[0].name)
            self.assertTrue(rescored["compliance_evaluation"]["compliant"])
            self.assertEqual(rescored["state"], "compliant_failure")
            self.assertFalse(original["compliance_evaluation"]["compliant"])

    def test_target_fix_resume_reuses_completed_prefix_and_calls_only_missing_edit(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = _FakeBackend(root / "rollouts" / "train")
            task_ids = batch_map["batches"][0]["task_ids"]
            backend.run_batch(
                task_ids=task_ids, phase="train", skill_version="S0", skill_path=None,
                execution_phase="step_001_parent",
            )
            backend.run_batch(
                task_ids=task_ids, phase="train", skill_version="S1",
                skill_path=root / "steps/step_001/candidate_skill.md",
                execution_phase="step_001_candidate_replay",
            )
            step_root = root / "steps" / "step_001"
            step_root.mkdir(parents=True, exist_ok=True)
            (step_root / "candidate_skill.md").write_text("# candidate\n", encoding="utf-8")
            first_task, second_task = (value.split(":", 1) for value in task_ids[:2])
            diagnoses = [
                {
                    "diagnosis_id": "diagnosis_001",
                    "source_ids": [
                        f"step_001_{first_task[0]}_{first_task[1]}_rollout_{index:02d}"
                        for index in range(1, 4)
                    ],
                },
                {
                    "diagnosis_id": "diagnosis_002",
                    "source_ids": [
                        f"step_001_{second_task[0]}_{second_task[1]}_rollout_{index:02d}"
                        for index in range(1, 4)
                    ],
                },
            ]
            edits = [
                {
                    "canonical_edit_id": "canonical_edit_001",
                    "derived_from_diagnosis_ids": ["diagnosis_001"],
                },
                {
                    "canonical_edit_id": "canonical_edit_002",
                    "derived_from_diagnosis_ids": ["diagnosis_002"],
                },
            ]
            (step_root / "diagnoses.json").write_text(
                json.dumps({"diagnoses": diagnoses}), encoding="utf-8",
            )
            (step_root / "candidate_edits.json").write_text(json.dumps(edits), encoding="utf-8")
            completed = {
                "canonical_edit_id": "canonical_edit_001", "status": "FIXED",
                "pair_transitions": [{"rollout_index": 1, "transition": "IMPROVED"}],
                "reason": "saved",
            }
            (step_root / "targeted_fix_error.json").write_text(json.dumps({
                "protocol_version": "autonomous_gse_v13", "step": 1,
                "completed_targeted_fix_results": [completed],
            }), encoding="utf-8")
            calls = []

            def judge(request):
                edit_id = request.canonical_edit["canonical_edit_id"]
                calls.append(edit_id)
                return {
                    "canonical_edit_id": edit_id, "status": "FIXED",
                    "pair_transitions": [{"rollout_index": 1, "transition": "IMPROVED"}],
                    "reason": "new",
                }

            report = resume_v13_target_fix_and_gate(
                campaign, batch_map, step_number=1, targeted_fix_judge=judge,
                regression_judge=lambda request: self.fail("No regression should exist"),
                artifact_root=root,
            )
            self.assertEqual(calls, ["canonical_edit_002"])
            targeted = _load(step_root / "targeted_fix_report.json")
            self.assertTrue(targeted["complete"])
            self.assertEqual(
                [value["canonical_edit_id"] for value in targeted["results"]],
                ["canonical_edit_001", "canonical_edit_002"],
            )
            self.assertFalse((step_root / "targeted_fix_error.json").exists())
            self.assertEqual(report["step_report"]["decision"], "ACCEPT")
            self.assertEqual(_load(root / "resume_state.json")["completed_steps"], 1)

    def test_three_parent_rollouts_make_one_diagnosis_per_task_without_model_calls(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend, calls = _FakeBackend(root / "rollouts"), []

            def diagnose(request):
                calls.append(request)
                value = _diagnosis()
                value["cross_rollout_analysis"]["support_evidence_refs"] = [
                    {"source_id": request.rollouts[0]["source_id"], "step_ids": [1]}
                ]
                return _tag(value)

            report = run_v13_campaign(
                campaign, batch_map, backend=backend, diagnoser=diagnose,
                editor=lambda request: self.fail("Editor must not run"),
                artifact_root=root / "artifacts",
            )
            self.assertEqual(len(calls), 60)
            self.assertTrue(all(len(request.rollouts) == 3 for request in calls))
            self.assertTrue(all(request.original_domain_policy.strip() for request in calls))
            self.assertTrue(all(request.available_tool_contracts for request in calls))
            self.assertTrue(all(
                ("Airline Agent Policy" in request.original_domain_policy)
                == (request.task_context["domain"] == "airline")
                for request in calls
            ))
            tools_by_domain = {
                request.task_context["domain"]: {
                    item["tool_name"] for item in request.available_tool_contracts
                }
                for request in calls
            }
            self.assertIn("update_reservation_baggages", tools_by_domain["airline"])
            self.assertIn("cancel_pending_order", tools_by_domain["retail"])
            self.assertEqual(backend.calls, [
                ("step_001_parent", 60), ("step_002_parent", 60), ("step_003_parent", 60),
            ])
            self.assertEqual([step["decision"] for step in report["steps"]], ["NO_CANDIDATE"] * 3)


if __name__ == "__main__":
    unittest.main()
