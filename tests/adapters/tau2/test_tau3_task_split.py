from __future__ import annotations

import json
from pathlib import Path

from src.adapters.tau2.tau3_task_split import build_frozen_split, load_frozen_split


REPO_ROOT = Path(__file__).resolve().parents[3]
TAU2_ROOT = REPO_ROOT / "external/tau2-bench"
FROZEN = REPO_ROOT / "experiments/campaigns/autonomous_gse_v09/batch_map.json"


def test_tau3_split_counts_batches_and_overlap_contract() -> None:
    split = load_frozen_split(FROZEN, TAU2_ROOT)
    assignment = split["assignment"]
    assert len(assignment["train"]["airline"]) == 21
    assert len(assignment["train"]["retail"]) == 30
    assert len(assignment["selection"]["airline"]) == 9
    assert len(assignment["selection"]["retail"]) == 9
    assert len(split["batches"]) == 3
    assert all(len(batch["task_ids"]) == 17 for batch in split["batches"])
    assert all(
        sum(item.startswith("airline:") for item in batch["task_ids"]) == 7
        and sum(item.startswith("retail:") for item in batch["task_ids"]) == 10
        for batch in split["batches"]
    )
    for domain in ("airline", "retail"):
        assert not (
            set(assignment["train"][domain])
            & set(assignment["selection"][domain])
        )
        assert not (
            (set(assignment["train"][domain]) | set(assignment["selection"][domain]))
            & set(split["official_test"][domain])
        )


def test_tau3_split_rebuild_is_deterministic_and_matches_frozen_file() -> None:
    first = build_frozen_split(TAU2_ROOT, campaign_seed=200)
    second = build_frozen_split(TAU2_ROOT, campaign_seed=200)
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert first == second == frozen
