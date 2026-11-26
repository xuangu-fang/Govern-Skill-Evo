"""Bind independent v27.1 stages to native LMB facts and Actor journals."""
from copy import deepcopy
from pathlib import Path
from contextlib import contextmanager
from src.skill_evolution.v27.benchmark import using_benchmark
from src.skill_evolution.v28 import validation
from src.skill_evolution.v28.storage import read
from .lmb import facts
from .lmb import protocol
from . import config as settings, actor_io, memory_operation, memory


RUNTIME_VERSION = 'v27_1_light_runtime_v1'


class CampaignAdapter:
    identity = protocol.IDENTITY
    method_version = settings.METHOD_VERSION

    def __init__(self, actor_adapter):
        protocol.require(isinstance(actor_adapter, actor_io.ActorAdapter), 'Expected v27.1 Actor binding')
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
        protocol.require(key in {f'{n}.md' for n in self.prompt_versions}, 'Unknown v27.1 prompt')
        return protocol.ROOT / 'docs/methods/v27_1/prompts' / key

    def validation_sources(self):
        return set(Path(__file__).parent.rglob('*.py'))

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

    def register_archive(self, directory):
        """Register only a completed, revalidated batch; exact rebinding is idempotent."""
        root = Path(directory).resolve()
        records = read(root / 'records.json')
        signature = read(root / 'batch.json')['signature']
        protocol.require(signature['config']['split'] == 'train' and
                  signature['config']['role'] in ('parent', 'candidate'),
                  'Test cannot become optimization evidence')
        self.actor_adapter._check_batch_records(records, signature['tasks'], signature['skill'],
                                               signature['config'], root)
        for record in records:
            rid = record['run_id']
            if rid in self._records:
                protocol.require(protocol.equal(record, self._records[rid]) and self._directories[rid] == root,
                          'Registered execution changed directory or content')
            self._records[rid] = deepcopy(record)
            self._directories[rid] = root

    @contextmanager
    def using(self):
        self.actor_adapter._preflight()
        with using_benchmark(self):
            yield self

    def source_record(self, run_id):
        protocol.require(isinstance(run_id, str) and run_id in self._records, 'Unregistered execution archive')
        return self.validate_record(self._records[run_id])

    def validate_record(self, record):
        protocol.require(isinstance(record, dict), 'Record must be an object')
        rid = record.get('run_id')
        protocol.require(isinstance(rid, str) and rid in self._records and
                  protocol.equal(record, self._records[rid]), 'Execution differs from registered archive')
        root = self._directories[rid]
        state = validation.current(self.actor_adapter)
        if state is not None:
            key = (self, root, rid)
            canonical = protocol.exact(record)
            if key in state.records:
                protocol.require(state.records[key] == canonical, 'Validated execution content changed')
            else:
                self._validate_record_archive(record, root, canonical=canonical)
                state.records[key] = canonical
        else:
            self._validate_record_archive(record, root)
        return deepcopy(record)

    def _validate_record_archive(self, record, root, *, canonical=None):
        config = {'split': 'train', 'role': record['provenance']['role']}
        self.actor_adapter.check_record_archive(record, record['task_id'], record['execution']['skill'], config, root)
        active = validation.current(self.actor_adapter)
        if active is not None: active.watch_tree(root)
        committed = read(root / 'records.json')
        batch = read(root / 'batch.json')
        protocol.require([r['task_id'] for r in committed] == batch['signature']['tasks'], 'Committed batch coverage differs')
        protocol.require(sum(protocol.equal(r, record) for r in committed) == 1, 'Record differs from committed batch')

    def validate_batch(self, records):
        protocol.require(isinstance(records, list) and records, 'Missing completed batch')
        first = self.validate_record(records[0])
        expected = read(self._directories[first['run_id']] / 'records.json')
        protocol.require(protocol.equal(records, expected), 'Facts require the complete committed batch in frozen order')


    build_facts = staticmethod(facts.build_facts)
    parent_text = staticmethod(facts.parent_text)
    execution_context = staticmethod(protocol.execution_context)

    def auxiliary_references(self, payload):
        return set()

    def validate_execution_source(self, source):
        protocol.fields(source, ('run',), 'Execution source')
        return facts.validate_run(source['run'])
