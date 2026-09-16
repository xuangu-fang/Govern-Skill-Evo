#!/usr/bin/env python3
"""Primitive A entry point; fail closed before model calls when Stage 0 blocks."""

from __future__ import annotations

import json
from pathlib import Path


EDITION = Path(__file__).resolve().parents[2]


def main() -> int:
    audit_path = EDITION / "construction/primitive_a/structural_audit/structural_audit.json"
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

