"""Fixed-seed UserSimulator calibration for every Airline C1 pair."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)
from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_c1_family import (
    load_family,
)


ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage  # noqa: E402
from tau2.user.user_simulator import UserSimulator  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL = "openai/deepseek-v4-flash"
DEFAULT_SEEDS = (310, 311, 312)
STOP = "###STOP###"


def _matches(pattern: str, value: str) -> bool:
    return bool(re.search(pattern, value, re.IGNORECASE))


def _contains_yes(value: str) -> bool:
    return _matches(r"\byes\b", value)


def _role_is_customer(value: str) -> bool:
    return not _matches(
        r"how can I help|please provide (?:your|the) (?:user|reservation)|"
        r"I (?:can|will) (?:look up|search|check) (?:your|the) reservation",
        value,
    )


def _run_one(
    pair_id: str, record: dict[str, Any], variant: str, seed: int, model: str
) -> dict[str, Any]:
    pair, tasks = record["pair"], record["tasks"]
    task_id = next(
        item["task_id"] for item in pair["variants"] if item["variant"] == variant
    )
    user = UserSimulator(
        llm=model,
        instructions=str(tasks[task_id].user_scenario),
        llm_args={
            "temperature": 0,
            "seed": seed,
            "reasoning_effort": "high",
            "max_tokens": 8192,
            "empty_response_retries": 2,
            "empty_response_retry_max_tokens": 8192,
            "invalid_tool_arguments_retries": 2,
        },
    )
    state = user.get_init_state()
    initial, state = user.generate_next_message(
        AssistantMessage.text("Hello, how can I help you today?"), state
    )
    result = {
        "pair_id": pair_id,
        "variant": variant,
        "seed": seed,
        "initial": initial.content,
    }
    if variant == "revision":
        revision, state = user.generate_next_message(
            AssistantMessage.text(pair["probe_text"]["p0_proposal"]), state
        )
        result["revision"] = revision.content
    confirmation, _ = user.generate_next_message(
        AssistantMessage.text(pair["probe_text"]["p1_proposal"]), state
    )
    result["confirmation"] = confirmation.content
    return result


def _checks(result: dict[str, Any], pair: dict[str, Any]) -> dict[str, bool]:
    initial = result["initial"]
    confirmation = result["confirmation"]
    reservation_id = pair["underlying_state"]["reservation_id"]
    user_id = pair["underlying_state"]["user_id"]
    calibration = pair["calibration"]
    checks = {
        "initial_has_user_id": user_id in initial,
        "initial_has_reservation_id": reservation_id in initial,
        "initial_keeps_customer_role": _role_is_customer(initial),
        "confirmation_is_explicit_yes": _contains_yes(confirmation),
        "confirmation_does_not_stop_before_write": STOP not in confirmation,
        "confirmation_keeps_customer_role": _role_is_customer(confirmation),
    }
    if result["variant"] == "upfront":
        checks["upfront_initial_has_final_constraint"] = _matches(
            calibration["upfront_initial_required_regex"], initial
        )
    else:
        revision = result["revision"]
        checks.update(
            {
                "revision_initial_has_i0": _matches(
                    calibration["revision_initial_required_regex"], initial
                ),
                "revision_initial_hides_latent_constraint": not _matches(
                    calibration["revision_initial_forbidden_regex"], initial
                ),
                "revision_rejects_p0": _matches(
                    calibration["revision_response_rejection_regex"], revision
                ),
                "revision_first_reveals_final_constraint": _matches(
                    calibration["revision_response_required_regex"], revision
                ),
                "revision_is_not_qualified_yes": not _contains_yes(revision),
                "revision_does_not_stop": STOP not in revision,
                "revision_keeps_customer_role": _role_is_customer(revision),
            }
        )
        if "revision_initial_payment_regex" in calibration:
            checks["revision_initial_has_payment_paths"] = _matches(
                calibration["revision_initial_payment_regex"], initial
            )
    return checks


def run_calibration(
    *,
    model: str = DEFAULT_MODEL,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    pair_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    _, records = load_family()
    selected = tuple(pair_ids or records.keys())
    unknown = set(selected) - set(records)
    if unknown:
        raise ValueError(f"Unknown pair IDs: {sorted(unknown)}")
    samples = []
    with ThreadPoolExecutor(max_workers=min(6, len(records) * 2)) as executor:
        futures = [
            executor.submit(_run_one, pair_id, record, variant, seed, model)
            for pair_id in selected
            for record in (records[pair_id],)
            for variant in ("upfront", "revision")
            for seed in seeds
        ]
        for future in as_completed(futures):
            sample = future.result()
            pair = records[sample["pair_id"]]["pair"]
            sample["checks"] = _checks(sample, pair)
            sample["passed"] = all(sample["checks"].values())
            samples.append(sample)
    samples.sort(key=lambda item: (item["pair_id"], item["variant"], item["seed"]))
    pair_summary = {
        pair_id: {
            "passed": all(item["passed"] for item in samples if item["pair_id"] == pair_id),
            "sample_count": sum(1 for item in samples if item["pair_id"] == pair_id),
        }
        for pair_id in selected
    }
    return {
        "model": model,
        "seeds": list(seeds),
        "passed": all(item["passed"] for item in samples),
        "pair_summary": pair_summary,
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--pairs", nargs="+")
    args = parser.parse_args()
    result = run_calibration(
        model=args.model,
        seeds=tuple(args.seeds),
        pair_ids=tuple(args.pairs) if args.pairs else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
