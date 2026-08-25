#!/usr/bin/env python3
"""Run the final frozen Train-only v02 canary in an independent artifact root."""

from pathlib import Path

from scripts.run_stweb_suitecrm_validated_v02_holdout_canary import REPO_ROOT, run_canary


if __name__ == "__main__":
    raise SystemExit(
        run_canary(
            output_root=(
                REPO_ROOT
                / "artifacts/stweb_suitecrm_interactive_validated_v02"
                / "final_canary_attempt_03"
            ),
            canary_path=(
                REPO_ROOT
                / "experiments/benchmarks/stweb_suitecrm_interactive_validated_v02"
                / "final_canary_manifest.json"
            ),
            attempt_id="final_canary_v02_attempt_03",
            report_key="final_canary_summary",
        )
    )
