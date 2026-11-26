"""SpreadsheetBench selective Update evolution."""
from pathlib import Path

from ..v25_2.cli import EXPERIMENT as V25_2_EXPERIMENT

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]

BASELINE = V25_2_EXPERIMENT / 'config'
