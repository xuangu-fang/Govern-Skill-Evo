"""Citation boundaries and the six preserved R07 responses; no model calls."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from src.skill_evolution.v27.explicit_references import parse as legacy_parse
from src.skill_evolution.v29_2 import replay, output_feedback

ALLOWED = {'Update': {'u1', 'u2'}, 'Evidence': {'P7', 'P7:0', 'P7:1', 'P7:outcome',
           'Q7', 'Q7:0', 'Q7:1', 'Q7:outcome', 'diff'}, 'Memory': set(),
           'Group': set(), 'Check': set()}


class ReplayReferenceTests(unittest.TestCase):
    def parse(self, value):
        return replay.parse_references(value, ALLOWED, location='62995')

    def test_namespace_word_followed_by_colon_and_space_is_prose(self):
        for suffix in ('the rule concerns names.', 'u2 concerns names.', '`Update:u2` concerns names.'):
            with self.subTest(suffix=suffix):
                result = self.parse('Neither implemented Update: ' + suffix)
                self.assertEqual(result, [('Update', 'u2')] if suffix.startswith('`') else [])
        for prefix in ALLOWED:
            with self.subTest(prefix=prefix):
                self.assertEqual(self.parse(prefix + ': ordinary explanation.'), [])

    def test_ordinary_code_spans_and_multiple_formal_citations(self):
        value = 'Returned `<answer>$ 166.75</answer>`; see `Evidence:P7:1` and `Update:u2`.'
        self.assertEqual(self.parse(value), [('Evidence', 'P7:1'), ('Update', 'u2')])
        self.assertEqual(self.parse('Use `plain code` and `another example`.'), [])

    def test_malformed_bare_unknown_and_unavailable_references_still_fail(self):
        invalid = ['Update:u2', 'Evidence:P7:outcome', 'Evidence:Q99:1', 'Update:`u2`',
                   '`Update:u2', 'Update:u2`', '`Evidence:P7:1',
                   '``Update:u2``', '```Evidence:P7:1```', '`Update:u2``', '``Update:u2`',
                   '`Update: u2`', '`Update :u2`', '` Update:u2`', '`Update:u2 `',
                   '`Update:u999`', '`Evidence:Q99:1`', '`Evidence:pair_1_user_1`',
                   '`Memory:M1`', '`Group:G1`', '`Check:c1`',
                   '`Update:u1`Evidence:Q99:1', '`plain code`Update:u2',
                   '`Update:u2\n`', '`Update:`', '`see Update:u2`',
                   '`Update:u1 Evidence:P7:1`']
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.parse(value)

    def test_feedback_names_task_text_position_and_offending_token(self):
        with self.assertRaises(ValueError) as caught:
            self.parse('说明： Evidence:P7:outcome')
        message = str(caught.exception)
        self.assertIn('62995', message)
        self.assertIn('text character 5', message)
        self.assertIn('Evidence:P7:outcome', message)
        self.assertIn('single-backtick', message)

    def test_legacy_parser_keeps_its_original_boundary(self):
        with self.assertRaises(ValueError):
            legacy_parse('Neither implemented Update: the rule concerns names.', ALLOWED, location='old')

    def test_all_six_real_outputs_pass_without_text_edits(self):
        fixture = json.loads((Path(__file__).with_name('fixtures') /
                              'replay_r07_reference_boundary.json').read_text())
        self.assertEqual(len(fixture['attempts']), 6)
        for attempt in fixture['attempts']:
            result = json.loads(attempt['content'])
            before = deepcopy(result)
            with self.subTest(attempt=attempt['attempt']):
                items = replay._validate_output(result, fixture['view'])
                self.assertEqual([x['task_id'] for x in items], ['61503', '62995'])
                self.assertEqual(result, before)

    def test_event_scope_is_not_relaxed_by_prose_boundary(self):
        fixture = json.loads((Path(__file__).with_name('fixtures') /
                              'replay_r07_reference_boundary.json').read_text())
        for citation in ('`Evidence:P5:1`', 'P5:1', '`Evidence:Q99:1`', '`Update:u999`'):
            result = json.loads(fixture['attempts'][0]['content'])
            result['entries'][0]['knowledge'][1]['text'] = 'Ordinary Update: explanation. ' + citation
            with self.subTest(citation=citation), self.assertRaises(ValueError):
                replay._validate_output(result, fixture['view'])

    def test_bad_citation_remains_output_feedback_with_precise_diagnostic(self):
        fixture = json.loads((Path(__file__).with_name('fixtures') /
                              'replay_r07_reference_boundary.json').read_text())
        result = json.loads(fixture['attempts'][0]['content'])
        result['entries'][0]['knowledge'][1]['text'] = 'See Evidence:P7:outcome'
        with self.assertRaises(output_feedback.OutputValidationError) as caught:
            output_feedback.output_call('replay output', replay._validate_output, result, fixture['view'])
        self.assertIn('62995: text character 5', str(caught.exception))
        self.assertIn('Evidence:P7:outcome', str(caught.exception))
