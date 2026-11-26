"""v29.2 binding: reuse the frozen Actor, not the v29.1 evolution engine."""
from pathlib import Path

from src.skill_evolution.v29.campaign import CampaignAdapter as ActorCampaignAdapter
from .config import METHOD_VERSION
from . import actor_io


RUNTIME_VERSION = 'v29_2_light_runtime_v1'


class CampaignAdapter(ActorCampaignAdapter):
    method_version = METHOD_VERSION

    def actor_batch(self, tasks, skill_file, directory, config):
        return actor_io.actor_batch(self.actor_adapter, tasks, skill_file, directory, config)

    def validation_sources(self):
        root = Path(__file__).resolve().parent
        return (super().validation_sources() | set(root.glob('*.py')) |
                {root.parents[2] / 'scripts/runs/run_v29_2_campaign.py'})
