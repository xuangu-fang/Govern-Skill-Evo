"""Bind model-written historical aliases to the view in which they were written.

This is identity bookkeeping, not interpretation or verification of a response.
The v2 profile reuses v1 behavioral rules and model output shapes unchanged.
"""

import re

from src.adapters.alfworld.verify_skill_run import require


PROFILE = "v22.unified_dsc.v2"
VIEW_SCHEMA = "v22.unified_dsc_view.v2"
HISTORY_REF = re.compile(r"(?<![\w:])(?P<name>H\d+)::")


def capture_reference_contexts(value, historical_contexts):
    """One shared map for all persistent explanations from this learning call."""
    texts = [row["observation"] for row in value["findings"]]
    for delta in value["memory_delta"]:
        texts.extend([delta["claim"], *delta["limits"]])
        texts.extend(row["reason"] for row in delta["retire_limits"])
    used = {match["name"] for text in texts for match in HISTORY_REF.finditer(text)}
    return {name: context for name, context in historical_contexts.items() if name in used}


def reference_contexts_by_origin(memory):
    """Find the generation-time map without assuming current Memory ordering."""
    result = {}
    for effect in memory:
        for basis in effect["basis"]:
            actual = basis["actual_update"]
            if "reference_contexts" not in actual:
                continue
            context, mapping = basis["context_id"], actual["reference_contexts"]
            require(isinstance(mapping, dict) and all(
                isinstance(name, str) and re.fullmatch(r"H\d+", name)
                and isinstance(origin, str) and origin for name, origin in mapping.items()),
                "Invalid historical reference context map.")
            require(context not in result or result[context] == mapping,
                    "Conflicting historical reference context maps.")
            result[context] = mapping
    return result


def rebind_history_references(text, origin, bindings, current_names):
    """Reproject only explicit aliases in prose, before qualifying bare aliases.

Missing legacy provenance stays unknown; neither guess from the current H number
nor block an otherwise valid update. One substitution avoids renaming cascades.
"""
    previous = bindings.get(origin, {})
    return HISTORY_REF.sub(
        lambda match: current_names.get(previous.get(match["name"]), "history_unknown") + "::", text)
