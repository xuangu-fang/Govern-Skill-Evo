from src.skill_evolution.autonomous_gse_v14_proposal import EditorContractError
from src.skill_evolution.unified_v14_step1_stress_test import (
    EDITOR_STRESS_TEST_FALLBACK_MAX_COMPLETION_TOKENS,
    EDITOR_STRESS_TEST_MAX_COMPLETION_TOKENS,
    SOURCE_ATTEMPT,
    _is_capacity_failure,
    load,
)


def test_stress_transport_budgets_and_source_patch_count():
    assert EDITOR_STRESS_TEST_MAX_COMPLETION_TOKENS == 32768
    assert EDITOR_STRESS_TEST_FALLBACK_MAX_COMPLETION_TOKENS == 65536
    source = load(SOURCE_ATTEMPT / "candidate/editor_request.json")
    assert len(source["eligible_diagnoses"]) == 17


def test_only_an_explicit_ceiling_hit_allows_64k_fallback():
    capacity = EditorContractError(
        "EDITOR_SCHEMA_CONTRACT_ERROR", raw_response="{", structured_output_mode="json_schema",
        error_reason="truncated", finish_reason="length", completion_tokens=32768,
        max_completion_tokens=32768,
    )
    not_ceiling = EditorContractError(
        "EDITOR_SCHEMA_CONTRACT_ERROR", raw_response="{", structured_output_mode="json_schema",
        error_reason="invalid", finish_reason="stop", completion_tokens=10,
        max_completion_tokens=32768,
    )
    assert _is_capacity_failure(capacity, 32768)
    assert not _is_capacity_failure(not_ceiling, 32768)
