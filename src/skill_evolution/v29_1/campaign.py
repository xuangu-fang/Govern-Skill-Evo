"""Explicit v29.1 binding with unchanged Actor, contracts and campaign engine."""
from pathlib import Path

from src.skill_evolution.v29.campaign import CampaignAdapter as V29CampaignAdapter
from src.skill_evolution.v29.benchmarks.docvqa import prompting, protocol

PROMPT_ROOT = protocol.ROOT / 'docs/methods/v29_1/prompts'
METHOD_VERSION = 'v29_1_campaign_v1'
PROMPT_VERSIONS = dict(prompting.PROMPT_VERSIONS,
    diagnosis='v29_1_docvqa_diagnosis_v1',
    preconditioner='v29_1_docvqa_preconditioner_v1')
DEFAULT_CONFIG = protocol.ROOT / 'experiments/configs/v29_1_docvqa_optimization160.json'


class CampaignAdapter(V29CampaignAdapter):
    method_version = METHOD_VERSION
    prompt_versions = PROMPT_VERSIONS

    def resource(self, key):
        if key in ('diagnosis.md', 'preconditioner.md'):
            return PROMPT_ROOT / key
        return super().resource(key)

    def validation_sources(self):
        return super().validation_sources() | {Path(__file__).resolve()}
