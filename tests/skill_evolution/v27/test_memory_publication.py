"""Single-publication reuse without weakening cold or interrupted recovery."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from . import test_offline as original
from .support import config, replay
from src.skill_evolution.v27 import evolution, memory_operation, stages
from src.skill_evolution.v27.benchmark import using_benchmark
from src.skill_evolution.v27.benchmarks.lmb import evidence
from src.skill_evolution.v27.benchmarks.lmb.adapter import LMBAdapter
from src.skill_evolution.v27.contracts import memory

CONTRACT = memory.MULTI_KNOWLEDGE_CONTRACT


class MemoryPublicationTests(original.Base):
    bind_data = original.CampaignTests.bind_data
    generator = original.CampaignTests.generator

    def load(self, directory):
        return memory.load_memory(directory, memory_contract=CONTRACT)

    def commit(self, directory, cid, bundle, result=None):
        return memory.commit_memory(directory, context_id=cid, context=bundle,
                                    result=replay() if result is None else result, memory_contract=CONTRACT)

    def bundle(self, active):
        _, bundle = self.edited()
        bundle['payload']['memory'] = deepcopy(active)
        evidence.validate_bundle(bundle)
        return bundle

    def prepared(self):
        source = self.root/'source'
        self.commit(source, 'R1', self.bundle(memory.empty_memory()))
        return source, self.bundle(self.load(source))

    def test_standalone_commit_scans_history_once(self):
        directory, bundle = self.prepared()
        with patch.object(memory, '_archive', wraps=memory._archive) as archive:
            self.commit(directory, 'R2', bundle)
        self.assertEqual(archive.call_count, 1)
        self.assertEqual(stages.read(directory/'active.json')['commits'], ['R1', 'R2'])

    def test_preparation_commit_and_repeated_views_share_one_history_scan(self):
        source, bundle = self.prepared(); dest = self.root/'dest'
        with patch.object(memory, '_archive', wraps=memory._archive) as archive:
            with memory_operation.operation(CONTRACT) as session:
                evolution._prepare_memory(source, dest, session=session)
                actual = self.commit(dest, 'R2', bundle)
                expected = self.load(dest)
                detached = self.load(dest); detached['entries'].clear(); detached['sources'].clear()
                actual['context']['payload']['memory']['entries'].clear()
                self.assertEqual(self.load(dest), expected)
                session.verify()
            self.assertEqual(archive.call_count, 1)
        self.assertEqual(self.load(dest), expected)
        self.assertIsNone(memory_operation.current(CONTRACT))

    def test_cold_load_and_adapter_change_never_share_previous_trust(self):
        directory, _ = self.prepared()
        for _ in range(2):
            with patch.object(memory, '_archive', wraps=memory._archive) as archive:
                self.load(directory)
            self.assertEqual(archive.call_count, 1)
        with memory_operation.operation(CONTRACT) as session:
            self.load(directory)
            with using_benchmark(LMBAdapter()), patch.object(memory, '_archive', wraps=memory._archive) as archive:
                self.assertIsNone(memory_operation.current(CONTRACT))
                self.load(directory)
                self.assertEqual(archive.call_count, 1)
            with memory_operation.operation(CONTRACT) as nested:
                self.assertIs(nested, session)
        path = directory/'archive/R1.json'
        changed = stages.read(path); changed['after_active_ids'] = []
        stages.save(path, changed)
        with self.assertRaises(ValueError): self.load(directory)

    def test_scoped_and_cold_commits_have_identical_bytes_and_revisions(self):
        reference, scoped = self.root/'reference', self.root/'scoped'
        active = memory.empty_memory()
        for index in range(1, 4):
            bundle = self.bundle(active)
            result = replay() if index < 3 else {'entries': []}
            if index == 2: result['entries'][0]['revises'] = ['M1']
            cid = f'R{index}'
            expected = self.commit(reference, cid, bundle, result)
            with memory_operation.operation(CONTRACT):
                self.assertEqual(self.commit(scoped, cid, bundle, result), expected)
                active = self.load(scoped)
                self.assertEqual(self.commit(scoped, cid, bundle, result), expected)
            for name in ('active.json', f'archive/{cid}.json'):
                self.assertEqual((reference/name).read_bytes(), (scoped/name).read_bytes())
            self.assertEqual(active, self.load(reference))
        self.assertEqual([entry['id'] for entry in active['entries']], ['M2'])

    def test_changed_memory_dependencies_rejected_before_commit(self):
        directory, bundle = self.prepared()
        commit_path, active_path = directory/'archive/R1.json', directory/'active.json'
        before = {path: path.read_bytes() for path in (commit_path, active_path)}
        view = memory._view
        for target in ('commit', 'active', 'membership'):
            with self.subTest(target=target):
                def changed_view(entries, contexts, active, contract):
                    result = view(entries, contexts, active, contract)
                    if 'R2' in contexts:
                        if target == 'commit': commit_path.write_bytes(before[commit_path] + b' ')
                        elif target == 'active': stages.save(active_path, {'commits': [], 'active_ids': []})
                        else: stages.save(directory/'archive/foreign.json', {})
                    return result
                try:
                    with self.assertRaises(ValueError), memory_operation.operation(CONTRACT):
                        self.load(directory)
                        with patch.object(memory, '_view', changed_view): self.commit(directory, 'R2', bundle)
                    self.assertFalse((directory/'archive/R2.json').exists())
                    self.assertIsNone(memory_operation.current(CONTRACT))
                finally:
                    for path, data in before.items(): path.write_bytes(data)
                    (directory/'archive/foreign.json').unlink(missing_ok=True)

    def test_active_snapshot_must_match_replay_even_with_cache(self):
        directory, _ = self.prepared()
        with self.assertRaisesRegex(ValueError, 'Active snapshot changed before commit'), memory_operation.operation(CONTRACT):
            self.load(directory)
            self.commit(directory, 'R2', self.bundle(memory.empty_memory()))
        self.assertFalse((directory/'archive/R2.json').exists())

    def test_cache_exit_checks_bytes_and_clears_after_interrupt(self):
        directory, _ = self.prepared(); path = directory/'archive/R1.json'
        before = path.read_bytes()
        with self.assertRaises(ValueError), memory_operation.operation(CONTRACT):
            self.load(directory)
            path.write_bytes(before + b' ')
        self.assertIsNone(memory_operation.current(CONTRACT))
        path.write_bytes(before)
        with self.assertRaises(KeyboardInterrupt), memory_operation.operation(CONTRACT):
            self.load(directory)
            raise KeyboardInterrupt()
        self.assertIsNone(memory_operation.current(CONTRACT))
        self.load(directory)

    def test_pending_commit_temp_and_mismatch_recovery(self):
        bundle = self.bundle(memory.empty_memory())
        expected = self.commit(self.root/'reference', 'R1', bundle)
        for mode in ('pending', 'temp', 'bad_pending', 'foreign_pending'):
            with self.subTest(mode=mode):
                directory = self.root/mode; (directory/'archive').mkdir(parents=True)
                if mode == 'temp': (directory/'archive/R1.tmp').write_text('partial')
                else:
                    value = deepcopy(expected)
                    if mode == 'bad_pending': value['after_active_ids'] = ['M999']
                    stages.save(directory/'archive'/('foreign.json' if mode == 'foreign_pending' else 'R1.json'), value)
                if mode in ('bad_pending', 'foreign_pending'):
                    with self.assertRaises(ValueError), memory_operation.operation(CONTRACT):
                        self.commit(directory, 'R1', bundle)
                    self.assertFalse((directory/'active.json').exists())
                else:
                    with memory_operation.operation(CONTRACT):
                        self.assertEqual(self.commit(directory, 'R1', bundle), expected)
                self.assertIsNone(memory_operation.current(CONTRACT))

    def test_interrupt_at_each_write_recovers_without_duplicate_commit(self):
        bundle = self.bundle(memory.empty_memory())
        write = memory.write_record
        for name in ('R1.json', 'active.json'):
            directory = self.root/name
            def interrupted(path, value):
                write(path, value)
                if path.name == name: raise KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt), memory_operation.operation(CONTRACT), patch.object(memory, 'write_record', interrupted):
                self.commit(directory, 'R1', bundle)
            self.assertIsNone(memory_operation.current(CONTRACT))
            with memory_operation.operation(CONTRACT):
                self.commit(directory, 'R1', bundle)
                self.assertEqual(len(self.load(directory)['entries']), 1)
            self.assertEqual(stages.read(directory/'active.json')['commits'], ['R1'])

    def test_already_advanced_prepared_directory_is_revalidated_cold(self):
        source, bundle = self.prepared(); dest = self.root/'dest'
        with memory_operation.operation(CONTRACT) as session:
            evolution._prepare_memory(source, dest, session=session)
            expected = self.commit(dest, 'R2', bundle)
        with patch.object(memory, '_archive', wraps=memory._archive) as archive:
            with memory_operation.operation(CONTRACT) as session:
                evolution._prepare_memory(source, dest, session=session)
                self.assertEqual(self.commit(dest, 'R2', bundle), expected)
            self.assertEqual(archive.call_count, 2)  # source plus advanced destination

    def test_real_publication_boundary_scans_once_and_resume_is_read_only(self):
        _, transport, adapter = self.bind_data(count=2)
        generator, calls = self.generator(); root = self.root/'campaign'
        with using_benchmark(adapter), patch.object(memory, '_archive', wraps=memory._archive) as archive:
            counts = []
            def hook(stage):
                if stage == 'memory': archive.reset_mock()
                if stage == 'after_publish': counts.append(archive.call_count)
            evolution.run_campaign(root, config=config(adapter, [[uid] for uid in adapter.dataset.rows]),
                                   generate=generator, hook=hook)
            self.assertEqual(counts, [1, 1])
            before = (transport.calls, len(calls))
            evolution.run_campaign(root, resume=True, generate=None)
            self.assertEqual((transport.calls, len(calls)), before)

    def test_tampering_before_publication_does_not_advance_official_state(self):
        for target in ('commit', 'active', 'view', 'base'):
            with self.subTest(target=target):
                _, transport, adapter = self.bind_data(count=1)
                generator, calls = self.generator(); root = self.root/target
                changed = []
                def hook(stage):
                    if stage != 'before_publish': return
                    dest = root/'rounds/R01/memory'
                    path = dest/'archive'/f'{root.name}_R01.json' if target == 'commit' else dest/f'{target}.json'
                    changed.append((path, path.read_bytes()))
                    path.write_bytes(path.read_bytes() + b' ' if target != 'active' else b'{"active_ids":[],"commits":[]}')
                with using_benchmark(adapter):
                    with self.assertRaises(ValueError):
                        evolution.run_campaign(root, config=config(adapter), generate=generator, hook=hook)
                    self.assertEqual(stages.read(root/'state.json')['next_round'], 1)
                    self.assertIsNone(memory_operation.current(CONTRACT))
                    for path, data in changed: path.write_bytes(data)
                    before = (transport.calls, len(calls))
                    evolution.run_campaign(root, resume=True, generate=None)
                    self.assertEqual(stages.read(root/'state.json')['next_round'], 2)
                    self.assertEqual((transport.calls, len(calls)), before)
