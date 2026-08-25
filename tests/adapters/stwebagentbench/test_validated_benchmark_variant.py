import json

import pytest

from src.adapters.stwebagentbench.benchmark_variant import (
    benchmark_artifact_group,
    benchmark_environment_id,
    benchmark_variant_metadata,
)
from src.adapters.stwebagentbench.validated_benchmark_runtime import (
    validate_validated_trajectory_lineage,
)


def test_original_and_interactive_variants_are_unchanged(monkeypatch):
    monkeypatch.setenv("STWEB_BENCHMARK_VARIANT", "original")
    assert benchmark_environment_id(56) == "browsergym/STWebAgentBenchEnv.56"
    assert benchmark_artifact_group(True) == "raw"
    assert benchmark_variant_metadata() == {}

    monkeypatch.setenv("STWEB_BENCHMARK_VARIANT", "interactive")
    assert benchmark_environment_id(56) == "browsergym/STWebAgentBenchInteractiveEnv.56"
    assert benchmark_artifact_group(True) == "raw_interactive_v2"
    assert benchmark_variant_metadata()["benchmark_variant"] == "ST-WebAgentBench-Interactive"


def test_v01_needs_review_variant_cannot_be_formally_started(monkeypatch):
    monkeypatch.setenv("STWEB_BENCHMARK_VARIANT", "interactive_validated")
    with pytest.raises(RuntimeError, match="not ready"):
        benchmark_environment_id(47)
    with pytest.raises(RuntimeError, match="not ready"):
        benchmark_variant_metadata()


def test_validated_trajectory_lineage_rejects_old_interactive(monkeypatch):
    from src.adapters.stwebagentbench import validated_benchmark_runtime as runtime

    monkeypatch.setenv("STWEB_BENCHMARK_VARIANT", "interactive_validated")
    historical_manifest = json.loads(runtime.FORMAL_MANIFEST.read_text())
    assert historical_manifest["status"] == "needs_review"
    monkeypatch.setattr(runtime, "_manifest", lambda: historical_manifest)
    metadata = benchmark_variant_metadata()
    validate_validated_trajectory_lineage({"run": metadata, "task": {"task_id": 47}})
    old = {**metadata, "benchmark_variant": "ST-WebAgentBench-Interactive"}
    with pytest.raises(ValueError, match="lineage mismatch"):
        validate_validated_trajectory_lineage({"run": old, "task": {"task_id": 47}})
