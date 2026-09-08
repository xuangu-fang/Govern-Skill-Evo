"""Export the frozen v14 semantic Diagnosis and its evidence isolation audit."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import (
    PROJECT_ROOT,
)


ROOT = PROJECT_ROOT / "artifacts/transition_ablation_step4v/learning"


def main() -> int:
    decision = json.loads((ROOT / "learning_decision.json").read_text(encoding="utf-8"))
    output = {
        "diagnoses": decision.get("diagnoses", []),
        "eligible_diagnosis_ids": decision.get("eligible_diagnosis_ids", []),
        "knowledge_isolation": decision.get("knowledge_isolation", {}),
    }
    path = ROOT / "diagnosis.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": path.as_posix(), **output}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
