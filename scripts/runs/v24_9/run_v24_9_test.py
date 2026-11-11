"""Evaluate the final published V24.9 Skill on the 134 held-out ALFWorld tasks."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.runs.v24_2.run_v24_2_test import main
from src.skill_evolution.v24_9 import campaign

if __name__ == '__main__':
    main(version=campaign, description=__doc__)
