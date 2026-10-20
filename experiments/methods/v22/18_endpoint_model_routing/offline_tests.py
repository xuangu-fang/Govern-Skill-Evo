"""Run shared V22/adapter tests, contract tests and routing tests against revision 18."""
import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REVISION = HERE / "revision"
BASE = HERE.parent / "12_contract_alignment/revision"


def main():
    sys.path.insert(0, str(REVISION))
    os.chdir(ROOT)
    loader = unittest.TestLoader()
    names = set()
    for start, package in (
        (ROOT / "tests/skill_evolution/v22", "tests.skill_evolution.v22"),
        (ROOT / "tests/adapters/alfworld", "tests.adapters.alfworld"),
        (BASE / "tests/skill_evolution/v22", "tests.skill_evolution.v22"),
        (REVISION / "tests/skill_evolution/v22", "tests.skill_evolution.v22"),
    ):
        for path in start.glob("test_*.py"):
            # The later mainline chunked transport is not part of this revision.
            if path.name != "test_chunked_retry.py":
                names.add(f"{package}.{path.stem}")
    # Module-name loading preserves revision-first imports. Local tests with the
    # same name replace the base revision's import-wiring checks.
    suite = loader.loadTestsFromNames(sorted(names))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return not result.wasSuccessful()


if __name__ == "__main__":
    raise SystemExit(main())
