"""Run inherited and local tests against this memory-contract revision."""
import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REVISION = HERE / "revision"
BASES = [HERE.parent / name / "revision" for name in ('20_memory_contract_fix', '17_p1_input', '12_contract_alignment')]


def main():
    sys.path.insert(0, str(REVISION))
    os.chdir(ROOT)
    loader = unittest.TestLoader()
    names = set()
    for start, package in (
        (ROOT / "tests/skill_evolution/v22", "tests.skill_evolution.v22"),
        (ROOT / "tests/adapters/alfworld", "tests.adapters.alfworld"),
        *((base / "tests/skill_evolution/v22", "tests.skill_evolution.v22") for base in BASES),
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
