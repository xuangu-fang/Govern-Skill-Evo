"""Validate the frozen v18 Skill-critical Joint Family admission contract."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "experiments/configs/v18_joint_family_admission_001"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads((FREEZE / "manifest.json").read_text(encoding="utf-8"))
    contract_path = FREEZE / "admission_contract.json"
    if digest(Path(__file__)) != manifest["validator_sha256"]:
        raise ValueError("Joint Family admission validator changed")
    if digest(contract_path) != manifest["admission_contract_sha256"]:
        raise ValueError("Frozen Joint Family admission contract changed")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["contract_id"] != "v18-joint-family-admission-1":
        raise ValueError("Unexpected Joint Family admission contract")
    if set(contract["conditions"]) != {"E0", "E_CAP", "E_GOV", "E_JOINT"}:
        raise ValueError("Four matched Skill conditions are required")
    quadrants = set(contract["gate_0_structural_orthogonality"]["required_paths_per_candidate"].values())
    if quadrants != {"CS", "CF", "VS", "VF"}:
        raise ValueError("Gate 0 must require all four quadrants")
    for gate in ("gate_1_mechanism_screen", "gate_2_family_admission"):
        value = contract[gate]
        if "e0_dual_headroom" not in " ".join(value):
            raise ValueError(f"{gate} lacks E0 Dual Headroom")
        if not any(key.startswith("paired_axis_separability") for key in value):
            raise ValueError(f"{gate} lacks ablation or Joint repair requirements")
        if not any(key.startswith("joint_repair") for key in value):
            raise ValueError(f"{gate} lacks Joint repair requirements")
    print(json.dumps({
        "status": "VALID",
        "contract_id": contract["contract_id"],
        "admission_contract_sha256": manifest["admission_contract_sha256"],
        "model_calls": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
