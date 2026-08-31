from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.adapters.tau2 import tau3_compliance_judge_v13 as compliance_v13
from src.learners.stwebagentbench import generate_governed_skill_v13 as editor_v13
from src.skill_evolution import autonomous_gse_v13_proposal as proposal_v13
from src.skill_evolution import diagnosis_contract_v13
from src.skill_evolution import diagnosis_v13
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_DIR = ROOT / "experiments/campaigns/autonomous_gse_v14"
MANIFEST = CAMPAIGN_DIR / "campaign_manifest.json"
BATCH_MAP = CAMPAIGN_DIR / "batch_map.json"
V13_DIR = ROOT / "experiments/campaigns/autonomous_gse_v13"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def campaign():
    return _load(MANIFEST)


@pytest.fixture
def batch_map():
    return _load(BATCH_MAP)


def _evidence(task_ids: list[str]) -> tuple[dict, ...]:
    result = []
    for tagged in task_ids:
        domain, task_id = tagged.split(":", 1)
        for rollout_index in (1, 2, 3):
            result.append({
                "source_id": f"{domain}_{task_id}_{rollout_index}",
                "domain": domain, "task_id": task_id,
                "rollout_index": rollout_index,
            })
    return tuple(result)


class TestV14LearnerParity:
    def test_compliance_judge_is_the_v13_implementation(self):
        assert v14.judge_compliance is compliance_v13.judge_compliance
        assert v14.compliance_v13.JUDGE_SYSTEM_PROMPT is compliance_v13.JUDGE_SYSTEM_PROMPT

    def test_diagnosis_and_contract_are_the_v13_implementations(self):
        assert v14.call_diagnosis is diagnosis_v13.call_diagnosis
        assert v14.MultiRolloutDiagnosisRequest is diagnosis_v13.MultiRolloutDiagnosisRequest
        assert v14.diagnosis_contract_v13.DIAGNOSIS_FIELDS is diagnosis_contract_v13.DIAGNOSIS_FIELDS
        assert v14.diagnosis_contract_v13.EVIDENCE_PATTERNS == {
            "contrastive", "recurrent", "insufficient",
        }

    def test_proposal_operator_and_editor_are_the_v13_implementations(self):
        assert v14.MultiRolloutDiagnosisProposalOperator is proposal_v13.MultiRolloutDiagnosisProposalOperator
        assert isinstance(v14.V13_PROPOSAL_OPERATOR, proposal_v13.MultiRolloutDiagnosisProposalOperator)
        assert v14.DiagnosisEditorRequest is proposal_v13.DiagnosisEditorRequest
        assert v14.call_governed_editor is editor_v13.call_governed_editor

    def test_editor_canonical_contract_and_verification_target_do_not_drift(self):
        source = inspect.getsource(proposal_v13._guard_editor_response)
        assert '"verification_target"' in source
        assert v14.proposal_v13._valid_verification_target is proposal_v13._valid_verification_target
        assert proposal_v13._valid_verification_target({
            "problem": "p", "trigger_condition": "t", "expected_behavior": "e",
        })

    def test_v14_adds_no_diagnosis_or_editor_prompt(self):
        runtime_source = inspect.getsource(v14)
        assert "DIAGNOSIS_SYSTEM_PROMPT =" not in runtime_source
        assert "EDITOR_SYSTEM_PROMPT =" not in runtime_source
        assert not (ROOT / "src/skill_evolution/diagnosis_v14.py").exists()
        assert not (ROOT / "src/learners/stwebagentbench/generate_governed_skill_v14.py").exists()
        assert not (ROOT / "src/adapters/tau2/tau3_compliance_judge_v14.py").exists()

    def test_v14_candidate_path_invokes_v13_operator(self, campaign, batch_map):
        context = ProposalContext(
            candidate_id="candidate_001", parent_skill="# Operational Skill",
            current_batch_governed_evidence=_evidence(batch_map["batches"][0]["task_ids"]),
        )
        sentinel = object()
        with patch.object(v14.V13_PROPOSAL_OPERATOR, "propose", return_value=sentinel) as propose:
            result = v14.propose_candidate(
                context, campaign=campaign, batch_map=batch_map, step=1,
                domain_contexts={"airline": {}, "retail": {}},
            )
        assert result is sentinel
        assert propose.call_count == 1
        assert propose.call_args.args[0] is context
        assert propose.call_args.args[1] is diagnosis_v13.call_diagnosis
        assert propose.call_args.args[2] is editor_v13.call_governed_editor


