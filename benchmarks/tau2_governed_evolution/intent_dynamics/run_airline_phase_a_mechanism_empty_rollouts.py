"""Run the frozen Step 4S suite with the v14 Base Agent and Empty Skill."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.tau2_governed_evolution.intent_dynamics import run_airline_deep_dependency_empty_rollouts as shared
from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_phase_a_mechanisms import MANIFEST_PATH, TASKS_PATH, load_suite, validate_run_contract


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACT_ROOT = PROJECT_ROOT / "artifacts/airline_phase_a_mechanism_step4s"


def main() -> int:
    shared.MANIFEST_PATH = MANIFEST_PATH
    shared.TASKS_PATH = TASKS_PATH
    shared.DEFAULT_ARTIFACT_ROOT = DEFAULT_ARTIFACT_ROOT
    shared.AUDIT_ID = "airline_phase_a_mechanism_expansion_step4s"
    shared.PHASE = "phase_a_procedural_mechanism_expansion"
    shared.SOURCE_PREFIX = "phase_a_mechanism"
    shared.load_suite = load_suite
    shared.validate_run_contract = validate_run_contract
    shared.shared.MANIFEST_PATH = MANIFEST_PATH
    shared.shared.TASKS_PATH = TASKS_PATH
    shared.shared.DEFAULT_ARTIFACT_ROOT = DEFAULT_ARTIFACT_ROOT
    shared.shared.load_suite = load_suite
    shared.shared.validate_run_contract = validate_run_contract
    shared.shared._run_one = shared._run_one
    result = shared.shared.run_audit(artifact_root=DEFAULT_ARTIFACT_ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
