"""Run one small real-task v0.13 end-to-end integration canary."""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.learners.stwebagentbench.generate_governed_skill_v13 import call_governed_editor
from src.skill_evolution import autonomous_gse_v12_benchmark_runtime as v12
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    EVIDENCE_CONTRACT_VERSION,
    PROTOCOL_VERSION,
    Tau3CampaignRolloutBackend,
    _candidate_edit_provenance,
    _evaluate_candidate_step,
    _rows_and_evidence,
    _write_json,
    load_authoritative_domain_contexts,
)
from src.skill_evolution.autonomous_gse_v13_proposal import (
    DiagnosisContractError,
    MultiRolloutDiagnosisProposalOperator,
)
from src.skill_evolution.diagnosis_v13 import call_diagnosis
from src.skill_evolution.evolution_gate_v11 import aggregate_counts
from src.skill_evolution.targeted_fix_v13 import call_targeted_fix

CAMPAIGN_PATH = REPO_ROOT / "experiments/campaigns/autonomous_gse_v13/campaign_manifest.json"
PARENT_SKILL_PATH = REPO_ROOT / "experiments/campaigns/autonomous_gse_v13/skills/S0_empty_skill.md"
OUTPUT_ROOT = REPO_ROOT / "artifacts/autonomous_gse_v13/canary/end_to_end_current"
TASK_IDS = ["airline:7", "airline:20", "retail:2", "retail:91", "retail:104"]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _states(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["state"] for row in rows)
    metrics = aggregate_counts(rows)
    return {
        **metrics,
        "CS": counts["compliant_success"],
        "CF": counts["compliant_failure"],
        "VS": counts["violating_success"],
        "VF": counts["violating_failure"],
    }


