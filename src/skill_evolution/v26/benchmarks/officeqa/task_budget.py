"""Explicit task output budgets shared by Parent and Candidate in fresh campaigns."""
from copy import deepcopy

from ...facts import require
from .adapter import OfficeQAEvidenceAdapter, SkillAdamEvidenceAdapter
from . import facts, evidence, protocol as p


class TaskBudgetRuntime:
    """Select a task's immutable transport inside the common case worker."""
    def __init__(self, runtime, task_transports):
        self._runtime = runtime
        self._task_transports = dict(task_transports)

    def __getattr__(self, name):
        return getattr(self._runtime, name)

    def run(self, case, skill, transport, *, owner, directory):
        selected = self._task_transports.get(case.case_id, transport)
        return self._runtime.run(case, skill, selected, owner=owner, directory=directory)


class TaskOutputBudgetAdapter(OfficeQAEvidenceAdapter):
    record_adapter = OfficeQAEvidenceAdapter

    def __init__(self, *args, task_transports, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_adapters = {}
        self.task_output_limits = {}
        for task, transport in task_transports.items():
            require(task in self.dataset.rows, 'Unknown task output budget ID')
            actual = transport.metadata()
            limit = actual['max_completion_tokens']
            require(type(limit) is int and limit > 0 and actual == {
                **self.transport.metadata(), 'max_completion_tokens': limit}, 'Only output budget may differ')
            self.task_output_limits[task] = limit
            self.task_adapters[task] = self.record_adapter(
                self.dataset, self.runtime, transport, workers=self.workers, gate_metric=self.gate_metric)
        self.runtime = TaskBudgetRuntime(self.runtime, task_transports)

    def _adapter(self, task):
        return self.task_adapters.get(task, self)

    def check_record(self, record, task, expected_skill, config):
        return OfficeQAEvidenceAdapter.check_record(self._adapter(task), record, task, expected_skill, config)

    def build_facts(self, records, *, role=None):
        require(isinstance(records, list) and records, 'Missing completed executions')
        role = role or records[0]['provenance']['role']
        skill = facts.parent_text(records[0])
        runs, sources = [], []
        for index, record in enumerate(records, 1):
            task = record['task_id']
            require(record['execution']['actor'] == self._adapter(task).transport.metadata(), 'Task Actor budget differs')
            require(facts.parent_text(record) == skill and record['provenance']['role'] == role, 'Mixed Skill or role')
            single = facts.build_facts([record], role=role)
            run = evidence.relabel(single['facts']['runs'][0], f'P{index}')
            runs.append(run)
            sources.append({k: run[k] for k in ('ref', 'task_id', 'run_id')})
        require(len({r['task_id'] for r in runs}) == len(runs) == len({r['run_id'] for r in runs}),
                'Duplicate execution/task')
        background = p.background({**self.transport.metadata(), 'task_max_completion_tokens': self.task_output_limits})
        return {'facts': {'parent': skill, 'runs': runs}, 'background': background, 'sources': sources}

    def runtime_snapshot(self, config):
        return {**super().runtime_snapshot(config), 'actor_task_output_limits': deepcopy(self.task_output_limits),
                'actor_scheduling': 'shared_four_worker_pool_per_task_output_limits_v1'}


class ParallelTaskOutputBudgetAdapter(TaskOutputBudgetAdapter):
    """Use the common parallel Actor pool for independent budgeted evaluations."""
    record_adapter = SkillAdamEvidenceAdapter
    allowed_workers = record_adapter.allowed_workers

    def runtime_snapshot(self, config):
        return {**super().runtime_snapshot(config), 'actor_scheduling': 'shared_pool_per_task_output_limits_v1'}
