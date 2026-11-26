"""Bind the shared OfficeQA Actor to the v26.3 protocol and checkpoint."""
from pathlib import Path

from . import protocol
from ._shared_campaign import CampaignAdapter as OfficeQAAdapter, RUNTIME_VERSION
from .. import v26_2


class CampaignAdapter(OfficeQAAdapter):
    method_version = protocol.METHOD_VERSION

    def validation_sources(self):
        directories = [Path(__file__).parent, *(Path(path) for path in v26_2.__path__)]
        return {source for directory in directories for source in directory.glob('*.py')}
