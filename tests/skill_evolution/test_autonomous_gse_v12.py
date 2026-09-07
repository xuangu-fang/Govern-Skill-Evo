from __future__ import annotations

import copy
import json
import tempfile
import sys
import types
import unittest
from pathlib import Path

from src.learners.stwebagentbench.generate_governed_skill_v12 import EDITOR_SYSTEM_PROMPT
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v12_benchmark_runtime import (
    build_campaign_dry_plan, build_holdout_plan, derive_rollout_seeds,
    matched_replay_plan, reevaluate_v12_step_1_target_fix_and_gate,
    run_v12_campaign,
)
from src.skill_evolution.autonomous_gse_v12_proposal import (
    DiagnosisContractError,
    MultiRolloutDiagnosisProposalOperator,
    group_task_evidence,
)
from src.skill_evolution.diagnosis_contract_v12 import validate_diagnosis
from src.skill_evolution.diagnosis_v12 import DIAGNOSIS_SYSTEM_PROMPT
from src.skill_evolution.evolution_gate_v12 import build_evolution_decision
from src.skill_evolution.targeted_fix_v12 import (
    SYSTEM_PROMPT as TARGETED_FIX_SYSTEM_PROMPT,
    TargetedFixRequest,
    TargetedFixResponseError,
    build_targeted_fix_prompts,
    parse_targeted_fix_response,
)

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_DIR = ROOT / "experiments/campaigns/autonomous_gse_v12"
MANIFEST = CAMPAIGN_DIR / "campaign_manifest.json"
BATCH_MAP = CAMPAIGN_DIR / "batch_map.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _experience(domain="airline", task_id="1", rollout_index=1, state="compliant_failure", policy_id=None):
    success = state.endswith("success")
    compliant = state.startswith("compliant")
    violations = [] if policy_id is None else [{"policy_template_id": policy_id}]
    return {
        "source_id": f"step_001_{domain}_{task_id}_rollout_{rollout_index:02d}",
        "domain": domain, "task_id": str(task_id), "rollout_index": rollout_index,
        "rollout_seed": 199 + rollout_index, "state": state, "task_success": success,
        "process_feedback": {"compliant": compliant, "violated_policies": violations},
        "actions": [{"step": 1, "actor": "user", "content": "help"}, {"step": 2, "actor": "agent", "content": "done"}],
    }


def _group(domain="airline", task_id="1"):
    return tuple(_experience(domain, task_id, index) for index in (1, 2, 3))


def _diagnosis(*, relevance="none", action="none", category=None, section=None, rule_id=None, problem=""):
    refs = [{"source_id": "step_001_airline_1_rollout_01", "step_ids": [2]}]
    return {
        "task_behavior_summary": "summary",
        "cross_rollout_analysis": {"stable_behavior": "", "key_behavior_difference": "", "counterevidence": "", "support_evidence_refs": refs, "counterevidence_refs": []},
        "root_cause": {"category": category, "explanation": "explanation"},
        "skill_update_relevance": relevance,
        "repair_policy_ids": [],
        "target_behavior": {"problem": problem, "trigger_condition": "when confirmation is required", "expected_behavior": "verify before asserting"},
        "update_recommendation": {"action": action, "target_section": section, "target_rule_id": rule_id, "objective": "prevent unsupported inference", "description": "require evidence before assertions"},
    }


def _tag(value):
    return "<DIAGNOSIS_JSON>" + json.dumps(value) + "</DIAGNOSIS_JSON>"


def _edit(patch_ids, text="Verify claims against available evidence before asserting them."):
    return {
        "derived_from_patch_ids": patch_ids, "operation": "add",
        "section": "Form entry and verification", "target_rule_id": "", "text": text,
        "reason": "canonical mechanism", "source_ids": [], "repair_policy_ids": [],
        "verification_target": {"problem": "unsupported inference", "trigger_condition": "when a claim is not yet confirmed", "expected_behavior": "verify against user, tool, policy, or state evidence"},
    }


def _row(index, state="compliant_success"):
    return {"domain": "airline", "task_id": "1", "rollout_index": index, "state": state, "task_success": state.endswith("success"), "compliant": state.startswith("compliant")}


