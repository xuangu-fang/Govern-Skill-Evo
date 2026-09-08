"""Run Step 4V Partial-view rollouts with the learned transition Skill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.tau2_governed_evolution.transition_ablation.run_transition_empty import (
    DEFAULT_ROOT,
    run,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--max-concurrency", type=int, default=6)
    args = parser.parse_args()
    result = run("partial_skill", args.output_root, args.max_concurrency)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
