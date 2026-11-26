"""OfficeQA data/evidence binding and public Actor bridge, without a trainer."""
from copy import deepcopy
import json
from pathlib import Path
import uuid

from skilladam.backends import openai_compatible as native
from skilladam.benchmarks.officeqa import tool_runtime
from src.adapters.officeqa.bridges import GovernActor, save_record
from src.adapters.officeqa.execution import atomic_json, _locked
from src.adapters.officeqa.transport import RequestFailure
from ...contracts import gate
from ...facts import require
from . import evidence, facts, protocol as p


class OfficeQAEvidenceAdapter:
    """Evidence and Prompt binding; no default model/Skill/optimizer."""
    identity = p.IDENTITY
    allowed_workers = (4,)

    def __init__(self, dataset=None, runtime=None, transport=None, *, workers=4, gate_metric=None):
        require(type(workers) is int and workers in self.allowed_workers, 'Unsupported OfficeQA worker count')
        require(gate_metric in (None, p.EM_GATE), 'Unsupported OfficeQA Gate metric')
        require(all(x is None for x in (dataset, runtime, transport)) or
                all(x is not None for x in (dataset, runtime, transport)), 'Supply all Actor dependencies explicitly')
        self.dataset, self.runtime, self.transport = dataset, runtime, transport
        self.workers, self.gate_metric = workers, gate_metric

    build_facts = staticmethod(facts.build_facts)
    parent_text = staticmethod(facts.parent_text)
    execution_context = staticmethod(p.execution_context)

    def evidence(self, operation, *args, **kwargs):
        require(operation in evidence.OPERATIONS, f'Unsupported evidence operation: {operation}')
        return evidence.OPERATIONS[operation](*args, **kwargs)

    def plan_fields(self):
        return ('parent', 'plan', 'runs', 'grouping', 'memory')

    def auxiliary_references(self, payload):
        return set()

    def validate_execution_source(self, source):
        p.fields(source, ('run',), 'Execution source')
        return evidence.validate_run(source['run'])

    def validation_sources(self):
        return {Path(module.__file__).resolve() for module in (facts, evidence, p)}

    def frozen_files(self):
        root = Path(__file__).resolve().parents[5]
        local = Path(__file__).resolve().parents[2]
        paths = sorted([*local.rglob('*.py'), *local.rglob('*.md'),
                        *(root / 'src/adapters/officeqa').glob('*.py')])
        return {str(path.relative_to(root)): path.read_text() for path in paths}

    def resource(self, key):
        from .prompting import resource_path
        return resource_path(key)

    def runtime_snapshot(self, config):
        """Freeze data/scorer identity without archiving reference answers as text."""
        import sys
        from importlib.metadata import version
        import skilladam
        from ...training import load_dataset
        self._bound()
        fresh = load_dataset(self.dataset.root, getattr(self.dataset, 'optimization_pool', None))
        tasks = sorted({task for batch in config['batches'] for task in batch})
        require(all(p.equal(fresh.rows[t], self.dataset.rows[t]) for t in tasks), 'Dataset changed after binding')
        package = Path(skilladam.__file__).resolve().parent
        return {'python': sys.version, 'requests': version('requests'),
                'prepared_root': str(self.dataset.root), 'parsed_root': str(self.runtime.parsed_root),
                'actor': self.transport.metadata(), 'workers': self.workers, 'gate_metric': self.gate_metric,
                'tasks': {t: {'case_sha256': p.digest(fresh.rows[t]),
                              **self._source_identity(fresh.case(t))} for t in tasks},
                'native_sources': {str(path.relative_to(package)): p.file_digest(path)
                                   for path in sorted(package.rglob('*.py'))}}

    def _bound(self):
        require(self.dataset is not None and self.runtime is not None and self.transport is not None,
                'Explicit dataset, runtime and transport required for Actor access')

    def _source_identity(self, case):
        """Bind actual source bytes and the neutral task context, without exposing gold."""
        messages, allowed = self.runtime.prepare(case, None)
        assets = {}
        for name in allowed:
            parsed = tool_runtime._locate_parsed_json(name, self.runtime.roots)
            require(parsed is not None, 'Missing parsed source')
            assets[name] = {'text_sha256': p.file_digest(self.runtime.text_root / name),
                            'parsed_json_sha256': p.file_digest(parsed)}
        return {'source_assets': assets, 'task_context_sha256': p.digest(self._redact(messages))}

    def _redact(self, value):
        return native._redact_officeqa_value(value, native._officeqa_redactions(
            data_root=self.runtime.parsed_root, allowed_roots=self.runtime.roots))

    def validate_config(self, config):
        require(isinstance(config, dict), 'Missing OfficeQA execution configuration')
        require(config.get('split') in ('train', 'validation', 'test'), 'Explicit public split required')
        require(config.get('role') in ('parent', 'candidate', 'evaluation'), 'Explicit execution role required')
        if config['role'] == 'evaluation':
            require(config['split'] == 'test', 'Evaluation requires Test split')
        else:
            require(config['split'] != 'test', 'Test cannot be used for optimization')

    def actor_batch(self, tasks, skill_file, directory, config, *, final=False):
        self._bound(); self.validate_config(config)
        require(type(final) is bool and final == (config['role'] == 'evaluation'), 'Execution role/final flag differs')
        tasks = list(tasks)
        require(tasks and len(tasks) == len(set(tasks)), 'Empty/duplicate tasks')
        cases = [self.dataset.case(t) for t in tasks]
        require(all(c.metadata['split'] == config['split'] for c in cases), 'Task is outside requested split')
        skill = Path(skill_file).read_text() if skill_file is not None else None
        directory = Path(directory); record_dir = directory / 'evidence'
        with _locked(record_dir):
            source_identities = {c.case_id: self._source_identity(c) for c in cases}
            signature = {'identity': self.identity, 'tasks': [p.public_task(c) for c in cases],
                         'source_identities': source_identities, 'actor': self.transport.metadata(),
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
            common = GovernActor(self.dataset, self.runtime, self.transport, workers=self.workers)
            records = common.actor_batch(tasks, skill_file, directory / 'actor', {'split': config['split']}, final=final)
            by_id = {c.case_id: c for c in cases}; result = []
            for raw in records:  # Keep journal completion order, including resumed entries.
                uid = raw['task_id']; case = by_id[uid]
                record = {'schema': p.RECORD_VERSION, 'run_id': meta['batch_id'] + ':' + p.digest(uid),
                          'task_id': uid, 'task': p.public_task(case), 'execution': deepcopy(raw),
                          'provenance': {'batch_id': meta['batch_id'], 'role': config['role'],
                                         **source_identities[uid], 'record_sha256': p.digest(raw)}}
                self.check_record(record, uid, skill, config)
                save_record(record_dir / 'records' / p.digest(uid), record); result.append(record)
            return result

    def actor_task(self, task, skill_file, directory, config, *, final=False):
        record = self.actor_batch([task], skill_file, directory, config, final=final)[0]
        return Path(directory) / 'evidence' / 'records' / p.digest(record['task_id']) / 'trajectory.json'

    def check_record(self, record, task, expected_skill, config):
        self._bound(); self.validate_config(config); facts.validate_envelope(record)
        case = self.dataset.case(task); raw = record['execution']
        require(record['task_id'] == task and p.equal(record['task'], p.public_task(case)), 'Canonical task differs')
        require(case.metadata['split'] == config['split'] and record['provenance']['role'] == config['role'], 'Execution split/role differs')
        require(raw['skill'] == expected_skill and p.equal(raw['actor'], self.transport.metadata()), 'Actor or Skill differs')
        current = self._source_identity(case)
        require(all(p.equal(record['provenance'][k], v) for k, v in current.items()), 'Source bytes or task context changed')
        initial, _ = self.runtime.prepare(case, expected_skill)
        require(p.equal(raw['initial_messages'], self._redact(initial)), 'Initial Actor input differs')
        parsed = self.runtime.scorer.parse_result(case, raw['raw_result'])
        require(p.equal(raw['metrics'], dict(self.runtime.scorer.evaluate(parsed).metrics)), 'Native score differs')
        return record

    def is_complete(self, record):
        try:
            facts.validate_envelope(record)
        except (ValueError, KeyError, TypeError, RequestFailure):
            return False
        return True

    def build_gate(self, parent_records, candidate_records, tasks, *, parent_skill, candidate_skill,
                   implementation_review=None):
        require(self.gate_metric == p.EM_GATE, 'Select officeqa_em_exact_v1 explicitly before building a Gate')
        tasks = list(tasks); require(tasks and len(tasks) == len(set(tasks)), 'Invalid Gate task IDs')
        parent = self.build_facts(parent_records, role='parent'); candidate = self.build_facts(candidate_records, role='candidate')
        require(parent['facts']['parent'] == parent_skill and candidate['facts']['parent'] == candidate_skill, 'Gate Skill differs')
        pp = {r['task_id']: r for r in parent_records}; qq = {r['task_id']: r for r in candidate_records}
        require(set(pp) == set(qq) == set(tasks), 'Incomplete Gate coverage')
        pairs = []
        for tid in tasks:
            if self.dataset is not None:
                for role, record, skill in (('parent', pp[tid], parent_skill), ('candidate', qq[tid], candidate_skill)):
                    self.check_record(record, tid, skill, {'split': record['task']['split'], 'role': role})
            evidence.verify_pair(pp[tid], qq[tid], implementation_review=implementation_review)
            pairs.append({'task_id': tid, 'parent': {'run_id': pp[tid]['run_id'], 'success': pp[tid]['execution']['metrics']['em'] == 1},
                          'candidate': {'run_id': qq[tid]['run_id'], 'success': qq[tid]['execution']['metrics']['em'] == 1}})
        payload = {'pairs': pairs}; gate.validate_input(payload, tasks)
        return {'metric': self.gate_metric, 'input': payload, 'result': gate.decide_gate(payload, tasks)}


class SkillAdamEvidenceAdapter(OfficeQAEvidenceAdapter):
    train_workers = 10
    test_workers = 20
    allowed_workers = (4, train_workers, test_workers)
