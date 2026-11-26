#!/usr/bin/env python3
"""Explicit mixed-budget functional pilot; never relabel old Actor executions."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.runs.run_v26_pilot import run_pilot, read_credentials
from src.skill_evolution.v26 import evolution as ev
from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter
from src.skill_evolution.v26.benchmarks.officeqa import evidence, facts, protocol as p
from src.skill_evolution.v26.contracts import gate
from src.skill_evolution.v26.training import load_dataset
from src.skill_evolution.v26.transport import HTTPGenerator
from src.adapters.officeqa.runtime import Runtime
from src.adapters.officeqa.transport import ChatTransport
from src.adapters.officeqa.history import validate_history


class MetadataTransport:
    def __init__(self, metadata): self.value = deepcopy(metadata)
    def metadata(self): return deepcopy(self.value)


class PilotAdapter(OfficeQAEvidenceAdapter):
    """Allow only manifest-pinned Parent records at the previous output limit."""
    def __init__(self, change, retained, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.change, self.retained = deepcopy(change), deepcopy(retained)
        self.old = OfficeQAEvidenceAdapter(self.dataset, self.runtime,
            MetadataTransport(change['old_actor']), gate_metric=self.gate_metric)
        ev.require(self.transport.metadata() == change['new_actor'], 'New Actor profile differs')
        ev.require({**change['old_actor'], 'max_completion_tokens': 32768} == change['new_actor'],
                   'Only Actor output limit may change')
        ev.require(change['old_actor']['max_completion_tokens'] == 16384, 'Unexpected old output limit')
        ev.require({r['run_id']: p.digest(r) for r in retained} == change['retained_records'],
                   'Retained record manifest differs')

    def _retained(self, record):
        if record['run_id'] not in self.change['retained_records']: return False
        ev.require(p.digest(record) == self.change['retained_records'][record['run_id']], 'Retained record changed')
        ev.require(record['provenance']['role'] == 'parent', 'Only Parent records may be retained')
        return True

    def _profile(self, record):
        facts.validate_envelope(record)
        expected = self.change['old_actor'] if self._retained(record) else self.change['new_actor']
        ev.require(record['execution']['actor'] == expected, 'Unapproved Actor profile')

    def check_record(self, record, task, expected_skill, config):
        self._profile(record)
        if self._retained(record): return self.old.check_record(record, task, expected_skill, config)
        return super().check_record(record, task, expected_skill, config)

    def build_facts(self, records, *, role=None):
        ev.require(records, 'Missing executions')
        role = role or records[0]['provenance']['role']; skill = facts.parent_text(records[0])
        runs, sources = [], []
        for i, record in enumerate(records, 1):
            self._profile(record)
            ev.require(facts.parent_text(record) == skill and record['provenance']['role'] == role,
                       'Mixed Skill or role')
            single = facts.build_facts([record], role=role)
            run = evidence.relabel(single['facts']['runs'][0], f'P{i}')
            runs.append(run); sources.append({k: run[k] for k in ('ref', 'task_id', 'run_id')})
        ev.require(len({r['task_id'] for r in runs}) == len(runs) == len({r['run_id'] for r in runs}),
                   'Duplicate task or execution')
        background = p.background(self.change['new_actor'])
        return {'facts': {'parent': skill, 'runs': runs}, 'background': background, 'sources': sources}

    def verify_pair(self, parent, candidate, *, implementation_review=None):
        self._profile(parent); self._profile(candidate)
        # Only validation copies normalize the single authorized difference.
        # Saved API responses, metadata, checksums and evidence records remain original.
        normalized = deepcopy(candidate)
        normalized['execution']['actor'] = deepcopy(parent['execution']['actor'])
        normalized['provenance']['record_sha256'] = p.digest(normalized['execution'])
        evidence.verify_pair(parent, normalized, implementation_review=implementation_review)

    def evidence(self, operation, *args, **kwargs):
        if operation == 'contracts.replay.verify_pair': return self.verify_pair(*args, **kwargs)
        return super().evidence(operation, *args, **kwargs)

    def resource(self, key):
        if key == 'execution_context.md':
            path = Path(self.change['execution_context_path'])
            ev.require(p.file_digest(path) == self.change['execution_context_sha256'], 'Pilot context changed')
            return path
        return super().resource(key)

    def actor_batch(self, tasks, skill_file, directory, config, *, final=False):
        self.validate_config(config)
        selected = [r for r in self.retained if r['task_id'] in tasks] if config['role'] == 'parent' else []
        skill = Path(skill_file).read_text() if skill_file else None
        for record in selected: self.check_record(record, record['task_id'], skill, config)
        missing = [t for t in tasks if t not in {r['task_id'] for r in selected}]
        fresh = super().actor_batch(missing, skill_file, directory, config, final=final) if missing else []
        return deepcopy(selected) + fresh  # Old completion order, then new completion order.

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
            self.verify_pair(pp[tid], qq[tid], implementation_review=implementation_review)
            pairs.append({'task_id': tid, **{side: {'run_id': r['run_id'], 'success': r['execution']['metrics']['em'] == 1}
                for side, r in [('parent', pp[tid]), ('candidate', qq[tid])]}})
        payload = {'pairs': pairs}; gate.validate_input(payload, tasks)
        return {'metric': self.gate_metric, 'input': payload, 'result': gate.decide_gate(payload, tasks)}

    def frozen_files(self):
        return {**super().frozen_files(), str(Path(__file__).relative_to(ROOT)): Path(__file__).read_text(),
                'scripts/runs/run_v26_pilot.py': (ROOT/'scripts/runs/run_v26_pilot.py').read_text()}

    def runtime_snapshot(self, config):
        return {**super().runtime_snapshot(config), 'pilot_budget_reuse': deepcopy(self.change)}


def prepare(source, root, adapter):
    """Import only complete, audited raw records; failed UID0007 stays in its old run."""
    source, root = Path(source).resolve(), Path(root).resolve()
    ev.require(not root.exists(), 'Continuation directory already exists; use --resume')
    cfg = ev.read(source/'config.json'); updated = deepcopy(cfg)
    updated['actor']['max_completion_tokens'] = 32768
    ev.require(adapter.transport.metadata() == updated['actor'], 'Continuation profile differs')
    folder = source/'rounds/R01/parent_runs'; meta = ev.read(folder/'evidence/batch.json')
    ev.require(meta['signature']['actor'] == cfg['actor'], 'Old batch profile differs')
    old = OfficeQAEvidenceAdapter(adapter.dataset, adapter.runtime, MetadataTransport(cfg['actor']), gate_metric=p.EM_GATE)
    states = {s['identity']['task_id']: (path, s) for path in (folder/'actor').rglob('actor_state.json')
              for s in [ev.read(path)]}
    retained = []; paths = []
    for line in (folder/'actor/results.jsonl').read_text().splitlines():
        row = json.loads(line); raw = row['record']; uid = row['id']; case = adapter.dataset.case(uid)
        ev.require(uid == raw['task_id'] and uid in cfg['batches'][0], 'Unexpected retained task')
        path, state = states[uid]; validate_history(state, reasoning=True)
        ev.require(state['status'] == 'completed' and state['record'] == raw, 'Retained state differs')
        record = {'schema': p.RECORD_VERSION, 'run_id': meta['batch_id']+':'+p.digest(uid),
                  'task_id': uid, 'task': p.public_task(case), 'execution': raw,
                  'provenance': {'batch_id': meta['batch_id'], 'role': 'parent',
                                 **meta['signature']['source_identities'][uid], 'record_sha256': p.digest(raw)}}
        old.check_record(record, uid, cfg['initial_skill']['text'], {'split': case.metadata['split'], 'role': 'parent'})
        retained.append(record); paths.append((uid, path))
    ev.require(len(retained) == 9 and len({r['task_id'] for r in retained}) == 9 and
               set(cfg['batches'][0]) - {r['task_id'] for r in retained} == {'UID0007'}, 'Expected nine complete Parent cases')
    change = {'purpose': 'user_authorized_mixed_budget_functional_pilot', 'source': str(source),
              'old_actor': cfg['actor'], 'new_actor': updated['actor'],
              'retained_records': {r['run_id']: p.digest(r) for r in retained},
              'retained_task_ids': [r['task_id'] for r in retained], 'rerun_tasks': ['UID0007'],
              'failed_old_attempts': 'preserved in source; not reset or imported as a completed execution'}
    root.mkdir(parents=True)
    context = root/'pilot_execution_context.md'
    note = ('\n\n## Authorized pilot budget exception\n\n'
            'This is a mixed-budget functional pilot. Retained Parent task IDs '+
            ', '.join(r['task_id'] for r in retained)+
            ' used max_completion_tokens=16384. The remaining Parent and every Candidate use 32768. '
            'All other Actor settings are identical. The 32768 profile above describes new requests. '
            'Do not attribute paired differences solely to Skill changes; this is not a controlled efficacy comparison.\n')
    context.write_text(adapter.resource('execution_context.md').read_text()+note)
    change.update(execution_context_path=str(context), execution_context_sha256=p.file_digest(context))
    ev.save(root/'continuation_config.json', updated)
    ev.save(root/'retained/records.json', retained); ev.save(root/'budget_reuse.json', change)
    for uid, path in paths:
        dest = root/'retained'/uid/'actor_state.json'; dest.parent.mkdir(parents=True)
        shutil.copyfile(path, dest)
    return updated, change, retained


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path); parser.add_argument('--source', type=Path)
    parser.add_argument('--resume', action='store_true'); parser.add_argument('--env-file', default=str(ROOT/'.env'))
    args = parser.parse_args(); root = args.directory.resolve()
    ev.require(bool(args.source) != args.resume, 'Supply --source or --resume')
    cfg = ev.read(args.source/'config.json' if args.source else root/'config.json')
    cfg['actor']['max_completion_tokens'] = 32768; actor = cfg['actor']; creds = read_credentials(args.env_file)
    ev.require(actor['endpoint'] == creds['OPENAI_BASE_URL'].rstrip('/')+'/chat/completions', 'Endpoint differs')
    ev.require(all(c['endpoint'] == actor['endpoint'] for c in cfg['module_calls'].values()), 'Method endpoint differs')
    transport = ChatTransport(endpoint=actor['endpoint'], api_key=creds['OPENAI_API_KEY'],
        **{k: actor[k] for k in ('model', 'max_completion_tokens', 'temperature', 'reasoning_effort', 'reasoning_mode', 'token_limit_field')})
    base = OfficeQAEvidenceAdapter(load_dataset(ROOT/'data/officeqa/prepared_v2', cfg.get('optimization_pool')),
        Runtime(ROOT/'data/officeqa/raw/treasury_bulletins_parsed'), transport, gate_metric=p.EM_GATE)
    if args.source: cfg, change, retained = prepare(args.source, root, base)
    else: change, retained = ev.read(root/'budget_reuse.json'), ev.read(root/'retained/records.json')
    adapter = PilotAdapter(change, retained, base.dataset, base.runtime, transport, gate_metric=p.EM_GATE)
    with using_benchmark(adapter):
        result = run_pilot(root, config=cfg if args.source else None,
                           generate=HTTPGenerator(creds['OPENAI_API_KEY']), resume=args.resume)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
