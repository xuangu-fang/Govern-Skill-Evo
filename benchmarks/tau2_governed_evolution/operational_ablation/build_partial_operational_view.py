"""Build and validate the Step 4U Retail partial operational view."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import (
    PROJECT_ROOT,
)


DIRECTORY = Path(__file__).resolve().parent
CANONICAL_POLICY_PATH = (
    PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/retail/policy.md"
)
PARTIAL_POLICY_PATH = DIRECTORY / "retail_partial_operational_policy.md"

GENERIC_ONE_SHOT = (
    "Exchange or modify order tools can only be called once per order. "
    "Be sure that all items to be changed are collected into a list before making the tool call!!!"
)
MODIFY_OPTION_CLOSING = (
    "This action can only be called once, and will change the order status to 'pending (items modifed)'. "
    "The agent will not be able to modify or cancel the order anymore. So you must confirm all the details "
    "are correct and be cautious before taking this action. In particular, remember to remind the customer "
    "to confirm they have provided all the items they want to modify."
)
EXCHANGE_COLLECTION_REMINDER = (
    " In particular, remember to remind the customer to confirm they have provided all items to be exchanged."
)

FORBIDDEN_POLICY_PATTERNS = (
    r"only be called once",
    r"all items to be changed are collected",
    r"pending \(items modifed\)",
    r"not be able to modify or cancel",
    r"confirm they have provided all (?:the )?items",
)
FORBIDDEN_TOOL_PATTERNS = (
    r"only be called once",
    r"only done once",
    r"can no longer",
    r"cannot (?:be )?modified or cancelled",
)

PARTIAL_TOOL_DESCRIPTIONS = {
    "modify_pending_order_items": (
        "Modify items in a pending order to available items of the same product type but different options. "
        "The agent must explain the item changes and price difference and obtain explicit user confirmation."
    ),
    "exchange_delivered_order_items": (
        "Exchange items in a delivered order for available items of the same product type but different options. "
        "The agent must explain the exchange and price difference and obtain explicit user confirmation."
    ),
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_partial_policy(canonical: str) -> str:
    if canonical.count(GENERIC_ONE_SHOT) != 1:
        raise ValueError("canonical generic one-shot clause drifted")
    if canonical.count(MODIFY_OPTION_CLOSING) != 1:
        raise ValueError("canonical modify option-closing clause drifted")
    if canonical.count(EXCHANGE_COLLECTION_REMINDER) != 1:
        raise ValueError("canonical exchange reminder clause drifted")
    partial = canonical.replace(GENERIC_ONE_SHOT, "")
    partial = partial.replace(
        MODIFY_OPTION_CLOSING,
        "Before modifying items, explain the modification details and obtain explicit user confirmation.",
    )
    partial = partial.replace(EXCHANGE_COLLECTION_REMINDER, "")
    assert_no_operational_leakage(partial, PARTIAL_TOOL_DESCRIPTIONS)
    return partial


def assert_no_operational_leakage(
    policy: str, tool_descriptions: dict[str, str]
) -> None:
    policy_hits = [
        pattern for pattern in FORBIDDEN_POLICY_PATTERNS
        if re.search(pattern, policy, re.I)
    ]
    tool_hits = {
        name: [
            pattern for pattern in FORBIDDEN_TOOL_PATTERNS
            if re.search(pattern, description, re.I)
        ]
        for name, description in tool_descriptions.items()
    }
    tool_hits = {name: hits for name, hits in tool_hits.items() if hits}
    if policy_hits or tool_hits:
        raise ValueError(
            f"partial operational view leaks withheld semantics: policy={policy_hits}, tools={tool_hits}"
        )


def build_and_write() -> dict[str, str]:
    canonical = CANONICAL_POLICY_PATH.read_text(encoding="utf-8")
    partial = build_partial_policy(canonical)
    PARTIAL_POLICY_PATH.write_text(partial, encoding="utf-8")
    return {
        "canonical_policy_sha256": sha256_text(canonical),
        "partial_policy_sha256": sha256_text(partial),
        "partial_policy_path": PARTIAL_POLICY_PATH.as_posix(),
    }


if __name__ == "__main__":
    print(build_and_write())
