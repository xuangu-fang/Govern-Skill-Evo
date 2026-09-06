"""Minimal loader for the v3 Airline novel-policy task pool."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
TAU2_ROOT = REPO_ROOT / "external" / "tau2-bench"
POLICY_PATH = Path(__file__).with_name("airline_policy_v3.md")
TASKS_PATH = Path(__file__).with_name("airline_novel_tasks.json")


def _ensure_tau2_importable() -> None:
    source = str((TAU2_ROOT / "src").resolve())
    if source not in sys.path:
        sys.path.insert(0, source)


def get_environment(*, db=None, solo_mode: bool = False):
    """Build the unchanged Airline environment with the v3 policy text."""
    _ensure_tau2_importable()
    from tau2.domains.airline.data_model import FlightDB
    from tau2.domains.airline.tools import AirlineTools
    from tau2.domains.airline.utils import AIRLINE_DB_PATH
    from tau2.environment.environment import Environment

    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    if db is None:
        db = FlightDB.load(AIRLINE_DB_PATH)
    return Environment(
        domain_name="airline",
        policy=POLICY_PATH.read_text(encoding="utf-8"),
        tools=AirlineTools(db),
    )


def get_tasks():
    """Load the 25 tasks through the original tau2 Task schema."""
    _ensure_tau2_importable()
    from tau2.data_model.tasks import Task

    with TASKS_PATH.open(encoding="utf-8") as stream:
        return [Task.model_validate(item) for item in json.load(stream)]
