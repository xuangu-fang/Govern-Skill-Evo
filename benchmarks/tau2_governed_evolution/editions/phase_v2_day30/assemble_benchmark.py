"""Assemble the Day 30 phase-v2 task set from its checked-in sources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EDITION = Path(__file__).resolve().parent
ROOT = EDITION.parents[3]
PHASE_V1 = EDITION.parent / "phase_v1_day30"
ADVANCED = EDITION / "construction" / "advanced_structure"
EXCLUDED_DUPLICATES = {
    "travel_request_027",
    "travel_request_031",
    "travel_request_033",
    "travel_request_035",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def source(relative: str) -> Path:
    return ADVANCED / relative


def append_tasks(
    assembled: list[dict[str, Any]],
    records: list[dict[str, str]],
    tasks: list[dict[str, Any]],
    path: Path,
) -> None:
    for task in tasks:
        task_id = task["id"]
        if task_id in EXCLUDED_DUPLICATES:
            continue
        assembled.append(task)
        records.append({"task_id": task_id, "source": str(path.relative_to(ROOT))})


def main() -> None:
    assembled: list[dict[str, Any]] = []
    records: list[dict[str, str]] = []

    phase_v1 = PHASE_V1 / "benchmark/formal_manifestation_admission/tasks/expanded_tasks.json"
    append_tasks(assembled, records, load_json(phase_v1), phase_v1)

    simple_sources = [
        "phase13_cs_reachable_clean_task_realization/tasks/candidate_tasks.json",
        "phase14t_tensioned_cs_reachable_realization/tasks/candidate_tasks.json",
        "phase15b_separable_cross_axis_vf_realization/tasks/candidate_tasks.json",
        "phase16c_latent_governance_variant_family_realization/tasks/candidate_tasks.json",
        "phase17b_separable_cross_axis_v2_clean_realization/tasks/candidate_tasks.json",
    ]
    for relative in simple_sources:
        path = source(relative)
        append_tasks(assembled, records, load_json(path), path)

    phase15f = source(
        "phase15f_independent_cross_axis_realization/"
        "independent_separable_vf_candidate_pool_v1.json"
    )
    phase15f_tasks = [candidate["task"] for candidate in load_json(phase15f)["candidates"]]
    append_tasks(assembled, records, phase15f_tasks, phase15f)

    ids = [task["id"] for task in assembled]
    if len(ids) != 72 or len(ids) != len(set(ids)):
        raise ValueError(f"expected 72 unique tasks, got {len(ids)} tasks and {len(set(ids))} ids")

    benchmark = EDITION / "benchmark"
    benchmark.mkdir(exist_ok=True)
    (benchmark / "tasks.json").write_text(
        json.dumps(assembled, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    manifest = {
        "edition": "phase_v2_day30",
        "task_count": len(assembled),
        "excluded_exact_duplicates": sorted(EXCLUDED_DUPLICATES),
        "tasks": records,
    }
    (benchmark / "task_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
