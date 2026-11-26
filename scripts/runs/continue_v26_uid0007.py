#!/usr/bin/env python3
"""Authorized UID0007-only budget continuation; original failure remains immutable."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.runs.run_v26_pilot import read_credentials
from src.adapters.officeqa.runtime import Runtime
from src.adapters.officeqa.transport import ChatTransport
from src.adapters.officeqa.history import validate_history
from src.skill_evolution.v26 import evolution as ev
from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter
from src.skill_evolution.v26.benchmarks.officeqa import facts, evidence, protocol as p
from src.skill_evolution.v26.contracts import gate
from src.skill_evolution.v26.training import load_dataset
from src.skill_evolution.v26.transport import HTTPGenerator

TASK_LIMITS = {'UID0007': 65536}
CONTEXT = ROOT / 'docs/methods/v26/UID0007_EXECUTION_CONTEXT.md'


class TaskBudgetAdapter(OfficeQAEvidenceAdapter):
    """Same task budget on both sides; no metadata normalization or Gate exception."""
    def __init__(self, change, retained, special_transport, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.change, self.retained = deepcopy(change), deepcopy(retained)
        ev.require(self.transport.metadata()['max_completion_tokens'] == 32768, 'Unexpected default budget')
        ev.require(special_transport.metadata() == {
            **self.transport.metadata(), 'max_completion_tokens': 65536}, 'Only output budget may differ')
        ev.require(change['task_max_completion_tokens'] == TASK_LIMITS, 'Unauthorized task budget')
        ev.require(change['retained_records'] == {r['run_id']: p.digest(r) for r in retained},
                   'Retained record manifest differs')
        self.special = OfficeQAEvidenceAdapter(self.dataset, self.runtime, special_transport,
                                               gate_metric=self.gate_metric)

    def _adapter(self, task):
        return self.special if task in TASK_LIMITS else self

    def check_record(self, record, task, expected_skill, config):
        if record['run_id'] in self.change['retained_records']:
            ev.require(p.digest(record) == self.change['retained_records'][record['run_id']],
                       'Retained record changed')
        return OfficeQAEvidenceAdapter.check_record(self._adapter(task), record, task, expected_skill, config)

    def build_facts(self, records, *, role=None):
        ev.require(bool(records), 'Missing executions')
        role = role or records[0]['provenance']['role']; skill = facts.parent_text(records[0])
        runs, sources = [], []
        for i, record in enumerate(records, 1):
            task = record['task_id']
            ev.require(record['execution']['actor'] == self._adapter(task).transport.metadata(),
                       'Task Actor budget differs')
            if record['run_id'] in self.change['retained_records']:
                ev.require(p.digest(record) == self.change['retained_records'][record['run_id']],
                           'Retained record changed')
            ev.require(facts.parent_text(record) == skill and record['provenance']['role'] == role,
                       'Mixed Skill or role')
            single = facts.build_facts([record], role=role)
            run = evidence.relabel(single['facts']['runs'][0], f'P{i}')
            runs.append(run); sources.append({k: run[k] for k in ('ref', 'task_id', 'run_id')})
        ev.require(len({r['task_id'] for r in runs}) == len(runs) == len({r['run_id'] for r in runs}),
                   'Duplicate execution/task')
        background = p.background(self.transport.metadata())
        return {'facts': {'parent': skill, 'runs': runs}, 'background': background, 'sources': sources}

    def resource(self, key):
        return CONTEXT if key == 'execution_context.md' else super().resource(key)

    def actor_batch(self, tasks, skill_file, directory, config, *, final=False):
        self.validate_config(config)
        tasks = list(tasks)
        ev.require(tasks and len(set(tasks)) == len(tasks), 'Empty/duplicate task list')
        skill = Path(skill_file).read_text() if skill_file else None
        selected = [r for r in self.retained if r['task_id'] in tasks
                    and config['role'] == 'parent' and r['execution']['skill'] == skill]
        for r in selected: self.check_record(r, r['task_id'], skill, config)
        pending = [t for t in tasks if t not in {r['task_id'] for r in selected}]
        result = deepcopy(selected)
        for special in (False, True):
            ids = [t for t in pending if (t in TASK_LIMITS) == special]
            if ids:
                adapter = self.special if special else self
                result.extend(OfficeQAEvidenceAdapter.actor_batch(adapter, ids, skill_file,
                    Path(directory) / ('task_budget' if special else 'default_budget'), config, final=final))
        return result

    def build_gate(self, parent_records, candidate_records, tasks, *, parent_skill, candidate_skill,
                   implementation_review=None):
        ev.require(self.gate_metric == p.EM_GATE, 'Explicit EM Gate required')
        self.build_facts(parent_records, role='parent'); self.build_facts(candidate_records, role='candidate')
        pp = {r['task_id']: r for r in parent_records}; qq = {r['task_id']: r for r in candidate_records}
        ev.require(set(pp) == set(qq) == set(tasks), 'Incomplete Gate coverage')
        pairs = []
        for tid in tasks:
            for role, record, skill in [('parent', pp[tid], parent_skill), ('candidate', qq[tid], candidate_skill)]:
                self.check_record(record, tid, skill, {'split': record['task']['split'], 'role': role})
            evidence.verify_pair(pp[tid], qq[tid], implementation_review=implementation_review)
            pairs.append({'task_id': tid, **{side: {'run_id': r['run_id'], 'success': r['execution']['metrics']['em'] == 1}
                for side, r in [('parent', pp[tid]), ('candidate', qq[tid])]}})
        payload = {'pairs': pairs}; gate.validate_input(payload, tasks)
        return {'metric': self.gate_metric, 'input': payload, 'result': gate.decide_gate(payload, tasks)}

    def frozen_files(self):
        return {**super().frozen_files(), str(Path(__file__).relative_to(ROOT)): Path(__file__).read_text(),
                str(CONTEXT.relative_to(ROOT)): CONTEXT.read_text()}

    def runtime_snapshot(self, config):
        return {**super().runtime_snapshot(config), 'task_budget_continuation': deepcopy(self.change)}


def import_records(source, base):
    """Audit nine completed records against current source bytes; never touch old journals."""
    cfg = ev.read(source / 'config.json'); folder = source / 'rounds/R01/parent_runs'
    meta = ev.read(folder / 'evidence/batch.json')
    ev.require(meta['signature']['actor'] == cfg['actor'] == base.transport.metadata(), 'Source profile differs')
    records = []
    for line in (folder / 'actor/results.jsonl').read_text().splitlines():
        row = json.loads(line); raw = row['record']; uid = row['id']
        # Case directory uses SHA256 of the literal ID, unlike p.digest(JSON).
        state = ev.read(folder / 'actor/cases' / hashlib.sha256(uid.encode()).hexdigest() / 'actor_state.json')
        validate_history(state, reasoning=raw['actor']['reasoning_mode'] == 'deepseek_thinking')
        ev.require(state['status'] == 'completed' and state['record'] == raw, 'Retained state differs')
        ev.require(uid == raw['task_id'] and uid in cfg['batches'][0], 'Unexpected retained task')
        record = {'schema': p.RECORD_VERSION, 'run_id': meta['batch_id'] + ':' + p.digest(uid),
            'task_id': uid, 'task': p.public_task(base.dataset.case(uid)), 'execution': raw,
            'provenance': {'batch_id': meta['batch_id'], 'role': 'parent',
                          **meta['signature']['source_identities'][uid], 'record_sha256': p.digest(raw)}}
        base.check_record(record, uid, cfg['initial_skill']['text'], {'split': 'train', 'role': 'parent'})
        records.append(record)
    ev.require(len(records) == len({r['task_id'] for r in records}) == 9 and
               set(cfg['batches'][0]) - {r['task_id'] for r in records} == {'UID0007'}, 'Expected nine completed cases')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--validation', type=Path)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(); root = args.directory.resolve()
    ev.require(args.resume != bool(args.source), 'Use --source for a new continuation or --resume')
    cfg = ev.read((args.source if args.source else root) / 'config.json')
    credentials = read_credentials(ROOT / '.env'); actor = cfg['actor']
    ev.require(actor['endpoint'] == credentials['OPENAI_BASE_URL'].rstrip('/') + '/chat/completions', 'Endpoint differs')
    ev.require(all(c['endpoint'] == actor['endpoint'] for c in cfg['module_calls'].values()), 'Method endpoint differs')
    def transport(limit):
        fields = {k: actor[k] for k in ('model', 'max_completion_tokens', 'temperature',
                                       'reasoning_effort', 'reasoning_mode', 'token_limit_field')}
        fields['max_completion_tokens'] = limit
        return ChatTransport(endpoint=actor['endpoint'], api_key=credentials['OPENAI_API_KEY'], **fields)
    default, special = transport(32768), transport(65536)
    dataset = load_dataset(ROOT / 'data/officeqa/prepared_v2', cfg.get('optimization_pool'))
    runtime = Runtime(ROOT / 'data/officeqa/corrected_v2/treasury_bulletins_parsed')
    base = OfficeQAEvidenceAdapter(dataset, runtime, default, gate_metric=p.EM_GATE)
    if args.source:
        ev.require(not root.exists(), 'Continuation directory already exists')
        ev.require(args.validation is not None, 'Completed single-task validation required')
        validation = args.validation.resolve(); result = ev.read(validation / 'validation_result.json')
        ev.require(result.get('passed') is True, 'UID0007 validation did not pass; training remains stopped')
        retained = import_records(args.source.resolve(), base)
        path = validation / 'validation/evidence/records' / p.digest('UID0007') / 'trajectory.json'
        record = ev.read(path)
        high = OfficeQAEvidenceAdapter(dataset, runtime, special, gate_metric=p.EM_GATE)
        high.check_record(record, 'UID0007', cfg['initial_skill']['text'], {'split': 'train', 'role': 'parent'})
        ev.require(record['execution']['metrics']['em'] == 1 and
                   record['execution']['raw_result']['termination_reason'] == 'answer', 'Validation must answer correctly')
        retained.append(record)
        change = {'source': str(args.source.resolve()), 'validation': str(validation),
            'task_max_completion_tokens': TASK_LIMITS, 'restart_from_round': 1,
            'retained_records': {r['run_id']: p.digest(r) for r in retained},
            'source_files_sha256': {str(f.relative_to(args.source)): p.file_digest(f)
                                   for f in sorted(args.source.rglob('*')) if f.is_file()},
            'validation_record_sha256': p.digest(record), 'at': ev.now()}
        root.mkdir(parents=True)
        ev.save(root / 'budget_policy.json', change); ev.save(root / 'retained/records.json', retained)
        shutil.copyfile(validation / 'validation_result.json', root / 'retained/validation_result.json')
    else:
        change, retained = ev.read(root / 'budget_policy.json'), ev.read(root / 'retained/records.json')
    adapter = TaskBudgetAdapter(change, retained, special, dataset, runtime, default, gate_metric=p.EM_GATE)
    with using_benchmark(adapter):
        result = ev.run_campaign(root, config=cfg, generate=HTTPGenerator(credentials['OPENAI_API_KEY']), resume=args.resume)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
