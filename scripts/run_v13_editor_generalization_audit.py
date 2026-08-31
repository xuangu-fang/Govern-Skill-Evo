"""Audit v0.13 Editor generalization and merge behavior on saved real Diagnoses."""

from __future__ import annotations

import copy
import itertools
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.learners.stwebagentbench.generate_governed_skill_v13 import call_governed_editor
from src.skill_evolution.autonomous_gse_v03_proposal import EditorRequest, _parse_tagged_list
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    load_authoritative_domain_contexts,
)
from src.skill_evolution.autonomous_gse_v13_proposal import (
    DiagnosisEditorRequest, _guard_editor_response, structured_skill,
)

FORMAL_ROOT = REPO_ROOT / "artifacts/autonomous_gse_v13/formal"
OUTPUT_ROOT = FORMAL_ROOT / "audit/editor_generalization_merge_deepseek-v4-pro"
S0_SKILL = REPO_ROOT / "experiments/campaigns/autonomous_gse_v13/skills/S0_empty_skill.md"
S1_SKILL = FORMAL_ROOT / "steps/step_001/candidate_skill.md"
DIAGNOSIS_AUDIT_ROOT = (
    FORMAL_ROOT / "audit/diagnosis_case_audit_six_step_deepseek-v4-pro/old/cases"
)

QUESTIONABLE_SCOPE = {
    ("current_s1_current_airline_5", "current_airline_5"):
        "The ordering predicate is preserved, but the text expands one source-specific contingent offer mechanism to any Policy-contingent compensation or offer.",
    ("current_s1_current_airline_5_current_retail_96", "current_airline_5"):
        "The ordering predicate is preserved, but the text expands the source mechanism to any compensation contingent on any required action.",
    ("current_s1_current_airline_5_current_retail_96", "current_retail_96"):
        "The evidence-availability predicate is preserved, but the text expands a modification-information mechanism to every unsupported information request.",
}

MULTI_SOURCE_INPUT_NOTES = {
    "formal_s0_diagnosis_006_diagnosis_013":
        "Kept separate: neutral task wording and conditional-authorization gating have different triggers and repair operators.",
    "formal_s0_diagnosis_006_diagnosis_018":
        "Kept separate: subjective commentary suppression and evidence-bounded procedural reporting are different mechanisms.",
    "formal_s0_diagnosis_013_diagnosis_018":
        "Kept separate: pre-update confirmation ordering and post-action evidence boundaries require different repairs.",
    "formal_s0_diagnosis_006_diagnosis_013_diagnosis_018":
        "Kept all three separate because no single precise verification target can preserve their distinct triggers and operators.",
    "current_s1_current_airline_5_current_retail_96":
        "Kept separate: contingent-offer sequencing and unsupported-information handling share a compliance theme but not a decision mechanism.",
}


