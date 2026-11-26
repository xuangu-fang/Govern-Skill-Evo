"""Frozen release view: the original 50 Train plus 24 Validation tasks."""
from src.skill_evolution.v26.training import OptimizationDataset
from . import protocol as p


class OfficeQADataset(OptimizationDataset):
    def __init__(self, prepared_root=None):
        super().__init__(prepared_root or p.ROOT / p.PLAN['benchmark']['prepared_root'])
        self.batches = [self.splits['train'][i:i+10] for i in range(0, 74, 10)]
        p.require(self.batches == p.PLAN['schedule']['batches'] and
                  self.splits['test'] == p.PLAN['schedule']['test_ids'], 'Frozen release inventory differs')
