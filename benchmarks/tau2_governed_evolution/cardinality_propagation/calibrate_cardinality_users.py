"""One fixed-seed UserSimulator sanity check per S5 task."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.cardinality_propagation.build_cardinality_tasks import PROJECT_ROOT
from benchmarks.tau2_governed_evolution.cardinality_propagation.validate_cardinality_tasks import load_suite
from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable


ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage  # noqa: E402
from tau2.user.user_simulator import UserSimulator  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/cardinality_propagation_step4w_s5/user_sanity.json"


def run(model: str) -> dict:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    rows = []
    for spec in manifest["tasks"]:
        candidate = spec["candidate"]
        user = UserSimulator(
            llm=model,
            instructions=str(tasks[spec["task_id"]].user_scenario),
            llm_args={"temperature": 0, "seed": manifest["user_sanity_seed"], "reasoning_effort": "high", "max_tokens": 8192},
        )
        state = user.get_init_state()
        initial, state = user.generate_next_message(AssistantMessage.text("Hello, how can I help?"), state)
        followup, _ = user.generate_next_message(
            AssistantMessage.text(
                f"I have the target and ${candidate['threshold']} limit. Are you changing the target flight, "
                "threshold, passenger scope, or fallback?"
            ),
            state,
        )
        initial_text = initial.content or ""
        followup_text = followup.content or ""
        checks = {
            "user_id": candidate["user_id"] in initial_text,
            "reservation_id": candidate["reservation_id"] in initial_text,
            "target_flight": candidate["target_flight"] in initial_text,
            "threshold": str(candidate["threshold"]) in initial_text,
            "entire_reservation_scope": bool(re.search(r"entire reservation|everyone|all passengers", initial_text, re.I)),
            "fallback_unchanged": bool(re.search(r"leave|unchanged|no change|do not change", initial_text, re.I)),
            "no_oracle_total_leak": str(candidate["total_delta"]) not in initial_text,
            "no_late_revision": not re.search(r"actually|change (?:it|that|the target)|new threshold|instead", followup_text, re.I),
            "no_stop": "###STOP###" not in initial_text and "###STOP###" not in followup_text,
        }
        rows.append(
            {
                "task_id": spec["task_id"],
                "seed": manifest["user_sanity_seed"],
                "initial": initial_text,
                "followup": followup_text,
                "checks": checks,
                "passed": all(checks.values()),
            }
        )
    return {"model": model, "passed": all(row["passed"] for row in rows), "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="openai/deepseek-v4-flash")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
