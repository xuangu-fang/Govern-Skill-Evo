"""Selected OfficeQA optimization pool; original prepared splits stay immutable."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

from src.adapters.officeqa.data import Dataset
from .facts import require


MERGED_POOL = 'officeqa_train50_validation24_v1'
POOL_IDS = json.loads((Path(__file__).with_name('resources') / 'officeqa_optimization_ids.json').read_text())


class OptimizationDataset(Dataset):
    """SkillAdam-style Train + Validation view, retaining source split provenance."""
    optimization_pool = MERGED_POOL

    def __init__(self, prepared_root):
        super().__init__(prepared_root)
        require(len(POOL_IDS['train']) == 50 and len(POOL_IDS['validation']) == 24,
                'Invalid frozen optimization inventory')
        require(all(self.splits[split] == ids for split, ids in POOL_IDS.items()),
                'Merged optimization requires the fixed 50 Train and 24 Validation IDs')
        self.source_splits = deepcopy(self.splits)
        merged = self.splits['train'] + self.splits['validation']
        require(len(set(merged)) == 74 and not set(merged) & set(self.splits['test']),
                'Optimization pool overlaps Test or contains duplicates')
        for uid in merged:
            row = self.rows[uid]
            self.rows[uid] = {**row, 'source_split': 'validation' if row['split'] == 'val' else 'train',
                              'split': 'train'}
        self.splits = {'train': merged, 'validation': [], 'test': self.splits['test']}

    def case(self, uid):
        case = super().case(uid)
        return replace(case, metadata={**case.metadata,
                       'source_split': self.rows[uid].get('source_split', case.metadata['split'])})

    def cases(self, split):
        return tuple(self.case(uid) for uid in self.splits[split])


def load_dataset(prepared_root, optimization_pool=None):
    require(optimization_pool in (None, MERGED_POOL), 'Unsupported optimization pool')
    return Dataset(prepared_root) if optimization_pool is None else OptimizationDataset(prepared_root)
