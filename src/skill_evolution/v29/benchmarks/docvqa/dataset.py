"""Read the existing 534-question release without downloading or reordering."""
from copy import deepcopy
from pathlib import Path
from skilladam.types import BenchmarkCase
from ...storage import read
from . import protocol as p


class DocVQADataset:
    batch_size = 15
    optimization_pool = 'v29_docvqa_optimization160_v1'

    def __init__(self, root=None):
        self.root = Path(root or p.DEFAULT_DATA_ROOT).resolve()
        info = read(self.root / 'dataset_info.json')
        p.require(info['revision'] == p.REVISION and info['source_config'] == 'DocVQA'
                  and info['source_split'] == 'validation', 'Unexpected DocVQA release')
        self.rows, self.source_ids = {}, {}
        for split, count in (('train', 107), ('val', 53), ('test', 374)):
            items = read(self.root / f'prepared/{split}/items.json')
            ids = items['ids']
            p.require(len(ids) == count and len(set(ids)) == count and set(ids) == set(items['by_id']),
                      f'Invalid {split} membership')
            self.source_ids[split] = list(ids)
            for task_id in ids:
                row = items['by_id'][task_id]
                p.require(task_id not in self.rows and row['id'] == task_id
                          and row['original_split'] == split, 'Duplicate ID or original split mismatch')
                self.rows[task_id] = deepcopy(row)
        self.splits = {'train': self.source_ids['train'] + self.source_ids['val'],
                       'test': list(self.source_ids['test'])}
        p.require(self.source_ids == read(self.root / 'source_split/skilladam_split_ids.json'),
                  'Prepared split IDs/order differ from the saved upstream partition')
        view = read(self.root / 'optimization160/manifest.json')
        items = read(self.root / 'optimization160/items.json')
        p.require(view['count'] == 160 and view['ids'] == items['ids'] == self.splits['train'],
                  'Optimization order differs from original Train followed by Validation')
        p.require(set(items['by_id']) == set(self.splits['train']), 'Optimization membership differs')
        for task_id in self.splits['train']:
            row = self.rows[task_id]
            p.require(items['by_id'][task_id] == {**row, 'effective_split': 'optimization'},
                      'Optimization view differs from prepared data')
        self.batches = [self.splits['train'][i:i + 15] for i in range(0, 160, 15)]
        for task_id in self.rows:
            case = p.validate_case(self.case(task_id))
            p.require((self.root / case.payload['image_path']).is_file(), 'Missing document image')

    def case(self, task_id):
        row = self.rows[task_id]
        return BenchmarkCase(case_id=task_id,
            payload={key: row[key] for key in ('question', 'image_path')},
            reference=deepcopy(row['answers']),
            metadata={'revision': p.REVISION, 'image_root': str(self.root),
                      'source_split': row['original_split'],
                      'split': 'test' if row['original_split'] == 'test' else 'train'})
