"""Native LMB journals and scorer with an explicit independent Actor binding."""
from copy import deepcopy
from pathlib import Path
from src.skill_evolution.v28.storage import read
from .lmb import actor, protocol as p
from .lmb.adapter import LMBExecution

METHOD_VERSION = 'v27_1_campaign_v1'
GATE_VERSION = 'v27_1_gate_selective_em_v1'


def read_skill(path):
    return Path(path).read_bytes().decode('utf-8')


class ArchiveOnly:
    def metadata(self): return deepcopy(p.ACTOR)
    def __call__(self, *args):
        raise RuntimeError('Archive-only recovery cannot issue requests')


class ActorAdapter(LMBExecution):
    # The operation watcher compares bytes. Native dataset/Actor/provenance
    # checksums remain enabled in the LMB execution implementation.
    verify_hashes = False
    profile = METHOD_VERSION
    workers = 20
    test_workers = 16

    def __init__(self, dataset, transport=None):
        self.dataset = dataset
        self.transport = transport if transport is not None else ArchiveOnly()
        self._actor = deepcopy(p.ACTOR)
        self._data_identity = deepcopy({'rows': dataset.rows, 'splits': dataset.splits})
        self._preflight()

    def _preflight(self):
        p.require(self.profile == METHOD_VERSION, 'Wrong LMB method binding')
        p.require(type(self.workers) is int and self.workers == 20 and
                  type(self.test_workers) is int and self.test_workers == 16,
                  'v27.1 requires Train/Test workers 20/16')
        p.require(p.equal(self._actor, p.ACTOR), 'Frozen Actor changed')
        p.background(self.transport.metadata())
        p.require(p.equal(self._data_identity, {'rows': self.dataset.rows, 'splits': self.dataset.splits}),
                  'Dataset changed after binding')

    def _bound(self):
        self._preflight()

    @staticmethod
    def task_key(task): return p.digest(task)

    def _cases(self, tasks, config):
        self._preflight(); self.validate_config(config)
        p.require(tasks and len(set(tasks)) == len(tasks), 'Missing/duplicate Actor tasks')
        cases = [self.dataset.case(t) for t in tasks]
        p.require(all(c.metadata['split'] == config['split'] for c in cases), 'Wrong task split')
        return cases

    def _check_batch_records(self, records, tasks, skill, config, root):
        self._cases(tasks, config)
        p.require(isinstance(records, list) and [r['task_id'] for r in records] == tasks,
                  'Completed Actor batch coverage/order differs')
        for record in records:
            self.check_record_archive(record, record['task_id'], skill, config, root)
        return records

    def read_batch(self, directory):
        root = Path(directory)
        records = read(root / 'records.json')
        sig = read(root / 'batch.json')['signature']
        return self._check_batch_records(records, sig['tasks'], sig['skill'], sig['config'], root)

    def build_gate(self, *args, **kwargs):
        raise ValueError('v27.1 uses its Update-level Gate after Replay')


def actor_batch(adapter, tasks, skill_file, directory, config, *, final=False):
    return adapter.actor_batch(tasks, skill_file, directory, config, final=final)
