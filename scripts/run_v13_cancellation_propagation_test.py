"""Run one isolated v0.13 downstream propagation test for the saved Cancellation diagnosis."""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.learners.stwebagentbench.generate_governed_skill_v13 import call_governed_editor
from src.learners.stwebagentbench.generate_skill import call_learner
from src.skill_evolution import autonomous_gse_v12_benchmark_runtime as v12
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    Tau3CampaignRolloutBackend,
    _candidate_edit_provenance,
    _evaluate_candidate_step,
    _rows_and_evidence,
    _write_json,
    load_authoritative_domain_contexts,
)
from src.skill_evolution.autonomous_gse_v13_proposal import (
    DiagnosisEditorRequest,
    MultiRolloutDiagnosisProposalOperator,
)
from src.skill_evolution.regression_diagnosis_v11 import (
    LEARNER_MODEL as REGRESSION_MODEL,
    RegressionDiagnosisRequest,
    build_regression_diagnosis_prompts,
    parse_regression_diagnosis_response,
)
from src.skill_evolution.targeted_fix_v13 import (
    LEARNER_MODEL as TARGETED_FIX_MODEL,
    TargetedFixRequest,
    build_targeted_fix_prompts,
    parse_targeted_fix_response,
)

CAMPAIGN_PATH = REPO_ROOT / "experiments/campaigns/autonomous_gse_v13/campaign_manifest.json"
DIAGNOSIS_PATH = REPO_ROOT / (
    "artifacts/autonomous_gse_v13/formal/canaries/"
    "pre_formal_diagnosis_output_contract_real_llm/"
    "cancellation_eligibility/diagnosis.json"
)
OUTPUT_ROOT = REPO_ROOT / (
    "artifacts/autonomous_gse_v13/formal/propagation/"
    "cancellation_known_wrong_diagnosis"
)


