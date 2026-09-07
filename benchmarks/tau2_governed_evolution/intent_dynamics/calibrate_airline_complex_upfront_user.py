"""Fixed-seed first-turn and confirmation calibration for Complex-Upfront tasks."""

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
from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_complex_upfront import (
    MANIFEST_PATH,
    load_suite,
)


ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage  # noqa: E402
from tau2.user.user_simulator import UserSimulator  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL = "openai/deepseek-v4-flash"
STOP = "###STOP###"


def _matches(pattern: str, value: str) -> bool:
    return bool(re.search(pattern, value, re.IGNORECASE))


def _customer_role(value: str) -> bool:
    return not _matches(
        r"how can I help|please provide (?:your|the) (?:user|reservation)|"
        r"I (?:can|will) (?:look up|search|check) (?:your|the) reservation",
        value,
    )


def _run_one(spec: dict[str, Any], task: Any, seed: int, model: str) -> dict[str, Any]:
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
    completeness, state = user.generate_next_message(
        AssistantMessage.text(
            "I recorded everything in your first request. Before I read the account, "
            "are there any transaction-relevant goals, constraints, budgets, fallback "
            "rules, payment preferences, or protected items that were not already stated?"
        ),
        state,
    )
    proposal = (
        "I have completed the required reads. Here is the exact complete proposal: "
        + spec["calibration_proposal"]
        + " Do you explicitly confirm that I should now execute this exact proposal?"
    )
    confirmation, _ = user.generate_next_message(
        AssistantMessage.text(proposal), state
    )
    initial_text = initial.content or ""
    completeness_text = completeness.content or ""
    confirmation_text = confirmation.content or ""
    checks = {
        "initial_contains_every_required_fact": all(
            _matches(pattern, initial_text)
            for pattern in spec["initial_required_regexes"]
        ),
        "initial_does_not_stop": STOP not in initial_text,
        "initial_customer_role": _customer_role(initial_text),
        "no_late_constraint_signal": not _matches(
            r"actually|I forgot|one more (?:thing|constraint)|I also need to add|"
            r"another requirement I didn't mention",
            completeness_text,
        ),
        "completeness_turn_does_not_stop": STOP not in completeness_text,
        "confirmation_is_explicit_yes": bool(
            _matches(
                r"^\s*(?:yes\b|confirmed\b|I (?:explicitly )?confirm\b|"
                r"please (?:go ahead|proceed)\b|go ahead\b)",
                confirmation_text,
            )
            and not _matches(
                r"before I (?:approve|confirm|say yes)|need to (?:see|review|verify)|"
                r"do not (?:make|execute|proceed)|don't (?:make|execute|proceed)|"
                r"not yet|but first|only (?:after|once)",
                confirmation_text,
            )
        ),
        "confirmation_does_not_stop": STOP not in confirmation_text,
        "confirmation_customer_role": _customer_role(confirmation_text),
    }
    return {
        "task_id": spec["task_id"],
        "seed": seed,
        "initial": initial_text,
        "completeness_check_response": completeness_text,
        "confirmation": confirmation_text,
        "checks": checks,
        "passed": all(checks.values()),
    }


def run_calibration(*, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    specs = {item["task_id"]: item for item in manifest["tasks"]}
    samples = []
    jobs = [
        (spec, tasks[task_id], seed, model)
        for task_id, spec in specs.items()
        for seed in manifest["calibration_seeds"]
    ]
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(_run_one, *job) for job in jobs]
        for future in as_completed(futures):
            samples.append(future.result())
    samples.sort(key=lambda item: (item["task_id"], item["seed"]))
    return {
        "model": model,
        "manifest": MANIFEST_PATH.as_posix(),
        "seeds": manifest["calibration_seeds"],
        "passed": all(item["passed"] for item in samples),
        "task_summary": {
            task_id: {
                "passed": all(
                    item["passed"] for item in samples if item["task_id"] == task_id
                ),
                "samples": sum(1 for item in samples if item["task_id"] == task_id),
            }
            for task_id in specs
        },
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT
        / "artifacts/airline_complex_upfront_step4/user_calibration.json",
    )
    args = parser.parse_args()
    result = run_calibration(model=args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
