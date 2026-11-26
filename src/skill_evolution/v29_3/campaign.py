"""Explicit v29.3 binding; inherited Actor and archive operations are unchanged."""
from pathlib import Path
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy

from src.skill_evolution.v29_2.campaign import CampaignAdapter as V29_2Adapter
from src.skill_evolution.v29_2 import config as base
from src.skill_evolution.v29.benchmarks.docvqa import protocol
from .config import METHOD_VERSION

DEFAULT_CONFIG = protocol.ROOT / 'experiments/configs/v29_3_docvqa_optimization160.json'
RUNTIME_VERSION = 'v29_3_light_runtime_v1'
_OPERATION = ContextVar('v29_3_operation', default=None)


class CampaignAdapter(V29_2Adapter):
    method_version = METHOD_VERSION

    @contextmanager
    def memory_operation(self):
        """Reuse current completed batches, without historical byte snapshots."""
        existing = _OPERATION.get()
        if existing is not None and existing[0] is self:
            yield existing[1]
            return
        cache = {}
        token = _OPERATION.set((self, cache))
        try:
            yield cache
        finally:
            _OPERATION.reset(token)

    def read_batch(self, directory):
        root = Path(directory).resolve()
        operation = _OPERATION.get()
        if operation is None or operation[0] is not self:
            return self.actor_adapter.read_batch(root)
        cache = operation[1]
        if root not in cache:
            cache[root] = self.actor_adapter.read_batch(root)
        return deepcopy(cache[root])

    def register_archive(self, directory):
        root = Path(directory).resolve()
        records = self.read_batch(root)
        protocol.require(all(r['provenance']['role'] in ('parent', 'candidate') and
                             r['task']['split'] == 'train' for r in records),
                         'Test cannot become optimization evidence')
        for record in records:
            rid = record['run_id']
            if rid in self._records:
                protocol.require(record == self._records[rid] and self._directories[rid] == root,
                                 'Registered execution changed')
            self._records[rid] = deepcopy(record)
            self._directories[rid] = root

    def begin_round(self):
        # Earlier executions are represented by committed Knowledge, not live archives.
        self._records.clear()
        self._directories.clear()

    def validation_sources(self):
        root = Path(__file__).resolve().parent
        return (super().validation_sources() | set(root.glob('*.py')) |
                set((root / 'prompts').glob('*.md')) |
                set((Path(base.__file__).parent / 'prompts').glob('*.md')) |
                {root.parents[2] / 'scripts/runs/run_v29_3_campaign.py'})
