"""Durable I/O receipts around the unchanged native SkillAdam algorithm."""
from collections.abc import Mapping
from dataclasses import asdict
import json
from pathlib import Path
import re

from skilladam.execution.contracts import GenerationResult, ToolCall
from skilladam.types import UsageRecord
from src.skill_evolution.v27.benchmarks.lmb import actor, protocol as p
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.stages import freeze, freeze_text, read, save


def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


class Recovery:
    def __init__(self, backend):
        self.backend = backend
        self.root = backend.output_dir.parent / 'recovery'

    def index(self, name):
        path = self.root / (name + '.json')
        return read(path) if path.exists() else {}

    def register(self, kind, key, signature):
        index = self.index(kind)
        if key in index:
            require(p.equal(index[key]['signature'], signature), f'{kind} request changed: {key}')
        else:
            index[key] = {'signature': signature, 'completion': None}
            save(self.root / (kind + '.json'), index)
        return index[key]

    def complete(self, kind, key, value):
        index = self.index(kind)
        checksum = p.digest(value)
        require(index[key]['completion'] in (None, checksum), f'{kind} completion changed: {key}')
        index[key]['completion'] = checksum
        save(self.root / (kind + '.json'), index)

    def generate(self, request):
        iteration = request.metadata['iteration']
        require(type(iteration) is int and iteration >= 0, 'Invalid generation iteration')
        require(request.stage in ('iteration_patch', 'momentum_update'), 'Unexpected optimizer stage')
        attempt = request.metadata.get('patch_attempt', 0)
        require(type(attempt) is int and attempt >= 0, 'Invalid patch attempt')
        key = f'iter_{iteration:03d}/{request.stage}_{attempt:02d}'
        signature = plain({'stage': request.stage, 'messages': request.messages,
                           'context': asdict(request.context), 'metadata': request.metadata})
        entry = self.register('generations', key, signature)
        path = self.root / 'generations' / (key + '.json')
        if path.exists():
            payload = read(path)
            require(entry['completion'] in (None, p.digest(payload)), 'Cached generation changed')
            require(p.equal(payload['signature'], signature), 'Cached generation input changed')
            value = payload['result']
            result = GenerationResult(value['text'], tuple(UsageRecord(**u) for u in value['usage']),
                                      tuple(ToolCall(c['name'], c['arguments']) for c in value['tool_calls']))
        else:
            require(entry['completion'] is None, 'Missing completed optimizer response')
            result = self.backend.generation.generate(request)
            value = {'text': result.text, 'usage': [plain(asdict(u)) for u in result.usage],
                     'tool_calls': [{'name': c.name, 'arguments': plain(c.arguments)} for c in result.tool_calls]}
            payload = {'signature': signature, 'result': value}
            freeze(path, payload)
        self.complete('generations', key, payload)
        return result

    def rollout_key(self, directory):
        key = str(Path(directory).relative_to(self.backend.output_dir))
        require(re.fullmatch(r'iter_\d{3,}/(training|validation_parent|validation_candidate)', key),
                'Invalid native rollout location')
        return key

    def validate(self):
        """Read-only, global preflight, including stages skipped by native resume."""
        backend = self.backend
        index = self.index('rollouts')
        if backend.output_dir.exists():
            for folder in backend.output_dir.glob('iter_*/*'):
                require(self.rollout_key(folder) in index, 'Unregistered Actor stage')
        for key, entry in index.items():
            root = backend.output_dir / key
            require(self.rollout_key(root) == key, 'Invalid archived rollout key')
            signature = entry['signature']
            tasks, skill, config = signature['tasks'], signature['skill'], signature['config']
            require(tasks and len(tasks) == len(set(tasks)) and
                    all(t in backend.dataset.splits['train'] for t in tasks), 'Invalid archived Actor tasks')
            expected_role = 'candidate' if key.endswith('/validation_candidate') else 'parent'
            require(config == {'split': 'train', 'role': expected_role}, 'Archived Actor role changed')
            batch_root = root / 'actor'
            if (root / 'skill.md').exists():
                freeze_text(root / 'skill.md', skill, read_only=True)
            else:
                require(entry['completion'] is None and not batch_root.exists(), 'Missing archived Actor Skill')
            batch_file = batch_root / 'batch.json'
            if not batch_file.exists():
                require(entry['completion'] is None and
                        (not batch_root.exists() or not any(q.name != '.execution.lock' for q in batch_root.iterdir())),
                        'Missing Actor batch archive')
                continue  # Registered before Actor execution; genuinely not started.
            batch = read(batch_file)
            expected = {'tasks': tasks, 'sources': {t: backend.actor._source_identity(backend.dataset.case(t)) for t in tasks},
                        'actor': backend.actor.transport.metadata(), 'skill': skill, 'config': config,
                        'workers': backend.actor.workers}
            require(p.equal(batch['signature'], expected), 'Archived Actor batch signature changed')
            records_file = batch_root / 'records.json'
            if records_file.exists():
                records = read(records_file)
                require(isinstance(records, list) and [r['task_id'] for r in records] == tasks,
                        'Archived Actor coverage changed')
                require(entry['completion'] in (None, p.digest(records)), 'Archived Actor records changed')
                for record in records:
                    backend.actor.check_record_archive(record, record['task_id'], skill, config, batch_root)
            else:
                require(entry['completion'] is None, 'Missing completed Actor records')
                for task in tasks:
                    folder = batch_root / 'actor' / p.digest(task)
                    if (folder / 'trajectory.json').exists():
                        backend.actor.check_record_archive(read(folder / 'trajectory.json'), task, skill, config, batch_root)
                    elif (folder / 'result.json').exists():
                        actor.read_completed(backend.dataset.case(task), skill, folder, backend.actor.transport.metadata())
                    else:
                        actor.validate_pending(backend.dataset.case(task), skill, folder, backend.actor.transport.metadata())
        for key, entry in self.index('generations').items():
            require(re.fullmatch(r'iter_\d{3,}/(iteration_patch|momentum_update)_\d{2,}', key), 'Invalid generation key')
            path = self.root / 'generations' / (key + '.json')
            if path.exists():
                payload = read(path)
                require(p.equal(payload['signature'], entry['signature']) and
                        entry['completion'] in (None, p.digest(payload)), 'Optimizer archive changed')
            else:
                require(entry['completion'] is None, 'Missing completed optimizer response')

    def record_usage(self, key, rows, ledger_path):
        """Replaying a durable result must not append its usage a second time."""
        path = self.root / 'usage_events.json'
        events = read(path) if path.exists() else []
        prior = next((e for e in events if e['key'] == key), None)
        if prior is None:
            events.append({'key': key, 'rows': rows})
            save(path, events)
        else:
            require(p.equal(prior['rows'], rows), 'Recovered usage differs')
        # Same native JSONL row schema, atomically regenerated from ordered receipts.
        ledger_path = Path(ledger_path)
        temporary = ledger_path.with_suffix('.tmp')
        temporary.write_text(''.join(json.dumps(row, sort_keys=True) + '\n'
                                     for e in events for row in e['rows']))
        temporary.replace(ledger_path)
