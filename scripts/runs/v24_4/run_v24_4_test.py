"""Evaluate the final published V24.4 Skill on the 134 held-out ALFWorld tasks."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.runs.v24_2.run_v24_2_test import main
from src.skill_evolution.v24_4 import campaign
from src.skill_evolution.v24_4.episodes import evaluate

if __name__ == '__main__':
    main(version=campaign, description=__doc__, load_skill=campaign.published_skill, evaluate=evaluate, relative_receipts=True)
