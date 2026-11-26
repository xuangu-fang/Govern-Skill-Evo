"""Seven ordered batches over the frozen v26.1 optimization pool."""
from copy import deepcopy
from ..v26_1.dataset import OfficeQADataset as BaselineDataset
from . import protocol


class OfficeQADataset(BaselineDataset):
    def __init__(self, prepared_root=None):
        super().__init__(prepared_root)
        batches = protocol.PLAN['schedule']['batches']
        protocol.require([uid for batch in batches for uid in batch] == self.splits['train'],
                         'v26.2 schedule differs from the release inventory')
        self.batches = deepcopy(batches)
