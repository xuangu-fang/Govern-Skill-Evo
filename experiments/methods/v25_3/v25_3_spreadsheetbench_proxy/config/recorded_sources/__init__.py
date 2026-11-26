"""SpreadsheetBench selective Update evolution."""
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
BASELINE = ROOT / 'experiments/comparisons/v25_2_prompt_only_20261101_001'
