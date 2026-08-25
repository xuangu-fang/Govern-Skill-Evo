import json

import pytest

from src.adapters.stwebagentbench.benchmark_variant import (
    benchmark_artifact_group,
    benchmark_environment_id,
    benchmark_variant_metadata,
)


def test_v02_variant_has_independent_environment_and_lineage(monkeypatch):
    from src.adapters.stwebagentbench import validated_benchmark_v02_runtime as runtime

    monkeypatch.setenv("STWEB_BENCHMARK_VARIANT", "interactive_validated_v02")
    monkeypatch.setenv("STWEB_VALIDATED_V02_CANARY", "1")
    manifest = json.loads(runtime.FORMAL_MANIFEST.read_text())
    monkeypatch.setattr(runtime, "_manifest", lambda: manifest)
    assert benchmark_environment_id(49) == "browsergym/STWebAgentBenchInteractiveValidatedV02Env.49"
    assert benchmark_artifact_group(True) == "raw_interactive_validated_v02"
    metadata = benchmark_variant_metadata()
    assert metadata["validated_benchmark_version"] == "stweb-suitecrm-interactive-validated-v02"
    assert metadata["hallucination_normalization_version"] == "stweb-hallucination-field-normalization-v02"
    with pytest.raises(ValueError, match="not retained"):
        benchmark_environment_id(56)


def test_v01_variant_remains_needs_review_and_is_not_reinterpreted(monkeypatch):
    monkeypatch.setenv("STWEB_BENCHMARK_VARIANT", "interactive_validated")
    monkeypatch.delenv("STWEB_VALIDATED_CANARY_RETRY_AUTHORIZATION", raising=False)
    with pytest.raises(RuntimeError, match="not ready"):
        benchmark_environment_id(47)
