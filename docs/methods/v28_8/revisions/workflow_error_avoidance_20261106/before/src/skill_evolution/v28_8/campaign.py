"""Bind independent v28.8 stages to existing SearchQA facts and Actor journals."""
from copy import deepcopy
from pathlib import Path
from src.skill_evolution.v28.method import SearchQAMethod
from src.skill_evolution.v28.benchmarks.searchqa import protocol
from . import config as settings, actor_io, memory_operation, memory


RUNTIME_VERSION = 'v28_8_light_runtime_v1'


class CampaignAdapter(SearchQAMethod):
    identity = 'v28_searchqa_v1'
    method_version = settings.METHOD_VERSION

    def __init__(self, actor_adapter):
        protocol.require(isinstance(actor_adapter, actor_io.ActorAdapter), 'Expected v28.8 Actor binding')
        self.actor_adapter, self.dataset = actor_adapter, actor_adapter.dataset
        self.profile = self.method_version
        self.prompt_versions = settings.prompt_versions()
        self._records, self._directories = {}, {}
        self._bound()

    def begin_round(self):
        # A fresh round uses only its own registered Actor evidence. Published
        # history is supplied through Memory, not old raw execution archives.
        self._records.clear()
        self._directories.clear()

    def plan_fields(self):
        return ('parent', 'plan', 'runs', 'memory')

    def _bound(self):
        self.actor_adapter._preflight()

    def actor_batch(self, tasks, skill_file, directory, config):
        return actor_io.actor_batch(self.actor_adapter, tasks, skill_file, directory, config)

    def resource(self, key):
        protocol.require(key in {f'{n}.md' for n in self.prompt_versions}, 'Unknown v28.8 prompt')
        return settings.MODULES[Path(key).stem].PROMPT_PATH

    def validation_sources(self):
        return set(Path(__file__).parent.glob('*.py'))

    def memory_operation(self):
        return memory_operation.operation(self)

    def verify_memory_operation(self):
        active = memory_operation.current(self)
        if active is not None: active.verify()

    def load_memory(self, directory):
        return memory.load_memory(directory)

    def commit_memory(self, *args, **kwargs):
        return memory.commit_memory(*args, **kwargs)

    def runtime_snapshot(self, config):
        tasks = [task for batch in config['batches'] for task in batch]
        return {'method': self.method_version, 'actor': deepcopy(self.actor_adapter._actor),
                'workers': self.actor_adapter.workers, 'test_workers': self.actor_adapter.test_workers,
                'gate_rule': config['gate_rule'], 'data': self.dataset.snapshot(),
                'tasks': [{'id': task, 'payload': deepcopy(dict(self.dataset.case(task).payload)),
                           'reference': deepcopy(self.dataset.case(task).reference),
                           'metadata': deepcopy(dict(self.dataset.case(task).metadata))} for task in tasks]}
