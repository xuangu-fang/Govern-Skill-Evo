"""Track the v26.8 overrides as well as inherited sources when resuming."""
from pathlib import Path

from ..v26_7.campaign import CampaignAdapter as PreviousAdapter, RUNTIME_VERSION
from .protocol import METHOD_VERSION


class CampaignAdapter(PreviousAdapter):
    method_version = METHOD_VERSION

    def validation_sources(self):
        return super().validation_sources() | set(Path(__file__).parent.glob('*.py'))
