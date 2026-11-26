"""Independent method binding around the original OfficeQA Actor and archive."""
from contextlib import contextmanager
from copy import deepcopy
import json
import uuid
from src.adapters.officeqa.bridges import GovernActor, _batch, save_record
from src.adapters.officeqa.execution import atomic_json, _locked
from .protocol import require
import hashlib
from pathlib import Path
from skilladam.backends import openai_compatible as native
from src.adapters.officeqa.history import validate_history
from src.adapters.officeqa.transport import RequestFailure
from src.skill_evolution.v26.benchmarks.officeqa.task_budget import TaskOutputBudgetAdapter
from src.skill_evolution.v27.benchmark import using_benchmark
from src.skill_evolution.v28 import validation
from . import evidence, protocol as p
from .actor_io import read_skill

RUNTIME_VERSION = 'v26_1_light_runtime_v1'


class ByteSkillActor(GovernActor):
    """The same common scheduler and Runtime, with an exact UTF-8 Skill read."""
    def actor_batch(self, tasks, skill_file, directory, config, *, final=False):
        cases = self._cases(tasks, config, final)
        skill = read_skill(skill_file)
        records = _batch(self.dataset, self.runtime, self.transport, cases, [skill] * len(cases),
                         directory, owner='govern', workers=self.workers, context={'final': final})
        for record in records:
            save_record(Path(directory) / 'predictions' / record['task_id'], record)
        return records


