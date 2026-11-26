"""Bind the shared OfficeQA campaign to the v26.9 Actor protocol."""
from pathlib import Path

from .. import v26_8
from ._shared_campaign import CampaignAdapter as OfficeQAAdapter, RUNTIME_VERSION
from .protocol import METHOD_VERSION


class CampaignAdapter(OfficeQAAdapter):
    method_version = METHOD_VERSION

    def validation_sources(self):
        directories = [Path(__file__).parent, *(Path(directory) for directory in v26_8.__path__)]
        return {source for directory in directories for source in directory.glob('*.py')}
