"""Pinned local SearchQA data and the 600-task optimization view."""
from copy import deepcopy
from skilladam.types import BenchmarkCase
from ...storage import read
from . import protocol as p

LOCK_SHA256 = '41b8b1268f5d7d5c4259f685e74bba4f5a415ccdea7814e42782f8c50c7a09a7'
VIEW_SHA256 = '397810ae16545aa600ec770fb8d6d23f90e959c11044590dae1e710a86519a5c'


class SearchQADataset:
    optimization_pool = 'v28_searchqa_train600_v1'
    def __init__(self, root=None, *, batch_size=15, verify_hashes=True):
        from pathlib import Path
        self.root = Path(root or p.ROOT / 'data/searchqa').resolve()
        p.actor_config(batch_size)  # Validate supported schedules and their Actor budget.
        self.batch_size = batch_size
        p.require(type(verify_hashes) is bool, 'Invalid data verification policy')
        self.verify_hashes = verify_hashes
        lock_path = self.root / 'v28_dataset.lock.json'
        view_path = self.root / 'v28_train600_v1/manifest.json'
        if self.verify_hashes:
            p.require(p.file_digest(lock_path) == LOCK_SHA256, 'Dataset lock drift')
            p.require(p.file_digest(view_path) == VIEW_SHA256, 'Optimization view drift')
        lock, view = read(lock_path), read(view_path)
        self._hashes = ({**lock['sha256'], 'v28_dataset.lock.json': LOCK_SHA256,
                         'v28_train600_v1/manifest.json': VIEW_SHA256} if self.verify_hashes else {})
        self._verify_files()
        self.rows, source_ids = {}, {}
        for split, entry in lock['splits'].items():
            rows = read(self.root / entry['path'])
            p.require(len(rows) == entry['count'], 'Wrong dataset split size')
            source_ids[split] = [row['id'] for row in rows]
            for row in rows:
                p.fields(row, ('id', 'question', 'context', 'answers'), 'Dataset row')
                p.require(row['id'] not in self.rows, 'Duplicate dataset ID')
                self.rows[row['id']] = {**row, 'source_split': split}
        self.splits = {'train': [v['id'] for v in view['optimization_cases']], 'test': view['test_ids']}
        p.require(self.splits['train'] == source_ids['train'] + source_ids['val'] and self.splits['test'] == source_ids['test'], 'Dataset order drift')
        p.require([len(self.splits[k]) for k in ('train', 'test')] == [600, 1400], 'Wrong frozen pool size')
        self.batches = view['batches']
        p.require(len(self.batches) == 40 and all(len(b) == 15 for b in self.batches)
                  and [i for b in self.batches for i in b] == self.splits['train'], 'Batch schedule drift')
        if batch_size in (30, 50, 60):
            ids = self.splits['train']
            self.batches = [ids[i:i + batch_size] for i in range(0, len(ids), batch_size)]
        self._identity = {'dataset_id': lock['dataset_id']}
        if self.verify_hashes:
            self._identity.update(source_revision=lock['source_revision'],
                                  lock_sha256=LOCK_SHA256, view_sha256=VIEW_SHA256)
            self._rows_digest = p.digest(self.rows)
            self._view_digest = p.digest({'splits': self.splits, 'batches': self.batches})
        for task_id in self.rows:
            p.validate_case(self.case(task_id))

    def _verify_files(self):
        if not self.verify_hashes:
            return
        for relative, checksum in self._hashes.items():
            p.require(p.file_digest(self.root / relative) == checksum, f'Dataset file drift: {relative}')

    def case(self, task_id):
        row = self.rows[task_id]
        return BenchmarkCase(case_id=task_id,
            payload={k: row[k] for k in ('question', 'context')}, reference=deepcopy(row['answers']),
            metadata={**self._identity, 'source_split': row['source_split'],
                      'split': 'test' if row['source_split'] == 'test' else 'train'})

    def snapshot(self):
        if not self.verify_hashes:
            return {**self._identity, 'root': str(self.root), 'batch_size': self.batch_size,
                    'splits': deepcopy(self.splits), 'batches': deepcopy(self.batches)}
        self._verify_files()
        p.require(p.digest(self.rows) == self._rows_digest and
                  p.digest({'splits': self.splits, 'batches': self.batches}) == self._view_digest, 'Bound dataset changed')
        return {**self._identity, 'files_sha256': deepcopy(self._hashes),
                'rows_sha256': self._rows_digest, 'schedule_sha256': self._view_digest}
