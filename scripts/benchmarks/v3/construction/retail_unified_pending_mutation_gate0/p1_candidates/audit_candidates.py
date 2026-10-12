#!/usr/bin/env python3
"""Materialize and zero-model audit eight pre-ID P1 trigger surfaces."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/retail_unified_pending_mutation_gate0/p1_candidates')
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from src.benchmark_v3.construction.retail_unified_pending_mutation_gate0.environment import get_environment  # noqa: E402
from src.benchmark_v3.construction.retail_unified_pending_mutation_gate0.evaluator import evaluate  # noqa: E402


SPECS = HERE / "specs.json"
INPUTS = HERE / "candidate_inputs.json"
RESULT = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/retail_unified_pending_mutation_gate0/p1_candidates/shortcut_audit.json')


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def address_text(address: dict[str, str]) -> str:
    parts = [address["address1"]]
    if address["address2"]:
        parts.append(address["address2"])
    parts.extend((address["city"], address["state"], address["zip"], address["country"]))
    return ", ".join(parts)


def prompt(spec: dict[str, Any]) -> str:
    item = f"replace the {spec['old_variant']} {spec['product_name']} with the available {spec['new_variant']} version"
    payment = (
        f"move the whole-order payment from the card ending {spec['old_payment_id'][-4:]} "
        f"to the card ending {spec['new_payment_id'][-4:]} and use the new card for the price difference"
    )
    address = None if spec["new_address"] is None else f"send this order to {address_text(spec['new_address'])}"
    ordered = [item, payment] if spec["request_relation"] == "item_before_payment" else [payment, item]
    if address:
        ordered.insert(1, address)
    joins = {
        "direct": "; also, ",
        "bundled": ", and please ",
        "concise": "; ",
        "conversational": ". I would also like you to ",
    }
    request = joins[spec["template"]].join(ordered)
    openings = {
        "direct": "Please update my pending order",
        "bundled": "I need a few changes on pending order",
        "concise": "Update pending order",
        "conversational": "Could you help revise pending order",
    }
    return (
        f"I am {spec['name']}, email {spec['email']}. {openings[spec['template']]} "
        f"{spec['order_id']}: {request}. Keep every other field unchanged."
    )


def apply_correct(spec: dict[str, Any]) -> dict[str, Any]:
    env = get_environment()
    env.tools.modify_pending_order_payment(spec["order_id"], spec["new_payment_id"])
    if spec["new_address"] is not None:
        env.tools.modify_pending_order_address(spec["order_id"], **spec["new_address"])
    env.tools.modify_pending_order_items(
        spec["order_id"], [spec["old_item_id"]], [spec["new_item_id"]], spec["new_payment_id"]
    )
    return evaluate(spec, env.tools.db.model_dump(mode="json"))


def apply_competing(spec: dict[str, Any]) -> tuple[dict[str, Any], str]:
    env = get_environment()
    env.tools.modify_pending_order_items(
        spec["order_id"], [spec["old_item_id"]], [spec["new_item_id"]], spec["new_payment_id"]
    )
    try:
        env.tools.modify_pending_order_payment(spec["order_id"], spec["new_payment_id"])
    except ValueError as error:
        return evaluate(spec, env.tools.db.model_dump(mode="json")), str(error)
    raise AssertionError("items-first competing path unexpectedly allowed whole-order payment replacement")


def predictor_accuracy(rows: list[dict[str, Any]], field: str) -> float:
    buckets: dict[Any, Counter[str]] = {}
    for row in rows:
        buckets.setdefault(row[field], Counter())[row["request_relation"]] += 1
    return sum(max(counts.values()) for counts in buckets.values()) / len(rows)


def main() -> None:
    payload = load(SPECS)
    rows = payload["candidates"]
    assert payload["formal_task_ids_allocated"] == 0
    assert len(rows) == 8
    assert Counter(row["request_relation"] for row in rows) == {
        "item_before_payment": 4,
        "payment_before_item": 4,
    }
    for field in ("label", "order_id", "user_id", "email", "old_item_id", "new_item_id", "old_payment_id", "new_payment_id"):
        assert len({row[field] for row in rows}) == 8

    prompts = {row["label"]: prompt(row) for row in rows}
    paths = {}
    for row in rows:
        correct = apply_correct(row)
        competing, rejection = apply_competing(row)
        assert correct["success"] and not competing["success"]
        assert "exactly one payment" in rejection
        text = prompts[row["label"]].lower()
        item_position = text.index("replace the")
        payment_position = text.index("whole-order payment")
        assert (item_position < payment_position) == (row["request_relation"] == "item_before_payment")
        paths[row["label"]] = {
            "correct_payment_before_items": "CS",
            "competing_items_before_payment": "CF",
            "payment_rejection": rejection,
        }

    audit_rows = [
        {
            **row,
            "candidate_position_parity": index % 2,
            "label_suffix_parity": (ord(row["label"][-1]) - ord("a") + 1) % 2,
            "order_suffix_parity": int(row["order_id"][-1]) % 2,
            "payment_suffix_parity": int(row["new_payment_id"][-1]) % 2,
            "has_address": row["new_address"] is not None,
            "old_price_band": "high" if row["old_price"] >= 100 else "low",
        }
        for index, row in enumerate(rows)
    ]
    fields = [
        "candidate_position_parity", "label_suffix_parity", "order_suffix_parity",
        "payment_suffix_parity", "template", "price_direction", "has_address", "old_price_band",
    ]
    accuracies = {field: predictor_accuracy(audit_rows, field) for field in fields}
    forbidden_identifier = re.compile(r"trigger|support|sequence|before|after|first|last|item|payment", re.IGNORECASE)
    identifiers_neutral = all(
        not forbidden_identifier.search(" ".join((row["label"], row["order_id"], row["user_id"])))
        for row in rows
    )
    forbidden_prompt = re.compile(r"payment first|items? first|before changing|after changing|must precede|do .* last", re.IGNORECASE)
    mapping_hidden = all(not forbidden_prompt.search(text) for text in prompts.values())
    generated_inputs = {
        "workspace_status": payload["workspace_status"],
        "formal_task_ids_allocated": 0,
        "inputs": [
            {"construction_label": row["label"], "reason_for_call": prompts[row["label"]]}
            for row in rows
        ],
    }
    write(INPUTS, generated_inputs)
    passed = all(value == 0.5 for value in accuracies.values()) and identifiers_neutral and mapping_hidden
    result = {
        "status": "PASS_P1_PURE_SURFACE_SHORTCUT_AUDIT" if passed else "HOLD_P1_PURE_SURFACE_SHORTCUT_AUDIT",
        "family_id": payload["family_id"],
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "candidate_count": len(rows),
        "request_order_counterbalance": dict(Counter(row["request_relation"] for row in rows)),
        "correct_first_write": "modify_pending_order_payment for every candidate",
        "non_mechanism_predictor_target": "request_relation (not the correct path)",
        "non_mechanism_single_field_accuracy": accuracies,
        "non_mechanism_fields_at_chance": all(value == 0.5 for value in accuracies.values()),
        "amount_balance": {
            relation: dict(Counter(row["price_direction"] for row in rows if row["request_relation"] == relation))
            for relation in ("item_before_payment", "payment_before_item")
        },
        "address_balance": {
            relation: dict(Counter(str(row["new_address"] is not None).lower() for row in rows if row["request_relation"] == relation))
            for relation in ("item_before_payment", "payment_before_item")
        },
        "unique_identifiers_are_mechanism_neutral": identifiers_neutral,
        "prompts_hide_required_mutation_sequence": mapping_hidden,
        "path_matrix": paths,
        "verdict": "READY_FOR_PRE_ID_SANITY_CHECK" if passed else "REVISE_SURFACES",
    }
    write(RESULT, result)
    assert passed
    print(result["status"])


if __name__ == "__main__":
    main()
