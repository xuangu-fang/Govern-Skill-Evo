"""Run shared V22/adapter tests and local contract tests against revision 12."""
import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REVISION = HERE / "revision"


def main():
    sys.path.insert(0, str(REVISION))
    os.chdir(ROOT)
    loader = unittest.TestLoader()
    names = set()
    for start, package in (
        (ROOT / "tests/skill_evolution/v22", "tests.skill_evolution.v22"),
        (ROOT / "tests/adapters/alfworld", "tests.adapters.alfworld"),
        (REVISION / "tests/skill_evolution/v22", "tests.skill_evolution.v22"),
    ):
        for path in start.glob("test_*.py"):
            # This later mainline transport test was not part of revision 12.
            if path.name != "test_chunked_retry.py":
                names.add(f"{package}.{path.stem}")
    # Loading by module name preserves overlay-first imports. unittest discovery
    # inserts its top-level directory ahead of the selected revision.
    suite = loader.loadTestsFromNames(sorted(names))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return not result.wasSuccessful()


if __name__ == "__main__":
    raise SystemExit(main())
