#!/usr/bin/env python3
"""Calibrate DeepSeek action generation on the 18 Selection initial states."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_ROOT = REPO_ROOT / "external/ST-WebAgentBench"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BENCHMARK_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BENCHMARK_ROOT / ".env")

from st_bench_example import DemoAgent  # noqa: E402

from src.adapters.stwebagentbench.seeded_agent import (  # noqa: E402
    seed_agent_client,
)
from src.skill_evolution.autonomous_gse_v06_benchmark_runtime import (  # noqa: E402
    BENCHMARK_AGENT_MODEL,
    selection_execution_seed,
)

DEFAULT_INPUT_ROOT = (
    REPO_ROOT
    / "artifacts/autonomous_gse_v06/raw/selection/initial_selection/s0_empty_skill"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "artifacts/autonomous_gse_v06/calibration/deepseek_action_budget.json"
)
DEFAULT_BUDGETS = (512, 1024, 2048, 4096, 8192)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("budgets must be positive integers")
    return parsed


def _load_initial_observations(root: Path) -> list[tuple[int, dict[str, Any]]]:
    observations = []
    for path in sorted(root.glob("task_*/trial_01/trajectory.json")):
        trajectory = json.loads(path.read_text(encoding="utf-8"))
        observations.append(
            (trajectory["task"]["task_id"], trajectory["initial_observation"])
        )
    if len(observations) != 18:
        raise ValueError(
            f"Expected 18 Selection observations under {root}, got {len(observations)}."
        )
    return observations


def _usage_value(usage: dict[str, Any] | None, key: str) -> int | None:
    if not isinstance(usage, dict):
        return None
    value = usage.get(key)
    return value if isinstance(value, int) else None


def run_calibration(
    observations: list[tuple[int, dict[str, Any]]],
    budgets: tuple[int, ...],
    *,
    campaign_seed: int,
    temperature: float,
    thinking: bool | None = None,
) -> dict[str, Any]:
    results = []
    summaries = []
    for budget in budgets:
        parse_failures = 0
        for task_id, observation in observations:
            agent = DemoAgent(
                BENCHMARK_AGENT_MODEL,
                max_tokens=budget,
                retry_on_token_exhaustion=False,
                thinking=thinking,
            )
            seed_agent_client(
                agent,
                selection_execution_seed(campaign_seed, task_id, 1),
                temperature=temperature,
            )
            action = None
            try:
                action = agent.get_action(observation)
            except RuntimeError:
                model_output = agent.last_llm_output
                if (
                    not isinstance(model_output, dict)
                    or model_output.get("action") is not None
                ):
                    raise
                parse_failures += 1
            model_output = agent.last_llm_output or {}
            usage = model_output.get("usage")
            details = (
                usage.get("completion_tokens_details", {})
                if isinstance(usage, dict)
                else {}
            )
            results.append(
                {
                    "budget": budget,
                    "task_id": task_id,
                    "action": action,
                    "parse_success": action is not None,
                    "completion_tokens": _usage_value(usage, "completion_tokens"),
                    "reasoning_tokens": _usage_value(details, "reasoning_tokens"),
                }
            )
        failure_rate = parse_failures / len(observations)
        summaries.append(
            {
                "budget": budget,
                "tasks": len(observations),
                "parse_failures": parse_failures,
                "parse_failure_rate": failure_rate,
                "below_one_percent": failure_rate < 0.01,
            }
        )
    qualifying = [item["budget"] for item in summaries if item["below_one_percent"]]
    return {
        "schema_version": "deepseek_action_budget_calibration_0.1.0",
        "model": BENCHMARK_AGENT_MODEL,
        "campaign_seed": campaign_seed,
        "temperature": temperature,
        "thinking": thinking,
        "budgets": list(budgets),
        "selection_tasks": len(observations),
        "selected_budget": min(qualifying) if qualifying else None,
        "summaries": summaries,
        "results": results,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--budgets", nargs="+", type=_positive_int, default=DEFAULT_BUDGETS
    )
    parser.add_argument("--campaign-seed", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument(
        "--thinking-disabled",
        action="store_true",
        help="Send DeepSeek thinking.type=disabled for this calibration.",
    )
    args = parser.parse_args()

    payload = run_calibration(
        _load_initial_observations(args.input_root.resolve()),
        tuple(dict.fromkeys(args.budgets)),
        campaign_seed=args.campaign_seed,
        temperature=args.temperature,
        thinking=False if args.thinking_disabled else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summaries"], ensure_ascii=False, indent=2))
    print(f"selected_budget={payload['selected_budget']}")
    print(f"output={args.output}")
    return 0 if payload["selected_budget"] is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
