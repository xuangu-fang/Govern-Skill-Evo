"""Local slash lists must neither invent history nor bypass evidence scope."""
import unittest
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v29.benchmarks.docvqa.evidence import references as legacy
from src.skill_evolution.v29_2.execution_references import references


class ExecutionReferenceTests(unittest.TestCase):
    def test_original_r03_response_passes_without_changing_its_content(self):
        from src.skill_evolution.v29_2 import diagnosis
        fixture = json.loads((Path(__file__).parent / 'fixtures/diagnosis_r03_slash_references.json').read_text())
        content = fixture['response_content']
        self.assertEqual(hashlib.sha256(content.encode()).hexdigest(), fixture['content_sha256'])
        result = json.loads(content)
        with patch.object(diagnosis, 'references', legacy), self.assertRaisesRegex(ValueError, 'unavailable execution reference'):
            diagnosis._validate_output(result, fixture['payload'])
        self.assertEqual(diagnosis._validate_output(result, fixture['payload']), result)

    def test_r03_list_is_four_local_references(self):
        value = 'numeric page tokens in P1/P5/P7/P10, labels in P8/P11'
        self.assertEqual(references(value), {'P1', 'P5', 'P7', 'P10', 'P8', 'P11'})
        self.assertIn('P1/P5', legacy(value))  # Legacy behavior is deliberately unchanged.

    def test_lists_preserve_every_local_reference_and_step(self):
        for value, expected in [
            ('P1:1/P5:outcome/P7:0', {'P1:1', 'P5:outcome', 'P7:0'}),
            ('P1/Q1/Q2/P9', {'P1', 'Q1', 'Q2', 'P9'}),
            ('`P1/P5/P7/P10`', {'P1', 'P5', 'P7', 'P10'}),
            ('P1 / P5 / Q99', {'P1', 'P5', 'Q99'}),
            ('P1:1-3', {'P1:1', 'P1:2', 'P1:3'}),
        ]:
            with self.subTest(value=value):
                self.assertEqual(references(value), expected)

    def test_history_remains_visible_including_history_before_or_after_lists(self):
        for value, expected in [
            ('R03/P1:1', 'R03/P1:1'), ('R03/diff', 'R03/diff'),
            ('campaign_R03/Q1:outcome', 'campaign_R03/Q1:outcome'),
            ('R03/P1/P5/P7/P10', 'R03/P1'),
            ('P1/P5; old-R03/P7:0', 'old-R03/P7:0'),
            ('P1:outcome/R03/P5:1', 'R03/P5:1'),
            ('P1/diff', 'P1/diff'), ('P1suffix/P5', 'P1suffix/P5'),
        ]:
            with self.subTest(value=value):
                self.assertIn(expected, references(value))

    def test_invalid_ranges_remain_invalid(self):
        for value in ('P1:3-1', 'P1:1-P2:3', 'P1:0-10001'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                references(value)
