"""Offline Memory publication/recovery using registered synthetic executions.

No real models or experiments. Fault injection covers both sides of HEAD's
publication boundary, immutable-object reuse and cross-round source checks.
"""
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import fcntl
from pathlib import Path
from threading import Barrier
import unittest
from unittest.mock import patch

from src.skill_evolution.v29 import modules as old_modules
from src.skill_evolution.v29.storage import read, save
from src.skill_evolution.v29_1.campaign import CampaignAdapter
from src.skill_evolution.v29_2 import diagnosis as d, preconditioner as p, editor as e
from src.skill_evolution.v29_2 import replay as r, gate as g, memory as m
from tests.skill_evolution.v29.test_actor import response
from tests.skill_evolution.v29.test_method import MethodBase, main_example
from tests.skill_evolution.v29_2.test_diagnosis import proposal
from tests.skill_evolution.v29_2.test_preconditioner import decisions
from tests.skill_evolution.v29_2.test_editor import diff, output, offline

_DEFAULT = object()


class MemoryTests(MethodBase):
    def setUp(self):
        super().setUp()
        offline(self)
        self.method = CampaignAdapter(self.adapter)
        self.enterContext(self.method.using())
        self.store = self.root / 'memory-v29_2'
        self.initial = m.load_memory(self.store)
        self.first = self.round(self.initial, 'R03')

    def actor_fixture(self, skill, contents, role):
        if skill is not None:
            return self.batch(skill, contents, role)
        self.counter += 1
        directory = self.root / f'no-skill-{self.counter}'
        by_question = {self.dataset.case(t).payload['question']: c for t, c in zip(self.tasks, contents)}
        self.transport.generate = lambda messages, slot: response(
            by_question[messages[1]['content'][0]['text'].split('\n\n')[0]])
        records = self.adapter.actor_batch(self.tasks, None, directory, {'split': 'train', 'role': role})
        self.method.register_archive(directory)
        return records, directory

    def round(self, previous, rid, *, parent=_DEFAULT, patches=None, mode='gate',
              links=('u1', 'u2'), history=None, reverse=False):
        if parent is _DEFAULT:
            parent = self.skill if previous['head'] is None else previous['selection']['selected_text']
        parent_contents = ['<answer>1,200</answer>', '<answer>12 May 2021</answer>']
        parents, parent_dir = self.actor_fixture(parent, parent_contents, 'parent')
        grouped = old_modules.grouping_call(parents, rid).complete(main_example('grouping'))
        if patches is None:
            context = ''.join(' ' + line for line in (parent or '').splitlines(keepends=True))
            patches = ([diff(context + f'+- Scoped rule {index} in {rid}.\n', create=parent is None)
                        for index in range(1, 4)] + ['']) if mode != 'no_change' else [''] * 4
        plan = proposal()
        plan['plan']['updates'] = [{**deepcopy(plan['plan']['updates'][0]), 'id': f'u{i}',
                                    'text': f'- Complete scoped requirement {i}.\n'}
                                   for i in range(1, len(patches) + 1)]
        diagnosed = d.diagnosis_call(grouped).complete(plan)
        conditioned = p.preconditioner_call(diagnosed, previous['memory'] if history is None else history).complete(
            decisions(*(['KEEP'] * len(patches))))
        edits = output(*patches)
        if reverse: edits['edits'].reverse()
        edited = e.editor_call(conditioned).complete(edits)
        context = {'edited': edited, 'parent_dir': parent_dir, 'diagnosed': diagnosed}
        if mode == 'no_change':
            context['prepared'] = m.prepare_no_change(previous, edited=edited)
        elif mode == 'editor_only':
            return context
        else:
            contents = parent_contents if mode == 'no_flips' else ['<answer>1,320</answer>', '<answer>12 May 2022</answer>']
            children, child_dir = self.actor_fixture(edited['candidate_text'], contents, 'candidate')
            bundle = r.build_replay_from_editor(edited, parents, children)
            if mode == 'no_flips':
                replayed = r.skip_replay(bundle)
            else:
                items = [{'task_id': pair['task_id'], 'update_id': uid,
                          'text': f'Exact event {index}: observed hard transition and scoped association.'}
                         for index, (pair, uid) in enumerate(zip(bundle['payload']['pairs'], links), 1)]
                if reverse: items.reverse()
                replayed = r.replay_call(bundle).complete({'entries': [{'knowledge': items}]})
            result = g.evaluate_gate(replayed)
            context.update(replayed=replayed, gate_result=result, child_dir=child_dir,
                           prepared=m.prepare_append(previous, replayed=replayed, gate_result=result))
        return context

    def commit(self, item=None, store=None):
        prepared = (item or self.first)['prepared']
        return m.commit_memory(store or self.store, prepared, expected_head=prepared['previous']['head'])

    def files(self, root=None):
        return {str(path.relative_to(root or self.root)): path.read_bytes()
                for path in (root or self.root).rglob('*') if path.is_file()}

    def test_empty_load_is_read_only_and_has_no_initial_parent_claim(self):
        self.assertEqual(self.initial, {'head': None, 'memory': {'rounds': []},
                                        'selection': None, 'selected_execution_source': None})
        self.assertFalse(self.store.exists())
        self.assertEqual(m.load_memory(self.store), self.initial)

    def test_generation_preserves_all_updates_decisions_and_exact_knowledge(self):
        prepared = self.first['prepared']
        record = prepared['round']
        self.assertEqual(record['round_id'], 'R03')
        self.assertEqual([u['gate_decision'] for u in record['source_updates']], ['Retain', 'Reject', 'Defer', None])
        self.assertEqual([u['text'] for u in record['source_updates']],
                         [u['text'] for u in self.first['edited']['effective_plan']['updates']])
        self.assertEqual([entry['id'] for entry in record['entries']], ['M1', 'M2'])
        self.assertEqual([entry['knowledge'] for entry in record['entries']], self.first['replayed']['knowledge'])
        self.assertIsNone(prepared['selected_execution_source'])
        p.validate_memory_view({'rounds': [record]})
        self.assertFalse(self.store.exists())

    def test_commit_load_preserve_selection_and_model_view_without_extra_fields(self):
        state = self.commit()
        self.assertEqual(state, m.load_memory(self.store))
        self.assertEqual(state['memory'], {'rounds': [self.first['prepared']['round']]})
        self.assertEqual(state['selection'], self.first['gate_result']['selection'])
        self.assertIsNone(state['selected_execution_source'])
        self.assertEqual(set(state), {'head', 'memory', 'selection', 'selected_execution_source'})
        self.assertEqual(len(list((self.store / 'commits').glob('*.json'))), 1)
        self.assertEqual(len(list((self.store / 'sources').glob('*.json'))), 1)
        self.assertEqual(read(self.store / 'HEAD.json')['head'], state['head'])

    def test_two_rounds_keep_local_ids_distinct_and_assign_global_memory_ids(self):
        first = self.commit()
        second = self.round(first, 'R01')  # Lexical order must not determine chronology.
        latest = self.commit(second)
        rounds = latest['memory']['rounds']
        self.assertEqual([row['round_id'] for row in rounds], ['R03', 'R01'])
        self.assertEqual([entry['id'] for row in rounds for entry in row['entries']], ['M1', 'M2', 'M3', 'M4'])
        self.assertEqual(rounds[0]['entries'][0]['knowledge']['task_id'], rounds[1]['entries'][0]['knowledge']['task_id'])
        self.assertEqual(m.load_memory(self.store, head=first['head']), first)
        self.assertEqual(m.load_memory(self.store), latest)

    def test_model_array_order_does_not_control_memory_id_or_update_order(self):
        item = self.round(self.initial, 'R04', reverse=True)
        state = self.commit(item)
        record = state['memory']['rounds'][0]
        self.assertEqual([u['id'] for u in record['source_updates']], ['u1', 'u2', 'u3', 'u4'])
        self.assertEqual([(entry['id'], entry['knowledge']['task_id']) for entry in record['entries']],
                         [('M1', self.tasks[0]), ('M2', self.tasks[1])])

    def test_loaded_history_is_direct_preconditioner_input_and_future_round_excluded(self):
        first = self.commit()
        second = self.round(first, 'R04')
        model_input = p.preconditioner_input(second['diagnosed'], m.load_memory(self.store)['memory'])
        self.assertEqual(model_input['memory'], first['memory'])
        self.commit(second)
        restored = m.load_memory(self.store, head=first['head'])
        self.assertEqual(p.preconditioner_input(second['diagnosed'], restored['memory']), model_input)
        with self.assertRaises(ValueError):
            p.preconditioner_input(second['diagnosed'], m.load_memory(self.store)['memory'])

    def test_no_flip_round_is_saved_with_defer_and_consumes_no_ids(self):
        first = self.commit()
        second = self.round(first, 'R04', mode='no_flips')
        self.assertEqual(second['prepared']['round']['entries'], [])
        self.assertEqual([u['gate_decision'] for u in second['prepared']['round']['source_updates']],
                         ['Defer', 'Defer', 'Defer', None])
        state = self.commit(second)
        self.assertEqual(state['selection']['selected_text'], first['selection']['selected_text'])
        self.assertEqual(state['selected_execution_source'], 'parent')
        third = self.round(state, 'R05')
        self.assertEqual([x['id'] for x in third['prepared']['round']['entries']], ['M3', 'M4'])

    def test_all_empty_patches_save_null_decisions_without_replay_gate(self):
        with patch.object(g, 'evaluate_gate', side_effect=AssertionError('No Gate for empty patches')):
            second = self.round(self.initial, 'R04', mode='no_change')
            state = self.commit(second)
            self.assertEqual(m.load_memory(self.store), state)
        record = state['memory']['rounds'][-1]
        self.assertEqual(record['entries'], [])
        self.assertEqual([u['gate_decision'] for u in record['source_updates']], [None] * 4)
        self.assertEqual(state['selection']['selected_text'], self.skill)
        self.assertEqual(state['selected_execution_source'], 'parent')

    def test_unlinked_events_are_not_discarded(self):
        item = self.round(self.initial, 'R04', links=(None, None))
        state = self.commit(item)
        self.assertEqual([x['knowledge']['update_id'] for x in state['memory']['rounds'][0]['entries']], [None, None])
        self.assertEqual(state['selection']['selected_text'], self.skill)
        self.assertEqual(state['selected_execution_source'], 'parent')

    def test_all_rejected_events_are_saved_with_parent_selection(self):
        item = self.round(self.initial, 'R04', links=(None, 'u1'))
        state = self.commit(item)
        self.assertEqual(state['memory']['rounds'][0]['source_updates'][0]['gate_decision'], 'Reject')
        self.assertEqual(len(state['memory']['rounds'][0]['entries']), 2)
        self.assertEqual(state['selected_execution_source'], 'parent')

    def test_no_change_preserves_absent_and_empty_parent_exactly(self):
        for index, parent in enumerate((None, '')):
            item = self.round(self.initial, f'R{index}', parent=parent, mode='no_change')
            store = self.root / f'empty-memory-{index}'
            state = self.commit(item, store)
            self.assertEqual(state['selection']['selected_text'], parent)
            self.assertEqual(m.load_memory(store), state)

    def test_executed_candidate_source_is_preserved_without_scores(self):
        context = ''.join(' ' + line for line in self.skill.splitlines(keepends=True))
        item = self.round(self.initial, 'R04', patches=[diff(context + '+Rule\n')], links=('u1', None))
        state = self.commit(item)
        self.assertEqual(state['selected_execution_source'], 'candidate')
        self.assertEqual(state['selection']['selected_text'], item['edited']['candidate_text'])
        self.assertEqual(set(state['selection']), {'selected_update_ids', 'selected_text', 'actual_diff'})

    def test_repeated_commit_is_idempotent_and_does_not_rewrite_files(self):
        first = self.commit()
        before = self.files(self.store)
        self.assertEqual(self.commit(), first)
        self.assertEqual(self.files(self.store), before)
        latest = self.commit(self.round(first, 'R04'))
        before = self.files(self.store)
        self.assertEqual(self.commit(), first)
        self.assertEqual(m.load_memory(self.store), latest)
        self.assertEqual(self.files(self.store), before)

    def test_same_round_different_content_rejected_without_overwrite(self):
        self.commit()
        changed = self.round(self.initial, 'R03', links=(None, None))
        before = self.files(self.store)
        with self.assertRaisesRegex(ValueError, 'different content'): self.commit(changed)
        self.assertEqual(self.files(self.store), before)

    def test_stale_new_round_and_wrong_expected_head_are_rejected(self):
        self.commit()
        stale = self.round(self.initial, 'R04')
        before = self.files(self.store)
        with self.assertRaisesRegex(ValueError, 'Stale Memory head'): self.commit(stale)
        with self.assertRaisesRegex(ValueError, 'Expected head'):
            m.commit_memory(self.store, self.first['prepared'], expected_head='wrong')
        self.assertEqual(self.files(self.store), before)

    def test_forged_prepared_fields_and_non_json_containers_rejected(self):
        for kind in ('round', 'update', 'decision', 'knowledge', 'id', 'selection', 'source_status',
                     'extra', 'missing', 'format', 'tuple', 'bool'):
            bad = deepcopy(self.first['prepared'])
            if kind == 'round': bad['round']['round_id'] = 'R99'
            elif kind == 'update': bad['round']['source_updates'][0]['text'] = 'forged'
            elif kind == 'decision': bad['round']['source_updates'][0]['gate_decision'] = 'Defer'
            elif kind == 'knowledge': bad['round']['entries'][0]['knowledge']['text'] = 'forged'
            elif kind == 'id': bad['round']['entries'][0]['id'] = 'M99'
            elif kind == 'selection': bad['selection']['selected_text'] = 'forged'
            elif kind == 'source_status': bad['selected_execution_source'] = 'candidate'
            elif kind == 'extra': bad['revises'] = []
            elif kind == 'missing': del bad['source']
            elif kind == 'format': bad['format'] = 'unknown'
            elif kind == 'tuple': bad['round']['entries'] = tuple(bad['round']['entries'])
            else: bad['source']['gate_result']['decisions'][0]['G'] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                m.commit_memory(self.store, bad, expected_head=None)
        self.assertFalse(self.store.exists())

    def test_preconditioner_history_parent_lineage_and_duplicate_round_checked(self):
        first = self.commit()
        for kind in ('history', 'parent', 'duplicate'):
            kwargs = {'history': {'rounds': []}} if kind == 'history' else (
                {'parent': self.skill} if kind == 'parent' else {})
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.round(first, 'R03' if kind == 'duplicate' else 'R04', **kwargs)

    def test_prepare_does_not_prove_a_fabricated_prefix_is_committed(self):
        first = self.commit()
        other = self.root / 'unrelated-store'
        second = self.round(first, 'R04')
        with self.assertRaisesRegex(ValueError, 'not committed history'):
            self.commit(second, other)
        self.assertEqual(m.load_memory(other), self.initial)

    def test_invalid_editor_and_gate_sources_cannot_generate_records(self):
        for patches in ([None] * 4, [''] * 4):
            edited = self.round(self.initial, 'R04', patches=patches, mode='editor_only')['edited']
            bad = deepcopy(self.first['replayed']); bad['audit']['editor'] = edited
            with self.assertRaises(ValueError):
                m.prepare_append(self.initial, replayed=bad, gate_result=self.first['gate_result'])
            if patches[0] is None:
                with self.assertRaises(ValueError): m.prepare_no_change(self.initial, edited=edited)
        with self.assertRaises(ValueError): m.prepare_no_change(self.initial, edited=self.first['edited'])
        for field in ('editor', 'candidate_text'):
            bad = deepcopy(self.first['edited']); del bad[field]
            with self.assertRaises(ValueError): m.prepare_no_change(self.initial, edited=bad)
        bad = deepcopy(self.first['gate_result']); bad['selection']['selected_text'] = 'forged'
        with self.assertRaises(ValueError):
            m.prepare_append(self.initial, replayed=self.first['replayed'], gate_result=bad)

    def test_current_commit_checks_actor_but_loading_history_does_not(self):
        state = self.commit()
        path = self.first['child_dir'] / 'actor/0001/trajectory.json'
        value = read(path); value['execution']['content'] = 'forged after commit'
        save(path, value)
        with self.assertRaises(ValueError): self.commit()
        self.assertEqual(m.load_memory(self.store), state)
        self.assertEqual(read(self.store / 'HEAD.json')['head'], state['head'])

    def test_committed_record_tampering_or_loss_are_detected(self):
        self.commit()
        paths = [next((self.store / folder).glob('*.json')) for folder in ('commits',)]
        for path in paths:
            original = path.read_bytes()
            for kind in ('modify', 'missing', 'duplicate_key', 'nonfinite'):
                with self.subTest(path=path.name, kind=kind):
                    if kind == 'missing': path.unlink()
                    elif kind == 'modify': path.write_bytes(original.replace(b'R03', b'R99', 1))
                    elif kind == 'duplicate_key': path.write_text('{"format":"x","format":"y"}\n')
                    else: path.write_text('{"value":NaN}\n')
                    with self.assertRaises(ValueError): m.load_memory(self.store)
                    path.write_bytes(original)

    def test_recomputed_hashes_do_not_bypass_chain_validation(self):
        state = self.commit()
        forged = read(self.store / 'commits' / f'{state["head"]}.json')
        forged['previous_head'] = state['head']
        data = m._bytes(forged)
        head = '000001-' + m._digest(data)
        (self.store / 'commits' / f'{head}.json').write_bytes(data)
        m._publish_head(self.store, head)
        with self.assertRaises(ValueError): m.load_memory(self.store)
        m._publish_head(self.store, state['head'])
        self.assertEqual(m.load_memory(self.store), state)

    def test_committed_history_load_does_not_open_source_files(self):
        state = self.commit()
        original = m._read
        def read_commits_only(path):
            self.assertNotEqual(path.parent.name, 'sources')
            return original(path)
        with patch.object(m, '_read', side_effect=read_commits_only), \
             patch.object(m, '_prepare', side_effect=AssertionError('No historical replay')):
            self.assertEqual(m.load_memory(self.store), state)

    def test_missing_or_corrupt_head_and_unpublished_head_are_not_silently_recovered(self):
        state = self.commit()
        path = self.store / 'HEAD.json'
        original = path.read_bytes()
        for value in (None, b'bad json', m._bytes({'format': m.HEAD_FORMAT, 'head': '../escape'})):
            if value is None: path.unlink()
            else: path.write_bytes(value)
            with self.assertRaises(ValueError): m.load_memory(self.store)
            path.write_bytes(original)
        with self.assertRaises(ValueError): m.load_memory(self.store, head='000001-' + '0' * 64)
        self.assertEqual(m.load_memory(self.store), state)

    def test_failure_before_head_switch_keeps_old_state_and_retry_reuses_objects(self):
        first = self.commit()
        second = self.round(first, 'R04')
        with patch.object(m, '_publish_head', side_effect=OSError('injected before HEAD')):
            with self.assertRaises(OSError): self.commit(second)
        self.assertEqual(m.load_memory(self.store), first)
        commits = list((self.store / 'commits').glob('*.json'))
        self.assertEqual(len(commits), 2)
        orphan = next(path.stem for path in commits if path.stem != first['head'])
        with self.assertRaisesRegex(ValueError, 'not published'): m.load_memory(self.store, head=orphan)
        immutable = {str(path): path.read_bytes() for folder in ('commits', 'sources')
                     for path in (self.store / folder).glob('*.json')}
        latest = self.commit(second)
        self.assertEqual(latest['head'], orphan)
        self.assertEqual(immutable, {str(path): path.read_bytes() for folder in ('commits', 'sources')
                                    for path in (self.store / folder).glob('*.json')})

    def test_first_commit_failure_leaves_explicit_empty_head_and_unpublished_objects(self):
        real = m._publish_head
        def fail(root, head):
            if head is not None: raise OSError('before first publication')
            return real(root, head)
        with patch.object(m, '_publish_head', side_effect=fail):
            with self.assertRaises(OSError): self.commit()
        self.assertEqual(m.load_memory(self.store), self.initial)
        self.assertEqual(len(list((self.store / 'commits').glob('*.json'))), 1)
        state = self.commit()
        self.assertEqual(m.load_memory(self.store), state)

    def test_failure_after_head_switch_recovers_published_state_and_retry_is_idempotent(self):
        real = m._publish_head
        def fail(root, head):
            real(root, head)
            if head is not None: raise OSError('after publication')
        with patch.object(m, '_publish_head', side_effect=fail):
            with self.assertRaises(OSError): self.commit()
        recovered = m.load_memory(self.store)
        self.assertEqual(recovered['memory']['rounds'], [self.first['prepared']['round']])
        before = self.files(self.store)
        self.assertEqual(self.commit(), recovered)
        self.assertEqual(self.files(self.store), before)

    def test_partial_atomic_write_is_not_visible_and_temporary_files_are_ignored(self):
        real = m.os.replace
        def fail(source, destination):
            if Path(destination).parent.name == 'commits': raise OSError('before commit rename')
            return real(source, destination)
        with patch.object(m.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError): self.commit()
        self.assertEqual(m.load_memory(self.store), self.initial)
        (self.store / 'commits' / '.abandoned.tmp').write_text('partial')
        self.assertEqual(m.load_memory(self.store), self.initial)
        self.assertEqual(len(list((self.store / 'commits').glob('*.json'))), 0)
        self.assertEqual(m.load_memory(self.store), self.initial)
        self.commit()

    def test_corrupt_orphan_is_not_overwritten_on_retry(self):
        real = m._publish_head
        def fail(root, head):
            if head is not None: raise OSError('before publication')
            return real(root, head)
        with patch.object(m, '_publish_head', side_effect=fail):
            with self.assertRaises(OSError): self.commit()
        orphan = next((self.store / 'commits').glob('*.json'))
        orphan.write_text('corrupt orphan')
        with self.assertRaisesRegex(ValueError, 'Immutable Memory object differs'): self.commit()
        self.assertEqual(orphan.read_text(), 'corrupt orphan')
        self.assertEqual(m.load_memory(self.store), self.initial)

    def test_writer_lock_is_held_until_publication_and_released_on_error(self):
        real = m._publish_head
        def check_lock(root, head):
            with (root / '.writer.lock').open('a+b') as stream:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            if head is not None: raise OSError('release on error')
            return real(root, head)
        with patch.object(m, '_publish_head', side_effect=check_lock):
            with self.assertRaises(OSError): self.commit()
        with (self.store / '.writer.lock').open('a+b') as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        self.commit()

    def test_concurrent_retries_are_idempotent_and_new_competing_round_is_stale(self):
        competing = self.round(self.initial, 'R04')
        for same in (True, False):
            store = self.root / f'concurrent-{same}'
            barrier = Barrier(2)
            def write(item):
                with self.method.using():
                    barrier.wait(timeout=10)
                    try:
                        return self.commit(item, store)
                    except ValueError as exc:
                        return str(exc)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(write, item) for item in
                           (self.first, self.first if same else competing)]
                results = [future.result(timeout=30) for future in futures]
            if same:
                self.assertEqual(results[0], results[1])
                self.assertIsInstance(results[0], dict)
            else:
                self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
                self.assertIn('Stale Memory head', next(result for result in results if isinstance(result, str)))
            self.assertEqual(len(list((store / 'commits').glob('*.json'))), 1)
            self.assertEqual(len(m.load_memory(store)['memory']['rounds']), 1)

    def test_preparation_and_loading_are_read_only_and_results_detached(self):
        before = self.files()
        previous, replayed, result = deepcopy((self.initial, self.first['replayed'], self.first['gate_result']))
        prepared = m.prepare_append(previous, replayed=replayed, gate_result=result)
        self.assertEqual(before, self.files())
        prepared['round']['source_updates'].clear()
        self.assertTrue(self.first['prepared']['round']['source_updates'])
        self.assertEqual((previous, replayed, result), (self.initial, self.first['replayed'], self.first['gate_result']))
        state = self.commit()
        before = self.files()
        loaded = m.load_memory(self.store)
        loaded['memory']['rounds'].clear()
        loaded['selection']['selected_update_ids'].clear()
        self.assertEqual(m.load_memory(self.store), state)
        self.assertEqual(before, self.files())

    def test_no_model_actor_old_memory_commit_or_external_process(self):
        seen = len(self.transport.seen)
        with ExitStack() as stack:
            for obj, name in ((d, 'diagnosis_call'), (p, 'preconditioner_call'), (e, 'editor_call'),
                              (r, 'replay_call'), (self.adapter, 'actor_batch'), (self.method, 'commit_memory')):
                stack.enter_context(patch.object(obj, name, side_effect=AssertionError('Forbidden execution')))
            prepared = m.prepare_append(self.initial, replayed=self.first['replayed'], gate_result=self.first['gate_result'])
            state = m.commit_memory(self.store, prepared, expected_head=None)
            self.assertEqual(m.load_memory(self.store), state)
        self.assertEqual(len(self.transport.seen), seen)


if __name__ == '__main__':
    unittest.main()