class CampaignAdapter(TaskOutputBudgetAdapter):
    method_version = 'v26_1_campaign_v1'
    verify_hashes = False
    test_workers = 4

    def __init__(self, dataset, runtime, transport, *, task_transports):
        super().__init__(dataset, runtime, transport, task_transports=task_transports, workers=4)
        self._records, self._directories = {}, {}
        self._rows = deepcopy(dataset.rows)
        self._preflight()

    @property
    def actor_adapter(self):
        return self

    def _preflight(self):
        p.validate_actor(self.transport.metadata())
        p.require(self.workers == self.test_workers == 4 and self.task_output_limits == p.LIMITS,
                  'OfficeQA workers or task budgets differ')
        p.require(p.equal(self.dataset.rows, self._rows), 'Bound task data changed')
        for task, adapter in self.task_adapters.items():
            p.require(adapter.transport.metadata() == {**self.transport.metadata(),
                      'max_completion_tokens': p.LIMITS[task]}, 'Task budget transport differs')

    @contextmanager
    def using(self):
        self._preflight()
        with using_benchmark(self): yield self

    def memory_operation(self):
        return validation.operation(self)

    def verify_memory_operation(self):
        active = validation.current(self)
        if active is not None: active.verify()

    def begin_round(self):
        self._records.clear()
        self._directories.clear()

    def validation_sources(self):
        return set(Path(__file__).parent.glob('*.py'))

    def runtime_snapshot(self, config):
        self._preflight()
        return {'method': self.method_version, 'actor': self.transport.metadata(),
                'revision': p.REVISION, 'parsed_root': str(self.runtime.parsed_root),
                'task_output_limits': self.task_output_limits, 'workers': 4, 'test_workers': 4}

    def actor_batch(self, tasks, skill_file, directory, config, *, final=False):
        from .telemetry import invocation
        with invocation(directory, 'actor_' + config['role']):
            return self._actor_batch(tasks, skill_file, directory, config, final=final)

    def _actor_batch(self, tasks, skill_file, directory, config, *, final=False):
        self._preflight()
        self._bound(); self.validate_config(config)
        require(type(final) is bool and final == (config['role'] == 'evaluation'), 'Execution role/final flag differs')
        tasks = list(tasks)
        require(tasks and len(tasks) == len(set(tasks)), 'Empty/duplicate tasks')
        cases = [self.dataset.case(t) for t in tasks]
        require(all(c.metadata['split'] == config['split'] for c in cases), 'Task is outside requested split')
        skill = read_skill(skill_file)
        directory = Path(directory); record_dir = directory / 'evidence'
        with _locked(record_dir):
            signature = {'identity': self.identity, 'tasks': [p.public_task(c) for c in cases],
                         'actor': self.transport.metadata(),
                         'skill': skill, 'role': config['role'], 'split': config['split'], 'workers': self.workers}
            if getattr(self, 'task_output_limits', None):
                signature['actor_task_output_limits'] = deepcopy(self.task_output_limits)
            meta_path = record_dir / 'batch.json'
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                require(p.equal(meta['signature'], signature), 'Evidence batch identity differs; use a new directory')
            else:
                meta = {'batch_id': str(uuid.uuid4()), 'signature': signature}; atomic_json(meta_path, meta)
            # Exactly one shared case pool: do not wrap this in V25's outer Actor pool.
            common = ByteSkillActor(self.dataset, self.runtime, self.transport, workers=self.workers)
            records = common.actor_batch(tasks, skill_file, directory / 'actor', {'split': config['split']}, final=final)
            by_id = {c.case_id: c for c in cases}; result = []
            for raw in records:  # Keep journal completion order, including resumed entries.
                uid = raw['task_id']; case = by_id[uid]
                record = {'schema': p.RECORD_VERSION, 'run_id': meta['batch_id'] + ':' + p.digest(uid),
                          'task_id': uid, 'task': p.public_task(case), 'execution': deepcopy(raw),
                          'provenance': {'batch_id': meta['batch_id'], 'role': config['role']}}
                self.check_record(record, uid, skill, config)
                save_record(record_dir / 'records' / p.digest(uid), record); result.append(record)
            from .stages import freeze
            freeze(directory / 'records.json', result)
            self.read_batch(directory)
            return result

    def check_record(self, record, task, expected_skill, config):
        self.validate_config(config)
        evidence.audit_execution(record)
        case = self.dataset.case(task)
        raw = record['execution']
        require(record['task_id'] == task and p.equal(record['task'], p.public_task(case)), 'Canonical task differs')
        require(case.metadata['split'] == config['split'] and record['provenance']['role'] == config['role'],
                'Execution split/role differs')
        require(raw['skill'] == expected_skill and p.equal(raw['actor'], self._adapter(task).transport.metadata()),
                'Actor or Skill differs')
        initial, _ = self.runtime.prepare(case, expected_skill)
        require(p.equal(raw['initial_messages'], self._redact(initial)), 'Initial Actor input differs')
        parsed = self.runtime.scorer.parse_result(case, raw['raw_result'])
        require(p.equal(raw['metrics'], dict(self.runtime.scorer.evaluate(parsed).metrics)), 'Native score differs')
        return record

    def is_complete(self, record):
        try:
            evidence.audit_execution(record)
        except (ValueError, KeyError, TypeError, RequestFailure):
            return False
        return True

    def read_batch(self, directory):
        from .stages import read
        root = Path(directory).resolve()
        records = read(root / 'records.json')
        meta = read(root / 'evidence/batch.json')
        signature = meta['signature']
        tasks = [t['id'] for t in signature['tasks']]
        p.require(isinstance(records, list) and len(records) == len(tasks) and
                  {r['task_id'] for r in records} == set(tasks), 'Incomplete Actor batch')
        p.require(signature['actor'] == self.transport.metadata() and signature['workers'] == 4 and
                  signature.get('actor_task_output_limits') == self.task_output_limits, 'Batch settings differ')
        p.require(signature['tasks'] == [p.public_task(self.dataset.case(t)) for t in tasks], 'Batch tasks differ')
        journal = []
        for line in (root / 'actor/results.jsonl').read_bytes().splitlines(keepends=True):
            p.require(line.endswith(b'\n'), 'Torn completed Actor journal')
            import json
            journal.append(json.loads(line))
        p.require([r['id'] for r in journal] == [r['task_id'] for r in records], 'Completion order differs')
        run = read(root / 'actor/run.json')
        p.require(run['ids'] == tasks and run['identity']['tasks'] == [self.dataset.rows[t] for t in tasks] and
                  run['identity']['skills'] == [signature['skill']] * len(tasks) and
                  run['identity']['actor'] == self.transport.metadata() and
                  run['identity']['context'] == {'final': signature['role'] == 'evaluation'}, 'Native batch identity differs')
        config = {'split': signature['split'], 'role': signature['role']}
        for row, record in zip(journal, records):
            tid = record['task_id']; raw = record['execution']
            self.check_record(record, tid, signature['skill'], config)
            p.require(record['provenance']['batch_id'] == meta['batch_id'], 'Source batch differs')
            p.require(p.equal(row['record'], raw), 'Batch raw record differs')
            p.require(p.equal(read(root / 'evidence/records' / p.digest(tid) / 'trajectory.json'), record),
                      'Envelope archive differs')
            state_path = root / 'actor/cases' / hashlib.sha256(tid.encode()).hexdigest() / 'actor_state.json'
            state = read(state_path)
            initial, _ = self.runtime.prepare(self.dataset.case(tid), signature['skill'])
            expected_identity = {'profile': raw['profile'], 'method': 'govern', 'task_id': tid,
                'skill': signature['skill'], 'actor': raw['actor'], 'input_sha256': hashlib.sha256(json.dumps(
                    {'messages': initial, 'reference': list(self.dataset.case(tid).reference)},
                    sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
            p.require(state['identity'] == expected_identity and state['initial'] == initial, 'Actor state identity differs')
            validate_history(state, reasoning=raw['actor']['reasoning_mode'] == 'deepseek_thinking')
            p.require(state['complete'] is True and state['status'] == 'completed' and
                      p.equal(state['record'], raw), 'Actor state is incomplete or differs')
            p.require(p.equal(native._redact_officeqa_value(state['rounds'], state['redactions']), raw['request_audit']) and
                      p.equal(native._redact_officeqa_value(state['messages'], state['redactions']), raw['raw_result']['messages']),
                      'Committed tools or requests differ from evidence')
        return records

    def register_archive(self, directory):
        root = Path(directory).resolve()
        records = self.read_batch(root)
        p.require(all(r['provenance']['role'] in ('parent', 'candidate') for r in records), 'Test cannot become method evidence')
        for record in records:
            rid = record['run_id']
            if rid in self._records:
                p.require(p.equal(self._records[rid], record) and self._directories[rid] == root, 'Archive rebinding differs')
            self._records[rid], self._directories[rid] = deepcopy(record), root

    def source_record(self, run_id):
        p.require(run_id in self._records, 'Unregistered execution')
        return self.validate_record(self._records[run_id])

    def validate_record(self, record):
        rid = record['run_id']
        p.require(rid in self._records and p.equal(record, self._records[rid]), 'Registered execution differs')
        root = self._directories[rid]
        active = validation.current(self)
        if active is None or root not in active.batches:
            records = self.read_batch(root)
            p.require(p.equal(records, [self._records[r['run_id']] for r in records]), 'Registered batch differs')
            if active is not None:
                active.batches[root] = records
                active.watch_tree(root)
        return deepcopy(record)

    def build_facts(self, records, *, role=None):
        with self.memory_operation():
            p.require(isinstance(records, list) and records, 'Missing completed batch')
            for record in records: self.validate_record(record)
            root = self._directories[records[0]['run_id']]
            from .stages import read
            p.require(p.equal(records, read(root / 'records.json')), 'Facts require the whole saved batch in completion order')
            skill = records[0]['execution']['skill']
            role = role or records[0]['provenance']['role']
            require(role in ('parent', 'candidate'), 'Test cannot enter optimization')
            runs = []
            for index, record in enumerate(records, 1):
                require(record['execution']['skill'] == skill and record['provenance']['role'] == role,
                        'Mixed Skill or role')
                runs.append(evidence.formal_run(record, f'P{index}'))
            background = p.background({**self.transport.metadata(), 'task_max_completion_tokens': self.task_output_limits})
            return {'facts': {'parent': skill, 'runs': runs}, 'background': background,
                    'sources': [{k: run[k] for k in ('ref', 'task_id', 'run_id')} for run in runs]}

    def plan_fields(self):
        return ('parent', 'plan', 'runs', 'memory')
