"""Explicit read-only archive binding for the five modules and v27 contracts.

Supply current/historical Actor batch directories explicitly, or register a newly
completed batch before referencing it.
This adapter has no provider or training entrypoint. A fresh process can bind the
same directories to recover evidence and Memory without executing Actors.
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import re

from src.skill_evolution.v27.benchmark import using_benchmark
from src.skill_evolution.v27.contracts import memory
from .storage import read
from .benchmarks.searchqa import protocol as p, facts, evidence, prompting
from . import replay, validation, memory_operation, profiles


class SearchQAMethod:
    build_facts = staticmethod(facts.build_facts)
    parent_text = staticmethod(facts.parent_text)
    execution_context = staticmethod(p.execution_context)

    def __init__(self, actor_adapter, *, archives):
        self.actor_adapter = actor_adapter
        self.profile = actor_adapter.profile
        self.prompt_versions = profiles.prompt_versions(self.profile)
        self.dataset = actor_adapter.dataset
        self._records = {}
        self._directories = {}
        actor_adapter._preflight()
        for directory in archives:
            self.register_archive(directory)

    def register_archive(self, directory):
        """Register only a completed, revalidated batch; exact rebinding is idempotent."""
        root = Path(directory).resolve()
        records = read(root / 'records.json')
        signature = read(root / 'batch.json')['signature']
        p.require(signature['config']['split'] == 'train' and
                  signature['config']['role'] in ('parent', 'candidate'),
                  'Test cannot become optimization evidence')
        self.actor_adapter._check_batch_records(records, signature['tasks'], signature['skill'],
                                               signature['config'], root)
        for record in records:
            rid = record['run_id']
            if rid in self._records:
                p.require(p.equal(record, self._records[rid]) and self._directories[rid] == root,
                          'Registered execution changed directory or content')
            self._records[rid] = deepcopy(record)
            self._directories[rid] = root

    @contextmanager
    def using(self):
        self.actor_adapter._preflight()
        with using_benchmark(self):
            yield self

    def source_record(self, run_id):
        p.require(isinstance(run_id, str) and run_id in self._records, 'Unregistered execution archive')
        return self.validate_record(self._records[run_id])

    def validate_record(self, record):
        p.require(isinstance(record, dict), 'Record must be an object')
        rid = record.get('run_id')
        p.require(isinstance(rid, str) and rid in self._records and
                  p.equal(record, self._records[rid]), 'Execution differs from registered archive')
        root = self._directories[rid]
        state = validation.current(self.actor_adapter)
        if state is not None:
            key = (self, root, rid)
            canonical = p.exact(record)
            if key in state.records:
                p.require(state.records[key] == canonical, 'Validated execution content changed')
            else:
                self._validate_record_archive(record, root, canonical=canonical)
                state.records[key] = canonical
        else:
            self._validate_record_archive(record, root)
        return deepcopy(record)

    def _validate_record_archive(self, record, root, *, canonical=None):
        config = {'split': 'train', 'role': record['provenance']['role']}
        self.actor_adapter.check_record_archive(record, record['task_id'], record['execution']['skill'], config, root)
        if validation.current(self.actor_adapter) is not None:
            _, index = self.actor_adapter._validated_archive_batch(root, record['execution']['skill'], config)
            p.require(index.get(record['run_id']) == canonical, 'Record differs from committed batch')
            return
        committed = read(root / 'records.json')
        batch = read(root / 'batch.json')
        p.require([r['task_id'] for r in committed] == batch['signature']['tasks'], 'Committed batch coverage differs')
        p.require(sum(p.equal(r, record) for r in committed) == 1, 'Record differs from committed batch')

    def validate_batch(self, records):
        p.require(isinstance(records, list) and records, 'Missing completed batch')
        first = self.validate_record(records[0])
        expected = read(self._directories[first['run_id']] / 'records.json')
        p.require(p.equal(records, expected), 'Facts require the complete committed batch in frozen order')

    def evidence(self, operation, *args, **kwargs):
        p.require(operation in evidence.OPERATIONS, 'Unknown or disabled evidence operation')
        return evidence.OPERATIONS[operation](*args, **kwargs)

    def plan_fields(self):
        return ('parent', 'plan', 'runs', 'grouping', 'memory')

    def auxiliary_references(self, payload):
        return set()

    def validate_execution_source(self, source):
        p.fields(source, ('run',), 'Execution source')
        return facts.validate_run(source['run'])

    def resource(self, key):
        if self.profile == profiles.V28_1 and key in {f'{name}.md' for name in self.prompt_versions}:
            folder = 'prompts' if key in ('diagnosis.md', 'preconditioner.md') else 'baseline/prompts'
            return profiles.REVIEWED / folder / key
        return prompting.resource_path(key)

    def commit_memory(self, directory, *, context_id, context, result):
        with self.memory_operation() as session:
            evidence.validate_bundle(context)
            replay.validate_result(result, context['payload'])
            return session.commit(directory, context_id=context_id, context=context, result=result)

    def memory_operation(self):
        return memory_operation.operation(self)

    def verify_memory_operation(self):
        session = memory_operation.current(self)
        if session is not None:
            session.verify()

    def load_memory(self, directory):
        with self.memory_operation() as session:
            return session.load(directory)

    def _load_memory(self, directory):
        # Recheck full audit bundles as well as the inherited Active lineage.
        root = Path(directory)
        state = memory._state(root)
        for cid in state['commits']:
            p.require(isinstance(cid, str) and re.fullmatch(r'[A-Za-z0-9_-]+', cid),
                      'Invalid Memory context ID')
            commit = read(root / 'archive' / f'{cid}.json')
            evidence.validate_bundle(commit['context'])
            replay.validate_result(commit['result'], commit['context']['payload'])
        entries, contexts = memory._archive(root, state, memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        view = memory._view(entries, contexts, state['active_ids'], memory.MULTI_KNOWLEDGE_CONTRACT)
        memory_operation.current(self).remember(root, state, entries, contexts, view)
        return view