class V12ContractTests(unittest.TestCase):
    def test_seed_and_matched_lineage_are_k3_deterministic(self):
        seeds = derive_rollout_seeds(200, 1000)
        self.assertEqual(seeds, (1200, 1201, 1202))
        self.assertEqual(len(set(seeds)), 3)
        self.assertEqual(seeds, derive_rollout_seeds(200, 1000))
        replay = matched_replay_plan(["airline:1", "retail:2"], 200)
        self.assertEqual(replay["parent"], replay["candidate"])
        self.assertEqual(len(replay["parent"]), 6)
        self.assertEqual({x["rollout_index"] for x in replay["parent"]}, {1, 2, 3})

    def test_dry_plan_and_holdout_budget(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        plan = build_campaign_dry_plan(campaign, batch_map)
        self.assertEqual([len(step["parent_units"]) for step in plan["steps"]], [60, 60, 60])
        self.assertEqual([step["maximum_parent_diagnosis_calls"] for step in plan["steps"]], [20, 20, 20])
        self.assertEqual(plan["computed_budget"], campaign["budget"])
        holdout = build_holdout_plan(campaign, batch_map, campaign["initial_parent"])
        self.assertEqual(len(holdout["s0_units"]), 120)
        self.assertEqual(holdout["s0_units"], holdout["s_final_units"])
        self.assertEqual(holdout["trajectory_count"], 240)

    def test_group_requires_exact_distinct_three(self):
        self.assertEqual(len(group_task_evidence(_group())), 1)
        with self.assertRaisesRegex(ValueError, "EXACTLY_THREE"):
            group_task_evidence(_group()[:2])
        duplicate = (_experience(rollout_index=1), _experience(rollout_index=1), _experience(rollout_index=3))
        with self.assertRaisesRegex(ValueError, "ROLLOUT_INDEX"):
            group_task_evidence(duplicate)

    def test_rollout_aware_evidence_refs_and_policy_lineage(self):
        diagnosis = _diagnosis()
        self.assertEqual(validate_diagnosis(diagnosis, experiences=_group(), skill_sections={"Planning and navigation": []}), ())
        diagnosis["cross_rollout_analysis"]["support_evidence_refs"][0]["source_id"] = "missing"
        self.assertIn("SUPPORT_EVIDENCE_SOURCE_NOT_FOUND", validate_diagnosis(diagnosis, experiences=_group(), skill_sections={"Planning and navigation": []}))
        diagnosis = _diagnosis()
        diagnosis["cross_rollout_analysis"]["support_evidence_refs"][0]["step_ids"] = [999]
        self.assertIn("SUPPORT_EVIDENCE_STEP_NOT_FOUND", validate_diagnosis(diagnosis, experiences=_group(), skill_sections={"Planning and navigation": []}))
        diagnosis = _diagnosis()
        diagnosis["repair_policy_ids"] = ["invented"]
        self.assertIn("POLICY_ID_NOT_IN_EVIDENCE", validate_diagnosis(diagnosis, experiences=_group(), skill_sections={"Planning and navigation": []}))

    def test_diagnosis_target_contract(self):
        sections = {"Planning and navigation": [{"rule_id": "rule_001", "clause": "x"}]}
        add = _diagnosis(relevance="update", action="add", category="skill_issue", problem="unsupported inference")
        self.assertEqual(validate_diagnosis(add, experiences=_group(), skill_sections=sections), ())
        add["update_recommendation"]["target_rule_id"] = "rule_001"
        self.assertIn("ADD_MUST_NOT_TARGET_RULE", validate_diagnosis(add, experiences=_group(), skill_sections=sections))
        replace = _diagnosis(relevance="update", action="replace", category="skill_issue", section="Planning and navigation", rule_id="rule_001")
        self.assertEqual(validate_diagnosis(replace, experiences=_group(), skill_sections=sections), ())
        replace["update_recommendation"]["target_rule_id"] = "rule_999"
        self.assertIn("TARGET_RULE_ID_NOT_FOUND", validate_diagnosis(replace, experiences=_group(), skill_sections=sections))
        none = _diagnosis()
        none["update_recommendation"]["action"] = "add"
        self.assertIn("NON_UPDATE_RELEVANCE_ACTION_MISMATCH", validate_diagnosis(none, experiences=_group(), skill_sections=sections))

    def test_prompts_encode_no_majority_and_minimal_generalization(self):
        combined = DIAGNOSIS_SYSTEM_PROMPT + EDITOR_SYSTEM_PROMPT
        self.assertIn("never majority voting", combined)
        self.assertIn("counterevidence", combined)
        self.assertIn("mechanism-level", combined)
        self.assertIn("ordering constraint", combined)
        self.assertNotIn("PARTIALLY_FIXED", combined)
        self.assertIn('{"source_id":"step_001_airline_5_rollout_01","step_ids":[22]}', DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn('Never put "skill_issue", "add", "replace", "delete", or', DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn('"skill_update_relevance":"update"', DIAGNOSIS_SYSTEM_PROMPT)
        self.assertIn("Every step_ids value is an integer array", DIAGNOSIS_SYSTEM_PROMPT)

    def test_any_invalid_diagnosis_fails_the_batch_and_preserves_raw(self):
        parent = (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text().replace("# Operational Skill", "# SuiteCRM Operational Skill")
        raw = _diagnosis()
        raw["cross_rollout_analysis"]["support_evidence_refs"] = [
            {"source_id": "step_001_airline_1_rollout_01", "step_id": 2}
        ]
        response = _tag(raw)
        with self.assertRaises(DiagnosisContractError) as captured:
            MultiRolloutDiagnosisProposalOperator().propose(
                ProposalContext("candidate", parent, _group()),
                lambda request: response,
                lambda request: self.fail("Editor must not run"),
            )
        self.assertEqual(captured.exception.invalid_diagnosis_ids, ("diagnosis_001",))
        self.assertEqual(captured.exception.validations[0].raw_response, response)

    def test_editor_merges_adds_and_preserves_provenance(self):
        parent = (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text().replace("# Operational Skill", "# SuiteCRM Operational Skill")
        evidence = tuple([*_group("airline", "1"), *_group("retail", "2")])
        calls = []
        def diagnose(request):
            value = _diagnosis(relevance="update", action="add", category="skill_issue", problem="unsupported inference")
            value["cross_rollout_analysis"]["support_evidence_refs"] = [{"source_id": request.rollouts[0]["source_id"], "step_ids": [2]}]
            return _tag(value)
        def editor(request):
            calls.append(request)
            return "<CANONICAL_EDITS_JSON>" + json.dumps([_edit(["diagnosis_001", "diagnosis_002"])]) + "</CANONICAL_EDITS_JSON>"
        decision = MultiRolloutDiagnosisProposalOperator().propose(ProposalContext("candidate", parent, evidence), diagnose, editor)
        self.assertEqual(decision.diagnosis_calls, 2)
        self.assertEqual(decision.editor_calls, 1)
        self.assertEqual(len(decision.applied_edits), 1)
        applied = decision.applied_edits[0]
        self.assertEqual(applied["canonical_edit_id"], "canonical_edit_001")
        self.assertEqual(set(applied["derived_from_patch_ids"]), {"diagnosis_001", "diagnosis_002"})
        self.assertEqual(set(applied["source_ids"]), {item["source_id"] for item in evidence})
        self.assertIsNotNone(applied["verification_target"])

    def test_add_merge_guard_and_replace_drift_guard(self):
        parent = (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text().replace("# Operational Skill", "# SuiteCRM Operational Skill")
        evidence = tuple(_experience(rollout_index=index, state="violating_failure", policy_id="policy_secret") for index in (1, 2, 3))
        def diagnose(request):
            value = _diagnosis(relevance="update", action="add", category="skill_issue", problem="unsupported inference")
            value["repair_policy_ids"] = ["policy_secret"]
            return _tag(value)
        def bad_editor(request):
            edit = _edit(["diagnosis_001"])
            edit["text"] = "Always follow policy_secret."
            return "<CANONICAL_EDITS_JSON>" + json.dumps([edit]) + "</CANONICAL_EDITS_JSON>"
        decision = MultiRolloutDiagnosisProposalOperator().propose(ProposalContext("candidate", parent, evidence), diagnose, bad_editor)
        self.assertEqual(decision.proposal_status, "NO_CANDIDATE")
        self.assertEqual(decision.excluded_edits[0]["reason"], "INVALID_EDIT_FORMAT")

        recipe_decision = MultiRolloutDiagnosisProposalOperator().propose(
            ProposalContext("candidate", parent, _group()),
            lambda request: _tag(_diagnosis(relevance="update", action="add", category="skill_issue", problem="unsupported inference")),
            lambda request: "<CANONICAL_EDITS_JSON>" + json.dumps([_edit(["diagnosis_001"], "Enter the first field then the second field.")]) + "</CANONICAL_EDITS_JSON>",
        )
        self.assertEqual(recipe_decision.proposal_status, "NO_CANDIDATE")

        parent_with_rule = parent.replace("## Planning and navigation\n", "## Planning and navigation\n\n- Check available evidence.\n", 1)
        def replace_diagnosis(request):
            return _tag(_diagnosis(relevance="update", action="replace", category="skill_issue", section="Planning and navigation", rule_id="rule_001", problem="weak verification"))
        def drifting_editor(request):
            edit = _edit(["diagnosis_001"])
            edit.update({"operation": "replace", "section": "Execution patterns", "target_rule_id": "rule_001"})
            return "<CANONICAL_EDITS_JSON>" + json.dumps([edit]) + "</CANONICAL_EDITS_JSON>"
        drift = MultiRolloutDiagnosisProposalOperator().propose(ProposalContext("candidate", parent_with_rule, _group()), replace_diagnosis, drifting_editor)
        self.assertEqual(drift.proposal_status, "NO_CANDIDATE")

    def test_distinct_behavioral_mechanisms_can_remain_separate(self):
        parent = (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text().replace("# Operational Skill", "# SuiteCRM Operational Skill")
        evidence = tuple([*_group("airline", "1"), *_group("retail", "2")])
        def diagnose(request):
            problem = "unsupported inference" if request.task_context["domain"] == "airline" else "premature termination"
            value = _diagnosis(relevance="update", action="add", category="skill_issue", problem=problem)
            value["cross_rollout_analysis"]["support_evidence_refs"] = [{"source_id": request.rollouts[0]["source_id"], "step_ids": [2]}]
            return _tag(value)
        def editor(request):
            first = _edit(["diagnosis_001"])
            second = _edit(["diagnosis_002"], "Continue until the final requested state is verified or a clear blocker is established.")
            second["section"] = "Error recovery and stopping"
            second["verification_target"] = {"problem": "premature termination", "trigger_condition": "when the goal requires multiple subgoals", "expected_behavior": "continue until final state or explicit blocker"}
            return "<CANONICAL_EDITS_JSON>" + json.dumps([first, second]) + "</CANONICAL_EDITS_JSON>"
        decision = MultiRolloutDiagnosisProposalOperator().propose(ProposalContext("candidate", parent, evidence), diagnose, editor)
        self.assertEqual(len(decision.applied_edits), 2)

    def test_target_fix_three_state_contract(self):
        fixed = {"status": "FIXED", "reason": "direct", "exercised_evidence_refs": [{"source_id": "c1", "step_ids": [1]}], "fix_evidence_refs": [{"source_id": "c1", "step_ids": [2]}], "recurrence_evidence_refs": []}
        recurrence = {"status": "NOT_FIXED", "reason": "recurred", "exercised_evidence_refs": [{"source_id": "c1", "step_ids": [1]}], "fix_evidence_refs": [], "recurrence_evidence_refs": [{"source_id": "c1", "step_ids": [2]}]}
        absent = {"status": "NOT_EXERCISED", "reason": "no opportunity", "exercised_evidence_refs": [], "fix_evidence_refs": [], "recurrence_evidence_refs": []}
        for value in (fixed, recurrence, absent):
            tagged = "<TARGETED_FIX_JSON>" + json.dumps(value) + "</TARGETED_FIX_JSON>"
            self.assertEqual(parse_targeted_fix_response(tagged)["status"], value["status"])
        fixed["fix_evidence_refs"] = []
        with self.assertRaisesRegex(ValueError, "DIRECT_FIX"):
            parse_targeted_fix_response("<TARGETED_FIX_JSON>" + json.dumps(fixed) + "</TARGETED_FIX_JSON>")
        absent["exercised_evidence_refs"] = [{"source_id": "c1", "step_ids": [1]}]
        with self.assertRaisesRegex(ValueError, "MUST_NOT_CLAIM"):
            parse_targeted_fix_response("<TARGETED_FIX_JSON>" + json.dumps(absent) + "</TARGETED_FIX_JSON>")

    def test_target_fix_prompt_has_exact_ref_examples_and_self_check(self):
        self.assertIn(
            '{"source_id":"step_001_airline_7_rollout_01","step_ids":[22]}',
            TARGETED_FIX_SYSTEM_PROMPT,
        )
        self.assertIn('{"source_id":"...","step_id":22}', TARGETED_FIX_SYSTEM_PROMPT)
        self.assertIn("Before returning, verify", TARGETED_FIX_SYSTEM_PROMPT)
        self.assertIn("positive\n  integer step IDs", TARGETED_FIX_SYSTEM_PROMPT)
        self.assertIn("valid_step_ids", TARGETED_FIX_SYSTEM_PROMPT)
        self.assertIn("successful state-changing tool result", TARGETED_FIX_SYSTEM_PROMPT)
        self.assertIn("must agree with, rather than contradict", TARGETED_FIX_SYSTEM_PROMPT)

    def test_target_fix_prompt_lists_valid_candidate_steps(self):
        request = TargetedFixRequest(
            canonical_edit={
                "canonical_edit_id": "canonical_edit_001",
                "verification_target": {
                    "problem": "p", "trigger_condition": "t", "expected_behavior": "e",
                },
            },
            supporting_diagnoses=(),
            matched_replays=({
                "diagnosis_id": "diagnosis_001",
                "parent_rollouts": [],
                "candidate_rollouts": [{
                    "source_id": "step_002_airline_33_rollout_03",
                    "trajectory": {"actions": [{"step": 1}, {"step": 28}]},
                }],
            },),
        )
        _, user = build_targeted_fix_prompts(request)
        payload = json.loads(user.split("\n", 1)[1])
        candidate = payload["matched_replays"][0]["candidate_rollouts"][0]
        self.assertEqual(candidate["valid_step_ids"], [1, 28])
        self.assertNotIn(29, candidate["valid_step_ids"])

    def test_target_fix_error_preserves_raw_response_and_edit_id(self):
        raw = '<TARGETED_FIX_JSON>{"status":"FIXED","reason":"x","exercised_evidence_refs":[{"source_id":"c1","step_id":1}],"fix_evidence_refs":[],"recurrence_evidence_refs":[]}</TARGETED_FIX_JSON>'
        request = TargetedFixRequest(
            canonical_edit={
                "canonical_edit_id": "canonical_edit_005",
                "verification_target": {
                    "problem": "p", "trigger_condition": "t", "expected_behavior": "e",
                },
            },
            supporting_diagnoses=(),
            matched_replays=(),
        )
        with self.assertRaises(TargetedFixResponseError) as captured:
            parse_targeted_fix_response(raw, request=request)
        self.assertEqual(captured.exception.code, "INVALID_TARGETED_FIX_EVIDENCE")
        self.assertEqual(captured.exception.raw_response, raw)
        self.assertEqual(captured.exception.canonical_edit_id, "canonical_edit_005")

    def test_gate_requires_every_edit_fixed_and_rate_collapse_is_strict(self):
        edits = [{"canonical_edit_id": "canonical_edit_001"}]
        parent = [_row(i) for i in (1, 2, 3)]
        fixed = [{"canonical_edit_id": "canonical_edit_001", "status": "FIXED"}]
        decision = build_evolution_decision(applied_canonical_edits=edits, targeted_fix_results=fixed, regression_diagnoses=[], parent_rows=parent, candidate_rows=copy.deepcopy(parent))
        self.assertEqual(decision["decision"], "ACCEPT")
        for status, reason in (("NOT_FIXED", "TARGET_NOT_FIXED"), ("NOT_EXERCISED", "TARGET_NOT_EXERCISED")):
            result = [{"canonical_edit_id": "canonical_edit_001", "status": status}]
            rejected = build_evolution_decision(applied_canonical_edits=edits, targeted_fix_results=result, regression_diagnoses=[], parent_rows=parent, candidate_rows=copy.deepcopy(parent))
            self.assertIn(reason, rejected["all_reasons"])
        regression = build_evolution_decision(applied_canonical_edits=edits, targeted_fix_results=fixed, regression_diagnoses=[{"attribution": "CHANGE_CAUSED"}], parent_rows=parent, candidate_rows=copy.deepcopy(parent))
        self.assertIn("CHANGE_CAUSED_REGRESSION", regression["all_reasons"])
        parent20 = [_row(i) for i in range(1, 21)]
        candidate17 = [_row(i, "compliant_failure" if i <= 3 else "compliant_success") for i in range(1, 21)]
        boundary = build_evolution_decision(applied_canonical_edits=edits, targeted_fix_results=fixed, regression_diagnoses=[], parent_rows=parent20, candidate_rows=candidate17)
        self.assertIn("AGGREGATE_COLLAPSE", boundary["all_reasons"])
        candidate18 = [_row(i, "compliant_failure" if i <= 2 else "compliant_success") for i in range(1, 21)]
        safe = build_evolution_decision(applied_canonical_edits=edits, targeted_fix_results=fixed, regression_diagnoses=[], parent_rows=parent20, candidate_rows=candidate18)
        self.assertEqual(safe["decision"], "ACCEPT")

    def test_regression_remains_pair_level_across_k3(self):
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *args, **kwargs: None
        sys.modules.setdefault("dotenv", dotenv)
        from src.skill_evolution.regression_diagnosis_v11 import build_regression_transition_report

        parent = [_row(1, "compliant_failure"), _row(2, "compliant_failure"), _row(3, "compliant_success")]
        candidate = [_row(1, "compliant_success"), _row(2, "compliant_success"), _row(3, "compliant_failure")]
        report = build_regression_transition_report(parent, candidate)
        self.assertEqual(len(report["transitions"]), 3)
        self.assertEqual(len(report["regression_set"]), 1)
        self.assertEqual(report["regression_set"][0]["rollout_index"], 3)


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
                governed = {"state": "compliant_failure", "task_success": False, "process_feedback": {"compliant": True, "violated_policies": []}, "actions": [{"step": 1, "actor": "agent", "content": "done"}]}
                path.write_text(json.dumps({"domain": domain, "task_id": task_id, "rollout_index": index, "rollout_seed": seed, "state": "compliant_failure", "task_evaluation": {"success": False}, "compliance_evaluation": {"compliant": True}, "governed_evidence": governed}))
                paths.append(path)
        return paths


class V12IntegrationTests(unittest.TestCase):
    def test_20_tasks_make_60_rollouts_and_20_diagnoses_per_step(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend, diagnosis_calls = _FakeBackend(root / "rollouts"), []
            def diagnose(request):
                diagnosis_calls.append(request)
                value = _diagnosis()
                value["cross_rollout_analysis"]["support_evidence_refs"] = [{"source_id": request.rollouts[0]["source_id"], "step_ids": [1]}]
                return _tag(value)
            report = run_v12_campaign(campaign, batch_map, backend=backend, diagnoser=diagnose, editor=lambda request: self.fail("editor must not run"), artifact_root=root / "artifacts")
            self.assertEqual(len(diagnosis_calls), 60)
            self.assertTrue(all(len(request.rollouts) == 3 for request in diagnosis_calls))
            self.assertEqual(backend.calls, [("step_001_parent", 60), ("step_002_parent", 60), ("step_003_parent", 60)])
            self.assertEqual([step["decision"] for step in report["steps"]], ["NO_CANDIDATE"] * 3)

    def test_resume_rejects_v11_state(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        with self.assertRaisesRegex(ValueError, "v0.12 resume protocol"):
            run_v12_campaign(campaign, batch_map, backend=object(), resume_state={"protocol_version": "autonomous_gse_v11"})

    def test_runtime_persists_diagnosis_contract_error_and_stops(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = _FakeBackend(root / "rollouts")
            malformed = _diagnosis()
            malformed["cross_rollout_analysis"]["support_evidence_refs"] = [
                {"source_id": "wrong", "step_id": 1}
            ]
            raw = _tag(malformed)
            with self.assertRaises(DiagnosisContractError):
                run_v12_campaign(
                    campaign,
                    batch_map,
                    backend=backend,
                    diagnoser=lambda request: raw,
                    editor=lambda request: self.fail("Editor must not run"),
                    artifact_root=root / "artifacts",
                )
            error = _load(root / "artifacts/diagnosis_contract_error.json")
            self.assertEqual(error["error_code"], "DIAGNOSIS_CONTRACT_ERROR")
            self.assertEqual(error["step"], 1)
            self.assertEqual(len(error["invalid_diagnosis_ids"]), 20)
            self.assertEqual(error["diagnoses"][0]["raw_response"], raw)
            self.assertFalse((root / "artifacts/resume_state.json").exists())

    def test_merged_canonical_edit_gets_one_target_fix_call(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *args, **kwargs: None
        sys.modules.setdefault("dotenv", dotenv)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend, diagnosis_count, target_calls = _FakeBackend(root / "rollouts"), 0, []
            def diagnose(request):
                nonlocal diagnosis_count
                diagnosis_count += 1
                if diagnosis_count == 1:
                    value = _diagnosis(relevance="update", action="add", category="skill_issue", problem="unsupported inference")
                else:
                    value = _diagnosis()
                value["cross_rollout_analysis"]["support_evidence_refs"] = [{"source_id": request.rollouts[0]["source_id"], "step_ids": [1]}]
                return _tag(value)
            def editor(request):
                return "<CANONICAL_EDITS_JSON>" + json.dumps([_edit(["diagnosis_001"])]) + "</CANONICAL_EDITS_JSON>"
            def targeted(request):
                target_calls.append(request)
                return {"canonical_edit_id": request.canonical_edit["canonical_edit_id"], "status": "FIXED", "reason": "direct", "exercised_evidence_refs": [], "fix_evidence_refs": [], "recurrence_evidence_refs": []}
            report = run_v12_campaign(campaign, batch_map, backend=backend, diagnoser=diagnose, editor=editor, targeted_fix_judge=targeted, regression_judge=lambda request: self.fail("no regression pair expected"), artifact_root=root / "artifacts")
            self.assertEqual(len(target_calls), 1)
            self.assertEqual(target_calls[0].canonical_edit["canonical_edit_id"], "canonical_edit_001")
            self.assertEqual(len(target_calls[0].matched_replays), 1)
            self.assertEqual(len(target_calls[0].matched_replays[0]["parent_rollouts"]), 3)
            self.assertEqual(len(target_calls[0].matched_replays[0]["candidate_rollouts"]), 3)
            self.assertEqual(report["steps"][0]["decision"], "ACCEPT")

    def test_target_fix_failure_persists_raw_response_and_completed_results(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *args, **kwargs: None
        sys.modules.setdefault("dotenv", dotenv)
        with tempfile.TemporaryDirectory() as directory:
            artifact_root = Path(directory) / "formal"
            backend = _FakeBackend(artifact_root / "rollouts/train")
            diagnosis_count = 0

            def diagnose(request):
                nonlocal diagnosis_count
                diagnosis_count += 1
                value = _diagnosis(
                    relevance="update" if diagnosis_count == 1 else "none",
                    action="add" if diagnosis_count == 1 else "none",
                    category="skill_issue" if diagnosis_count == 1 else None,
                    problem="unsupported inference" if diagnosis_count == 1 else "",
                )
                value["cross_rollout_analysis"]["support_evidence_refs"] = [{
                    "source_id": request.rollouts[0]["source_id"], "step_ids": [1],
                }]
                return _tag(value)

            def editor(request):
                return "<CANONICAL_EDITS_JSON>" + json.dumps([
                    _edit(["diagnosis_001"])
                ]) + "</CANONICAL_EDITS_JSON>"

            raw = '<TARGETED_FIX_JSON>{"status":"FIXED","reason":"x","exercised_evidence_refs":[{"source_id":"bad","step_id":1}],"fix_evidence_refs":[],"recurrence_evidence_refs":[]}</TARGETED_FIX_JSON>'

            def invalid_target(request):
                raise TargetedFixResponseError(
                    "INVALID_TARGETED_FIX_EVIDENCE",
                    raw,
                    canonical_edit_id=request.canonical_edit["canonical_edit_id"],
                )

            with self.assertRaises(TargetedFixResponseError):
                run_v12_campaign(
                    campaign,
                    batch_map,
                    backend=backend,
                    diagnoser=diagnose,
                    editor=editor,
                    targeted_fix_judge=invalid_target,
                    regression_judge=lambda request: self.fail("regression must not run"),
                    artifact_root=artifact_root,
                )

            error = _load(artifact_root / "targeted_fix_error.json")
            self.assertEqual(error["canonical_edit_id"], "canonical_edit_001")
            self.assertEqual(error["error_code"], "INVALID_TARGETED_FIX_EVIDENCE")
            self.assertEqual(error["raw_response"], raw)
            self.assertEqual(error["completed_targeted_fix_results"], [])
            partial = _load(artifact_root / "steps/step_001/targeted_fix_report.json")
            self.assertFalse(partial["complete"])

    def test_step_1_reevaluation_reuses_rollouts_diagnoses_and_regressions(self):
        campaign, batch_map = _load(MANIFEST), _load(BATCH_MAP)
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *args, **kwargs: None
        sys.modules.setdefault("dotenv", dotenv)
        with tempfile.TemporaryDirectory() as directory:
            artifact_root = Path(directory) / "formal"
            backend = _FakeBackend(artifact_root / "rollouts/train")
            diagnosis_count = 0
            editor_count = 0

            def diagnose(request):
                nonlocal diagnosis_count
                diagnosis_count += 1
                first_in_step = (diagnosis_count - 1) % 20 == 0
                value = _diagnosis(
                    relevance="update" if first_in_step else "none",
                    action="add" if first_in_step else "none",
                    category="skill_issue" if first_in_step else None,
                    problem="unsupported inference" if first_in_step else "",
                )
                value["cross_rollout_analysis"]["support_evidence_refs"] = [{
                    "source_id": request.rollouts[0]["source_id"], "step_ids": [1],
                }]
                return _tag(value)

            def editor(request):
                nonlocal editor_count
                editor_count += 1
                text = (
                    "Verify claims against available evidence before asserting them."
                    if editor_count == 1
                    else "Continue until the requested final state is verified or a blocker is established."
                )
                return "<CANONICAL_EDITS_JSON>" + json.dumps([
                    _edit(["diagnosis_001"], text)
                ]) + "</CANONICAL_EDITS_JSON>"

            def initial_target(request):
                source_id = request.matched_replays[0]["candidate_rollouts"][0]["source_id"]
                if source_id.startswith("step_002_"):
                    raise TargetedFixResponseError(
                        "TARGETED_FIX_EVIDENCE_NOT_FOUND", "bad step",
                        canonical_edit_id=request.canonical_edit["canonical_edit_id"],
                    )
                return {
                    "canonical_edit_id": request.canonical_edit["canonical_edit_id"],
                    "status": "FIXED", "reason": "direct",
                    "exercised_evidence_refs": [], "fix_evidence_refs": [],
                    "recurrence_evidence_refs": [],
                }

            with self.assertRaises(TargetedFixResponseError):
                run_v12_campaign(
                    campaign, batch_map, backend=backend, diagnoser=diagnose,
                    editor=editor, targeted_fix_judge=initial_target,
                    regression_judge=lambda request: self.fail("no regressions expected"),
                    artifact_root=artifact_root,
                )
            calls_before = copy.deepcopy(backend.calls)
            diagnoses_before = diagnosis_count

            def rejudge(request):
                return {
                    "canonical_edit_id": request.canonical_edit["canonical_edit_id"],
                    "status": "NOT_FIXED", "reason": "recurrence",
                    "exercised_evidence_refs": [], "fix_evidence_refs": [],
                    "recurrence_evidence_refs": [],
                }

            report = reevaluate_v12_step_1_target_fix_and_gate(
                campaign, batch_map, targeted_fix_judge=rejudge,
                artifact_root=artifact_root,
            )
            self.assertEqual(backend.calls, calls_before)
            self.assertEqual(diagnosis_count, diagnoses_before)
            self.assertEqual(report["reused"], {
                "parent_rollouts": 60, "candidate_rollouts": 60,
                "diagnoses": 20, "canonical_edits": 1,
                "regression_diagnoses": 0,
            })
            self.assertEqual(report["step"]["decision"], "REJECT")
            resume = _load(artifact_root / "resume_state.json")
            self.assertEqual(resume["current_parent"]["version"], "S0")
            self.assertTrue((artifact_root / "steps/step_001/targeted_fix_report.before_prompt_grounding.json").exists())
            self.assertTrue((artifact_root / "steps/step_001/evolution_decision.before_prompt_grounding.json").exists())

if __name__ == "__main__":
    unittest.main()
