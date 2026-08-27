"""Frozen τ³ v0.11 Evolution/Holdout assignment."""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any

from src.adapters.tau2.tau3_task_split import DOMAINS, Tau3SplitError


def _load_official_splits(tau2_root: Path) -> dict[str, dict[str, list[str]]]:
    return {
        domain: json.loads(
            (
                tau2_root
                / "data/tau2/domains"
                / domain
                / "split_tasks.json"
            ).read_text(encoding="utf-8")
        )
        for domain in DOMAINS
    }


def build_frozen_split(tau2_root: Path, campaign_seed: int = 200) -> dict[str, Any]:
    """Deterministically select 60 train tasks and 40 official-test tasks."""

    official = _load_official_splits(tau2_root)
    evolution: dict[str, list[str]] = {}
    holdout: dict[str, list[str]] = {}
    for domain in DOMAINS:
        train = list(official[domain]["train"])
        random.Random(f"{campaign_seed}:evolution:{domain}").shuffle(train)
        evolution[domain] = train[:30]

        test = list(official[domain]["test"])
        if domain == "airline" and len(test) == 20:
            holdout[domain] = test
        else:
            random.Random(f"{campaign_seed}:holdout:{domain}").shuffle(test)
            holdout[domain] = test[:20]

    batches = []
    for index in range(3):
        task_ids = [
            *(
                f"airline:{task_id}"
                for task_id in evolution["airline"][index * 10 : (index + 1) * 10]
            ),
            *(
                f"retail:{task_id}"
                for task_id in evolution["retail"][index * 10 : (index + 1) * 10]
            ),
        ]
        batches.append({"batch_id": f"batch_{index + 1}", "task_ids": task_ids})

    result = {
        "schema_version": "tau3_gse_task_split_0.11.0",
        "campaign_seed": campaign_seed,
        "assignment": {
            "evolution": evolution,
            "holdout": holdout,
        },
        "batches": batches,
        "provenance": {
            "evolution_source_split": "official_train",
            "holdout_source_split": "official_test",
        },
    }
    validate_frozen_split(result, official)
    return result


def validate_frozen_split(
    split: dict[str, Any],
    official_splits: dict[str, dict[str, list[str]]],
) -> None:
    if split.get("schema_version") != "tau3_gse_task_split_0.11.0":
        raise Tau3SplitError("Invalid v0.11 split schema.")
    assignment = split.get("assignment", {})
    evolution = assignment.get("evolution", {})
    holdout = assignment.get("holdout", {})
    for domain in DOMAINS:
        train_ids = evolution.get(domain)
        test_ids = holdout.get(domain)
        if not isinstance(train_ids, list) or len(train_ids) != 30:
            raise Tau3SplitError(f"Evolution requires 30 {domain} tasks.")
        if not isinstance(test_ids, list) or len(test_ids) != 20:
            raise Tau3SplitError(f"Holdout requires 20 {domain} tasks.")
        if len(set(train_ids)) != 30 or not set(train_ids) <= set(
            official_splits[domain]["train"]
        ):
            raise Tau3SplitError(f"Evolution {domain} assignment is invalid.")
        if len(set(test_ids)) != 20 or not set(test_ids) <= set(
            official_splits[domain]["test"]
        ):
            raise Tau3SplitError(f"Holdout {domain} assignment is invalid.")
        if set(train_ids) & set(test_ids):
            raise Tau3SplitError("Official Test leaked into Evolution.")

    batches = split.get("batches")
    if not isinstance(batches, list) or len(batches) != 3:
        raise Tau3SplitError("Exactly three Evolution batches are required.")
    flattened: list[str] = []
    for index, batch in enumerate(batches, start=1):
        task_ids = batch.get("task_ids", [])
        if (
            batch.get("batch_id") != f"batch_{index}"
            or len(task_ids) != 20
            or sum(item.startswith("airline:") for item in task_ids) != 10
            or sum(item.startswith("retail:") for item in task_ids) != 10
        ):
            raise Tau3SplitError("Each batch requires 10 Airline and 10 Retail tasks.")
        flattened.extend(task_ids)
    expected = {
        *(f"airline:{item}" for item in evolution["airline"]),
        *(f"retail:{item}" for item in evolution["retail"]),
    }
    if len(flattened) != 60 or len(set(flattened)) != 60 or set(flattened) != expected:
        raise Tau3SplitError("Evolution batches must exactly partition 60 tasks.")


def load_frozen_split(path: Path, tau2_root: Path) -> dict[str, Any]:
    split = json.loads(path.read_text(encoding="utf-8"))
    validate_frozen_split(split, _load_official_splits(tau2_root))
    return copy.deepcopy(split)
