"""Static validation for the reviewed unified Phase-A context artifacts.

This module performs no rollout, agent, model, user-simulator, or evaluator call.
"""

from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = Path(__file__).resolve().parent
UNIFIED = DIRECTORY / "unified"

POLICY_PATHS = {
    "airline": PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/airline/policy.md",
    "retail": PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/retail/policy.md",
}
REGISTRY_PATHS = {
    domain: DIRECTORY / f"{domain}_semantic_registry.json"
    for domain in ("airline", "retail")
}
UNIFIED_POLICY_PATHS = {
    domain: UNIFIED / f"{domain}_phase_a_policy.md"
    for domain in ("airline", "retail")
}
OVERRIDE_PATHS = {
    domain: UNIFIED / f"{domain}_phase_a_tool_overrides.json"
    for domain in ("airline", "retail")
}

POLICY_EDITS = {
    "airline": [
        {
            "location": "Modify flight / Change flights",
            "before": "- Some flight segments can be kept, but their prices will not be updated based on the current price.",
            "after": "- Some flight segments can be kept.",
            "ids": ["AIR_POLICY_FLIGHT_HISTORY_001"],
        },
        {
            "location": "Modify flight / Change flights",
            "before": "- The API does not check these for the agent, so the agent must make sure the rules apply before calling the API!\n",
            "after": "",
            "ids": ["AIR_POLICY_FLIGHT_ENFORCEMENT_001"],
        },
        {
            "location": "Cancel flight",
            "before": "The API does not check that cancellation rules are met, so the agent must make sure the rules apply before calling the API!\n\n",
            "after": "",
            "ids": ["AIR_POLICY_CANCEL_ENFORCEMENT_001"],
        },
    ],
    "retail": [
        {
            "location": "Modify pending order / Modify items",
            "before": (
                "This action can only be called once, and will change the order status to "
                "'pending (items modifed)'. The agent will not be able to modify or cancel "
                "the order anymore. So you must confirm all the details are correct and be "
                "cautious before taking this action. In particular, remember to remind the "
                "customer to confirm they have provided all the items they want to modify."
            ),
            "after": (
                "This action can only be called once. So you must confirm all the details are "
                "correct and be cautious before taking this action. In particular, remember "
                "to remind the customer to confirm they have provided all the items they want "
                "to modify."
            ),
            "ids": [
                "RET_POLICY_MODIFY_ITEMS_STATUS_001",
                "RET_POLICY_MODIFY_ITEMS_FUTURE_MODIFY_001",
                "RET_POLICY_MODIFY_ITEMS_FUTURE_CANCEL_001",
            ],
        }
    ],
}

TOOL_EDITS = {
    "airline": [],
    "retail": [
        {
            "tool": "cancel_pending_order",
            "location": "function.description",
            "before": (
                "The refund will be added to the user's gift card balance immediately if the payment\n"
                "was made using a gift card, otherwise the refund would take 5-7 business days to process."
            ),
            "after": (
                "The refund is immediate if the payment was made using a gift card; otherwise, "
                "the refund takes 5-7 business days to process."
            ),
            "ids": ["RET_TOOL_CANCEL_DETAILS_004"],
        }
    ],
}

EXPECTED_HIDE = {
    domain: {
        knowledge_id
        for edit in POLICY_EDITS[domain] + TOOL_EDITS[domain]
        for knowledge_id in edit["ids"]
    }
    for domain in ("airline", "retail")
}

