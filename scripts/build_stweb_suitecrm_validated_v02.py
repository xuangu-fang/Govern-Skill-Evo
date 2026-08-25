#!/usr/bin/env python3
from src.adapters.stwebagentbench.validated_suitecrm_v02 import build

if __name__ == "__main__":
    manifest = build()
    print(manifest["status"])
