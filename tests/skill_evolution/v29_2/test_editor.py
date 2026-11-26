"""Offline Editor acceptance: exact patch composition and verified handoff.

Synthetic archives and authored outputs only; these tests do not establish
model editing quality or semantic independence of selectable modifications.
"""
from copy import deepcopy
import itertools
import json
import socket
import subprocess
import unittest
from unittest.mock import patch

from src.skill_evolution.v27.contracts import memory as old_memory
from src.skill_evolution.v27.contracts.editor import actual_diff, NO_NEWLINE
from src.skill_evolution.v27.unnumbered_patch import apply_patch as old_apply_patch
from src.skill_evolution.v29 import modules as old_modules
from src.skill_evolution.v29.benchmarks.docvqa import protocol, prompting
from src.skill_evolution.v29.storage import read, save
from src.skill_evolution.v29_1.campaign import CampaignAdapter
from src.skill_evolution.v29_2 import diagnosis as d, preconditioner as p, editor as e
from tests.skill_evolution.v29.test_actor import HIDDEN, FIVE
from tests.skill_evolution.v29.test_method import MethodBase, main_example
from tests.skill_evolution.v29_2.test_diagnosis import proposal
from tests.skill_evolution.v29_2.test_preconditioner import decisions, memory_view


def offline(test):
    attempts = []

    def deny(*args, **kwargs):
        attempts.append('network_or_process')
        raise AssertionError('Offline Editor test attempted network/process access')

    for obj, name in ((socket.socket, 'connect'), (socket.socket, 'connect_ex'),
                      (socket, 'create_connection'), (subprocess, 'Popen')):
        test.enterContext(patch.object(obj, name, deny))
    test.addCleanup(lambda: test.assertEqual(attempts, []))


def diff(body, *, create=False):
    return ('--- /dev/null\n' if create else '--- a/SKILL.md\n') + '+++ b/SKILL.md\n@@\n' + body


def output(*patches):
    return {'edits': [{'update_id': f'u{i}', 'patch': value,
                       'reason': 'Implement the corresponding requirement or explain existing coverage.'}
                      for i, value in enumerate(patches, 1)]}


def payload(parent, count=1):
    return {'parent': parent, 'plan': {'goal': 'Implement the scoped requirements.',
                                     'updates': [{'id': f'u{i}', 'text': f'Complete requirement {i}.'}
                                                 for i in range(1, count + 1)]}}


def replace_line(old, new):
    def body(prefix, line):
        return prefix + line if line.endswith('\n') else prefix + line + '\n' + NO_NEWLINE + '\n'
    return diff(body('-', old) + body('+', new))