PROTECTED_PHRASES = {
    "airline": [
        "Basic economy flights cannot be modified.",
        "Otherwise, flight can be cancelled if any of the following is true:",
        "obtain explicit user confirmation (yes)",
        "Some flight segments can be kept.",
        "each piece of flight in the ENTIRE new reservation",
        "All payment methods must already be in user profile",
        "If the booking user is a regular member:",
        "If the booking user is a silver member:",
        "If the booking user is a gold member:",
        "Each extra baggage is 50 dollars.",
        "Each reservation can have at most five passengers.",
        "There are two types of trip: **one way** and **round trip**.",
        "There are three cabin classes: **basic economy**, **economy**, **business**.",
    ],
    "retail": [
        "authenticate the user identity",
        "obtain explicit user confirmation (yes)",
        "This action can only be called once.",
        "same product but of different product option",
        "There could be duplicate items in the list.",
        "in the same position and be of the same product.",
        "payment method to pay or receive refund of the price difference",
        "The refund must either go to the original payment method, or an existing gift card.",
        "payment will be refunded.",
        "The refund is immediate if the payment was made using a gift card",
        "An order can only be returned if its status is 'delivered'",
        "An order can only be exchanged if its status is 'delivered'",
        "the total will be refunded via the original payment method",
    ],
}

