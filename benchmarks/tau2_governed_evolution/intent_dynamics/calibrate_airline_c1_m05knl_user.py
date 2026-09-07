"""Small fixed-seed UserSimulator calibration for the Airline C1 pair."""

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
from benchmarks.tau2_governed_evolution.intent_dynamics.probe_airline_c1_m05knl import (
    P0_PROPOSAL,
    P1_PROPOSAL,
)
from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_c1_m05knl import (
    load_pair,
)


ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage  # noqa: E402
from tau2.user.user_simulator import UserSimulator  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL = "openai/deepseek-v4-flash"
DEFAULT_SEEDS = (300, 301, 302)
STOP = "###STOP###"
DEADLINE = re.compile(r"\b7(?::00)?\s*(?:pm|p\.m\.)\b", re.IGNORECASE)


def _contains_yes(value: str) -> bool:
    return bool(re.search(r"\byes\b", value, re.IGNORECASE))


def _run_one(variant: str, seed: int, model: str) -> dict[str, Any]:
    tasks, _ = load_pair()
    task = tasks[f"airline_c1_m05knl_{variant}"]
    user = UserSimulator(
        llm=model,
        instructions=str(task.user_scenario),
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
        "variant": variant,
        "seed": seed,
        "initial": initial.content,
    }
    if variant == "revision":
        revision, state = user.generate_next_message(
            AssistantMessage.text(P0_PROPOSAL), state
        )
        result["revision"] = revision.content
    confirmation, _ = user.generate_next_message(
        AssistantMessage.text(P1_PROPOSAL), state
    )
    result["confirmation"] = confirmation.content
    return result


def _checks(result: dict[str, Any]) -> dict[str, bool]:
    initial = result["initial"]
    confirmation = result["confirmation"]
    checks = {
        "initial_has_user_id": "aarav_garcia_1177" in initial,
        "initial_has_reservation_id": "M05KNL" in initial,
        "confirmation_is_explicit_yes": _contains_yes(confirmation),
        "confirmation_does_not_stop_before_write": STOP not in confirmation,
    }
    if result["variant"] == "upfront":
        checks["upfront_initial_has_deadline"] = bool(DEADLINE.search(initial))
    else:
        revision = result["revision"]
        checks.update(
            {
                "revision_initial_requests_cheapest_economy": (
                    "cheapest" in initial.lower() and "economy" in initial.lower()
                ),
                "revision_initial_hides_deadline": (
                    not DEADLINE.search(initial)
                    and all(
                        marker not in initial.lower()
                        for marker in ("arrival", "arrive", "late", "midnight")
                    )
                ),
                "revision_rejects_late_p0": any(
                    marker in revision.lower()
                    for marker in ("too late", "after midnight", "after 7")
                ),
                "revision_first_reveals_deadline": bool(DEADLINE.search(revision)),
                "revision_is_not_qualified_yes": not _contains_yes(revision),
                "revision_does_not_stop": STOP not in revision,
            }
        )
    return checks


def run_calibration(
    *, model: str = DEFAULT_MODEL, seeds: tuple[int, ...] = DEFAULT_SEEDS
) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    samples = []
    with ThreadPoolExecutor(max_workers=min(3, len(seeds) * 2)) as executor:
        futures = [
            executor.submit(_run_one, variant, seed, model)
            for variant in ("upfront", "revision")
            for seed in seeds
        ]
        for future in as_completed(futures):
            sample = future.result()
            sample["checks"] = _checks(sample)
            sample["passed"] = all(sample["checks"].values())
            samples.append(sample)
    samples.sort(key=lambda item: (item["variant"], item["seed"]))
    return {
        "model": model,
        "seeds": list(seeds),
        "passed": all(item["passed"] for item in samples),
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    args = parser.parse_args()
    result = run_calibration(model=args.model, seeds=tuple(args.seeds))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
