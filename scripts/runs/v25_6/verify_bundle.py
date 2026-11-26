"""Check published SpreadsheetBench v25.6 experiment records."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.runs.spreadsheetbench import verify_archive

RUNS = {
    'v25_6_spreadsheetbench_deepseek': 12,
}


if __name__ == '__main__':
    verify_archive.main('v25_6', RUNS)
