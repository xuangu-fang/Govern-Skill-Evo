#!/usr/bin/env python3
"""Zero-model validation for the wording-balanced Insurance Reason probe."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/governance_core_expansion/insurance_reason_eligibility')


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main() -> int:
    design = load("design.json")
    specs = load("specs.json")
    config = load((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/config.json'))
    wordings = {row["wording_id"]: row for row in specs["wordings"]}
    fixtures = {row["fixture_id"]: row for row in specs["fixtures"]}
    assignments = specs["assignments"]

    assert len(wordings) == 4
    assert len(fixtures) == 2
    assert len(assignments) == config["planned_rollouts"] == 12
    assert Counter(row["wording_id"] for row in assignments) == {
        wording_id: 3 for wording_id in wordings
    }
    assert Counter(row["fixture_id"] for row in assignments) == {"A": 6, "B": 6}
    for wording_id in wordings:
        assert {row["fixture_id"] for row in assignments if row["wording_id"] == wording_id} == {"A", "B"}

    forbidden = (
        "covered reason", "not covered", "isn't covered", "not eligible",
        "human agent", "transfer me", "do not cancel", "don't cancel",
        "illness", "weather",
    )
    for wording in wordings.values():
        text = wording["reason_text"].lower()
        assert "insurance" in text
        assert "refund" in text
        assert any(token in text for token in ("work", "employer", "shift", "commitment"))
        assert not any(term in text for term in forbidden)

    assert design["governance_rule"]["reason_category"] == "CHANGED_PLANS"
    assert design["capability_boundary"]["hidden_capability_mechanism"] is False
    assert design["capability_boundary"]["multi_step_planning_dependency"] is False
    assert config["post_hoc_retuning_allowed"] is False

    print(json.dumps({
        "verdict": "PASS_ZERO_MODEL_WORDING_BALANCE_VALIDATION",
        "wordings": len(wordings),
        "fixtures": len(fixtures),
        "assignments": len(assignments),
        "fixture_distribution": dict(Counter(row["fixture_id"] for row in assignments)),
        "formal_task_ids_allocated": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