class TestV14FrozenSplit:
    def test_three_balanced_disjoint_evolution_batches(self, campaign, batch_map):
        v14.validate_batch_map(batch_map, campaign)
        batches = [batch["task_ids"] for batch in batch_map["batches"]]
        assert [len(batch) for batch in batches] == [20, 20, 20]
        for batch in batches:
            assert sum(item.startswith("airline:") for item in batch) == 10
            assert sum(item.startswith("retail:") for item in batch) == 10
        assert not set(batches[0]) & set(batches[1])
        assert not set(batches[0]) & set(batches[2])
        assert not set(batches[1]) & set(batches[2])

    def test_monitor_is_explicit_fixed_and_maximally_feasible(self, campaign, batch_map):
        monitor = batch_map["monitor"]
        assert monitor["monitor_id"] == "fixed_monitor_m"
        assert monitor["fixed_across_steps"] is True
        assert monitor["source_split"] == "official_train"
        assert monitor["learning_access"] == "forbidden"
        assert monitor["feedback_to_learner"] == "forbidden"
        assert monitor["execution_enabled"] is False
        assert len(monitor["task_ids"]) == 0
        assert campaign["monitor"]["requested_tasks"] == 20
        assert campaign["monitor"]["capacity_status"] == "insufficient_balanced_official_train_capacity"

    def test_official_pool_proves_balanced_monitor_capacity_is_zero(self, campaign, batch_map):
        pools = v14.load_official_task_pools(ROOT / campaign["benchmark"]["path"])
        assert len(pools["airline"]["official_train"]) == 30
        assert len(pools["retail"]["official_train"]) == 74
        derived = v14.derive_fixed_monitor_assignment(
            campaign_seed=campaign["campaign_seed"], official_pools=pools,
            evolution_assignment=batch_map["assignment"]["evolution"],
        )
        assert derived == {"airline": [], "retail": []}
        assert derived == v14.derive_fixed_monitor_assignment(
            campaign_seed=campaign["campaign_seed"], official_pools=pools,
            evolution_assignment=batch_map["assignment"]["evolution"],
        )

    def test_evolution_monitor_and_test_are_strictly_disjoint(self, campaign, batch_map):
        v14.validate_batch_map(batch_map, campaign)
        batches = [set(value["task_ids"]) for value in batch_map["batches"]]
        monitor = set(batch_map["monitor"]["task_ids"])
        test = {
            *(f"airline:{x}" for x in batch_map["assignment"]["test"]["airline"]),
            *(f"retail:{x}" for x in batch_map["assignment"]["test"]["retail"]),
        }
        groups = [*batches, monitor, test]
        assert all(
            not groups[left] & groups[right]
            for left in range(len(groups)) for right in range(left + 1, len(groups))
        )

    def test_train_test_provenance_matches_official_splits(self, campaign, batch_map):
        pools = v14.load_official_task_pools(ROOT / campaign["benchmark"]["path"])
        assignment = batch_map["assignment"]
        for domain in ("airline", "retail"):
            assert set(assignment["evolution"][domain]) <= set(pools[domain]["official_train"])
            assert set(assignment["monitor"][domain]) <= set(pools[domain]["official_train"])
            assert set(assignment["test"][domain]) <= set(pools[domain]["official_test"])

    @pytest.mark.parametrize("target", ("batch", "monitor", "test"))
    def test_overlap_fails_closed(self, campaign, batch_map, target):
        drifted = copy.deepcopy(batch_map)
        if target == "batch":
            drifted["batches"][1]["task_ids"][0] = drifted["batches"][0]["task_ids"][0]
        elif target == "monitor":
            drifted["assignment"]["monitor"]["airline"] = [
                drifted["assignment"]["evolution"]["airline"][0]
            ]
            drifted["monitor"]["task_ids"] = [drifted["batches"][0]["task_ids"][0]]
        else:
            drifted["assignment"]["test"]["airline"][0] = drifted["assignment"]["evolution"]["airline"][0]
        with pytest.raises(v14.RuntimeContractError):
            v14.validate_batch_map(drifted, campaign)

    def test_v13_batch_map_and_campaign_remain_unchanged(self, batch_map):
        v13_map = _load(V13_DIR / "batch_map.json")
        assert batch_map["assignment"]["evolution"] == v13_map["assignment"]["evolution"]
        assert batch_map["batches"] == v13_map["batches"]
        assert (CAMPAIGN_DIR / "skills/S0_empty_skill.md").read_text() == (
            V13_DIR / "skills/S0_empty_skill.md"
        ).read_text()


class TestV14LearnerIsolationAndPlan:
    def test_monitor_or_test_evidence_cannot_enter_learner(self, campaign, batch_map):
        batch_ids = batch_map["batches"][0]["task_ids"]
        protected = v14._protected_task_ids(batch_map)
        evidence = list(_evidence(batch_ids))
        evidence[0]["domain"], evidence[0]["task_id"] = "airline", batch_map["assignment"]["test"]["airline"][0]
        with pytest.raises(v14.RuntimeContractError, match="Monitor/Test evidence"):
            v14.validate_learner_evidence(
                tuple(evidence), batch_task_ids=batch_ids, protected_task_ids=protected,
            )

    def test_non_current_batch_evidence_cannot_enter_learner(self, batch_map):
        batch_ids = batch_map["batches"][0]["task_ids"]
        evidence = list(_evidence(batch_ids))
        domain, task_id = batch_map["batches"][1]["task_ids"][0].split(":", 1)
        evidence[0]["domain"], evidence[0]["task_id"] = domain, task_id
        with pytest.raises(v14.RuntimeContractError, match="outside the current Evolution batch"):
            v14.validate_learner_evidence(
                tuple(evidence), batch_task_ids=batch_ids,
                protected_task_ids=v14._protected_task_ids(batch_map),
            )

    def test_dry_plan_separates_defined_and_executable_workload(self, campaign, batch_map):
        plan = v14.build_campaign_dry_plan(campaign, batch_map)
        assert [len(step["parent_rollout_units"]) for step in plan["steps"]] == [60, 60, 60]
        workload = plan["workload_summary"]
        assert workload["evolution"]["trajectories"] == 180
        assert workload["monitor"]["requested_trajectories"] == 60
        assert workload["monitor"]["defined_trajectories"] == 0
        assert workload["monitor"]["execution_enabled"] is False
        assert workload["test"]["trajectories_if_explicitly_authorized"] == 240
        assert plan["phase_3_and_later"] == "not_implemented"

    def test_contract_rejects_sampling_drift(self, campaign, batch_map):
        drifted = copy.deepcopy(campaign)
        drifted["agent"]["temperature"] = 0.0
        with pytest.raises(v14.RuntimeContractError, match="agent sampling"):
            v14.validate_batch_map(batch_map, drifted)
