"""Freeze the τ³ Airline/Retail train and Selection assignment."""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any


DOMAINS = ("airline", "retail")


class Tau3SplitError(ValueError):
    """Raised when the frozen τ³ split violates the campaign contract."""


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
    """Build the one-time assignment; callers persist it as ``batch_map.json``."""

    official = _load_official_splits(tau2_root)
    rng = random.Random(campaign_seed)
    shuffled: dict[str, list[str]] = {}
    for domain in DOMAINS:
        shuffled[domain] = list(official[domain]["train"])
        rng.shuffle(shuffled[domain])

    airline_train = shuffled["airline"][:21]
    airline_selection = shuffled["airline"][21:30]
    retail_train = shuffled["retail"][:30]
    retail_selection = shuffled["retail"][30:39]

    batches = []
    for index in range(3):
        tasks = [
            *[
                f"airline:{task_id}"
                for task_id in airline_train[index * 7 : (index + 1) * 7]
            ],
            *[
                f"retail:{task_id}"
                for task_id in retail_train[index * 10 : (index + 1) * 10]
            ],
        ]
        batches.append({"batch_id": f"batch_{index + 1}", "task_ids": tasks})

    result = {
        "schema_version": "tau3_gse_task_split_0.9.0",
        "campaign_seed": campaign_seed,
        "source_split": "official_train",
        "assignment": {
            "train": {
                "airline": airline_train,
                "retail": retail_train,
            },
            "selection": {
                "airline": airline_selection,
                "retail": retail_selection,
            },
            "unused_retail_train": shuffled["retail"][39:],
        },
        "batches": batches,
        "official_test": {
            domain: list(official[domain]["test"]) for domain in DOMAINS
        },
    }
    validate_frozen_split(result, official)
    return result


def validate_frozen_split(
    split: dict[str, Any],
    official_splits: dict[str, dict[str, list[str]]],
) -> None:
    assignment = split.get("assignment", {})
    train = assignment.get("train", {})
    selection = assignment.get("selection", {})
    expected_counts = {
        "train": {"airline": 21, "retail": 30},
        "selection": {"airline": 9, "retail": 9},
    }
    for name, source in (("train", train), ("selection", selection)):
        for domain in DOMAINS:
            values = source.get(domain)
            if not isinstance(values, list) or len(values) != expected_counts[name][
                domain
            ]:
                raise Tau3SplitError(f"Invalid {name} {domain} task count.")
            if not set(values) <= set(official_splits[domain]["train"]):
                raise Tau3SplitError(f"{name} contains non-train {domain} tasks.")
            if set(values) & set(official_splits[domain]["test"]):
                raise Tau3SplitError("Official Test leaked into learning phases.")
        if len(source["airline"]) != len(set(source["airline"])) or len(
            source["retail"]
        ) != len(set(source["retail"])):
            raise Tau3SplitError(f"Duplicate task in {name} assignment.")

    for domain in DOMAINS:
        if set(train[domain]) & set(selection[domain]):
            raise Tau3SplitError("Train and Selection overlap.")

    batches = split.get("batches")
    if not isinstance(batches, list) or len(batches) != 3:
        raise Tau3SplitError("Exactly three Train batches are required.")
    flattened: list[str] = []
    for batch in batches:
        task_ids = batch.get("task_ids", [])
        if (
            len(task_ids) != 17
            or sum(item.startswith("airline:") for item in task_ids) != 7
            or sum(item.startswith("retail:") for item in task_ids) != 10
        ):
            raise Tau3SplitError(
                "Each batch must contain 7 Airline and 10 Retail tasks."
            )
        flattened.extend(task_ids)
    expected = {
        *[f"airline:{item}" for item in train["airline"]],
        *[f"retail:{item}" for item in train["retail"]],
    }
    if len(flattened) != len(set(flattened)) or set(flattened) != expected:
        raise Tau3SplitError("Train batches do not exactly partition Train tasks.")


def load_frozen_split(path: Path, tau2_root: Path) -> dict[str, Any]:
    split = json.loads(path.read_text(encoding="utf-8"))
    validate_frozen_split(split, _load_official_splits(tau2_root))
    return copy.deepcopy(split)
