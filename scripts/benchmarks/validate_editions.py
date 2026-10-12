"""Validate all named benchmark editions without running model calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = (Path(__file__).resolve().parents[2] / 'benchmarks/tau2_governed_evolution')
EDITIONS = ROOT / "editions"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_edition(name: str) -> tuple[int, list[str]]:
    edition = EDITIONS / name
    version = load_json(edition / "VERSION.json")
    tasks: list[dict[str, Any]] = []
    errors: list[str] = []
    for relative in version["task_files"]:
        path = edition / relative
        if not path.is_file():
            errors.append(f"missing task file: {relative}")
            continue
        payload = load_json(path)
        if not isinstance(payload, list):
            errors.append(f"task file is not a JSON list: {relative}")
            continue
        tasks.extend(payload)

    ids = [task.get("id") for task in tasks]
    if any(not isinstance(task_id, str) or not task_id for task_id in ids):
        errors.append("every task must have a non-empty string id")
    if len(ids) != len(set(ids)):
        errors.append("task ids are not unique")
    if len(tasks) != version["task_count"]:
        errors.append(f"expected {version['task_count']} tasks, found {len(tasks)}")

    split_file = version.get("split_file")
    if split_file:
        split_path = edition / split_file
        if not split_path.is_file():
            errors.append(f"missing split file: {split_file}")
        else:
            split_payload = load_json(split_path)
            splits = split_payload.get("splits", {})
            split_ids = [task_id for members in splits.values() for task_id in members]
            expected_splits = {"train", "monitor"}
            if version.get("control_task_count", 0):
                expected_splits.add("control")
            if set(splits) != expected_splits:
                errors.append(
                    "split file must contain exactly " + ", ".join(sorted(expected_splits))
                )
            if split_payload.get("test_split") is not None:
                errors.append("test_split must be null")
            if len(split_ids) != len(set(split_ids)):
                errors.append("split membership is not disjoint")
            if set(split_ids) != set(ids):
                errors.append("split membership does not cover the formal task set exactly")
    return len(tasks), errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("editions", nargs="*", help="edition ids; defaults to all editions")
    args = parser.parse_args()
    names = args.editions or sorted(path.name for path in EDITIONS.iterdir() if (path / "VERSION.json").is_file())
    failed = False
    for name in names:
        count, errors = validate_edition(name)
        if errors:
            failed = True
            print(f"FAIL {name}: " + "; ".join(errors))
        else:
            print(f"PASS {name}: {count} unique tasks")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
