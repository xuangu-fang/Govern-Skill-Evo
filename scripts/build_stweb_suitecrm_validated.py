#!/usr/bin/env python3
"""Build the frozen SuiteCRM validated benchmark overlay."""

from __future__ import annotations

import json

from src.adapters.stwebagentbench.validated_suitecrm import build


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
