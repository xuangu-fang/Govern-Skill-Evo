"""A reviewed source change must not exempt later drift or damaged evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from .source_provenance import MANIFEST, RECONCILIATION, verify

ROOT = Path(__file__).resolve().parents[3]


class SourceProvenanceTests(unittest.TestCase):
    def fixture(self, root):
        audit = json.loads((ROOT / RECONCILIATION).read_text())
        sources = json.loads((ROOT / MANIFEST).read_text())['sources']
        paths = {str(MANIFEST), str(RECONCILIATION), *sources}
        for change in audit['changes'].values():
            paths.update(change[key] for key in ('historical_snapshot', 'reviewed_snapshot', 'diff'))
        for name in paths:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        return sources, audit

    def test_reviewed_change_has_complete_historical_evidence(self):
        report = verify(ROOT)
        self.assertEqual((report['sources_checked'], report['unchanged'], report['reviewed_changes']), (65, 63, 2))
        self.assertEqual(report['sources']['src/skill_evolution/v25/config.py']['status'], 'reviewed_source_change')
        self.assertEqual(report['sources']['benchmarks/livemathematicianbench/model_access.json']['status'], 'reviewed_source_change')

    def test_future_changes_to_reviewed_and_unreviewed_sources_are_rejected(self):
        for name in ('src/skill_evolution/v25/config.py', 'src/skill_evolution/v26/config.py', 'benchmarks/livemathematicianbench/model_access.json'):
            with self.subTest(source=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.fixture(root)
                path = root / name
                path.write_bytes(path.read_bytes() + b'\n# Unreviewed change\n')
                with self.assertRaises(ValueError):
                    verify(root)

    def test_damaged_or_missing_review_evidence_is_rejected(self):
        for target in ('manifest', 'historical_snapshot', 'reviewed_snapshot', 'diff', 'missing_change'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, audit = self.fixture(root)
                change = audit['changes']['src/skill_evolution/v25/config.py']
                if target == 'missing_change':
                    audit['changes'] = {}
                    (root / RECONCILIATION).write_text(json.dumps(audit))
                else:
                    path = root / (MANIFEST if target == 'manifest' else change[target])
                    path.write_bytes(path.read_bytes() + b'\n')
                with self.assertRaises(ValueError):
                    verify(root)
