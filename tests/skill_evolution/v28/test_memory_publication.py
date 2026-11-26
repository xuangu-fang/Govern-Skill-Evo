"""Publication reuse, durable-format equivalence and fail-closed boundaries."""
from copy import deepcopy
from unittest.mock import patch

from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v28 import evolution, memory_operation, stages
from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
from .runtime_support import Base
from .campaign_support import bind, Generator


class MemoryPublicationTests(Base):
    def run_one(self):
        _, _, adapter, config = bind(rounds=1, batch_size=1)
        root = self.root / 'campaign'
        with adapter.using():
            evolution.run_round(root, config=config, generate=Generator())
        cid = root.name + '_R01'
        return adapter, root, cid, stages.read(root / f'rounds/R01/memory/archive/{cid}.json')

    def test_publication_scans_history_once_and_copies_are_detached(self):
        _, _, adapter, config = bind(rounds=1, batch_size=1)
        root = self.root / 'reuse'
        with patch.object(adapter, '_load_memory', wraps=adapter._load_memory) as load, \
             patch.object(memory, '_archive', wraps=memory._archive) as archive:
            def hook(stage):
                if stage == 'knowledge_review': load.reset_mock(); archive.reset_mock()
            with adapter.using():
                evolution.run_round(root, config=config, generate=Generator(), hook=hook)
            self.assertEqual(load.call_count, 1)
            self.assertEqual(archive.call_count, 1)
        with adapter.using(), adapter.memory_operation():
            path = root / 'rounds/R01/memory'
            first = adapter.load_memory(path); expected = deepcopy(first)
            first['entries'].clear(); first['sources'].clear()
            self.assertEqual(adapter.load_memory(path), expected)

    def test_commit_matches_inherited_format_and_idempotence(self):
        adapter, root, cid, commit = self.run_one()
        reference = self.root / 'reference'
        with adapter.using():
            expected = memory.commit_memory(reference, context_id=cid, context=commit['context'],
                                            result=commit['result'], memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
            self.assertEqual(commit, expected)
            for name in ('active.json', f'archive/{cid}.json'):
                self.assertEqual((reference / name).read_bytes(), (root / 'rounds/R01/memory' / name).read_bytes())
            again = adapter.commit_memory(root / 'rounds/R01/memory', context_id=cid,
                                          context=commit['context'], result=commit['result'])
            self.assertEqual(again, commit)
            bad = deepcopy(commit['result']); bad['entries'][0]['knowledge'][0]['text'] += ' changed'
            self.reject(adapter.commit_memory, root / 'rounds/R01/memory', context_id=cid,
                        context=commit['context'], result=bad)

    def test_pending_commit_and_temp_file_recovery(self):
        adapter, _, cid, commit = self.run_one()
        with adapter.using():
            for mode in ('pending', 'temp', 'bad_pending', 'foreign_pending'):
                with self.subTest(mode=mode):
                    dest = self.root / mode; (dest / 'archive').mkdir(parents=True)
                    stages.save(dest / 'active.json', {'active_ids': [], 'commits': []})
                    if mode == 'temp':
                        (dest / 'archive' / f'{cid}.tmp').write_text('incomplete write')
                    else:
                        value = deepcopy(commit)
                        if mode == 'bad_pending': value['after_active_ids'] = ['M999']
                        stages.save(dest / 'archive' / ('unrelated.json' if mode == 'foreign_pending' else f'{cid}.json'), value)
                    if mode in ('bad_pending', 'foreign_pending'):
                        self.reject(adapter.commit_memory, dest, context_id=cid, context=commit['context'], result=commit['result'])
                        self.assertEqual(stages.read(dest / 'active.json')['commits'], [])
                    else:
                        self.assertEqual(adapter.commit_memory(dest, context_id=cid, context=commit['context'], result=commit['result']), commit)
                        self.assertEqual(stages.read(dest / 'active.json')['commits'], [cid])

    def test_crash_between_commit_file_and_active_switch_recovers(self):
        adapter, _, cid, commit = self.run_one()
        dest = self.root / 'crash'; dest.mkdir()
        stages.save(dest / 'active.json', {'active_ids': [], 'commits': []})
        original = memory_operation.write_record
        def interrupted(path, value):
            if path.name == 'active.json': raise KeyboardInterrupt()
            return original(path, value)
        with adapter.using():
            with patch.object(memory_operation, 'write_record', interrupted), self.assertRaises(KeyboardInterrupt):
                adapter.commit_memory(dest, context_id=cid, context=commit['context'], result=commit['result'])
            self.assertEqual(stages.read(dest / 'active.json')['commits'], [])
            self.assertEqual(stages.read(dest / f'archive/{cid}.json'), commit)
            self.assertEqual(adapter.commit_memory(dest, context_id=cid, context=commit['context'], result=commit['result']), commit)

    def test_mutations_after_memory_prepared_never_publish(self):
        for target in ('active', 'view', 'commit', 'skill', 'response', 'base'):
            with self.subTest(target=target):
                _, _, adapter, config = bind(rounds=1, batch_size=1)
                root = self.root / target
                def hook(stage):
                    if stage != 'before_publish': return
                    rd = root / 'rounds/R01'
                    paths = {
                        'active': rd / 'memory/active.json', 'view': rd / 'memory/view.json',
                        'commit': rd / f'memory/archive/{root.name}_R01.json',
                        'skill': rd / 'editor/attempts/001/candidate.md', 'base': rd / 'memory/base.json',
                        'response': rd / 'parent_runs/actor' / p.digest(config['batches'][0][0]) / 'attempts/001/response.json',
                    }
                    path = paths[target]; path.write_bytes(path.read_bytes() + b' ')
                with adapter.using():
                    self.reject(evolution.run_round, root, config=config, generate=Generator(), hook=hook)
                self.assertEqual(stages.read(root / 'state.json')['next_round'], 1)

    def test_cached_history_and_added_commit_are_rechecked(self):
        adapter, root, cid, _ = self.run_one()
        dest = root / 'rounds/R01/memory'
        with adapter.using():
            with self.assertRaises(ValueError), adapter.memory_operation():
                adapter.load_memory(dest)
                stages.save(dest / 'archive/foreign.json', {})
                adapter.load_memory(dest)
        self.assertIsNone(memory_operation.current(adapter))
