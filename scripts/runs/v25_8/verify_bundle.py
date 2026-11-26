"""Check published SpreadsheetBench v25.8 experiment records."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.runs.spreadsheetbench import verify_archive

RUNS = {
    'v25_8_spreadsheetbench_official_20261118_232447': 19,
}


def verify(path_type=None):
    run_id, = RUNS
    return verify_archive.verify('v25_8', run_id, RUNS[run_id], path_type)


if __name__ == '__main__':
    verify_archive.main('v25_8', RUNS)
