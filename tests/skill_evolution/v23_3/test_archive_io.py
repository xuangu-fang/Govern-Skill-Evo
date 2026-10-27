"""Standalone path checks; no experiment imports, model calls or hash checks.

Run directly with Python to avoid loading the experiment test conftest.
"""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'v23_3_archive_paths', ROOT / 'experiments/methods/v23_3/archive_io.py')
archive_io = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(archive_io)


class ArchiveWritePaths(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix='v23_3-path-check-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'experiments'
        self.archive = self.root / 'artifacts'
        self.source.mkdir()
        self.archive.mkdir()
        for name, value in [('EXPERIMENTS', self.source), ('ARCHIVE', self.archive)]:
            replacement = patch.object(archive_io, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)

    def write_new(self, path):
        # The existing save functions resolve the directory and file separately.
        archive_io.resolve(path.parent).mkdir(parents=True, exist_ok=True)
        with archive_io.resolve(path).open('x') as stream:
            stream.write('new record')

    def test_new_file_in_archived_directory(self):
        parent = self.archive / 'study/runs/A/http/001'
        parent.mkdir(parents=True)
        target = self.source / 'study/runs/A/http/001/new_record.json'
        self.assertEqual(archive_io.resolve(target), parent / target.name)
        self.write_new(target)
        self.assertEqual((parent / target.name).read_text(), 'new record')
        self.assertFalse(target.parent.exists())

    def test_new_nested_directory_stays_in_archive(self):
        (self.source / 'study').mkdir()
        (self.archive / 'study/runs').mkdir(parents=True)
        target = self.source / 'study/runs/new_attempt/http/request.json'
        expected = self.archive / target.relative_to(self.source)
        self.assertEqual(archive_io.resolve(target), expected)
        self.write_new(target)
        self.assertEqual(expected.read_text(), 'new record')
        self.assertFalse((self.source / 'study/runs').exists())

    def test_new_curated_file_stays_in_existing_source_directory(self):
        for root in (self.source, self.archive):
            (root / 'study/results').mkdir(parents=True)
        target = self.source / 'study/results/new_report.json'
        self.assertEqual(archive_io.resolve(target), target)
        self.write_new(target)
        self.assertFalse((self.archive / target.relative_to(self.source)).exists())

    def test_existing_archived_file_keeps_location(self):
        for root in (self.source, self.archive):
            (root / 'study/results').mkdir(parents=True)
        target = self.source / 'study/results/raw.json'
        archived = self.archive / target.relative_to(self.source)
        archived.write_text('saved raw data')
        self.assertEqual(archive_io.resolve(target), archived)
        with self.assertRaises(FileExistsError):
            self.write_new(target)
        self.assertEqual(archived.read_text(), 'saved raw data')

    def test_existing_curated_file_takes_precedence(self):
        for root, value in [(self.source, 'curated'), (self.archive, 'archived')]:
            (root / 'study').mkdir()
            (root / 'study/report.json').write_text(value)
        target = self.source / 'study/report.json'
        self.assertEqual(archive_io.resolve(target), target)
        self.assertEqual(archive_io.resolve(target).read_text(), 'curated')

    def test_unmigrated_new_path_stays_in_source(self):
        target = self.source / 'new_study/results/new_report.json'
        self.assertEqual(archive_io.resolve(target), target)
        self.write_new(target)
        self.assertTrue(target.is_file())

    def test_external_and_explicit_archive_paths_are_unchanged(self):
        for target in (self.root / 'external/new.json', self.archive / 'study/new.json'):
            self.assertEqual(archive_io.resolve(target), target)
            self.write_new(target)
            self.assertTrue(target.is_file())


if __name__ == '__main__':
    unittest.main()