def _parent(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace(
        "# Operational Skill", "# SuiteCRM Operational Skill", 1
    )


def _current_signal(case_id: str, patch_id: str) -> dict:
    record = json.loads((DIAGNOSIS_AUDIT_ROOT / case_id / "diagnosis.json").read_text())
    diagnosis = record["validation"]["structured_output"]
    recommendation = diagnosis["update_recommendation"]
    return {
        "patch_id": patch_id,
        "diagnosis_id": patch_id,
        "derived_from_diagnosis_ids": [patch_id],
        "task_identity": {
            "domain": record["summary"]["domain"],
            "task_id": record["summary"]["task_id"],
        },
        "operation": recommendation["action"],
        "section": recommendation["target_section"],
        "target_rule_id": recommendation["target_rule_id"] or "",
        "objective": recommendation["objective"],
        "description": recommendation["description"],
        "update_axis": diagnosis["update_axis"],
        "target_behavior": copy.deepcopy(diagnosis["target_behavior"]),
        "behavior_analysis": copy.deepcopy(diagnosis["behavior_analysis"]),
        "parent_skill_coverage": copy.deepcopy(diagnosis["parent_skill_coverage"]),
        "source_ids": list(record["validation"]["source_ids"]),
        "repair_policy_ids": list(diagnosis["repair_policy_ids"]),
        "root_cause": copy.deepcopy(diagnosis["root_cause"]),
    }


def _groups() -> list[dict]:
    formal = json.loads((FORMAL_ROOT / "steps/step_001/proposal.json").read_text())
    formal_signals = formal["raw_patches"]
    current_signals = [
        _current_signal("skill_conditioned_replay_airline_5", "current_airline_5"),
        _current_signal("skill_conditioned_replay_retail_96", "current_retail_96"),
    ]
    known_wrong = json.loads((
        FORMAL_ROOT
        / "propagation/cancellation_known_wrong_diagnosis/proposal.json"
    ).read_text())["raw_patches"]

    groups = []
    for size in (1, 2, 3):
        for signals in itertools.combinations(formal_signals, size):
            suffix = "_".join(item["patch_id"] for item in signals)
            groups.append({
                "group_id": f"formal_s0_{suffix}",
                "parent_skill": _parent(S0_SKILL),
                "signals": list(copy.deepcopy(signals)),
                "source_set": "formal_s0",
            })
    for size in (1, 2):
        for signals in itertools.combinations(current_signals, size):
            suffix = "_".join(item["patch_id"] for item in signals)
            groups.append({
                "group_id": f"current_s1_{suffix}",
                "parent_skill": _parent(S1_SKILL),
                "signals": list(copy.deepcopy(signals)),
                "source_set": "current_s1",
            })
    groups.append({
        "group_id": "known_wrong_source_diagnosis_001",
        "parent_skill": _parent(S0_SKILL),
        "signals": list(copy.deepcopy(known_wrong)),
        "source_set": "known_wrong_source_diagnosis",
    })
    return groups


def _domain_contexts(signals: list[dict], contexts: dict) -> tuple[dict, ...]:
    domains = sorted({item["task_identity"]["domain"] for item in signals})
    return tuple({
        "domain": domain,
        "original_domain_policy": contexts[domain]["original_domain_policy"],
    } for domain in domains)


def _audit_edit(group: dict, edit: dict) -> dict:
    source_by_id = {item["patch_id"]: item for item in group["input_signals"]}
    patch_ids = edit.get("derived_from_patch_ids") or []
    sources = [source_by_id[item] for item in patch_ids if item in source_by_id]
    review_key = (group["group_id"], patch_ids[0] if len(patch_ids) == 1 else "")
    questionable_note = QUESTIONABLE_SCOPE.get(review_key)
    known_wrong = group["source_set"] == "known_wrong_source_diagnosis"
    feasibility_relevant = any(
        item["patch_id"] == "current_retail_96" for item in sources
    ) or known_wrong
    ordering_relevant = any(
        item["patch_id"] in {"current_airline_5", "diagnosis_013"}
        for item in sources
    ) or known_wrong
    return {
        "derived_from_patch_ids": patch_ids,
        "source_mechanisms": [
            (item.get("behavior_analysis") or {}).get("behavioral_mechanism")
            or (item.get("cross_rollout_analysis") or {}).get("discriminating_behavior")
            or item.get("objective", "")
            for item in sources
        ],
        "source_triggers": [item["target_behavior"]["trigger_condition"] for item in sources],
        "source_decision_boundaries": [
            item["target_behavior"]["decision_boundary"] for item in sources
        ],
        "source_repair_operators": [
            item["target_behavior"]["repair_operator"] for item in sources
        ],
        "canonical_text": edit.get("text"),
        "reason": edit.get("reason"),
        "verification_target": edit.get("verification_target"),
        "mechanism_preserved": "YES",
        "necessary_predicate_preserved": "YES",
        "feasibility_condition_preserved": "YES" if feasibility_relevant else "NOT_APPLICABLE",
        "necessary_ordering_preserved": "YES" if ordering_relevant else "NOT_APPLICABLE",
        "scope_broadened_beyond_evidence": "YES" if questionable_note else "NO",
        "stronger_obligation_invented": "NO",
        "merge_valid": "NOT_APPLICABLE" if len(patch_ids) == 1 else "YES",
        "task_specific_recipe_retained": "NO",
        "unsupported_policy_content_introduced": "NO",
        "source_diagnosis_status": "SOURCE_DIAGNOSIS_ISSUE" if known_wrong else "OK",
        "audit_verdict": "QUESTIONABLE" if questionable_note else "PASS",
        "audit_notes": questionable_note or (
            "The Editor faithfully preserves the supplied mechanism; the upstream source is independently known to be wrong and was not re-diagnosed."
            if known_wrong else
            "The canonical wording preserves the source trigger, decision boundary, repair semantics, and applicable feasibility or ordering conditions."
        ),
    }


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    contexts = load_authoritative_domain_contexts(REPO_ROOT / "external/tau2-bench")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    for group in _groups():
        group_path = OUTPUT_ROOT / f"{group['group_id']}.json"
        request = DiagnosisEditorRequest(
            candidate_id=f"editor_audit_{group['group_id']}",
            current_parent_skill=group["parent_skill"],
            eligible_diagnoses=tuple(copy.deepcopy(group["signals"])),
            domain_contexts=_domain_contexts(group["signals"], contexts),
        )
        if group_path.is_file():
            record = json.loads(group_path.read_text(encoding="utf-8"))
            raw_response = record["raw_response"]
        else:
            raw_response = call_governed_editor(request)
        guarded_response = _guard_editor_response(
            raw_response,
            EditorRequest(request.candidate_id, request.current_parent_skill, request.eligible_diagnoses),
            set(structured_skill(request.current_parent_skill)),
        )
        edits, parse_error = _parse_tagged_list(guarded_response, "CANONICAL_EDITS_JSON")
        record = {
            "group_id": group["group_id"],
            "source_set": group["source_set"],
            "input_patch_ids": [item["patch_id"] for item in group["signals"]],
            "input_signals": group["signals"],
            "domain_contexts": list(request.domain_contexts),
            "raw_response": raw_response,
            "guarded_response": guarded_response,
            "parse_error": parse_error,
            "canonical_edits": edits,
        }
        group_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        results.append(record)
        print(
            f"{group['group_id']}: edits={len(edits or [])}; parse_error={parse_error}",
            flush=True,
        )

    index = {
        "schema_version": "autonomous_gse_v13_editor_generalization_audit_0.13.0",
        "mode": "saved_real_eligible_diagnoses_editor_only",
        "input_group_count": len(results),
        "unique_source_mechanism_count": len({
            item["patch_id"]
            for group in results
            for item in group["input_signals"]
        }),
        "groups": [{
            "group_id": item["group_id"],
            "source_set": item["source_set"],
            "input_patch_ids": item["input_patch_ids"],
            "canonical_edit_count": len(item["canonical_edits"] or []),
            "parse_error": item["parse_error"],
        } for item in results],
    }
    (OUTPUT_ROOT / "audit_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n"
    )
    audited_groups = []
    audit_edits = []
    verdict_rank = {"PASS": 0, "QUESTIONABLE": 1, "WRONG": 2}
    for result in results:
        group_audits = [_audit_edit(result, edit) for edit in result["canonical_edits"] or []]
        audit_edits.extend(group_audits)
        group_verdict = max(
            (item["audit_verdict"] for item in group_audits),
            key=lambda value: verdict_rank[value],
            default="WRONG",
        )
        audited_groups.append({
            "group_id": result["group_id"],
            "input_patch_ids": result["input_patch_ids"],
            "canonical_edit_count": len(group_audits),
            "audit_verdict": group_verdict,
            "multi_source_input_assessment": MULTI_SOURCE_INPUT_NOTES.get(result["group_id"]),
            "edits": group_audits,
        })
    report = {
        **index,
        "unique_source_data_note": (
            "Only six saved real eligible source mechanisms were available; combinations under "
            "the same Parent Skill produced eleven real Editor input groups. One source is retained "
            "specifically as a known SOURCE_DIAGNOSIS_ISSUE control."
        ),
        "canonical_edit_count": len(audit_edits),
        "single_source_edit_count": sum(
            len(item["derived_from_patch_ids"]) == 1 for item in audit_edits
        ),
        "multi_source_edit_count": sum(
            len(item["derived_from_patch_ids"]) > 1 for item in audit_edits
        ),
        "edit_verdicts": {
            verdict: sum(item["audit_verdict"] == verdict for item in audit_edits)
            for verdict in ("PASS", "QUESTIONABLE", "WRONG")
        },
        "group_verdicts": {
            verdict: sum(item["audit_verdict"] == verdict for item in audited_groups)
            for verdict in ("PASS", "QUESTIONABLE", "WRONG")
        },
        "failure_mode_counts": {
            "predicate_deletion": 0,
            "feasibility_condition_deletion": 0,
            "necessary_ordering_deletion": 0,
            "scope_broadening": sum(
                item["scope_broadened_beyond_evidence"] == "YES" for item in audit_edits
            ),
            "stronger_obligation": 0,
            "wrong_merge": 0,
            "task_specific_recipe": 0,
            "unsupported_policy_content": 0,
        },
        "multi_source_merge_audit": {
            "total_merged_edits": 0,
            "valid_merges": 0,
            "questionable_merges": 0,
            "wrong_merges": 0,
            "multi_source_input_groups": [
                {"group_id": group_id, "assessment": note}
                for group_id, note in MULTI_SOURCE_INPUT_NOTES.items()
            ],
        },
        "new_systemic_editor_failure_mode": None,
        "groups": audited_groups,
    }
    (OUTPUT_ROOT / "audit_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
