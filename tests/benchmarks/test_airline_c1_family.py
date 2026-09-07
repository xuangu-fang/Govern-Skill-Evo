from benchmarks.tau2_governed_evolution.intent_dynamics.probe_airline_c1_family import (
    run_probes,
)
from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_c1_family import (
    validate_family,
)


def test_airline_c1_family_static_contract() -> None:
    result = validate_family()

    assert result["passed"], result
    assert result["underlying_states"] == 4
    assert result["task_count"] == 8
    assert len(result["trigger_types"]) == 4


def test_airline_c1_family_official_outcome_separation() -> None:
    result = run_probes(with_judge=False)

    assert result["passed"], result
    for probes in result["pairs"].values():
        assert probes["upfront_cs"]["official"]["success"] is True
        assert probes["revision_cs"]["official"]["success"] is True
        assert probes["revision_vs"]["official"]["success"] is True
        assert probes["revision_vf"]["official"]["success"] is False