def _pairing(parent_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidate = {
        (row["domain"], row["task_id"], row["rollout_index"]): row
        for row in candidate_rows
    }
    result = []
    for parent in parent_rows:
        key = (parent["domain"], parent["task_id"], parent["rollout_index"])
        after = candidate[key]
        result.append({
            "domain": parent["domain"],
            "task_id": parent["task_id"],
            "rollout_index": parent["rollout_index"],
            "parent_seed": parent["rollout_seed"],
            "candidate_seed": after["rollout_seed"],
            "matched": parent["rollout_seed"] == after["rollout_seed"],
        })
    return result


def _diagnosis_summary(proposal: Any) -> dict[str, Any]:
    roots = Counter()
    patterns = Counter()
    valid = repaired = failed = 0
    for diagnosis in proposal.diagnoses:
        validation = diagnosis["validation"]
        if validation["valid"]:
            valid += 1
        else:
            failed += 1
        structured = diagnosis.get("structured_output") or {}
        roots[str((structured.get("root_cause") or {}).get("category"))] += 1
        patterns[str((structured.get("behavior_analysis") or {}).get("evidence_pattern"))] += 1
        raw = diagnosis.get("raw_response") or ""
        if validation["valid"] and raw.startswith("<DIAGNOSIS_JSON>{"):
            repaired += 1
    axes = Counter()
    eligible = set(proposal.eligible_diagnosis_ids)
    for diagnosis in proposal.diagnoses:
        if diagnosis["diagnosis_id"] in eligible:
            axes[diagnosis["structured_output"]["update_axis"]] += 1
    return {
        "total": len(proposal.diagnoses),
        "valid": valid,
        "deterministically_repaired": repaired,
        "fail_closed": failed,
        "root_cause_distribution": dict(roots),
        "evidence_pattern_distribution": dict(patterns),
        "eligible_updates": len(eligible),
        "eligible_update_axes": dict(axes),
    }


def _edit_summary(edits: list[dict[str, Any]]) -> dict[str, Any]:
    operations = Counter(edit["operation"] for edit in edits)
    return {
        "canonical_edit_count": len(edits),
        "operations": {key: operations[key] for key in ("add", "replace", "delete")},
        "single_source": sum(len(edit["derived_from_diagnosis_ids"]) == 1 for edit in edits),
        "multi_source": sum(len(edit["derived_from_diagnosis_ids"]) > 1 for edit in edits),
        "edits": copy.deepcopy(edits),
    }


def _artifact_check(step_root: Path, candidate_created: bool) -> dict[str, bool]:
    required = {
        "parent_rollouts": OUTPUT_ROOT / "rollouts/train/step_001_parent",
        "diagnoses": step_root / "diagnoses.json",
        "proposal": step_root / "proposal.json",
        "gate_decision": step_root / "evolution_decision.json",
    }
    if candidate_created:
        required.update({
            "canonical_edits": step_root / "candidate_edits.json",
            "candidate_skill": step_root / "candidate_skill.md",
            "candidate_rollouts": OUTPUT_ROOT / "rollouts/train/step_001_candidate_replay",
            "target_fix": step_root / "targeted_fix_report.json",
            "regression": step_root / "regression_diagnoses.json",
            "aggregate": step_root / "aggregate_metrics.json",
        })
    return {name: path.exists() for name, path in required.items()}


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    if (OUTPUT_ROOT / "canary_report.json").exists():
        raise RuntimeError(f"Refusing to overwrite completed canary: {OUTPUT_ROOT}")
    campaign = _load(CAMPAIGN_PATH)
    backend = Tau3CampaignRolloutBackend(campaign, artifact_root=OUTPUT_ROOT)
    contexts = load_authoritative_domain_contexts(REPO_ROOT / campaign["benchmark"]["path"])
    step_root = OUTPUT_ROOT / "steps/step_001"
    step_root.mkdir(parents=True, exist_ok=True)

    print("[1/7] Parent rollouts", flush=True)
    parent_paths = backend.run_batch(
        task_ids=TASK_IDS,
        phase="train",
        skill_version="S0",
        skill_path=None,
        execution_phase="step_001_parent",
    )
    parent_rows, experiences = _rows_and_evidence(parent_paths, step=1)

    proposal_path = step_root / "proposal.json"
    candidate_path = step_root / "candidate_skill.md"
    edits_path = step_root / "candidate_edits.json"
    if proposal_path.exists() and candidate_path.exists() and edits_path.exists():
        print("[2/7] Resume saved Diagnosis and Editor artifacts", flush=True)
        proposal = SimpleNamespace(**_load(proposal_path))
    else:
        print("[2/7] Task-level Diagnosis and Editor", flush=True)
        operator = MultiRolloutDiagnosisProposalOperator()
        try:
            proposal = operator.propose(
                ProposalContext(
                    candidate_id="canary_candidate_001",
                    parent_skill=v12._method_skill(PARENT_SKILL_PATH.read_text(encoding="utf-8")),
                    current_batch_governed_evidence=tuple(experiences),
                ),
                call_diagnosis,
                call_governed_editor,
                domain_contexts=contexts,
            )
        except DiagnosisContractError as error:
            _write_json(step_root / "diagnosis_contract_error.json", {
                "protocol_version": PROTOCOL_VERSION,
                "invalid_diagnosis_ids": list(error.invalid_diagnosis_ids),
                "diagnoses": [item.as_dict() for item in error.validations],
            })
            raise
        _write_json(step_root / "diagnoses.json", {
            "diagnoses": proposal.diagnoses,
            "eligible_diagnosis_ids": proposal.eligible_diagnosis_ids,
        })
        _write_json(proposal_path, copy.deepcopy(proposal.__dict__))

    diagnosis_summary = _diagnosis_summary(proposal)
    if proposal.proposal_status != "CANDIDATE" or proposal.candidate_skill is None:
        decision = {
            "decision": "NO_ELIGIBLE_UPDATE",
            "primary_reason": proposal.proposal_reason,
        }
        _write_json(step_root / "evolution_decision.json", decision)
        report = {
            "schema_version": "autonomous_gse_v13_end_to_end_canary_0.13.0",
            "protocol_version": PROTOCOL_VERSION,
            "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
            "task_ids": TASK_IDS,
            "tasks": len(TASK_IDS),
            "rollouts_per_task": 3,
            "parent": _states(parent_rows),
            "diagnosis": diagnosis_summary,
            "candidate_created": False,
            "gate": decision,
            "artifacts": _artifact_check(step_root, False),
        }
        _write_json(OUTPUT_ROOT / "canary_report.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        return 0

    print("[3/7] Candidate Skill", flush=True)
    if not candidate_path.exists():
        candidate_path.write_text(v12._canonical_skill(proposal.candidate_skill), encoding="utf-8")
    edits = _load(edits_path) if edits_path.exists() else _candidate_edit_provenance(proposal)
    if not edits_path.exists():
        _write_json(edits_path, edits)

    print("[4/7] Matched Candidate replay", flush=True)
    candidate_paths = backend.run_batch(
        task_ids=TASK_IDS,
        phase="train",
        skill_version="S1",
        skill_path=candidate_path,
        execution_phase="step_001_candidate_replay",
    )
    candidate_rows, _ = _rows_and_evidence(candidate_paths, step=1)
    pairing = _pairing(parent_rows, candidate_rows)
    _write_json(step_root / "pairing_audit.json", pairing)

    print("[5/7] Target Fix", flush=True)
    print("[6/7] Regression, aggregate, Gate", flush=True)
    decision = _evaluate_candidate_step(
        root=OUTPUT_ROOT,
        step_root=step_root,
        step_number=1,
        parent_rows=parent_rows,
        candidate_rows=candidate_rows,
        diagnoses=proposal.diagnoses,
        edits=edits,
        targeted_fix_judge=call_targeted_fix,
        regression_judge=None,
        resume_targeted_fix_results=True,
    )

    print("[7/7] Integration report", flush=True)
    transitions = _load(step_root / "regression_transition_report.json")
    regressions = _load(step_root / "regression_diagnoses.json")["diagnoses"]
    targeted = _load(step_root / "targeted_fix_report.json")["results"]
    report = {
        "schema_version": "autonomous_gse_v13_end_to_end_canary_0.13.0",
        "protocol_version": PROTOCOL_VERSION,
        "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
        "task_ids": TASK_IDS,
        "tasks": len(TASK_IDS),
        "rollouts_per_task": 3,
        "parent": _states(parent_rows),
        "diagnosis": diagnosis_summary,
        "editor": _edit_summary(edits),
        "candidate_created": True,
        "pairing": {
            "total": len(pairing),
            "matched": sum(item["matched"] for item in pairing),
            "all_matched": all(item["matched"] for item in pairing),
            "pairs": pairing,
        },
        "candidate": _states(candidate_rows),
        "targeted_fix": targeted,
        "regression": {
            "transition_counts": transitions["transition_counts"],
            "regression_counts": transitions["counts"],
            "diagnoses": regressions,
            "change_caused": sum(
                item["attribution"] == "CHANGE_CAUSED" for item in regressions
            ),
        },
        "aggregate": _load(step_root / "aggregate_metrics.json"),
        "gate": decision,
        "artifacts": _artifact_check(step_root, True),
    }
    _write_json(OUTPUT_ROOT / "canary_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
