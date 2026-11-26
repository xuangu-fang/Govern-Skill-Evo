"""Prepare aligned-Actor inputs without starting training or model calls."""
import argparse
from pathlib import Path
from shutil import copytree
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.binding import components
from src.skill_evolution.skilladam.spreadsheetbench.layout import ALIGNED_CONFIG


def prepare(output):
    output = Path(output)
    if output.exists():
        raise ValueError('Use a new experiment directory')
    components()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        staged = Path(temporary) / 'experiment'
        copytree(ALIGNED_CONFIG, staged)
        staged.rename(output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(prepare(parser.parse_args().output))
