#!/usr/bin/env python3
"""Primitive A entry point; fail closed before model calls when Stage 0 blocks."""

from __future__ import annotations

import json
from pathlib import Path


EDITION = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')


def main() -> int:
    audit_path = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/primitive_a/structural_audit/structural_audit.json')
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit["result"] != "PASS" or audit["qualified_task_count"] == 0:
        print(
            "BLOCKED: Primitive A Stage 0 verdict is "
            f"{audit['result']} with {audit['qualified_task_count']} qualified tasks; "
            "no model rollout was started."
        )
        return 2
    raise RuntimeError("No rollout adapter is installed until the structural gate passes")


if __name__ == "__main__":
    raise SystemExit(main())

