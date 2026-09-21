import json
from pathlib import Path

from src.skill_evolution import benchmark_runtime_v18_v4 as runtime
from src.skill_evolution import formal_v18_v4 as formal


ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "benchmarks/tau2_governed_evolution/editions/phase_final_candidate_day35"
V4 = ROOT / "benchmarks/tau2_governed_evolution/editions/phase_v4_day36"


def load(path):
    return json.loads(Path(path).read_text())


def test_benchmark_v4_adds_eight_joint_tasks_without_mutating_v3():
    assert load(V3 / "VERSION.json")["task_count"] == 73
    version = load(V4 / "VERSION.json")
    splits = load(V4 / "benchmark/splits.json")
    registry = runtime.BenchmarkRegistry()
    assert version["task_count"] == 81
    assert len(splits["splits"]["train"]) == len(registry.task_ids("train")) == 36
    assert len(splits["splits"]["monitor"]) == len(registry.task_ids("monitor")) == 45
    assert [task_id for task_id in registry.task_ids() if task_id.startswith("JRA-01-")] == [
        f"JRA-01-C{index:02d}" for index in range(1, 9)
    ]


def test_benchmark_v4_preserves_hold_and_records_separate_admission():
    decision = load(V4 / "benchmark/admission_decision.json")
    validation = load(V4 / "integration_validation.json")
    source = load(ROOT / decision["source_summary"])
    assert source["verdict"] == decision["contract_v3_result_preserved"] == "HOLD_REPLICATION"
    assert decision["decision"] == "ADMIT_TO_BENCHMARK_V4"
    assert validation["status"] == "PASS_BENCHMARK_V4_INTEGRATION"
    assert validation["jra_oracle_cs"] == validation["jra_task_count"] == 8


def test_v18_benchmark_v4_freeze_is_current_and_uses_diagnosis_v321():
    config = formal.verify_freeze()
    assert config["version"] == "v18-formal-3-benchmark-v4"
    assert config["benchmark_edition"] == "phase_v4_day36"
    assert config["diagnosis"]["prompt"] == "v18-group-diagnosis-3.2.1"
    assert len(config["tasks"]["train"]) == 36
    assert len(config["tasks"]["monitor"]) == 45


def test_jra_routes_to_joint_deterministic_evaluator():
    registry = runtime.BenchmarkRegistry()
    evaluator = runtime.DeterministicEvaluatorDispatcher(registry)
    assert evaluator.route("JRA-01-C01") == "JRA-01"
    assert registry.get("JRA-01-C01").logical_domain == "airline"
