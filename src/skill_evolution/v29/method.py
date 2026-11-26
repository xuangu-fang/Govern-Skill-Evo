"""Explicit training-archive binding for deterministic five-module operations."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import re

from src.skill_evolution.v27.benchmark import using_benchmark
from .benchmarks.docvqa import protocol as p, facts, evidence, prompting
from . import memory_operation


class DocVQAMethod:
    parent_text = staticmethod(facts.parent_text)
    execution_context = staticmethod(p.execution_context)

    def __init__(self, actor_adapter, *, archives):
        self.actor_adapter = actor_adapter
        self.dataset = actor_adapter.dataset
        self._records, self._directories = {}, {}
        for directory in archives:
            self.register_archive(directory)

    def register_archive(self, directory):
        root = Path(directory).resolve()
        records = self.read_batch(root)
        p.require(all(r['provenance']['role'] in ('parent', 'candidate')
                      and r['task']['split'] == 'train' for r in records),
                  'Test cannot become optimization evidence')
        for record in records:
            rid = record['run_id']
            if rid in self._records:
                p.require(record == self._records[rid] and self._directories[rid] == root,
                          'Registered execution changed')
            self._records[rid] = deepcopy(record)
            self._directories[rid] = root

    @contextmanager
    def using(self):
        with using_benchmark(self):
            yield self

    def source_record(self, run_id):
        p.require(isinstance(run_id, str) and run_id in self._records, 'Unregistered execution archive')
        return self.validate_record(self._records[run_id])

    def validate_record(self, record):
        p.require(isinstance(record, dict), 'Expected execution record')
        rid = record.get('run_id')
        p.require(isinstance(rid, str) and rid in self._records and record == self._records[rid],
                  'Execution differs from the registered archive')
        batch = self.read_batch(self._directories[rid])
        p.require(sum(r == record for r in batch) == 1, 'Execution differs from its completed batch')
        return deepcopy(record)

    def validate_batch(self, records):
        p.require(isinstance(records, list) and records, 'Missing completed batch')
        first = self.validate_record(records[0])
        expected = self.read_batch(self._directories[first['run_id']])
        p.require(records == expected, 'Facts require the complete batch in its saved order')

    def build_facts(self, records, *, role='parent'):
        self.validate_batch(records)
        p.require(role in ('parent', 'candidate') and
                  all(r['provenance']['role'] == role for r in records), 'Unexpected execution role')
        return facts.build_facts(records, adapter=self,
                                 directory=self._directories[records[0]['run_id']])

    def read_batch(self, directory):
        session = memory_operation.current(self)
        return session.batch(directory) if session is not None else self.actor_adapter.read_batch(directory)

    def project_record(self, record, ref):
        session = memory_operation.current(self)
        key = (record['run_id'], ref)
        if session is not None and key in session.projections:
            return deepcopy(session.projections[key])
        run = facts.project_execution(self.dataset.case(record['task_id']), record['execution'],
                                      ref=ref, run_id=record['run_id'])
        if session is not None:
            session.projections[key] = deepcopy(run)
        return run

    def evidence(self, operation, *args, **kwargs):
        p.require(operation in evidence.OPERATIONS, 'Unknown evidence operation')
        return evidence.OPERATIONS[operation](*args, **kwargs)

    def plan_fields(self):
        return ('parent', 'plan', 'runs', 'grouping', 'memory')

    def auxiliary_references(self, payload):
        return set()

    def validate_execution_source(self, source):
        p.fields(source, ('run',), 'Execution source')
        # This is a persisted historical source, not a new Actor observation.
        run = source['run']
        p.fields(run, ('ref', 'task_id', 'run_id', 'initial', 'attempts', 'outcome'), 'Historical run')
        p.nonempty_text(run['task_id'], 'Historical task ID')
        p.nonempty_text(run['run_id'], 'Historical run ID')
        ref = run['ref']
        p.require(isinstance(ref, str) and re.fullmatch(r'[PQ][1-9]\d*', ref), 'Invalid historical run reference')
        p.require(run['initial']['ref'] == ref + ':0' and run['outcome']['ref'] == ref + ':outcome' and
                  isinstance(run['attempts'], list) and len(run['attempts']) == 1 and
                  run['attempts'][0]['ref'] == ref + ':1', 'Invalid historical run structure')
        return run

    def resource(self, key):
        return prompting.resource_path(key)

    def validation_sources(self):
        return {path.resolve() for path in Path(__file__).parent.rglob('*.py')}

    def memory_operation(self):
        return memory_operation.operation(self)

    def begin_round(self):
        self._records.clear()
        self._directories.clear()

    def load_memory(self, directory):
        """Read committed Active entries without reopening historical Actor archives."""
        with memory_operation.operation(self) as session:
            return session.load(directory)

    def commit_memory(self, directory, *, context_id, context, result):
        """Existing immutable commit + atomic Active switch; no Gate/model call."""
        with memory_operation.operation(self) as session:
            return session.commit(directory, context_id=context_id, context=context, result=result)
