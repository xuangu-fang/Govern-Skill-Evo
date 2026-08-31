"""Replay saved v0.13 Diagnosis raw responses through deterministic contract repair."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_v13_diagnosis_case_audit import OUTPUT_ROOT, _experience
from src.skill_evolution.autonomous_gse_v13_proposal import structured_skill
from src.skill_evolution.diagnosis_contract_v13 import (
    parse_and_validate_diagnosis, repair_diagnosis_contract_fields,
    validate_diagnosis,
)


def _tag(diagnosis: dict) -> str:
    return (
        "<DIAGNOSIS_JSON>"
        + json.dumps(diagnosis, ensure_ascii=False, separators=(",", ":"))
        + "</DIAGNOSIS_JSON>"
    )


def main() -> None:
    cases = []
    counts = Counter()
    for audit_set in ("old", "fresh"):
        for path in sorted((OUTPUT_ROOT / audit_set / "cases").glob("*/diagnosis.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            raw = record.get("initial_raw_response") or record.get("raw_response") or ""
            experiences = tuple(_experience(Path(item)) for item in record["rollout_paths"])
            parent_skill = Path(record["parent_skill_path"]).read_text(encoding="utf-8").replace(
                "# Operational Skill", "# SuiteCRM Operational Skill", 1
            )
            diagnosis_id = f"repair_policy_{audit_set}_{path.parent.name}"
            validation = parse_and_validate_diagnosis(
                diagnosis_id, raw, experiences=experiences,
                skill_sections=structured_skill(parent_skill),
            )
            embedded_validation_errors = []
            if validation.structured_output is None and raw.lstrip().startswith("{"):
                try:
                    embedded = json.loads(raw)
                except json.JSONDecodeError:
                    pass
                else:
                    embedded_validation_errors = list(validate_diagnosis(
                        embedded, experiences=experiences,
                        skill_sections=structured_skill(parent_skill),
                    ))
            final_validation = validation
            disposition = "raw_valid"
            if validation.valid:
                counts["raw_valid"] += 1
            else:
                counts["raw_invalid"] += 1
                repaired = repair_diagnosis_contract_fields(
                    validation.structured_output, validation.validation_errors,
                )
                if repaired is None:
                    disposition = "semantic_fail_closed"
                    counts["semantic_fail_closed"] += 1
                else:
                    candidate_validation = parse_and_validate_diagnosis(
                        diagnosis_id, _tag(repaired), experiences=experiences,
                        skill_sections=structured_skill(parent_skill),
                    )
                    if candidate_validation.valid:
                        final_validation = candidate_validation
                        disposition = "deterministic_repaired"
                        counts["deterministic_repaired"] += 1
                    else:
                        disposition = "repair_failed_revalidation"
                        counts["semantic_fail_closed"] += 1
            if final_validation.valid:
                counts["final_valid"] += 1
            cases.append({
                "audit_set": audit_set,
                "case_id": path.parent.name,
                "raw_valid": validation.valid,
                "raw_validation_errors": list(validation.validation_errors),
                "embedded_validation_errors": embedded_validation_errors,
                "disposition": disposition,
                "final_valid": final_validation.valid,
                "final_validation_errors": list(final_validation.validation_errors),
            })

    report = {
        "schema_version": "autonomous_gse_v13_diagnosis_repair_policy_regression_0.13.0",
        "mode": "saved_raw_responses_no_model_calls",
        "task_count": len(cases),
        "counts": {
            key: counts[key] for key in (
                "raw_valid", "raw_invalid", "deterministic_repaired",
                "semantic_fail_closed", "final_valid",
            )
        },
        "cases": cases,
    }
    output = OUTPUT_ROOT / "repair_policy_regression.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
