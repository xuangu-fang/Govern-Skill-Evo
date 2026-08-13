#!/usr/bin/env python3
"""Build the deterministic 3 x 17 Train batch map for Autonomous GSE v0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAMPAIGN_MANIFEST = (
    REPO_ROOT
    / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
)
SCHEMA_VERSION = "autonomous_gse_batch_map_0.1.0"
ALGORITHM = "sha256_rank_v01"
EXPECTED_TEMPLATE_COUNT = 17
EXPECTED_TASKS_PER_TEMPLATE = 3
EXPECTED_BATCH_COUNT = 3
EXPECTED_TASK_COUNT = 51


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def assignment_sha256(seed: str, template_id: int, task_id: int) -> str:
    material = f"{seed}\n{template_id}\n{task_id}".encode("utf-8")
    return sha256_bytes(material)


def _require_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer.")
    return value


def _normalized_train_templates(
    source_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    if source_manifest.get("status") != "frozen":
        raise ValueError("The source task manifest must be frozen.")

    train = source_manifest.get("splits", {}).get("train")
    if not isinstance(train, dict):
        raise ValueError("The source manifest must contain splits.train.")
    if train.get("template_count") != EXPECTED_TEMPLATE_COUNT:
        raise ValueError("Train must declare exactly 17 intent templates.")
    if train.get("task_count") != EXPECTED_TASK_COUNT:
        raise ValueError("Train must declare exactly 51 tasks.")

    templates = train.get("templates")
    if not isinstance(templates, list) or len(templates) != EXPECTED_TEMPLATE_COUNT:
        raise ValueError("Train must contain exactly 17 template records.")

    normalized: list[dict[str, Any]] = []
    seen_template_ids: set[int] = set()
    seen_task_ids: set[int] = set()

    for index, template in enumerate(templates):
        if not isinstance(template, dict):
            raise ValueError(f"Train template {index} must be an object.")

        template_id = _require_int(
            template.get("intent_template_id"),
            f"Train template {index} intent_template_id",
        )
        if template_id in seen_template_ids:
            raise ValueError(f"Duplicate intent template: {template_id}.")
        seen_template_ids.add(template_id)

        task_ids = template.get("task_ids")
        if not isinstance(task_ids, list) or len(task_ids) != (
            EXPECTED_TASKS_PER_TEMPLATE
        ):
            raise ValueError(
                f"Template {template_id} must contain exactly 3 tasks."
            )

        normalized_task_ids: list[int] = []
        for task_id_value in task_ids:
            task_id = _require_int(
                task_id_value,
                f"Template {template_id} task_id",
            )
            if task_id in seen_task_ids:
                raise ValueError(f"Duplicate Train task: {task_id}.")
            seen_task_ids.add(task_id)
            normalized_task_ids.append(task_id)

        normalized.append(
            {
                "intent_template_id": template_id,
                "task_ids": sorted(normalized_task_ids),
            }
        )

    if len(seen_task_ids) != EXPECTED_TASK_COUNT:
        raise ValueError("Train must contain 51 unique tasks.")

    return sorted(normalized, key=lambda item: item["intent_template_id"])


def build_batch_map(
    source_manifest: dict[str, Any],
    *,
    campaign_id: str,
    seed: str,
    source_path: str,
    source_sha256: str,
) -> dict[str, Any]:
    """Return a deterministic, outcome-independent 3 x 17 batch map."""

    if not isinstance(campaign_id, str) or not campaign_id:
        raise ValueError("campaign_id must be a non-empty string.")
    if not isinstance(seed, str) or not seed:
        raise ValueError("assignment seed must be a non-empty string.")
    if not isinstance(source_path, str) or not source_path:
        raise ValueError("source_path must be a non-empty string.")
    if not isinstance(source_sha256, str) or len(source_sha256) != 64:
        raise ValueError("source_sha256 must be a SHA-256 hex digest.")
    try:
        int(source_sha256, 16)
    except ValueError as error:
        raise ValueError("source_sha256 must be a SHA-256 hex digest.") from error

    templates = _normalized_train_templates(source_manifest)
    batch_assignments: list[list[dict[str, Any]]] = [
        [] for _ in range(EXPECTED_BATCH_COUNT)
    ]

    for template in templates:
        template_id = template["intent_template_id"]
        ranked_tasks = sorted(
            (
                {
                    "digest": assignment_sha256(
                        seed,
                        template_id,
                        task_id,
                    ),
                    "intent_template_id": template_id,
                    "task_id": task_id,
                }
                for task_id in template["task_ids"]
            ),
            key=lambda item: (item["digest"], item["task_id"]),
        )

        for rank, task in enumerate(ranked_tasks, start=1):
            batch_assignments[rank - 1].append(
                {
                    "intent_template_id": task["intent_template_id"],
                    "task_id": task["task_id"],
                }
            )

    batches: list[dict[str, Any]] = []
    all_task_ids: list[int] = []
    for rank, assignments in enumerate(batch_assignments, start=1):
        ordered = sorted(
            assignments,
            key=lambda item: item["intent_template_id"],
        )
        task_ids = [item["task_id"] for item in ordered]
        template_ids = [item["intent_template_id"] for item in ordered]
        if len(task_ids) != EXPECTED_TEMPLATE_COUNT:
            raise AssertionError("Planner produced an incomplete batch.")
        if len(set(task_ids)) != EXPECTED_TEMPLATE_COUNT:
            raise AssertionError("Planner produced duplicate tasks in a batch.")
        if len(set(template_ids)) != EXPECTED_TEMPLATE_COUNT:
            raise AssertionError("Planner produced duplicate templates in a batch.")

        all_task_ids.extend(task_ids)
        batches.append(
            {
                "assignments": ordered,
                "batch_id": f"batch_{rank:03d}",
            }
        )

    if len(all_task_ids) != EXPECTED_TASK_COUNT or len(set(all_task_ids)) != (
        EXPECTED_TASK_COUNT
    ):
        raise AssertionError("Planner output does not cover 51 unique tasks.")

    return {
        "assignment": {
            "algorithm": ALGORITHM,
            "seed": seed,
        },
        "batches": batches,
        "campaign_id": campaign_id,
        "schema_version": SCHEMA_VERSION,
        "source": {
            "manifest_id": source_manifest.get("manifest_id"),
            "path": source_path,
            "sha256": source_sha256,
            "split": "train",
        },
        "status": "frozen",
    }


def _resolve_repo_file(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    path.relative_to(REPO_ROOT)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def build_from_campaign_manifest(
    campaign_manifest_path: Path,
) -> dict[str, Any]:
    campaign_manifest = json.loads(
        campaign_manifest_path.read_text(encoding="utf-8")
    )
    if campaign_manifest.get("protocol_version") != "autonomous_gse_v01":
        raise ValueError("Campaign must use autonomous_gse_v01.")
    if campaign_manifest.get("status") not in {"draft", "frozen"}:
        raise ValueError("Campaign status must be draft or frozen.")

    train = campaign_manifest.get("train")
    if not isinstance(train, dict):
        raise ValueError("Campaign must contain a train contract.")

    expected_contract = {
        "assignment_algorithm": ALGORITHM,
        "batches": EXPECTED_BATCH_COUNT,
        "intent_templates": EXPECTED_TEMPLATE_COUNT,
        "outcome_independent_assignment": True,
        "overlap_between_batches": 0,
        "tasks_per_batch": EXPECTED_TEMPLATE_COUNT,
        "tasks_per_template": EXPECTED_TASKS_PER_TEMPLATE,
        "template_balanced": True,
        "total_tasks": EXPECTED_TASK_COUNT,
    }
    mismatches = {
        key: {"expected": expected, "actual": train.get(key)}
        for key, expected in expected_contract.items()
        if train.get(key) != expected
    }
    if mismatches:
        raise ValueError(f"Campaign Train contract mismatch: {mismatches}")

    source = train.get("source_manifest")
    if not isinstance(source, dict):
        raise ValueError("Campaign must bind the source task manifest.")
    source_path_value = source.get("path")
    source_sha = source.get("sha256")
    if not isinstance(source_path_value, str) or not isinstance(source_sha, str):
        raise ValueError("Source task manifest binding is incomplete.")

    source_path = _resolve_repo_file(source_path_value)
    actual_source_sha = sha256_file(source_path)
    if actual_source_sha != source_sha:
        raise ValueError(
            "Source task manifest hash mismatch: "
            f"expected={source_sha}, actual={actual_source_sha}"
        )

    source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
    return build_batch_map(
        source_manifest,
        campaign_id=campaign_manifest["campaign_id"],
        seed=train["assignment_seed"],
        source_path=source_path_value,
        source_sha256=source_sha,
    )


def write_frozen_batch_map(output_path: Path, payload: dict[str, Any]) -> str:
    """Create the batch map without overwriting a frozen artifact."""

    if output_path.exists():
        raise FileExistsError(
            "Frozen batch output already exists; refusing to overwrite: "
            f"{output_path}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    digest = sha256_bytes(data)
    with output_path.open("xb") as handle:
        handle.write(data)

    return digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the deterministic Autonomous GSE v0.1 Train batches."
    )
    parser.add_argument(
        "--campaign-manifest",
        type=Path,
        default=DEFAULT_CAMPAIGN_MANIFEST,
        help="Draft or frozen Autonomous GSE v0.1 campaign manifest.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output batch_map.json; defaults next to the campaign manifest.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = args.campaign_manifest.resolve()
    output_path = (
        args.output.resolve()
        if args.output
        else manifest_path.with_name("batch_map.json")
    )
    payload = build_from_campaign_manifest(manifest_path)
    digest = write_frozen_batch_map(output_path, payload)
    print(f"Wrote {output_path}")
    print(f"SHA-256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
