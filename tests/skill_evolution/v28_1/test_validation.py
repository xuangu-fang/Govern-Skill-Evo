"""Byte-only validation tolerates metadata changes without trusting changed evidence."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.skill_evolution.v28.memory_operation import MemoryOperation
from src.skill_evolution.v28.validation import ValidationOperation


class ValidationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / 'response.json'
        self.path.write_bytes(b'AAAA')
        self.adapter = SimpleNamespace(verify_hashes=False)
        self.checks = ValidationOperation(self.adapter)
        self.enterContext(patch('hashlib.sha256', side_effect=AssertionError('No hashes in v28.1')))

    def during_read(self, change):
        original = Path.read_bytes
        changed = False

        def read(path):
            nonlocal changed
            data = original(path)
            if path == self.path and not changed:
                changed = True
                change()
            return data

        return patch.object(Path, 'read_bytes', read)

    def test_metadata_change_during_read_is_allowed(self):
        with self.during_read(lambda: self.path.chmod(0o600)):
            self.checks.watch_file(self.path)
        self.checks.verify()

    def test_content_change_during_read_is_rejected(self):
        with self.during_read(lambda: self.path.write_bytes(b'BBBB')):
            with self.assertRaisesRegex(ValueError, 'changed while reading'):
                self.checks.watch_file(self.path)

    def test_metadata_changes_at_operation_end_are_allowed(self):
        self.checks.watch_file(self.path)
        self.path.chmod(0o600)
        stamp = self.path.stat()
        os.utime(self.path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1000000000))
        self.checks.verify()

    def test_identical_content_replacement_is_allowed(self):
        self.checks.watch_file(self.path)
        replacement = self.root / 'replacement'
        replacement.write_bytes(self.path.read_bytes())
        replacement.replace(self.path)
        self.checks.verify()

    def test_same_size_content_change_with_restored_mtime_is_rejected(self):
        self.checks.watch_file(self.path)
        stamp = self.path.stat()
        self.path.write_bytes(b'BBBB')
        os.utime(self.path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with self.assertRaisesRegex(ValueError, 'dependency changed'):
            self.checks.verify()

    def test_missing_file_and_changed_membership_are_rejected(self):
        self.checks.watch_file(self.path)
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.checks.verify()
        checks = ValidationOperation(self.adapter)
        checks.watch_tree(self.root)
        self.path.write_bytes(b'AAAA')
        with self.assertRaisesRegex(ValueError, 'membership changed'):
            checks.verify()

    def test_memory_hardlink_keeps_content_validation(self):
        self.checks.watch_file(self.path)
        dest = self.root / 'linked.json'
        os.link(self.path, dest)
        session = MemoryOperation(SimpleNamespace(actor_adapter=self.adapter), self.checks)
        session.linked(self.path, dest)
        self.checks.verify()
        dest.write_bytes(b'BBBB')
        with self.assertRaisesRegex(ValueError, 'Memory source changed'):
            session.linked(self.path, dest)
        with self.assertRaisesRegex(ValueError, 'dependency changed'):
            self.checks.verify()
