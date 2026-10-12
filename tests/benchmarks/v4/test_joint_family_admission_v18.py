import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FREEZE = ROOT / "experiments/benchmarks/tau2/joint-admission/v18_joint_family_admission_001/config"
FREEZE_V3 = ROOT / "experiments/benchmarks/tau2/joint-admission/v18_joint_family_admission_003/config"
REPLICATION_V1 = ROOT / "benchmarks/tau2_governed_evolution/final_candidate/construction/joint_capability_experience_mapping_v1/replication_v1"


def test_joint_family_admission_freeze_and_core_invariants():
    contract_path = FREEZE / "admission_contract.json"
    contract = json.loads(contract_path.read_text())
    manifest = json.loads((FREEZE / "manifest.json").read_text())
    assert hashlib.sha256(contract_path.read_bytes()).hexdigest() == manifest["admission_contract_sha256"]
    assert set(contract["conditions"]) == {"E0", "E_CAP", "E_GOV", "E_JOINT"}
    assert set(contract["gate_0_structural_orthogonality"]["required_paths_per_candidate"].values()) == {
        "CS", "CF", "VS", "VF",
    }
    for gate_name in ("gate_1_mechanism_screen", "gate_2_family_admission"):
        gate = contract[gate_name]
        assert any(key.startswith("e0_dual_headroom") for key in gate)
        assert any(key.startswith("paired_axis_separability") for key in gate)
        assert any(key.startswith("joint_repair") for key in gate)


def test_reference_conditions_are_true_component_ablations():
    contract = json.loads((FREEZE / "admission_contract.json").read_text())
    assert "Only" in contract["conditions"]["E_CAP"]
    assert "Only" in contract["conditions"]["E_GOV"]
    assert "no additional repair text" in contract["conditions"]["E_JOINT"]
    rules = contract["gate_1_mechanism_screen"]["paired_axis_separability"]
    assert rules["e_cap_governance_violations_remaining_min"] > 0
    assert rules["e_gov_capability_failures_remaining_min"] > 0


def test_joint_family_admission_v3_is_one_seed_task_variant_replication():
    contract_path = FREEZE_V3 / "admission_contract.json"
    contract = json.loads(contract_path.read_text())
    manifest = json.loads((FREEZE_V3 / "manifest.json").read_text())
    design = contract["replication_design"]
    assert hashlib.sha256(contract_path.read_bytes()).hexdigest() == manifest["admission_contract_sha256"]
    assert design["fresh_task_variants_per_split"] == 4
    assert design["seeds_per_task"] == 1
    assert design["predeclared_seeds"] == [11701]
    assert design["total_rollouts"] == 32


def test_fresh_replication_freeze_covers_requested_code_and_preserves_skill_bytes():
    freeze = json.loads(((Path(__file__).resolve().parents[3] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/freeze_manifest.json')).read_text())
    relocations = json.loads((REPLICATION_V1 / "source_relocations.json").read_text())["relocations"]
    assert freeze["status"] == "FROZEN_BEFORE_MODEL_CALLS"
    assert freeze["planned_trajectories"] == 32
    assert set(freeze["code_summary"]) == {"runtime", "fixture", "tools", "evaluator", "replay", "runner"}
    for relative, expected in freeze["files"].items():
        preserved = relocations.get(relative, relative)
        assert hashlib.sha256((ROOT / preserved).read_bytes()).hexdigest() == expected
    capability = ((Path(__file__).resolve().parents[3] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/capability.md')).read_bytes()
    governance = ((Path(__file__).resolve().parents[3] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/governance.md')).read_bytes()
    assert ((Path(__file__).resolve().parents[3] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/joint.md')).read_bytes() == capability + b"\n" + governance
