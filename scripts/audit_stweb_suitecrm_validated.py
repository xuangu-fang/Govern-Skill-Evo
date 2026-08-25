#!/usr/bin/env python3
"""Re-run the deterministic audit without invoking an LLM."""

from __future__ import annotations

import json

from src.adapters.stwebagentbench.validated_suitecrm import build


if __name__ == "__main__":
    manifest = build()
    print(json.dumps({"status": manifest["status"], "manifest_id": manifest["manifest_id"]}, indent=2))
