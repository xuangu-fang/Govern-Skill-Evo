"""Bind v27.2 prompts to the shared LMB Actor and verified campaign evidence."""
from pathlib import Path
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27_1.campaign import CampaignAdapter as LMBCampaignAdapter
from . import config, prompts

RUNTIME_VERSION = 'v27_2_light_runtime_v1'


class CampaignAdapter(LMBCampaignAdapter):
    method_version = config.METHOD_VERSION

    def __init__(self, actor_adapter):
        super().__init__(actor_adapter)
        self.prompt_versions = config.prompt_versions()

    def resource(self, key):
        require(key in {f'{name}.md' for name in self.prompt_versions}, 'Unknown v27.2 prompt')
        return prompts.DIRECTORY / key

    def validation_sources(self):
        return (super().validation_sources() | set(Path(__file__).parent.glob('*.py')) |
                {self.resource(f'{name}.md') for name in self.prompt_versions})
