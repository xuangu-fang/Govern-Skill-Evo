"""Keep the v26.1 Actor and include the v26.2 overrides in resume checks."""
from pathlib import Path
from ..v26_1.campaign import CampaignAdapter as BaselineAdapter, RUNTIME_VERSION
from .protocol import METHOD_VERSION


class CampaignAdapter(BaselineAdapter):
    method_version = METHOD_VERSION

    def validation_sources(self):
        return super().validation_sources() | set(Path(__file__).parent.glob('*.py'))
