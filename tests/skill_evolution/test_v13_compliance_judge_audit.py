from __future__ import annotations

from scripts.run_v13_compliance_judge_audit import classify_case, summarize_cases


def _violation(
    *, correct: str = "YES", applicability: str = "APPLICABLE",
    grounding: str = "SUPPORTED", error_type: str = "none",
    granularity: str = "GRANULARITY_OK",
) -> dict:
    return {
        "violation_index": 1,
        "policy_section": "Policy > Rule",
        "applicability": applicability,
        "evidence_grounding": grounding,
        "violation_correct": correct,
        "error_type": error_type,
        "granularity": granularity,
        "notes": "fixture",
    }


def _audit(
    assessment: str, *, violations: list[dict] | None = None,
    missed_type: str | None = None, **issues: bool,
) -> dict:
    return {
        "true_compliance_assessment": assessment,
        "reported_violation_audits": violations or [],
        "missed_violations": ([{
            "policy_clause": "Agents must not perform X.",
            "policy_section": "Policy > Rule",
            "evidence_steps": [3],
            "reason": "The trajectory performs X.",
            "error_type": missed_type,
        }] if missed_type else []),
        "policy_applicability_issue": issues.get("policy_applicability_issue", False),
        "evidence_grounding_issue": issues.get("evidence_grounding_issue", False),
        "unsupported_claim_issue": issues.get("unsupported_claim_issue", False),
        "tool_policy_confusion": issues.get("tool_policy_confusion", False),
        "granularity_issue": issues.get("granularity_issue", False),
        "notes": "fixture",
    }


def _case(judge_compliant: bool, audit: dict) -> dict:
    return {
        "judge": {"valid": True, "structured_output": {
            "compliant": judge_compliant,
            "violations": [] if judge_compliant else [{"policy_clause": "rule"}],
        }},
        "audit": {"valid": True, "structured_output": audit},
        "classification": classify_case(judge_compliant, audit),
    }


def test_correct_violation_is_true_positive_pass() -> None:
    result = classify_case(False, _audit("VIOLATED", violations=[_violation()]))

    assert result["matrix_class"] == "TP"
    assert result["overall_verdict"] == "PASS"


def test_wrong_applicability_is_false_positive() -> None:
    audit = _audit(
        "CLEAR_COMPLIANT",
        violations=[_violation(
            correct="NO", applicability="NOT_APPLICABLE", error_type="wrong_scope"
        )],
        policy_applicability_issue=True,
    )

    result = classify_case(False, audit)
    summary = summarize_cases([_case(False, audit)])

    assert result["matrix_class"] == "FP"
    assert result["overall_verdict"] == "WRONG"
    assert summary["false_positive_breakdown"] == {"wrong_scope": 1}


def test_supported_claim_false_positive_is_counted() -> None:
    audit = _audit(
        "CLEAR_COMPLIANT",
        violations=[_violation(
            correct="NO", error_type="unsupported_claim_false_positive"
        )],
        unsupported_claim_issue=True,
    )

    summary = summarize_cases([_case(False, audit)])

    assert summary["false_positive_breakdown"] == {
        "unsupported_claim_false_positive": 1
    }
    assert summary["issue_counts"]["unsupported_claim_issue"] == 1


def test_tool_capability_is_not_policy_obligation() -> None:
    audit = _audit(
        "CLEAR_COMPLIANT",
        violations=[_violation(correct="NO", error_type="tool_policy_confusion")],
        tool_policy_confusion=True,
    )

    summary = summarize_cases([_case(False, audit)])

    assert summary["false_positive_breakdown"] == {"tool_policy_confusion": 1}
    assert summary["issue_counts"]["tool_policy_confusion"] == 1


def test_missed_violation_is_false_negative() -> None:
    audit = _audit("VIOLATED", missed_type="missed_prohibition")

    result = classify_case(True, audit)
    summary = summarize_cases([_case(True, audit)])

    assert result["matrix_class"] == "FN"
    assert result["overall_verdict"] == "WRONG"
    assert summary["false_negative_breakdown"] == {"missed_prohibition": 1}


def test_unclear_evidence_is_uncertain_not_wrong() -> None:
    audit = _audit("NO_VIOLATION_BUT_UNCERTAIN", evidence_grounding_issue=True)

    result = classify_case(True, audit)
    summary = summarize_cases([_case(True, audit)])

    assert result["matrix_class"] == "uncertain"
    assert result["overall_verdict"] == "QUESTIONABLE"
    assert summary["uncertainty_silently_mapped_to_compliant_rate"] == 1.0


def test_bundled_violation_is_granularity_issue_without_losing_true_positive() -> None:
    audit = _audit(
        "VIOLATED",
        violations=[_violation(error_type="bundled_violation", granularity="BUNDLED")],
        granularity_issue=True,
    )

    result = classify_case(False, audit)
    summary = summarize_cases([_case(False, audit)])

    assert result["matrix_class"] == "TP"
    assert result["overall_verdict"] == "QUESTIONABLE"
    assert summary["issue_counts"]["granularity_issue"] == 1


def test_irrelevant_evidence_step_is_false_positive_grounding_issue() -> None:
    audit = _audit(
        "CLEAR_COMPLIANT",
        violations=[_violation(
            correct="NO", grounding="UNSUPPORTED", error_type="insufficient_evidence"
        )],
        evidence_grounding_issue=True,
    )

    summary = summarize_cases([_case(False, audit)])

    assert summary["confusion_matrix"]["FP"] == 1
    assert summary["false_positive_breakdown"] == {"insufficient_evidence": 1}
    assert summary["issue_counts"]["evidence_grounding_issue"] == 1
