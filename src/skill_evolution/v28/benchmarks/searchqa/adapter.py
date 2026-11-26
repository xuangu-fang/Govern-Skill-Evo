"""SearchQA Actor batches and archive-verified EM Gate; no training launcher."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import uuid
from urllib.parse import quote

from ...storage import freeze, read, save
from ... import validation, profiles
from . import actor, protocol as p, scoring


class SearchQAActorAdapter:
    def __init__(self, dataset, transport=None, *, workers=15, test_workers=15, profile=profiles.V28):
        p.require(type(workers) is int and workers == 15 and
                  type(test_workers) is int and test_workers == 15, 'Frozen v28 worker limits are 15/15')
        self.profile = profiles.check(profile)
        self.verify_hashes = self.profile == profiles.V28
        p.require(self.verify_hashes == getattr(dataset, "verify_hashes", True),
                  "Dataset verification policy differs from method profile")
        self.dataset, self.transport = dataset, transport
        self.workers, self.test_workers = workers, test_workers
        self._data = deepcopy(dataset.snapshot())
        self._protocol = p.implementation_identity()
        expected = p.actor_config(getattr(dataset, 'batch_size', 15))
        self._actor = p.background(expected if transport is None else transport.metadata())
        if hasattr(dataset, 'batch_size'):
            p.require(p.equal(self._actor, expected), 'Actor budget differs from selected batch profile')

    def _preflight(self):
        p.require(p.equal(self.dataset.snapshot(), self._data), 'Bound dataset identity changed')
        p.require(p.equal(p.implementation_identity(), self._protocol), 'Bound implementation identity changed')
        p.background(self._actor)
        if self.transport is not None:
            p.require(p.equal(self.transport.metadata(), self._actor), 'Bound Actor changed')

    @staticmethod
    def validate_config(config):
        p.fields(config, ('split', 'role'), 'Execution configuration')
        p.require(config['split'] in ('train', 'test') and config['role'] in ('parent', 'candidate', 'evaluation'), 'Invalid execution role/split')
        p.require((config['role'] == 'evaluation') == (config['split'] == 'test'), 'Test is isolated from optimization')

    def _cases(self, tasks, config):
        self.validate_config(config)
        p.require(isinstance(tasks, list) and tasks and all(isinstance(t, str) and t.strip() for t in tasks), 'Missing task IDs')
        p.require(len(tasks) == len(set(tasks)), 'Duplicate task ID')
        cases = [p.validate_case(self.dataset.case(task)) for task in tasks]
        p.require(all(c.case_id == task and c.metadata['split'] == config['split'] for task, c in zip(tasks, cases)), 'Task ID/split mismatch')
        return cases

    def task_key(self, task_id):
        return p.digest(task_id) if self.verify_hashes else "task-" + quote(task_id, safe="")

    def _source_identity(self, case):
        if not self.verify_hashes:
            return {"method_profile": self.profile, "scorer": p.SCORER_PROFILE, "gate": p.GATE_PROFILE}
        return {'case_sha256': p.digest({'id': case.case_id, 'payload': case.payload,
                                        'reference': case.reference, 'metadata': case.metadata}),
                'dataset_sha256': p.digest(self._data), 'protocol_sha256': p.digest(self._protocol),
                'task_context_sha256': p.digest(p.messages(case.payload, None)),
                'scorer': p.SCORER_PROFILE, 'gate': p.GATE_PROFILE}

    def _signature(self, tasks, skill, config):
        cases = self._cases(tasks, config)
        p.require(skill is None or isinstance(skill, str), 'Skill must be text or None')
        return {'tasks': tasks, 'sources': {c.case_id: self._source_identity(c) for c in cases},
                'actor': self._actor, 'protocol': self._protocol, 'dataset': self._data,
                'skill': skill, 'config': config,
                'workers': self.test_workers if config['role'] == 'evaluation' else self.workers}

    def actor_batch(self, tasks, skill_file, directory, config, *, final=False):
        p.require(self.transport is not None, 'Explicit Actor transport required')
        self._preflight()
        p.require(type(final) is bool and final == (config.get('role') == 'evaluation'), 'Execution final flag differs')
        cases = self._cases(tasks, config)
        skill = None if skill_file is None else Path(skill_file).read_bytes().decode('utf-8')
        signature = self._signature(tasks, skill, config)
        root = Path(directory)
        with actor.locked(root):
            if (root / 'batch.json').exists():
                batch = read(root / 'batch.json')
                p.fields(batch, ('batch_id', 'signature'), 'Batch')
                p.nonempty_text(batch['batch_id'], 'Batch ID')
                p.require(p.equal(batch['signature'], signature), 'Frozen batch differs')
            else:
                p.require(not any(q.name != '.execution.lock' for q in root.iterdir()), 'Missing batch identity for existing archive')
                batch = {'batch_id': str(uuid.uuid4()), 'signature': signature}
                save(root / 'batch.json', batch)
            if (root / 'records.json').exists():
                records = read(root / 'records.json')
                self._check_batch_records(records, tasks, skill, config, root)
                return records
            # Audit every completion AND pending journal before constructing any
            # workers, including when the pending task precedes a corrupt one.
            for case in cases:
                folder = root / 'actor' / self.task_key(case.case_id)
                if (folder / 'trajectory.json').exists():
                    self._check_record_journal(read(folder / 'trajectory.json'), case.case_id, skill, config, root, batch)
                elif (folder / 'result.json').exists():
                    actor.read_completed(case, skill, folder, self._actor, verify_hashes=self.verify_hashes)
                else:
                    actor.validate_pending(case, skill, folder, self._actor, verify_hashes=self.verify_hashes)

            def run(case):
                folder = root / 'actor' / self.task_key(case.case_id)
                execution = actor.execute(case, skill, folder, self.transport, verify_hashes=self.verify_hashes)
                record = {'schema': p.RECORD_VERSION, 'run_id': batch['batch_id'] + ':' + self.task_key(case.case_id),
                          'task_id': case.case_id, 'task': p.public_task(case), 'execution': execution,
                          'provenance': {'batch_id': batch['batch_id'], 'role': config['role'],
                                         **self._source_identity(case)}}
                if self.verify_hashes:
                    record['provenance']['record_sha256'] = p.digest(execution)
                self.check_record(record, case.case_id, skill, config)
                freeze(folder / 'trajectory.json', record)
                return record

            with ThreadPoolExecutor(max_workers=signature['workers']) as pool:
                futures = [pool.submit(run, case) for case in cases]
                records = [future.result() for future in futures]
            freeze(root / 'records.json', records)
            return records

    def check_record(self, record, task_id, expected_skill, config):
        self.validate_config(config)
        case = self._cases([task_id], config)[0]
        p.fields(record, ('schema', 'run_id', 'task_id', 'task', 'execution', 'provenance'), 'Record')
        p.require(record['schema'] == p.RECORD_VERSION and record['task_id'] == task_id
                  and p.equal(record['task'], p.public_task(case)), 'Canonical task/schema differs')
        execution, provenance = record['execution'], record['provenance']
        source = self._source_identity(case)
        extra = ('record_sha256',) if self.verify_hashes else ()
        p.fields(provenance, ('batch_id', 'role', *source, *extra), 'Provenance')
        p.nonempty_text(provenance['batch_id'], 'Batch ID')
        p.require(record['run_id'] == provenance['batch_id'] + ':' + self.task_key(task_id), 'Run identity differs')
        p.require(provenance['role'] == config['role'] and
                  all(provenance[k] == v for k, v in source.items()), 'Source identity or role differs')
        if self.verify_hashes:
            p.require(provenance['record_sha256'] == p.digest(execution), 'Execution checksum differs')
        p.fields(execution, ('skill', 'actor', 'initial_messages', 'content', 'termination',
                             'answer', 'metrics', 'api_requests', 'usage_records'), 'Execution')
        p.require(execution['skill'] == expected_skill and p.equal(execution['actor'], self._actor), 'Actor or Skill differs')
        p.require(p.equal(execution['initial_messages'], p.messages(case.payload, expected_skill)), 'Actor input differs')
        p.require(execution['termination'] == 'stop', 'Incomplete execution')
        answer, metrics = scoring.score(execution['content'], case.reference)
        p.require(p.equal(execution['answer'], answer) and p.equal(execution['metrics'], metrics), 'Derived answer/score differs')
        count = execution['api_requests']
        p.require(type(count) is int and 1 <= count <= 6, 'Invalid Actor request count')
        p.require(isinstance(execution['usage_records'], list) and len(execution['usage_records']) == count, 'Usage/request count differs')
        for usage in execution['usage_records']:
            p.fields(usage, ('input_tokens', 'output_tokens', 'total_tokens', 'reasoning_tokens'), 'Usage')
            p.require(all(v is None or type(v) is int and v >= 0 for v in usage.values()), 'Invalid usage')
        return record

    def check_record_archive(self, record, task_id, expected_skill, config, directory):
        """Read-only check against canonical data, frozen batch and raw journal."""
        root = Path(directory)
        if validation.current(self) is not None:
            batch, _ = self._validated_archive_batch(root, expected_skill, config)
            p.require(task_id in batch['signature']['tasks'], 'Archived batch task differs')
            return self._check_record_journal(record, task_id, expected_skill, config, root, batch)
        batch = read(root / 'batch.json')
        p.fields(batch, ('batch_id', 'signature'), 'Batch')
        tasks = batch['signature']['tasks']
        p.require(task_id in tasks and p.equal(batch['signature'], self._signature(tasks, expected_skill, config)), 'Archived batch signature differs')
        return self._check_record_journal(record, task_id, expected_skill, config, root, batch)

    def _validated_archive_batch(self, root, skill, config):
        """One signature and exact record index per completed batch and operation."""
        state = validation.current(self)
        p.require(state is not None, 'Batch reuse requires a validation operation')
        root = Path(root).resolve()
        if root not in state.batches:
            state.watch_tree(root)
            batch, records = read(root / 'batch.json'), read(root / 'records.json')
            p.fields(batch, ('batch_id', 'signature'), 'Batch')
            tasks = batch['signature']['tasks']
            p.require(p.equal(batch['signature'], self._signature(tasks, skill, config)),
                      'Archived batch signature differs')
            p.require(isinstance(records, list) and all(isinstance(r, dict) for r in records) and
                      [r.get('task_id') for r in records] == tasks, 'Committed batch coverage differs')
            index = {r['run_id']: p.exact(r) for r in records}
            p.require(len(index) == len(records), 'Duplicate committed execution identity')
            state.batches[root] = batch, index
        batch, index = state.batches[root]
        p.require(batch['signature']['skill'] == skill and p.equal(batch['signature']['config'], config),
                  'Archived batch Skill/config differs')
        return batch, index

    def _check_record_journal(self, record, task_id, expected_skill, config, root, batch):
        # Callers verify the shared batch signature once, rather than rebuilding
        # all 1,400 Test task identities for every individual completed journal.
        self.check_record(record, task_id, expected_skill, config)
        p.require(record['provenance']['batch_id'] == batch['batch_id'], 'Archived batch ID differs')
        folder = root / 'actor' / self.task_key(task_id)
        completed = actor.read_completed(self.dataset.case(task_id), expected_skill, folder, self._actor,
                                         verify_hashes=self.verify_hashes)
        p.require(p.equal(completed, record['execution']) and
                  p.equal(read(folder / 'trajectory.json'), record), 'Trajectory differs from Actor archive')
        return record

    def _check_batch_records(self, records, tasks, skill, config, directory):
        p.require(isinstance(records, list) and all(isinstance(r, dict) for r in records)
                  and [r.get('task_id') for r in records] == tasks, 'Completed batch coverage/order differs')
        batch = read(Path(directory) / 'batch.json')
        p.fields(batch, ('batch_id', 'signature'), 'Batch')
        p.require(p.equal(batch['signature'], self._signature(tasks, skill, config)), 'Gate batch membership/identity differs')
        for record in records:
            self._check_record_journal(record, record['task_id'], skill, config, Path(directory), batch)

    def build_gate(self, parent_records, candidate_records, tasks, *, parent_skill, candidate_skill,
                   parent_directory, candidate_directory):
        """Require complete original archives; never recover or make requests."""
        self._preflight()
        self._cases(tasks, {'split': 'train', 'role': 'parent'})
        for role, records, skill, directory in (
            ('parent', parent_records, parent_skill, parent_directory),
            ('candidate', candidate_records, candidate_skill, candidate_directory),
        ):
            self._check_batch_records(records, tasks, skill, {'split': 'train', 'role': role}, directory)
            p.require(p.equal(read(Path(directory) / 'records.json'), records), 'Gate records differ from committed batch')
        identities = [r['run_id'] for r in parent_records + candidate_records]
        p.require(len(identities) == len(set(identities)), 'Gate reuses execution identity')
        pairs = []
        for parent, candidate in zip(parent_records, candidate_records):
            p.require(p.equal(parent['task'], candidate['task']), 'Paired task differs')
            for key in self._source_identity(self.dataset.case(parent['task_id'])):
                p.require(parent['provenance'][key] == candidate['provenance'][key], 'Paired source identity differs')
            pairs.append({'task_id': parent['task_id'],
                          'parent': {'run_id': parent['run_id'], 'success': parent['execution']['metrics']['em'] == 1},
                          'candidate': {'run_id': candidate['run_id'], 'success': candidate['execution']['metrics']['em'] == 1}})
        def scores(records):
            return [{'task_id': r['task_id'], 'metrics': r['execution']['metrics']} for r in records]
        return {'metric': p.GATE_PROFILE, 'input': {'pairs': pairs},
                'result': scoring.compare_scores(scores(parent_records), scores(candidate_records), tasks)}
