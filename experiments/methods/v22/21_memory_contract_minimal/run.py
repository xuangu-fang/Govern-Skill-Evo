"""Select memory-contract overrides before invoking the revision's runner."""
import os
from pathlib import Path
import sys

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here / "revision"))
    os.chdir(here.parents[3])
    from src.skill_evolution.v22.continual_runner import main

    raise SystemExit(main())
