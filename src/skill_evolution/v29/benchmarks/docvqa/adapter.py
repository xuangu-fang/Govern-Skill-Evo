"""Explicit single-batch Actor API; no optimizer, campaign or Test launcher."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import uuid

from ...storage import read, save, freeze
from . import actor, protocol as p, scoring


class DocVQAActorAdapter:
    def __init__(self, dataset, transport=None):
        self.dataset = dataset
        self.transport = transport
        self.workers = self.test_workers = 60
        if transport is not None:
            p.validate_config(transport.metadata())

    def _cases(self, tasks, config):
        p.require(isinstance(config, dict) and set(config) == {'split', 'role'}, 'Expected split/role')
        p.require(config['split'] in ('train', 'test')
                  and config['role'] in ('parent', 'candidate', 'evaluation')
                  and (config['role'] == 'evaluation') == (config['split'] == 'test'),
                  'Test and optimization roles must remain separate')
        p.require(isinstance(tasks, list) and tasks and all(isinstance(t, str) for t in tasks)
                  and len(set(tasks)) == len(tasks), 'Expected unique task IDs')
        cases = [p.validate_case(self.dataset.case(task)) for task in tasks]
        p.require(all(c.case_id == task and c.metadata['split'] == config['split']
                      for task, c in zip(tasks, cases)), 'Task ID/split mismatch')
        return cases

    def _signature(self, tasks, skill, config):
        self._cases(tasks, config)
        p.require(skill is None or isinstance(skill, str), 'Skill must be text or None')
        return {'tasks': list(tasks), 'skill': skill, 'config': deepcopy(config),
                'actor': p.actor_config(), 'workers': self.test_workers
                if config['role'] == 'evaluation' else self.workers}

    @staticmethod
    def _folder(root, index):
        return Path(root) / 'actor' / f'{index:04}'

    @staticmethod
    def _record(case, execution, batch, index):
        return {'schema': p.RECORD_VERSION, 'task_id': case.case_id,
                'run_id': f"{batch['batch_id']}:{index:04}",
                'task': {'id': case.case_id, 'split': case.metadata['split'], **deepcopy(case.payload)},
                'execution': execution,
                'provenance': {'batch_id': batch['batch_id'], 'role': batch['signature']['config']['role']}}

    def read_batch(self, directory):
        """Read and validate a completed batch without writes or transport calls."""
        root = Path(directory)
        batch = read(root / 'batch.json')
        signature = batch['signature']
        tasks, skill, config = (signature[k] for k in ('tasks', 'skill', 'config'))
        p.require(signature == self._signature(tasks, skill, config), 'Batch configuration differs')
        p.nonempty_text(batch['batch_id'], 'Batch ID')
        cases = self._cases(tasks, config)
        records = []
        for index, case in enumerate(cases, 1):
            folder = self._folder(root, index)
            result = actor.read_completed(case, skill, folder)
            record = self._record(case, result, batch, index)
            freeze(folder / 'trajectory.json', record, read_only=True)
            records.append(record)
        freeze(root / 'records.json', records, read_only=True)
        return records

    def actor_batch(self, tasks, skill_file, directory, config, *, final=False):
        p.require(self.transport is not None, 'Explicit Actor transport required')
        p.validate_config(self.transport.metadata())
        p.require(type(final) is bool and final == (config.get('role') == 'evaluation'), 'Invalid final flag')
        cases = self._cases(tasks, config)
        skill = None if skill_file is None else Path(skill_file).read_text(encoding='utf-8')
        signature = self._signature(tasks, skill, config)
        # Check all task inputs before creating execution directories or starting workers.
        for case in cases:
            p.messages_for_case(case, skill)
        root = Path(directory)
        with actor.locked(root):
            if (root / 'batch.json').exists():
                batch = read(root / 'batch.json')
                p.require(batch['signature'] == signature, 'Existing batch differs')
            else:
                p.require(not any(q.name != '.execution.lock' for q in root.iterdir()),
                          'Missing identity for existing batch')
                batch = {'batch_id': str(uuid.uuid4()), 'signature': signature}
                save(root / 'batch.json', batch)
            if (root / 'records.json').exists():
                return self.read_batch(root)
            for index, case in enumerate(cases, 1):
                folder = self._folder(root, index)
                actor.validate_pending(case, skill, folder)
                if (folder / 'trajectory.json').exists():
                    expected = self._record(case, actor.read_completed(case, skill, folder), batch, index)
                    freeze(folder / 'trajectory.json', expected, read_only=True)

            def run(index, case):
                folder = self._folder(root, index)
                execution = actor.execute(case, skill, folder, self.transport)
                record = self._record(case, execution, batch, index)
                freeze(folder / 'trajectory.json', record)
                return record

            with ThreadPoolExecutor(max_workers=min(signature['workers'], len(cases))) as pool:
                futures = [pool.submit(run, i, case) for i, case in enumerate(cases, 1)]
                records = [future.result() for future in futures]
            freeze(root / 'records.json', records)
            return records

    def build_gate(self, parent_directory, candidate_directory):
        parent = self.read_batch(parent_directory)
        candidate = self.read_batch(candidate_directory)
        p.require(all(r['provenance']['role'] == 'parent' for r in parent)
                  and all(r['provenance']['role'] == 'candidate' for r in candidate), 'Expected training pair roles')
        tasks = [r['task_id'] for r in parent]
        p.require(tasks == [r['task_id'] for r in candidate], 'Paired task order differs')
        p.require(parent[0]['provenance']['batch_id'] != candidate[0]['provenance']['batch_id'],
                  'Parent and Candidate must be independent executions')
        for left, right in zip(parent, candidate):
            p.require(left['task'] == right['task'] and left['task']['split'] == 'train', 'Paired task differs')
            p.require(left['execution']['initial_messages'][1] == right['execution']['initial_messages'][1],
                      'Paired question/image differs')
        def metrics(records):
            return [{'task_id': r['task_id'], 'metrics': r['execution']['metrics']} for r in records]
        return {'metric': p.GATE_PROFILE,
                'result': scoring.compare_scores(metrics(parent), metrics(candidate), tasks)}