FORBIDDEN_PHRASES = {
    "airline": [
        "their prices will not be updated based on the current price",
        "The API does not check these for the agent",
        "The API does not check that cancellation rules are met",
    ],
    "retail": [
        "pending (items modifed)",
        "will not be able to modify or cancel the order anymore",
        "added to the user's gift card balance",
    ],
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _phase_a_action(entry: dict[str, Any]) -> str:
    if entry["agent_visible_in_canonical_runtime"] == "NO":
        return "NO_CHANGE"
    if entry["primary_role"] == "L":
        return "HIDE"
    return "KEEP"


def _canonical_tool_surfaces() -> dict[str, dict[str, Any]]:
    sys.path.insert(0, str(PROJECT_ROOT / "external/tau2-bench/src"))
    from tau2.domains.airline.tools import AirlineTools
    from tau2.domains.retail.tools import RetailTools

    return {
        "airline": {
            name: tool.openai_schema["function"]
            for name, tool in AirlineTools(None).get_tools().items()
        },
        "retail": {
            name: tool.openai_schema["function"]
            for name, tool in RetailTools(None).get_tools().items()
        },
    }


def validate() -> dict[str, Any]:
    registries = {domain: _load(path) for domain, path in REGISTRY_PATHS.items()}
    canonical_tools = _canonical_tool_surfaces()
    summary: dict[str, Any] = {
        "ADDED_NONCANONICAL_INFORMATION": 0,
        "NON_LATENT_REMOVAL": 0,
        "domains": {},
        "same_domain_context_for_all_tasks": False,
        "protected_visible_semantics_preserved": False,
        "all_reviewed_hide_units_transformed": False,
    }

    transformed_hide: set[str] = set()
    all_protected = True
    for domain in ("airline", "retail"):
        entries = registries[domain]["entries"]
        by_id = {entry["knowledge_id"]: entry for entry in entries}
        derived_hide = {
            entry["knowledge_id"] for entry in entries
            if _phase_a_action(entry) == "HIDE"
        }
        if derived_hide != EXPECTED_HIDE[domain]:
            raise AssertionError(
                f"{domain} reviewed HIDE drift: derived={sorted(derived_hide)} "
                f"expected={sorted(EXPECTED_HIDE[domain])}"
            )

        canonical_policy = POLICY_PATHS[domain].read_text(encoding="utf-8")
        expected_policy = canonical_policy
        for edit in POLICY_EDITS[domain]:
            if expected_policy.count(edit["before"]) != 1:
                raise AssertionError(f"{domain} canonical policy edit source drift: {edit['ids']}")
            for knowledge_id in edit["ids"]:
                if _phase_a_action(by_id[knowledge_id]) != "HIDE":
                    summary["NON_LATENT_REMOVAL"] += 1
            expected_policy = expected_policy.replace(edit["before"], edit["after"])
            transformed_hide.update(edit["ids"])

        unified_policy = UNIFIED_POLICY_PATHS[domain].read_text(encoding="utf-8")
        expected_artifact_policy = expected_policy.rstrip("\n") + "\n"
        if unified_policy != expected_artifact_policy:
            summary["ADDED_NONCANONICAL_INFORMATION"] += 1

        override = _load(OVERRIDE_PATHS[domain])
        if override["override_scope"] != "agent_visible_description_only":
            raise AssertionError(f"{domain} override broadens beyond descriptions")
        if set(override["overrides"]) != {edit["tool"] for edit in TOOL_EDITS[domain]}:
            raise AssertionError(f"{domain} tool override set drift")

        unified_tools = deepcopy(canonical_tools[domain])
        for edit in TOOL_EDITS[domain]:
            tool_name = edit["tool"]
            canonical_description = canonical_tools[domain][tool_name]["description"]
            if canonical_description.count(edit["before"]) != 1:
                raise AssertionError(f"{domain} canonical tool edit source drift: {edit['ids']}")
            expected_description = canonical_description.replace(edit["before"], edit["after"])
            actual_override = override["overrides"][tool_name]
            if set(actual_override) != {"description", "removed_registry_ids"}:
                raise AssertionError(f"{domain}/{tool_name} override changes unsupported fields")
            if actual_override["description"] != expected_description:
                summary["ADDED_NONCANONICAL_INFORMATION"] += 1
            if actual_override["removed_registry_ids"] != edit["ids"]:
                raise AssertionError(f"{domain}/{tool_name} registry mapping drift")
            for knowledge_id in edit["ids"]:
                if _phase_a_action(by_id[knowledge_id]) != "HIDE":
                    summary["NON_LATENT_REMOVAL"] += 1
            unified_tools[tool_name]["description"] = actual_override["description"]
            transformed_hide.update(edit["ids"])

        if override["canonical_tool_surface_sha256"] != _sha256_json(canonical_tools[domain]):
            raise AssertionError(f"{domain} canonical tool surface hash drift")
        if override["unified_tool_surface_sha256"] != _sha256_json(unified_tools):
            raise AssertionError(f"{domain} unified tool surface hash drift")

        visible_text = unified_policy + "\n" + "\n".join(
            tool["description"] for tool in unified_tools.values()
        ) + "\n" + json.dumps(unified_tools, ensure_ascii=False)
        missing = [phrase for phrase in PROTECTED_PHRASES[domain] if phrase not in visible_text]
        leaks = [phrase for phrase in FORBIDDEN_PHRASES[domain] if phrase in visible_text]
        if missing or leaks:
            all_protected = False
            raise AssertionError(f"{domain} protected/latent check failed: missing={missing}, leaks={leaks}")

        summary["domains"][domain] = {
            "context_id": override["context_id"],
            "canonical_policy_sha256": _sha256_text(canonical_policy),
            "unified_policy_sha256": _sha256_text(unified_policy),
            "canonical_visible_l_units_removed": len(EXPECTED_HIDE[domain]),
            "policy_edits": len(POLICY_EDITS[domain]),
            "tool_description_edits": len(TOOL_EDITS[domain]),
            "hide_ids": sorted(EXPECTED_HIDE[domain]),
            "protected_phrase_checks": len(PROTECTED_PHRASES[domain]),
        }

    manifest = _load(UNIFIED / "unified_context_manifest.json")
    expected_ids = {
        "airline": "AIRLINE_PHASE_A_UNIFIED_V1",
        "retail": "RETAIL_PHASE_A_UNIFIED_V1",
    }
    summary["same_domain_context_for_all_tasks"] = (
        manifest["selection_key"] == "domain"
        and manifest["task_specific_switching"] is False
        and {
            domain: value["context_id"]
            for domain, value in manifest["contexts"].items()
        } == expected_ids
    )
    summary["protected_visible_semantics_preserved"] = all_protected
    summary["all_reviewed_hide_units_transformed"] = transformed_hide == set().union(
        *EXPECTED_HIDE.values()
    )

    ready = (
        summary["ADDED_NONCANONICAL_INFORMATION"] == 0
        and summary["NON_LATENT_REMOVAL"] == 0
        and summary["same_domain_context_for_all_tasks"]
        and summary["protected_visible_semantics_preserved"]
        and summary["all_reviewed_hide_units_transformed"]
    )
    summary["UNIFIED_PHASE_A_CONTEXT_VERDICT"] = (
        "READY_FOR_SUCCESS_V1" if ready else "CONTEXT_TRANSFORMATION_DIRTY"
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