def _parent_rows(experiences: tuple[dict, ...]) -> list[dict]:
    return [{
        "source_id": item["source_id"],
        "domain": item["domain"],
        "task_id": str(item["task_id"]),
        "rollout_index": item["rollout_index"],
        "rollout_seed": item["rollout_seed"],
        "task_success": item["task_success"],
        "compliant": item["process_feedback"]["compliant"],
        "state": item["state"],
        "trajectory": copy.deepcopy(item),
    } for item in experiences]


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    campaign = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
    saved_diagnosis = json.loads(DIAGNOSIS_PATH.read_text(encoding="utf-8"))
    request = saved_diagnosis["request"]
    diagnosis_raw = saved_diagnosis["raw_response"]
    experiences = tuple(copy.deepcopy(request["rollouts"]))
    parent_rows = _parent_rows(experiences)
    parent_skill = request["current_parent_skill"]
    domain_contexts = load_authoritative_domain_contexts(
        REPO_ROOT / campaign["benchmark"]["path"]
    )

    _write_json(OUTPUT_ROOT / "input.json", {
        "campaign_path": CAMPAIGN_PATH.as_posix(),
        "saved_diagnosis_path": DIAGNOSIS_PATH.as_posix(),
        "task": "airline:39",
        "parent_rollout_seeds": [row["rollout_seed"] for row in parent_rows],
        "parent_source_ids": [row["source_id"] for row in parent_rows],
        "diagnosis_raw_response": diagnosis_raw,
        "new_parent_rollouts": 0,
    })
    _write_json(OUTPUT_ROOT / "parent_rows.json", {"rows": parent_rows})

    editor_records: list[dict] = []

    def saved_diagnoser(_request: object) -> str:
        return diagnosis_raw

    def recording_editor(editor_request: DiagnosisEditorRequest) -> str:
        response = call_governed_editor(editor_request)
        record = {"request": asdict(editor_request), "raw_response": response}
        editor_records.append(record)
        _write_json(OUTPUT_ROOT / "editor_call.json", record)
        return response

    proposal = MultiRolloutDiagnosisProposalOperator().propose(
        ProposalContext(
            candidate_id="cancellation_propagation_candidate",
            parent_skill=parent_skill,
            current_batch_governed_evidence=experiences,
        ),
        saved_diagnoser,
        recording_editor,
        domain_contexts=domain_contexts,
    )
    _write_json(OUTPUT_ROOT / "proposal.json", copy.deepcopy(proposal.__dict__))
    if proposal.proposal_status != "CANDIDATE" or proposal.candidate_skill is None:
        _write_json(OUTPUT_ROOT / "summary.json", {
            "editor_generated_edit": False,
            "proposal_status": proposal.proposal_status,
            "gate_decision": "REJECT",
            "blocked_at": "EDITOR",
        })
        return

    candidate_path = OUTPUT_ROOT / "candidate_skill.md"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(v12._canonical_skill(proposal.candidate_skill), encoding="utf-8")
    edits = _candidate_edit_provenance(proposal)
    _write_json(OUTPUT_ROOT / "candidate_edits.json", edits)

    backend = Tau3CampaignRolloutBackend(campaign, artifact_root=OUTPUT_ROOT)
    candidate_paths = backend.run_batch(
        task_ids=["airline:39"],
        phase="train",
        skill_version="S1",
        skill_path=candidate_path,
        execution_phase="matched_candidate_replay",
    )
    candidate_rows, _ = _rows_and_evidence(candidate_paths, step=1)
    _write_json(OUTPUT_ROOT / "candidate_rows.json", {"rows": candidate_rows})

    targeted_calls: list[dict] = []

    def recording_targeted_fix(targeted_request: TargetedFixRequest) -> dict:
        system, user = build_targeted_fix_prompts(targeted_request)
        raw, model, usage = call_learner(TARGETED_FIX_MODEL, system, user, temperature=0.0)
        record = {
            "request": asdict(targeted_request),
            "raw_response": raw,
            "resolved_model": model,
            "usage": usage,
        }
        targeted_calls.append(record)
        _write_json(OUTPUT_ROOT / f"targeted_fix_call_{len(targeted_calls):02d}.json", record)
        return parse_targeted_fix_response(raw, request=targeted_request)

    regression_calls: list[dict] = []

    def recording_regression(regression_request: RegressionDiagnosisRequest) -> dict:
        system, user = build_regression_diagnosis_prompts(regression_request)
        raw, model, usage = call_learner(REGRESSION_MODEL, system, user, temperature=0.0)
        record = {
            "request": asdict(regression_request),
            "raw_response": raw,
            "resolved_model": model,
            "usage": usage,
        }
        regression_calls.append(record)
        _write_json(OUTPUT_ROOT / f"regression_call_{len(regression_calls):02d}.json", record)
        parsed = parse_regression_diagnosis_response(raw)
        return {
            "pair_id": regression_request.pair_id,
            "domain": regression_request.domain,
            "parent_state": regression_request.parent_state,
            "candidate_state": regression_request.candidate_state,
            "regression_type": regression_request.regression_type,
            **parsed,
        }

    decision = _evaluate_candidate_step(
        root=OUTPUT_ROOT,
        step_root=OUTPUT_ROOT,
        step_number=1,
        parent_rows=parent_rows,
        candidate_rows=candidate_rows,
        diagnoses=proposal.diagnoses,
        edits=edits,
        targeted_fix_judge=recording_targeted_fix,
        regression_judge=recording_regression,
    )
    targeted = json.loads(
        (OUTPUT_ROOT / "targeted_fix_report.json").read_text(encoding="utf-8")
    )["results"]
    regressions = json.loads(
        (OUTPUT_ROOT / "regression_diagnoses.json").read_text(encoding="utf-8")
    )["diagnoses"]
    _write_json(OUTPUT_ROOT / "summary.json", {
        "editor_generated_edit": bool(edits),
        "editor_calls": len(editor_records),
        "edits": edits,
        "candidate_skill_path": candidate_path.as_posix(),
        "parent_rollout_seeds": [row["rollout_seed"] for row in parent_rows],
        "candidate_rollout_seeds": [row["rollout_seed"] for row in candidate_rows],
        "matched_seed_lineage": [row["rollout_seed"] for row in parent_rows]
        == [row["rollout_seed"] for row in candidate_rows],
        "targeted_fix": targeted,
        "regression_diagnoses": regressions,
        "gate": decision,
    })
    print(json.dumps({
        "output_root": OUTPUT_ROOT.as_posix(),
        "editor_generated_edit": bool(edits),
        "targeted_fix": [item["status"] for item in targeted],
        "regressions": len(regressions),
        "gate": decision["decision"],
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
