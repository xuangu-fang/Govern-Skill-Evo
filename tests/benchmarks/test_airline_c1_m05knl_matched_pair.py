from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_c1_m05knl import (
    validate_pair,
)
from benchmarks.tau2_governed_evolution.intent_dynamics.probe_airline_c1_m05knl import (
    run_probes,
)


def test_airline_c1_m05knl_static_pair_contract() -> None:
    result = validate_pair()

    assert result["passed"], result["checks"]
    assert all(result["checks"].values())
    assert result["p0_execution"]["new_total"] == 207
    assert result["p1_execution"]["new_total"] == 216


def test_airline_c1_m05knl_official_outcome_separation() -> None:
    result = run_probes(with_judge=False)

    assert result["passed"], result["probes"]
    assert result["probes"]["upfront_cs"]["official"]["success"] is True
    assert result["probes"]["revision_cs"]["official"]["success"] is True
    assert result["probes"]["revision_vs"]["official"]["success"] is True
    assert result["probes"]["revision_vf"]["official"]["success"] is False
