"""Offline fixtures; conversion generates test inputs, never repairs model output."""
import re
from src.skill_evolution.v23.editor import actual_diff
from tests.skill_evolution.v23_4.helpers import Fake, keep, withdraw, memory as legacy_memory, read


def patch(old, new):
    return re.sub(r"^@@ [^\n]+\n", "@@\n", actual_diff(old, new), flags=re.M)


def revise(payload, index=0, replacement="Allow relevant inspections while retaining the visible goal.\n"):
    update = payload["plan"]["updates"][index]
    return {"target": update["id"], "focus": ["S"], "change": "Permit relevant inspections.",
            "reason": "Current `P1:1` motivates exploration; benefit remains unverified.",
            "to": {"patch": patch(update["text"], replacement)}}


def memory(payload):
    from src.skill_evolution.v23.memory import normalize_memory, LEGACY_CONTRACT
    return normalize_memory(legacy_memory(payload), source_contract=LEGACY_CONTRACT)
