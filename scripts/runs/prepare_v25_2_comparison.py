"""Compatibility entry for the maintained SpreadsheetBench v25.2 preparer."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.skill_evolution.v25_2.cli import prepare


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(prepare(parser.parse_args().output)['experiment'])
