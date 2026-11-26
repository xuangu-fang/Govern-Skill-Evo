"""Reuse must preserve archive rejection and detect changes after cache hits."""
from copy import deepcopy
import os
import shutil
from unittest.mock import patch

from src.skill_evolution.v28 import validation
from src.skill_evolution.v28.method import SearchQAMethod
from src.skill_evolution.v28.benchmarks.searchqa import actor, protocol as p
from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
from src.skill_evolution.v28.storage import read, save
from .runtime_support import Base, Dataset, Transport


class ValidationCacheTests(Base):
    def setUp(self):
        super().setUp()
        self.adapter = SearchQAActorAdapter(Dataset(2), Transport())
        self.archive = self.root / 'batch'
        self.config = {'split': 'train', 'role': 'parent'}
        self.records = self.adapter.actor_batch(list(self.adapter.dataset.rows), self.skill, self.archive, self.config)
        self.method = SearchQAMethod(self.adapter, archives=[self.archive])
        self.folder = self.archive / 'actor' / p.digest(self.records[0]['task_id'])

    def validate(self):
        return self.method.validate_record(self.records[0])

    def test_each_identity_batch_and_execution_checked_once(self):
        with patch.object(p, '_implementation_identity', wraps=p._implementation_identity) as identity, \
             patch.object(self.adapter, '_signature', wraps=self.adapter._signature) as signature, \
             patch.object(actor, 'read_completed', wraps=actor.read_completed) as completed:
            with validation.operation(self.adapter):
                for _ in range(3):
                    for record in self.records:
                        self.assertEqual(self.method.validate_record(record), record)
            self.assertEqual(identity.call_count, 1)
            self.assertEqual(signature.call_count, 1)
            self.assertEqual(completed.call_count, 2)
        self.assertIsNone(validation.current())

    def test_new_operation_revalidates_and_return_values_are_detached(self):
        with patch.object(actor, 'read_completed', wraps=actor.read_completed) as completed:
            for _ in range(2):
                with validation.operation(self.adapter):
                    result = self.validate()
                    result['execution']['skill'] = 'modified caller copy'
                    self.assertEqual(self.validate(), self.records[0])
            self.assertEqual(completed.call_count, 2)

    def test_cached_record_content_and_registered_content_cannot_change(self):
        with validation.operation(self.adapter):
            self.validate()
            bad = deepcopy(self.records[0]); bad['execution']['content'] = 'forged'
            self.reject(self.method.validate_record, bad)
            rid = bad['run_id']; old = self.method._records[rid]
            self.method._records[rid] = bad
            try:
                self.reject(self.method.validate_record, bad)
            finally:
                self.method._records[rid] = old

    def test_cached_batch_still_checks_expected_skill_and_role(self):
        with validation.operation(self.adapter):
            self.validate()
            self.reject(self.adapter.check_record_archive, self.records[0], self.records[0]['task_id'],
                        'wrong Skill', self.config, self.archive)
            self.reject(self.adapter.check_record_archive, self.records[0], self.records[0]['task_id'],
                        self.records[0]['execution']['skill'], {'split': 'train', 'role': 'candidate'}, self.archive)

    def test_changed_files_rejected_before_first_validation(self):
        for filename, mutate in (
            ('records.json', lambda value: value.reverse()),
            ('batch.json', lambda value: value['signature'].update(skill='changed')),
        ):
            with self.subTest(filename=filename):
                path = self.archive / filename; original = path.read_bytes()
                try:
                    value = read(path); mutate(value); save(path, value)
                    with self.assertRaises(ValueError), validation.operation(self.adapter):
                        self.validate()
                finally:
                    path.write_bytes(original)

    def test_raw_response_tampering_before_operation_rejected(self):
        path = self.folder / 'attempts/001/response.json'
        value = read(path); value['choices'][0]['message']['content'] = '<answer>forged</answer>'
        save(path, value)
        with self.assertRaises(ValueError), validation.operation(self.adapter):
            self.validate()

    def test_post_hit_mutations_are_rejected_at_operation_boundary(self):
        paths = [self.folder / 'attempts/001/response.json', self.archive / 'records.json',
                 self.archive / 'batch.json', self.folder / 'signature.json']
        for path in paths:
            with self.subTest(path=path.name):
                original = path.read_bytes(); stamp = path.stat()
                try:
                    with self.assertRaisesRegex(ValueError, 'dependency changed'), validation.operation(self.adapter):
                        self.validate()
                        path.write_bytes(original + b' ')
                        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
                        self.validate()  # Hit is provisional; operation must not succeed.
                finally:
                    path.write_bytes(original)
                self.assertIsNone(validation.current())

    def test_post_hit_add_delete_and_replace_are_rejected(self):
        path = self.folder / 'result.json'
        original = path.read_bytes()
        for action in ('add', 'delete', 'replace'):
            with self.subTest(action=action):
                extra = self.folder / 'attempts/002'
                try:
                    with self.assertRaises((ValueError, FileNotFoundError)), validation.operation(self.adapter):
                        self.validate()
                        if action == 'add':
                            extra.mkdir()
                        elif action == 'delete':
                            path.unlink()
                        else:
                            replacement = self.root / 'replacement'
                            replacement.write_bytes(original)
                            replacement.replace(path)
                        self.validate()
                finally:
                    path.write_bytes(original)
                    if extra.exists(): extra.rmdir()

    def test_prompt_render_snapshot_is_local_and_not_a_source_lock(self):
        context = self.root / 'context'
        shutil.copytree(p.CONTEXT, context)
        with patch.object(p, 'CONTEXT', context):
            with validation.operation(self.adapter):
                self.validate()
                path = context / 'actor_system.md'
                path.write_text(path.read_text() + 'changed')
                self.validate()  # This operation retains its original rendered request.
            # The next operation renders current messages and rejects reuse of a
            # completed execution with a different request, not a Prompt hash.
            with self.assertRaises(ValueError), validation.operation(self.adapter):
                self.validate()

    def test_cached_templates_preserve_read_text_newline_semantics(self):
        context = self.root / 'context'
        shutil.copytree(p.CONTEXT, context)
        for name in ('actor_system.md', 'actor_user.md'):
            path = context / name
            path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        with patch.object(p, 'CONTEXT', context):
            adapter = SearchQAActorAdapter(Dataset(2))
            payload = adapter.dataset.case(self.records[0]['task_id']).payload
            expected = p.messages(payload, self.records[0]['execution']['skill'])
            with validation.operation(adapter):
                self.assertEqual(p.messages(payload, self.records[0]['execution']['skill']), expected)

    def test_load_memory_rechecks_dependencies_before_returning(self):
        def changed_load(_):
            self.validate()
            path = self.folder / 'result.json'
            path.write_bytes(path.read_bytes() + b' ')
            self.validate()
            return {'entries': [], 'sources': {}}
        with patch.object(self.method, '_load_memory', side_effect=changed_load):
            self.reject(self.method.load_memory, self.root / 'empty_memory')
        self.assertIsNone(validation.current())

    def test_source_files_are_not_watched_by_validation(self):
        with patch.object(p, 'file_digest', side_effect=AssertionError('No source digests')):
            self.assertEqual(p.implementation_identity(), self.adapter._protocol)
        with validation.operation(self.adapter) as state:
            self.validate()
            for path in state.files:
                self.assertFalse(path.is_relative_to(p.ROOT / 'src'))
                self.assertFalse(path.is_relative_to(p.ROOT / 'external'))

    def test_bound_dataset_changes_rejected(self):
        with self.assertRaises(ValueError), validation.operation(self.adapter):
            self.validate()
            self.adapter.dataset.rows[self.records[0]['task_id']]['context'] = 'changed'

    def test_bound_actor_config_changes_rejected(self):
        with self.assertRaises(ValueError), validation.operation(self.adapter):
            self.validate()
            self.adapter.transport.config['max_tokens'] = 32768

    def test_exception_discards_cache(self):
        with self.assertRaises(RuntimeError), validation.operation(self.adapter):
            self.validate()
            raise RuntimeError('interrupted')
        self.assertIsNone(validation.current())
        with patch.object(actor, 'read_completed', wraps=actor.read_completed) as completed:
            with validation.operation(self.adapter): self.validate()
            self.assertEqual(completed.call_count, 1)

    def test_nested_operation_reuses_only_same_adapter(self):
        with validation.operation(self.adapter) as outer:
            with validation.operation(self.adapter) as inner:
                self.assertIs(inner, outer)
            other = SearchQAActorAdapter(Dataset(2))
            with validation.operation(other) as inner:
                self.assertIsNot(inner, outer)
            self.assertIs(validation.current(), outer)