class PatchCompositionTests(unittest.TestCase):
    def setUp(self):
        offline(self)

    def build(self, parent, *patches):
        return e.construct_candidate(output(*patches), payload(parent, len(patches)))

    def test_single_update_multiple_hunks_preserve_unrelated_text(self):
        parent = 'A\nB\nC\nD\n'
        change = diff('-A\n+a\n B\n@@\n C\n-D\n+d\n')
        result = self.build(parent, change)
        self.assertEqual(result['candidate_text'], 'a\nB\nC\nd\n')
        self.assertEqual(result['actual_diff'], actual_diff(parent, result['candidate_text']))
        self.assertEqual(result['candidate_text'], old_apply_patch(parent, change))

    def test_shared_context_and_modified_context_are_allowed_across_updates(self):
        result = self.build('A\nB\nC\n', diff(' A\n-B\n+b\n C\n'), diff(' A\n B\n-C\n+c\n'))
        self.assertEqual(result['candidate_text'], 'A\nb\nc\n')

    def test_same_gap_insertions_use_effective_order_not_output_order(self):
        edits = output(diff(' A\n+first\n B\n'), diff(' A\n+second\n B\n'))
        edits['edits'].reverse()
        result = e.construct_candidate(edits, payload('A\nB\n', 2))
        self.assertEqual(result['candidate_text'], 'A\nfirst\nsecond\nB\n')

    def test_insertions_at_replacement_boundaries_preserve_both_sides(self):
        result = self.build('A\nB\nC\nD\n', diff(' A\n-B\n-C\n+X\n D\n'),
                            diff(' A\n+start\n B\n'), diff(' C\n+end\n D\n'))
        self.assertEqual(result['candidate_text'], 'A\nstart\nX\nend\nD\n')

    def test_deletion_with_boundary_insertion_can_replace_entire_parent(self):
        result = self.build('A\n', diff('-A\n'), diff('+Z\n A\n'))
        self.assertEqual(result['candidate_text'], 'Z\n')

    def test_overlapping_deletions_and_replacements_are_conflicts_even_if_identical(self):
        for left, right in ((diff('-A\n+a\n B\n'), diff('-A\n+a\n B\n')),
                            (diff('-A\n B\n'), diff('-A\n+a\n B\n')),
                            (diff('-A\n-B\n+X\n'), diff(' A\n-B\n+b\n'))):
            with self.subTest(left=left, right=right), self.assertRaisesRegex(ValueError, 'Conflicting patches'):
                self.build('A\nB\n', left, right)

    def test_insertion_strictly_inside_replacement_is_a_conflict(self):
        with self.assertRaisesRegex(ValueError, 'Conflicting patches'):
            self.build('A\nB\nC\n', diff('-A\n-B\n+X\n C\n'), diff(' A\n+inside\n B\n'))

    def test_later_patch_cannot_use_an_earlier_patch_result_as_context(self):
        with self.assertRaisesRegex(ValueError, 'source match'):
            self.build('A\nB\n', diff('-A\n+a\n B\n'), diff(' a\n-B\n+b\n'))

    def test_null_and_empty_parent_creation_have_exact_distinct_headers(self):
        for parent in (None, ''):
            created = self.build(parent, diff('+First.\n', create=parent is None),
                                 diff('+Second.\n', create=parent is None))
            self.assertEqual(created['candidate_text'], 'First.\nSecond.\n')
            with self.assertRaises(ValueError):
                self.build(parent, diff('+Wrong header.\n', create=parent is not None))

    def test_empty_patch_preserves_parent_and_is_not_a_defer_decision(self):
        for parent in (None, '', 'A\n'):
            self.assertEqual(self.build(parent, '', ''), {
                'editor_status': 'no_change', 'candidate_text': None, 'actual_diff': None})
        result = self.build('A\n', '', diff(' A\n+B\n'))
        self.assertEqual(result['candidate_text'], 'A\nB\n')

    def test_null_stops_whole_construction_without_partial_candidate(self):
        self.assertEqual(self.build('A\n', diff('-A\n+a\n'), None), {
            'editor_status': 'needs_revision', 'candidate_text': None, 'actual_diff': None})
        self.assertEqual(self.build(None, '', None)['editor_status'], 'needs_revision')
        # A semantic stop does not hide malformed non-null edits or missing IDs.
        with self.assertRaises(ValueError):
            self.build('A\n', None, 'not a diff')

    def test_exact_mapping_and_schema_are_required(self):
        valid = output('', '')
        variants = [None, [], {}, {'edits': None}, {'edits': []},
                    {**valid, 'implementations': []}, {**valid, 'candidate': 'Skill'}]
        for key in ('update_id', 'patch', 'reason'):
            bad = deepcopy(valid)
            del bad['edits'][0][key]
            variants.append(bad)
        for key in ('update_ids', 'status', 'basis', 'implementation'):
            bad = deepcopy(valid)
            bad['edits'][0][key] = ['u1', 'u2']
            variants.append(bad)
        for uid in ('u2', 'u99', '', [], None):
            bad = deepcopy(valid)
            bad['edits'][0]['update_id'] = uid
            variants.append(bad)
        for value in ([], {}, 1, True):
            bad = deepcopy(valid)
            bad['edits'][0]['patch'] = value
            variants.append(bad)
        for reason in ('', ' ', None, [], '\0'):
            bad = deepcopy(valid)
            bad['edits'][0]['reason'] = reason
            variants.append(bad)
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                e.construct_candidate(bad, payload('A\n', 2))

    def test_pure_input_view_rejects_extra_fields_and_invalid_plan(self):
        variants = [{**payload('A\n'), 'memory': {}}, payload(12),
                    {'parent': 'A\n', 'plan': None}, payload('A\n', 0)]
        for change in ('basis', 'checks', 'goal', 'text', 'duplicate', 'missing'):
            bad = payload('A\n')
            if change == 'basis': bad['plan']['updates'][0]['basis'] = ['P1:1']
            elif change == 'checks': bad['plan']['checks'] = []
            elif change == 'goal': bad['plan']['goal'] = ' '
            elif change == 'text': bad['plan']['updates'][0]['text'] = ''
            elif change == 'duplicate': bad['plan']['updates'] *= 2
            else: del bad['plan']['updates'][0]['id']
            variants.append(bad)
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                e.construct_candidate(output(''), bad)

    def test_invalid_patch_syntax_and_noop_hunks_are_rejected(self):
        variants = [' ', '\n', '\0', '\ud800', '--- a/other.md\n+++ b/SKILL.md\n@@\n-A\n+a\n',
                    diff('-A\n+a\n').replace('@@\n', '@@ -1 +1 @@\n'),
                    diff('-A\n+a'), diff(' A\n'), diff('-A\n+A\n'), diff(''),
                    diff('+insert without context\n'), diff('A\n+a\n'),
                    diff('-A\n+a\n') + 'commentary\n', diff('-A\n+a\n@@\n')]
        for change in variants:
            with self.subTest(change=repr(change)), self.assertRaises(ValueError):
                self.build('A\n', change)

    def test_missing_and_ambiguous_context_require_exact_unique_match(self):
        for parent, change in (('A\n', diff('-a\n+X\n')),
                               ('A\nA\n', diff('-A\n+X\n')),
                               (' A\n', diff('-A\n+X\n'))):
            with self.subTest(parent=parent), self.assertRaises(ValueError):
                self.build(parent, change)

    def test_hunks_within_one_patch_keep_old_order_and_context_nonoverlap(self):
        for change in (diff(' B\n-C\n+c\n@@\n-A\n+a\n'),
                       diff('-A\n+a\n B\n@@\n B\n-C\n+c\n')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.build('A\nB\nC\n', change)

    def test_creation_rejects_multiple_hunks_and_context(self):
        for change in (diff('+A\n@@\n+B\n', create=True), diff(' A\n+B\n', create=True)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.build(None, change)

    def test_markdown_whitespace_crlf_and_unicode_remain_literal(self):
        parent = '# Rules\r\n\r\n  - 日期：旧值  \r\n'
        change = diff(' # Rules\r\n \r\n-  - 日期：旧值  \r\n+  - 日期：新值  \r\n')
        self.assertEqual(self.build(parent, change)['candidate_text'], '# Rules\r\n\r\n  - 日期：新值  \r\n')
        self.assertEqual(old_apply_patch(parent, change), self.build(parent, change)['candidate_text'])

    def test_missing_final_newline_identity_and_invalid_interior_markers(self):
        marker = NO_NEWLINE + '\n'
        change = diff('-A\n' + marker + '+B\n' + marker)
        self.assertEqual(self.build('A', change)['candidate_text'], 'B')
        self.assertIn(NO_NEWLINE, self.build('A', change)['actual_diff'])
        # Explicitly add LF before appending; do not silently concatenate lines.
        self.assertEqual(self.build('A', diff('-A\n' + marker + '+A\n+B\n'))['candidate_text'], 'A\nB\n')
        for body in (' A\n' + marker + '+B\n', '+B\n' + marker + ' A\n',
                     '-A\n+B\n' + marker + marker):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.build('A', diff(body))

    def test_joint_eof_validation_rejects_individually_plausible_insertions(self):
        marker = NO_NEWLINE + '\n'
        with self.assertRaisesRegex(ValueError, 'Candidate EOF'):
            self.build(None, diff('+A\n' + marker, create=True), diff('+B\n', create=True))

    def test_combined_candidate_cannot_be_empty_whitespace_or_unchanged(self):
        for changes in ((diff('-A\n'),), (diff('-A\n+ \n'),), (diff('-A\n'), diff('+A\n A\n'))):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.build('A\n', *changes)

    def test_failure_is_atomic_and_results_do_not_mutate_inputs(self):
        view, edits = payload('A\nB\n', 2), output(diff('-A\n+a\n B\n'), diff('missing\n'))
        before = deepcopy((view, edits))
        with self.assertRaises(ValueError):
            e.construct_candidate(edits, view)
        self.assertEqual((view, edits), before)
        edits['edits'][1]['patch'] = diff(' A\n-B\n+b\n')
        self.assertEqual(e.construct_candidate(edits, view)['candidate_text'], 'a\nb\n')

    def test_disjoint_replacements_and_deletions_match_manual_expected_text(self):
        # Exhaustive small cases exercise context sharing without another diff algorithm.
        lines = ['A\n', 'B\n', 'C\n', 'D\n']
        for positions in itertools.permutations(range(4), 2):
            for deleted in itertools.product((False, True), repeat=2):
                patches, expected = [], list(lines)
                for index, remove in zip(positions, deleted):
                    body = ''.join((' ' + line if i != index else
                                    '-' + line + ('' if remove else '+' + line.lower()))
                                   for i, line in enumerate(lines))
                    patches.append(diff(body))
                    expected[index] = '' if remove else lines[index].lower()
                    self.assertEqual(self.build(''.join(lines), patches[-1])['candidate_text'],
                                     old_apply_patch(''.join(lines), patches[-1]))
                with self.subTest(positions=positions, deleted=deleted):
                    self.assertEqual(self.build(''.join(lines), *patches)['candidate_text'], ''.join(expected))


class InlineCompositionTests(unittest.TestCase):
    def setUp(self):
        offline(self)

    def test_same_line_disjoint_words_full_candidate_and_every_subset(self):
        parent = 'Preserve dates and author names exactly.\n'
        edits = output(replace_line(parent, parent.replace('dates', 'numbers')),
                       replace_line(parent, parent.replace('author', 'publisher')),
                       replace_line(parent, parent.replace('exactly', 'verbatim')))
        view = payload(parent, 3)
        edits['edits'].reverse()
        before = deepcopy((edits, view))
        for flags in itertools.product((False, True), repeat=3):
            ids = [f'u{i}' for i, flag in enumerate(flags, 1) if flag]
            expected = parent
            for enabled, old, new in zip(flags, ('dates', 'author', 'exactly'),
                                         ('numbers', 'publisher', 'verbatim')):
                if enabled: expected = expected.replace(old, new)
            for requested in itertools.permutations(ids):
                selected = e.construct_selected(edits, view, list(requested))
                self.assertEqual(selected, {'selected_update_ids': ids, 'selected_text': expected,
                                            'actual_diff': actual_diff(parent, expected)})
        self.assertEqual(e.construct_candidate(edits, view)['candidate_text'],
                         'Preserve numbers and publisher names verbatim.\n')
        self.assertEqual((edits, view), before)

    def test_adjacent_character_edits_are_allowed(self):
        parent = 'abcd\n'
        edits = output(replace_line(parent, 'aXcd\n'), replace_line(parent, 'abYd\n'))
        self.assertEqual(e.construct_candidate(edits, payload(parent, 2))['candidate_text'], 'aXYd\n')

    def test_character_insertions_share_gap_in_effective_order(self):
        parent = 'ab\n'
        edits = output(replace_line(parent, 'aXYb\n'), replace_line(parent, 'aZb\n'))
        edits['edits'].reverse()
        view = payload(parent, 2)
        self.assertEqual(e.construct_candidate(edits, view)['candidate_text'], 'aXYZb\n')
        self.assertEqual(e.construct_selected(edits, view, ['u2', 'u1'])['selected_text'], 'aXYZb\n')
        self.assertEqual(e.construct_selected(edits, view, ['u1'])['selected_text'], 'aXYb\n')
        self.assertEqual(e.construct_selected(edits, view, ['u2'])['selected_text'], 'aZb\n')

    def test_character_insertion_at_both_replacement_boundaries(self):
        parent = 'abcd\n'
        edits = output(replace_line(parent, 'aXd\n'), replace_line(parent, 'aL bcd\n'),
                       replace_line(parent, 'abcRd\n'))
        view = payload(parent, 3)
        self.assertEqual(e.construct_candidate(edits, view)['candidate_text'], 'aL XRd\n')
        self.assertEqual(e.construct_selected(edits, view, ['u2', 'u3'])['selected_text'], 'aL bcRd\n')
        self.assertEqual(e.construct_selected(edits, view, ['u1'])['selected_text'], 'aXd\n')

    def test_actual_overlap_and_interior_insertion_are_rejected(self):
        parent = 'abcd|z\n'
        for left, right in (('aXd|z\n', 'abY|z\n'), ('aXd|z\n', 'aXd|z\n'),
                            ('ad|z\n', 'aXd|z\n'), ('X|z\n', 'abQcd|z\n')):
            edits, view = output(replace_line(parent, left), replace_line(parent, right)), payload(parent, 2)
            with self.subTest(left=left, right=right):
                with self.assertRaisesRegex(ValueError, 'Conflicting patches'):
                    e.construct_candidate(edits, view)
                for ids in ([], ['u1'], ['u2']):
                    with self.assertRaisesRegex(ValueError, 'Conflicting patches'):
                        e.construct_selected(edits, view, ids)

    def test_ambiguous_repeated_text_alignment_is_not_guessed(self):
        for parent, changed in (('aa|z\n', 'a|z\n'), ('aa|z\n', 'aaa|z\n'),
                                ('ab|z\n', 'abab|z\n')):
            edits = output(replace_line(parent, changed), replace_line(parent, parent.replace('z', 'Z')))
            view = payload(parent, 2)
            with self.subTest(parent=parent, changed=changed):
                # A whole-line patch alone remains exact and valid. It cannot
                # provide an unambiguous character location for joint editing.
                self.assertEqual(e.construct_candidate(output(edits['edits'][0]['patch']),
                                                       payload(parent))['candidate_text'], changed)
                for ids in (None, [], ['u2']):
                    with self.assertRaisesRegex(ValueError, 'Ambiguous inline modification location'):
                        if ids is None: e.construct_candidate(edits, view)
                        else: e.construct_selected(edits, view, ids)

    def test_repeated_text_outside_unique_modifications_is_allowed(self):
        parent = 'tag tag | old | end\n'
        edits = output(replace_line(parent, parent.replace('old', 'new')),
                       replace_line(parent, parent.replace('end', 'fin')))
        self.assertEqual(e.construct_candidate(edits, payload(parent, 2))['candidate_text'],
                         'tag tag | new | fin\n')

    def test_multiple_islands_keep_conservative_span_and_whole_patch_ownership(self):
        parent = 'abcdef\n'
        first = replace_line(parent, 'AbCdef\n')
        valid = output(first, replace_line(parent, 'abcdeF\n'))
        self.assertEqual(e.construct_candidate(valid, payload(parent, 2))['candidate_text'], 'AbCdeF\n')
        self.assertEqual(e.construct_selected(valid, payload(parent, 2), ['u1'])['selected_text'], 'AbCdef\n')
        with self.assertRaisesRegex(ValueError, 'Conflicting patches'):
            e.construct_candidate(output(first, replace_line(parent, 'aBcdef\n')), payload(parent, 2))

    def test_inline_changes_mix_with_other_hunks_and_line_gap_insertions(self):
        parent = '# Rules\nabcd\nTail\n'
        edits = output(diff(' # Rules\n-abcd\n+aBcd\n@@\n-Tail\n+End\n'),
                       diff(' # Rules\n-abcd\n+abcD\n Tail\n'),
                       diff(' # Rules\n+Before\n abcd\n+After\n Tail\n'))
        view = payload(parent, 3)
        for flags in itertools.product((False, True), repeat=3):
            ids = [f'u{i}' for i, flag in enumerate(flags, 1) if flag]
            expected = ('# Rules\n' + ('Before\n' if flags[2] else '') + 'a' +
                        ('B' if flags[0] else 'b') + 'c' + ('D' if flags[1] else 'd') + '\n' +
                        ('After\n' if flags[2] else '') + ('End\n' if flags[0] else 'Tail\n'))
            self.assertEqual(e.construct_selected(edits, view, ids)['selected_text'], expected)
        self.assertEqual(e.construct_candidate(edits, view)['candidate_text'],
                         '# Rules\nBefore\naBcD\nAfter\nEnd\n')

    def test_multiline_blocks_and_whole_line_deletions_are_not_guessed(self):
        parent = 'ab\ncd\n'
        first = diff('-ab\n+aB\n cd\n')
        for second in (diff('-ab\n-cd\n+Ab\n+cD\n'), diff('-ab\n cd\n')):
            with self.subTest(second=second), self.assertRaisesRegex(ValueError, 'Conflicting patches'):
                e.construct_candidate(output(first, second), payload(parent, 2))

    def test_unicode_crlf_and_missing_final_newline_survive_all_subsets(self):
        for ending in ('\n', '\r\n', ''):
            parent = '  日期：旧；作者：甲😀  ' + ending
            edits = output(replace_line(parent, parent.replace('旧', '新')),
                           replace_line(parent, parent.replace('甲', '乙')))
            for flags in itertools.product((False, True), repeat=2):
                expected = parent.replace('旧', '新') if flags[0] else parent
                if flags[1]: expected = expected.replace('甲', '乙')
                ids = [f'u{i}' for i, flag in enumerate(flags, 1) if flag]
                selected = e.construct_selected(edits, payload(parent, 2), ids)
                self.assertEqual(selected['selected_text'], expected)
                self.assertEqual(selected['actual_diff'], actual_diff(parent, expected))

    def test_inline_newline_change_still_checks_subset_eof(self):
        parent = 'ab\nTail\n'
        edits = output(replace_line('ab\n', 'ab'), replace_line('ab\n', 'aB\n'), diff('-Tail\n'))
        view = payload(parent, 3)
        self.assertEqual(e.construct_candidate(edits, view)['candidate_text'], 'aB')
        self.assertEqual(e.construct_selected(edits, view, ['u1', 'u3'])['selected_text'], 'ab')
        self.assertEqual(e.construct_selected(edits, view, ['u2'])['selected_text'], 'aB\nTail\n')
        with self.assertRaisesRegex(ValueError, 'Selected Skill EOF'):
            e.construct_selected(edits, view, ['u1', 'u2'])

    def test_null_stop_still_validates_inline_conflicts(self):
        parent = 'abcd\n'
        view = payload(parent, 3)
        valid = output(replace_line(parent, 'aBcd\n'), replace_line(parent, 'abcD\n'), None)
        self.assertEqual(e.construct_candidate(valid, view)['editor_status'], 'needs_revision')
        for invalid in (output(replace_line(parent, 'aBcd\n'), replace_line(parent, 'aXcd\n'), None),
                        output(replace_line(parent, 'abbcd\n'), replace_line(parent, 'abcD\n'), None)):
            with self.assertRaises(ValueError): e.construct_candidate(invalid, view)

    def test_exhaustive_disjoint_character_operations_match_manual_composition(self):
        parent = 'abcd\n'
        for positions in itertools.permutations(range(4), 2):
            for operations in itertools.product(('insert', 'delete', 'replace'), repeat=2):
                patches, expected = [], list(parent)
                for pos, operation, token in zip(positions, operations, ('X', 'Y')):
                    value = token + parent[pos] if operation == 'insert' else '' if operation == 'delete' else token
                    changed = parent[:pos] + value + parent[pos + 1:]
                    patches.append(replace_line(parent, changed))
                    expected[pos] = value
                    self.assertEqual(old_apply_patch(parent, patches[-1]), changed)
                edits, view = output(*patches), payload(parent, 2)
                with self.subTest(positions=positions, operations=operations):
                    self.assertEqual(e.construct_candidate(edits, view)['candidate_text'], ''.join(expected))
                    self.assertEqual(e.construct_selected(edits, view, ['u2', 'u1'])['selected_text'], ''.join(expected))
                    for index in range(2):
                        self.assertEqual(e.construct_selected(edits, view, [f'u{index + 1}'])['selected_text'],
                                         old_apply_patch(parent, patches[index]))
                    self.assertEqual(e.construct_selected(edits, view, [])['selected_text'], parent)


class SubsetCompositionTests(unittest.TestCase):
    def setUp(self):
        offline(self)

    def test_every_subset_uses_original_context_and_stable_same_gap_order(self):
        parent = '# Answer Format\nA\nB\n'
        edits = output(diff(' # Answer Format\n A\n+Date.\n B\n'),
                       diff(' # Answer Format\n A\n+Author.\n B\n'),
                       diff(' # Answer Format\n A\n-B\n+b\n'))
        edits['edits'].reverse()
        view = payload(parent, 3)
        before = deepcopy((edits, view))
        for flags in itertools.product((False, True), repeat=3):
            ids = [f'u{i}' for i, flag in enumerate(flags, 1) if flag]
            expected = ('# Answer Format\nA\n' + ('Date.\n' if flags[0] else '') +
                        ('Author.\n' if flags[1] else '') + ('b\n' if flags[2] else 'B\n'))
            for requested in itertools.permutations(ids):
                with self.subTest(ids=requested):
                    result = e.construct_selected(edits, view, list(requested))
                    self.assertEqual(result, {'selected_update_ids': ids, 'selected_text': expected,
                                              'actual_diff': actual_diff(parent, expected)})
        self.assertEqual((edits, view), before)
        full = e.construct_candidate(edits, view)
        self.assertEqual(e.construct_selected(edits, view, ['u3', 'u1', 'u2'])['selected_text'],
                         full['candidate_text'])

    def test_single_selected_patch_keeps_all_its_hunks(self):
        parent = 'A\nB\nC\nD\n'
        edits = output(diff('-A\n+a\n B\n@@\n C\n-D\n+d\n'), diff(' A\n-B\n+b\n C\n'))
        view = payload(parent, 2)
        self.assertEqual(e.construct_selected(edits, view, ['u1'])['selected_text'], 'a\nB\nC\nd\n')
        self.assertEqual(e.construct_selected(edits, view, ['u2'])['selected_text'], 'A\nb\nC\nD\n')

    def test_empty_selection_or_only_empty_patch_preserves_exact_parent(self):
        for parent in (None, '', 'A', 'A\r\n'):
            view = payload(parent, 2)
            for ids in ([], ['u2'], ['u2', 'u1']):
                with self.subTest(parent=parent, ids=ids):
                    selected = e.construct_selected(output('', ''), view, ids)
                    self.assertEqual(selected['selected_text'], parent)
                    self.assertEqual(selected['actual_diff'], '')
        edits = output(diff(' A\n+New rule.\n'), '')
        for ids in ([], ['u2']):
            self.assertEqual(e.construct_selected(edits, payload('A\n', 2), ids)['selected_text'], 'A\n')
        created = output(diff('+Rule.\n', create=True))
        self.assertIsNone(e.construct_selected(created, payload(None), [])['selected_text'])

    def test_empty_subset_result_rejected_despite_valid_full_candidate(self):
        edits, view = output(diff('-A\n'), diff('+Z\n A\n')), payload('A\n', 2)
        self.assertEqual(e.construct_candidate(edits, view)['candidate_text'], 'Z\n')
        with self.assertRaisesRegex(ValueError, 'empty Skill'):
            e.construct_selected(edits, view, ['u1'])
        self.assertEqual(e.construct_selected(edits, view, [])['selected_text'], 'A\n')
        self.assertEqual(e.construct_selected(edits, view, ['u2'])['selected_text'], 'Z\nA\n')

    def test_subset_eof_is_rechecked_not_inherited_from_full_candidate(self):
        edits = output(diff('-A\n+X\n' + NO_NEWLINE + '\n'), diff('-B\n'))
        view = payload('A\nB\n', 2)
        self.assertEqual(e.construct_candidate(edits, view)['candidate_text'], 'X')
        with self.assertRaisesRegex(ValueError, 'Selected Skill EOF'):
            e.construct_selected(edits, view, ['u1'])
        self.assertEqual(e.construct_selected(edits, view, ['u2'])['selected_text'], 'A\n')

    def test_valid_subset_can_cancel_to_parent_without_silent_fallback(self):
        edits = output(diff('-A\n'), diff('+A\n A\n'), diff('+B\n A\n'))
        view = payload('A\n', 3)
        self.assertEqual(e.construct_candidate(edits, view)['candidate_text'], 'A\nB\n')
        self.assertEqual(e.construct_selected(edits, view, ['u2', 'u1']), {
            'selected_update_ids': ['u1', 'u2'], 'selected_text': 'A\n', 'actual_diff': ''})

    def test_selection_requires_unique_known_ids(self):
        edits, view = output(diff('-A\n+a\n'), ''), payload('A\n', 2)
        for ids in (None, 'u1', {'u1'}, ('u1',), ['u1', 'u1'], ['unknown'], [None], [[]], [True]):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                e.construct_selected(edits, view, ids)

    def test_selection_cannot_bypass_null_or_invalid_unselected_patch(self):
        view = payload('A\n', 2)
        for edits in (output(diff('-A\n+a\n'), None), output(diff('-A\n+a\n'), 'bad diff'),
                      output(diff('-A\n+a\n'), diff('-A\n+b\n')), output('')):
            for ids in ([], ['u1']):
                with self.subTest(edits=edits, ids=ids), self.assertRaises(ValueError):
                    e.construct_selected(edits, view, ids)


class EditorTests(MethodBase):
    def setUp(self):
        super().setUp()
        offline(self)
        self.method = CampaignAdapter(self.adapter)
        self.enterContext(self.method.using())
        self.grouped = old_modules.grouping_call(self.parent(), 'R01').complete(main_example('grouping'))
        diagnosed = d.diagnosis_call(self.grouped).complete(proposal())
        self.saved = p.preconditioner_call(diagnosed, memory_view()).complete(decisions())
        self.payload = e.editor_input(self.saved)
        # One contextual addition, grounded in the synthetic Original requirement.
        self.patch = diff(''.join(' ' + line for line in self.skill.splitlines(keepends=True)) +
                          '+- For a total question, select the requested total rather than a subtotal.\n')

    def test_versioned_call_projects_only_verified_parent_and_id_text(self):
        call = e.editor_call(self.saved)
        self.assertEqual((call.name, call.prompt_version, call.contract_version),
                         ('editor', e.PROMPT_VERSION, e.CONTRACT_VERSION))
        self.assertEqual(json.loads(call.messages[1]['content']), self.payload)
        self.assertEqual(set(self.payload), {'parent', 'plan'})
        self.assertEqual(self.payload['plan']['updates'], [
            {key: value for key, value in u.items() if key != 'basis'}
            for u in self.saved['effective_plan']['updates']])
        parsed = output(self.patch)
        result = call.complete_text(json.dumps(parsed))
        self.assertEqual(result['editor'], parsed)
        self.assertEqual(result['candidate_text'], old_apply_patch(self.skill, self.patch))
        self.assertEqual(result['editor_status'], 'candidate')
        self.assertEqual(len(self.transport.seen), 2)  # Only synthetic Parent fixture calls.

    def test_upstream_sensitive_fields_are_not_projected(self):
        saved = deepcopy(self.saved)
        saved['preconditioner']['adjustments'][0]['reason'] += ' PRIVATE_REASON'
        saved['memory']['rounds'][0]['entries'][0]['knowledge']['text'] += ' PRIVATE_MEMORY'
        saved['update_diffs'] = {'u1': 'PRIVATE_AUDIT_DIFF'}
        body = e.editor_call(saved).messages[1]['content']
        for forbidden in ('PRIVATE_REASON', 'PRIVATE_MEMORY', 'PRIVATE_AUDIT_DIFF', HIDDEN,
                          '"basis"', '"checks"', '"runs"', '"memory"', 'reference_answers',
                          'reasoning_content', 'image_url', 'data:image'):
            self.assertNotIn(forbidden, body)

    def test_upstream_effective_plan_and_decisions_are_recompiled(self):
        for change in ('goal', 'text', 'id', 'basis', 'action', 'missing'):
            saved = deepcopy(self.saved)
            if change == 'goal': saved['effective_plan']['goal'] = 'changed'
            elif change in ('text', 'id', 'basis'): saved['effective_plan']['updates'][0][change] = 'changed'
            elif change == 'action': saved['preconditioner']['adjustments'][0]['action'] = 'WITHDRAW'
            else: del saved['preconditioner']
            with self.subTest(change=change), self.assertRaises(ValueError):
                e.editor_call(saved)

    def test_withdrawn_updates_and_adjustment_reasons_do_not_reach_editor(self):
        value = proposal()
        value['plan']['updates'] = [{**deepcopy(value['plan']['updates'][0]), 'id': f'u{i}'}
                                   for i in range(1, 4)]
        saved = d.diagnosis_call(self.grouped).complete(value)
        prepared = p.preconditioner_call(saved, memory_view()).complete(decisions('KEEP', 'REPLACE', 'WITHDRAW'))
        view = e.editor_input(prepared)
        self.assertEqual([u['id'] for u in view['plan']['updates']], ['u1', 'u2'])
        self.assertEqual(view['plan']['updates'][1]['text'], prepared['effective_plan']['updates'][1]['text'])
        with self.assertRaises(ValueError):
            e.editor_call(prepared).complete(output('', '', ''))

    def test_all_withdraw_and_legacy_preconditioner_are_rejected(self):
        diagnosed = d.diagnosis_call(self.grouped).complete(proposal())
        withdrawn = p.preconditioner_call(diagnosed, memory_view()).complete(decisions('WITHDRAW'))
        legacy_diagnosed = old_modules.diagnosis_call(self.grouped).complete(main_example('diagnosis'))
        legacy = old_modules.preconditioner_call(legacy_diagnosed, old_memory.empty_memory()).complete(main_example('preconditioner'))
        for saved in (withdrawn, legacy):
            with self.subTest(saved=saved['effective_plan']), self.assertRaises(ValueError):
                e.editor_call(saved)

    def test_exact_input_projection_is_required_at_validation(self):
        for change in ('parent', 'goal', 'text', 'basis'):
            bad = deepcopy(self.payload)
            if change == 'parent': bad['parent'] = 'forged'
            elif change == 'goal': bad['plan']['goal'] = 'forged'
            else: bad['plan']['updates'][0][change] = 'forged'
            with self.subTest(change=change), self.assertRaises(ValueError):
                e.validate_editor(output(''), bad, saved=self.saved)
        self.assertEqual(e.validate_editor(output(''), self.payload, saved=self.saved)['editor_status'], 'no_change')

    def test_completion_rechecks_registered_archives(self):
        call = e.editor_call(self.saved)
        path = self.parent_dir / 'actor/0001/trajectory.json'
        record = read(path)
        record['execution']['content'] = 'changed after preparation'
        save(path, record)
        with self.assertRaises(ValueError):
            call.complete(output(self.patch))

    def test_archive_backed_selection_reuses_exact_editor_result_without_execution(self):
        saved = e.editor_call(self.saved).complete(output(self.patch))
        before = deepcopy(saved)
        seen = len(self.transport.seen)
        files = {str(path): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        with patch.object(e, 'render_prompt', side_effect=AssertionError('Selection does not call Editor')):
            selected = e.select_skill(saved, ['u1'])
            parent = e.select_skill(saved, [])
        self.assertEqual(selected, {'selected_update_ids': ['u1'], 'selected_text': saved['candidate_text'],
                                    'actual_diff': saved['actual_diff']})
        self.assertEqual(parent, {'selected_update_ids': [], 'selected_text': self.skill, 'actual_diff': ''})
        self.assertEqual(saved, before)
        self.assertEqual(len(self.transport.seen), seen)
        self.assertEqual(files, {str(path): path.read_bytes() for path in self.root.rglob('*') if path.is_file()})
        selected['selected_update_ids'].clear()
        self.assertEqual(e.select_skill(saved, ['u1'])['selected_update_ids'], ['u1'])

    def test_archive_backed_selection_rejects_changed_handoff_even_for_empty_selection(self):
        original = e.editor_call(self.saved).complete(output(self.patch))
        for field in ('candidate_text', 'actual_diff', 'editor_status', 'editor'):
            bad = deepcopy(original)
            if field == 'editor': bad[field]['edits'][0]['patch'] = ''
            else: bad[field] = 'forged'
            with self.subTest(field=field), self.assertRaises(ValueError):
                e.select_skill(bad, [])
        for value in ('', None):
            saved = e.editor_call(self.saved).complete(output(value))
            if value is None:
                with self.assertRaises(ValueError): e.select_skill(saved, [])
            else:
                self.assertEqual(e.select_skill(saved, [])['selected_text'], self.skill)

    def test_archive_backed_selection_rechecks_parent_execution_sources(self):
        saved = e.editor_call(self.saved).complete(output(self.patch))
        path = self.parent_dir / 'actor/0001/trajectory.json'
        record = read(path)
        record['execution']['content'] = 'changed after construction'
        save(path, record)
        with self.assertRaises(ValueError):
            e.select_skill(saved, [])

    def test_frozen_inputs_and_detached_results(self):
        saved, parsed = deepcopy(self.saved), output(self.patch)
        call = e.editor_call(saved)
        saved['effective_plan']['updates'][0]['text'] = 'caller changed'
        call.input['facts']['parent'] = 'public copy changed'
        call.messages[1]['content'] = '{}'
        result = call.complete(parsed)
        parsed['edits'][0]['patch'] = None
        self.assertEqual(result['editor'], output(self.patch))
        result['editor']['edits'][0]['patch'] = ''
        result['effective_plan']['updates'].clear()
        again = call.complete(output(self.patch))
        self.assertEqual(again['effective_plan'], self.saved['effective_plan'])
        self.assertEqual(again['candidate_text'], old_apply_patch(self.skill, self.patch))

    def test_semantic_stop_and_no_change_preserve_raw_mapping_and_memory(self):
        call = e.editor_call(self.saved)
        for value, status in (('', 'no_change'), (None, 'needs_revision')):
            result = call.complete(output(value))
            self.assertEqual(result['editor_status'], status)
            self.assertIsNone(result['candidate_text'])
            self.assertIsNone(result['actual_diff'])
            self.assertEqual(result['editor'], output(value))
            self.assertEqual(result['memory'], self.saved['memory'])

    def test_invalid_json_is_not_converted_to_null_or_empty_patch(self):
        call = e.editor_call(self.saved)
        for raw in ('', '[]', '{} trailing', '{"edits":[],"edits":[]}', '{"edits":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                call.complete_text(raw)

    def test_prompt_runtime_and_preserved_v29_1_editing_requirements(self):
        old = (FIVE / 'prompts/editor.md').read_text()
        prompt = e.render_prompt(protocol.actor_config())
        start, end = '## Agreed Actor protocol and runtime', '## Input and implementation scope'
        self.assertEqual(prompt.split(start)[1].split(end)[0], old.split(start)[1].split(end)[0])
        for requirement in ('Do not duplicate requirements already adequately supplied by Parent',
                            'Edit only Skill text, not base protocol', 'lack of image access alone is not a blocker',
                            'Any null stops construction', 'same original Parent', 'Effective Update order',
                            'not what another patch will add', 'other proposed edits do not invalidate',
                            'not establish independent behavioral effects',
                            'different rules in the same section or at adjacent original positions',
                            'They do not need separate sections or distinct locating context',
                            'character edits are uniquely located and non-overlapping',
                            'repeated text allows more than one insertion/deletion location',
                            'Multi-line blocks and whole-line deletions retain their original line ranges',
                            'valid full Candidate does not guarantee that every subset is valid'):
            self.assertIn(requirement, prompt)
        self.assertNotIn('plan has goal, updates and checks', prompt)
        self.assertNotIn('with exactly patch and reason', prompt)
        self.assertNotIn('Deleting or replacing the same original line twice is a conflict', prompt)
        example = json.loads(prompt.split('```json\n')[1].split('\n```')[0])
        self.assertEqual(e.construct_candidate(example, payload('Old guidance.\n'))['candidate_text'],
                         'Revised guidance.\n')

    def test_prompt_version_and_runtime_mismatch_are_rejected(self):
        self.assertEqual(e.PROMPT_VERSION, 'v29_2_docvqa_editor_v3')
        self.assertEqual(e.CONTRACT_VERSION, 'v29_2_editor_mapped_patches_v2')
        for version in ('v29_docvqa_editor_v1', 'v29_2_docvqa_editor_v1', 'v29_2_docvqa_editor_v2'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                e.render_prompt(protocol.actor_config(), prompt_version=version)
        changed = protocol.actor_config()
        changed['temperature'] = 0
        with self.assertRaises(ValueError):
            e.render_prompt(changed)

    def test_old_editor_prompt_and_schema_remain_unchanged(self):
        diagnosed = old_modules.diagnosis_call(self.grouped).complete(main_example('diagnosis'))
        prepared = old_modules.preconditioner_call(diagnosed, old_memory.empty_memory()).complete(main_example('preconditioner'))
        old = old_modules.editor_call(prepared)
        self.assertEqual(old.messages[0]['content'], (FIVE / 'prompts/editor.md').read_text())
        self.assertEqual(prompting.render('editor', protocol.actor_config()), old.messages[0]['content'])
        old.complete(main_example('editor'))
        with self.assertRaises(ValueError):
            old.complete(output(self.patch))
        with self.assertRaises(ValueError):
            e.editor_call(self.saved).complete(main_example('editor'))


if __name__ == '__main__':
    unittest.main()
