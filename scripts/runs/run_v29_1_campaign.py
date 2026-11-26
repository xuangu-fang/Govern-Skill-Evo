"""Train/test v29.1 explicitly; --validate-only is offline and creates no run."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from scripts.runs import run_v29_campaign as shared
from src.skill_evolution.v29_1.campaign import CampaignAdapter, DEFAULT_CONFIG


def main(argv=None):
    return shared.main(argv, adapter_type=CampaignAdapter, default_config=DEFAULT_CONFIG)


if __name__ == '__main__':
    main()
