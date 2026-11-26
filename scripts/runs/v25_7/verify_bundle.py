"""Check published SpreadsheetBench v25.7 experiment records."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.runs.spreadsheetbench import verify_archive

RUNS = {
    'v25_7_spreadsheetbench_deepseek': 0,
    'v25_7_spreadsheetbench_v41_20261116': 10,
    'v25_7_spreadsheetbench_official_20261118_212017': 1,
}


if __name__ == '__main__':
    verify_archive.main('v25_7', RUNS)
