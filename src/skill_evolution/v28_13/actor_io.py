"""Reuse SearchQA Actor execution/scoring with an independent method identity."""
from pathlib import Path
from src.skill_evolution.v28 import profiles
from src.skill_evolution.v28.storage import read
from src.skill_evolution.v28.benchmarks.searchqa import actor, protocol as p
from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter

METHOD_VERSION = 'v28_13_campaign_v1'
GATE_VERSION = 'v28_13_gate_net_em_min2_v1'


def read_skill(path):
    return Path(path).read_bytes().decode('utf-8')


class ActorAdapter(SearchQAActorAdapter):
    def __init__(self, dataset, transport=None):
        # Use the existing plain-journal policy, then bind our own provenance.
        super().__init__(dataset, transport, profile=profiles.V28_1)
        self.profile = METHOD_VERSION
        self.workers = 60
        p.require(dataset.batch_size in (30, 50, 60), 'v28.13 Actor requires batch30, batch50 or batch60')

    def _preflight(self):
        super()._preflight()
        p.require(type(self.workers) is int and type(self.test_workers) is int and
                  self.workers == 60 and self.test_workers == 15, 'v28.13 requires Train/Test workers 60/15')

    def _source_identity(self, case):
        return {'method_profile': self.profile, 'scorer': p.SCORER_PROFILE, 'gate': GATE_VERSION}

    def _signature(self, tasks, skill, config):
        value = super()._signature(tasks, skill, config)
        # The legacy gate name is not part of this method's Actor protocol.
        value['protocol'] = {'prompt': p.prompt_identity(), 'scorer': p.SCORER_PROFILE}
        return value

    def read_batch(self, directory):
        root = Path(directory); records = read(root / 'records.json')
        sig = read(root / 'batch.json')['signature']
        self._check_batch_records(records, sig['tasks'], sig['skill'], sig['config'], root)
        return records

    def build_gate(self, *args, **kwargs):
        raise ValueError('v28.13 uses its Update-level Gate after Replay')


def actor_batch(adapter, tasks, skill_file, directory, config, *, final=False):
    if adapter.transport is not None:
        return adapter.actor_batch(tasks, skill_file, directory, config, final=final)
    skill = None if skill_file is None else read_skill(skill_file)
    for task in tasks:
        actor.read_completed(adapter.dataset.case(task), skill,
                             Path(directory) / 'actor' / adapter.task_key(task),
                             adapter._actor, verify_hashes=False)
    class ArchiveOnly:
        def metadata(self): return p.actor_config(30)
        def __call__(self, *args): raise RuntimeError('Archive-only recovery cannot issue requests')
    return ActorAdapter(adapter.dataset, ArchiveOnly()).actor_batch(tasks, skill_file, directory, config, final=final)
