"""Transport-only high-headroom stress continuation of Unified v14 Step 1."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from src.learners.stwebagentbench.generate_governed_skill_v14 import (
    DiagnosisEditorRequest,
    EditorContractError,
    call_governed_editor,
)
from src.learners.stwebagentbench.generate_skill import call_learner
from src.skill_evolution.autonomous_gse_v03_proposal import EditorRequest, ProposalContext
from src.skill_evolution.autonomous_gse_v05_proposal import _parse_skill, _parse_tagged_list, propose_from_update_signals
from src.skill_evolution.autonomous_gse_v14_proposal import _guard_editor_response
from src.skill_evolution.autonomous_gse_v14_unified_step1_pilot import (
    PILOT_ROOT,
    prepare_requests,
)

SOURCE_ATTEMPT = PILOT_ROOT / "attempt_3_clean_adapter"
OUT = PILOT_ROOT / "attempt_4_high_headroom_stress_test"
EDITOR_STRESS_TEST_MAX_COMPLETION_TOKENS = 32768
EDITOR_STRESS_TEST_FALLBACK_MAX_COMPLETION_TOKENS = 65536


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _stress_learner_call(budget: int):
    def learner_call(model, system, user, *, response_format=None, max_completion_tokens=None):
        return call_learner(
            model, system, user, temperature=0.0,
            response_format=response_format, max_completion_tokens=budget,
        )
    return learner_call


def _is_capacity_failure(error: EditorContractError, budget: int) -> bool:
    return (
        error.code == "EDITOR_SCHEMA_CONTRACT_ERROR"
        and error.finish_reason == "length"
        and error.completion_tokens == budget
        and error.max_completion_tokens == budget
    )


def run_editor() -> None:
    source = load(SOURCE_ATTEMPT / "candidate/editor_request.json")
    if len(source.get("eligible_diagnoses", [])) != 17:
        raise RuntimeError("STRESS_TEST_REQUIRES_EXACTLY_17_ELIGIBLE_PATCHES")
    parent, _, requests, _, _, _ = prepare_requests()
    if source.get("current_parent_skill") != parent:
        raise RuntimeError("PARENT_SKILL_DRIFT")
    request = DiagnosisEditorRequest(
        candidate_id=source["candidate_id"],
        current_parent_skill=source["current_parent_skill"],
        eligible_diagnoses=tuple(source["eligible_diagnoses"]),
    )
    response = None
    attempts = []
    for budget in (
        EDITOR_STRESS_TEST_MAX_COMPLETION_TOKENS,
        EDITOR_STRESS_TEST_FALLBACK_MAX_COMPLETION_TOKENS,
    ):
        try:
            response = call_governed_editor(
                request, learner_call=_stress_learner_call(budget),
            )
        except EditorContractError as error:
            attempts.append({"budget": budget, "status": "FAIL", **error.as_dict()})
            write(OUT / f"editor/editor_{budget}_error.json", attempts[-1])
            if budget == EDITOR_STRESS_TEST_MAX_COMPLETION_TOKENS and _is_capacity_failure(error, budget):
                continue
            write(OUT / "editor/editor_transport.json", {
                "attempts": attempts, "final_status": "FAIL",
                "editor_batching": False, "update_pruning": False,
            })
            raise
        attempts.append({
            "budget": budget, "status": "PASS", **response.editor_transport,
        })
        break
    if response is None:
        raise RuntimeError("EDITOR_TRANSPORT_CAPACITY_FAILURE")

    structured = json.loads(response.raw_response)
    write(OUT / "editor/canonical_edits.json", structured["canonical_edits"])
    write(OUT / "editor/editor_transport.json", {
        "attempts": attempts, "final_status": "PASS",
        "structured_output_mode": "json_schema",
        "schema_valid": True, "editor_batching": False,
        "update_pruning": False,
    })

    signals = source["eligible_diagnoses"]
    editor_request = EditorRequest(
        candidate_id=source["candidate_id"], current_parent_skill=parent,
        raw_patches=tuple(signals),
    )
    guarded = _guard_editor_response(response, editor_request, set(_parse_skill(parent)))
    guarded_edits, parse_error = _parse_tagged_list(guarded, "CANONICAL_EDITS_JSON")
    if parse_error or guarded_edits is None or any(
        isinstance(edit, dict) and "v13_validation_error" in edit for edit in guarded_edits
    ):
        write(OUT / "editor/editor_guard.json", {
            "status": "FAIL", "parse_error": parse_error, "edits": guarded_edits,
        })
        raise RuntimeError("EDITOR_GUARD_FAILURE")
    write(OUT / "editor/editor_guard.json", {"status": "PASS", "edits": guarded_edits})

    evidence = tuple(item for item_request in requests for item in item_request.rollouts)
    decision = propose_from_update_signals(
        ProposalContext("STEP1_STRESS_CANDIDATE", parent, evidence),
        signals, lambda _: guarded, upstream_calls=34,
    )
    write(OUT / "candidate/edit_provenance.json", dataclasses.asdict(decision))
    if decision.proposal_status != "CANDIDATE" or not decision.candidate_skill:
        raise RuntimeError(f"NO_VALID_STRESS_CANDIDATE:{decision.proposal_reason}")
    (OUT / "candidate/candidate_skill.md").write_text(decision.candidate_skill)

    editor_patch_use = [
        patch_id for edit in decision.canonical_edits if isinstance(edit, dict)
        for patch_id in edit.get("derived_from_patch_ids", [])
    ]
    applied_patch_use = [
        patch_id for edit in decision.applied_edits
        for patch_id in edit.get("derived_from_patch_ids", [])
    ]
    patch_ids = [item["patch_id"] for item in signals]
    write(OUT / "editor/editor_consumption.json", {
        "eligible_patches": len(patch_ids),
        "canonical_edits": len(decision.canonical_edits),
        "applied_edits": len(decision.applied_edits),
        "excluded_edits": len(decision.excluded_edits),
        "merged_canonical_edits": sum(len(edit.get("derived_from_patch_ids", [])) > 1 for edit in decision.canonical_edits if isinstance(edit, dict)),
        "single_source_canonical_edits": sum(len(edit.get("derived_from_patch_ids", [])) == 1 for edit in decision.canonical_edits if isinstance(edit, dict)),
        "editor_missing_patch_ids": sorted(set(patch_ids) - set(editor_patch_use)),
        "editor_duplicated_patch_ids": sorted({item for item in editor_patch_use if editor_patch_use.count(item) > 1}),
        "editor_consumed_patch_ids": len(set(editor_patch_use)),
        "applied_patch_ids": len(set(applied_patch_use)),
        "unapplied_patch_ids": sorted(set(patch_ids) - set(applied_patch_use)),
    })
    print("STRESS_EDITOR", attempts[-1], "CANDIDATE_RULES", len(decision.applied_edits), flush=True)


if __name__ == "__main__":
    run_editor()
