"""Offline contract tests. Synthetic replacements are NOT model Repair results."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.methods.v23_5.repair_001 import prepare as p, repair as r


class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p.verify_sources()
        cls.cases = {name: p.load_case(name) for name in p.io.ROUNDS}

    def setUp(self):
        original, verdicts, self.candidate, self.payload = deepcopy(self.cases['R01'])
        self.value = p.build_input(original, verdicts, self.candidate)
        self.result = {'changes': [{'target': deepcopy(self.value['targets'][0]['target']),
                                   'knowledge': deepcopy(self.value['targets'][0]['knowledge'])}]}
        self.result['changes'][0]['knowledge']['text'] = 'SYNTHETIC CONTRACT TEST ONLY; not an evaluated correction.'

    def test_real_target_selection(self):
        for name, expected, count in [('R01', 4, 9), ('R02', 2, 24), ('R03', 1, 36)]:
            original, verdicts, candidate, _ = self.cases[name]
            value = p.build_input(original, verdicts, candidate)
            self.assertEqual([t['target'] for t in value['targets']], [{'entry_index': 0, 'knowledge_index': expected}])
            self.assertEqual(len(value['source_records']), count)
            self.assertNotIn('reference_review', json.dumps(value))

    def test_issue_only_reference_included(self):
        original, verdicts, candidate, _ = deepcopy(self.cases['R01'])
        verdicts['results'][4]['issues'][0]['evidence'].append('P1:2')
        value = p.build_input(original, verdicts, candidate)
        self.assertIn('P1:2', value['source_records'])
        self.assertEqual(value['source_records']['P1:2'], original['source_records']['P1:2'])

    def test_exact_restore_all_real_selected_records(self):
        for original, verdicts, candidate, _ in self.cases.values():
            before = r.exact((original, verdicts, candidate))
            value = p.build_input(original, verdicts, candidate)
            restored = p.shared.restore({**value, 'targets': [{'knowledge': {'evidence': list(value['source_records'])}}]})
            full = p.shared.restore(original)
            for ref in value['source_records']:
                self.assertEqual(r.exact(restored['source_records'][ref]), r.exact(full['source_records'][ref]))
            self.assertEqual(before, r.exact((original, verdicts, candidate)))

    def test_missing_shared_menu_rejected(self):
        original, verdicts, candidate, _ = deepcopy(self.cases['R01'])
        del original['command_sets'][original['source_records']['Q5:49']['command_set_refs'][
            next(iter(original['source_records']['Q5:49']['command_set_refs']))]]
        with self.assertRaises(ValueError):
            p.build_input(original, verdicts, candidate)

    def test_candidate_binding(self):
        original, verdicts, candidate, _ = deepcopy(self.cases['R01'])
        candidate['entries'][0]['knowledge'][4]['text'] += ' changed'
        with self.assertRaises(ValueError):
            p.build_input(original, verdicts, candidate)
        with self.assertRaises(ValueError):
            r.merge(self.result, self.value, candidate, self.payload)

    def test_no_conflicts_no_changes(self):
        original, verdicts, candidate, payload = deepcopy(self.cases['R01'])
        for row in verdicts['results']:
            row.update(verdict='SUPPORTED', issues=[])
        value = p.build_input(original, verdicts, candidate)
        self.assertEqual(value['targets'], [])
        self.assertEqual(value['source_records'], {})
        self.assertEqual(r.merge({'changes': []}, value, candidate, payload), candidate)

    def test_replacement_preserves_others_and_inputs(self):
        before = r.exact((self.result, self.value, self.candidate, self.payload))
        merged = r.merge(self.result, self.value, self.candidate, self.payload)
        self.assertEqual(merged['entries'][0]['knowledge'][:4], self.candidate['entries'][0]['knowledge'][:4])
        self.assertEqual(merged['entries'][0]['revises'], self.candidate['entries'][0]['revises'])
        self.assertEqual(before, r.exact((self.result, self.value, self.candidate, self.payload)))
        merged['entries'][0]['knowledge'][0]['text'] = 'detached'
        self.assertEqual(before, r.exact((self.result, self.value, self.candidate, self.payload)))

    def test_null_deletion(self):
        self.result['changes'][0]['knowledge'] = None
        merged = r.merge(self.result, self.value, self.candidate, self.payload)
        self.assertEqual(merged['entries'][0]['knowledge'], self.candidate['entries'][0]['knowledge'][:4])

    def test_original_indices_after_deletion_and_output_order(self):
        # Test-only expanded authorization, never used by the real input builder.
        self.value['targets'] = [{'target': {'entry_index': 0, 'knowledge_index': i},
                                 'knowledge': deepcopy(k)} for i, k in enumerate(self.candidate['entries'][0]['knowledge'])]
        self.value['source_records'] = deepcopy(self.cases['R01'][0]['source_records'])
        changes = [{'target': t['target'], 'knowledge': None if i in (0, 2) else
                    {**deepcopy(t['knowledge']), 'text': f'SYNTHETIC {i}'}}
                   for i, t in enumerate(self.value['targets'])]
        merged = r.merge({'changes': list(reversed(changes))}, self.value, self.candidate, self.payload)
        self.assertEqual([k['text'] for k in merged['entries'][0]['knowledge']], ['SYNTHETIC 1', 'SYNTHETIC 3', 'SYNTHETIC 4'])

    def test_last_item_deletion_blocked(self):
        self.candidate['entries'][0]['knowledge'] = [self.candidate['entries'][0]['knowledge'][4]]
        self.value['targets'][0]['target']['knowledge_index'] = 0
        self.result['changes'][0] = {'target': {'entry_index': 0, 'knowledge_index': 0}, 'knowledge': None}
        with self.assertRaisesRegex(ValueError, 'nonempty array'):
            r.merge(self.result, self.value, self.candidate, self.payload)

    def test_deleting_only_diff_holder_blocked(self):
        for k in self.candidate['entries'][0]['knowledge'][:4]:
            k['evidence'].remove('diff')
        self.result['changes'][0]['knowledge'] = None
        with self.assertRaisesRegex(ValueError, 'edit and execution'):
            r.merge(self.result, self.value, self.candidate, self.payload)

    def test_revision_metadata_and_retained_history(self):
        _, _, candidate, payload = deepcopy(self.cases['R02'])
        old = payload['memory']['entries'][0]
        entry = candidate['entries'][0]
        entry['revises'] = [old['id']]
        entry['knowledge'] = deepcopy(old['knowledge']) + entry['knowledge']
        index = len(entry['knowledge']) - 1
        value = {'targets': [{'target': {'entry_index': 0, 'knowledge_index': index},
                              'knowledge': deepcopy(entry['knowledge'][index])}],
                 'source_records': self.cases['R02'][0]['source_records']}
        result = {'changes': [{'target': value['targets'][0]['target'], 'knowledge': None}]}
        merged = r.merge(result, value, candidate, payload)
        self.assertEqual(merged['entries'][0]['knowledge'], entry['knowledge'][:-1])
        self.assertEqual(merged['entries'][0]['revises'], [old['id']])

    def test_unrelated_entries_preserved(self):
        self.candidate['entries'].append(deepcopy(self.candidate['entries'][0]))
        merged = r.merge(self.result, self.value, self.candidate, self.payload)
        self.assertEqual(merged['entries'][1], self.candidate['entries'][1])

    def test_formal_reference_validation_still_applies(self):
        self.value['source_records']['unknown:1'] = {}
        self.result['changes'][0]['knowledge']['evidence'].append('unknown:1')
        r.validate_result(self.result, self.value)
        with self.assertRaises(ValueError):
            r.merge(self.result, self.value, self.candidate, self.payload)

    def test_historical_permissions_not_bypassed(self):
        _, _, candidate, payload = deepcopy(self.cases['R02'])
        original = self.cases['R02'][0]
        value = p.build_input(original, self.cases['R02'][1], candidate)
        # Full archive has run steps not exposed in Knowledge Only history.
        allowed = {ref for e in payload['memory']['entries'] for k in e['knowledge'] for ref in k['evidence']}
        hidden = next(f'{ref}:{step["step"].split(":")[1]}' for ref, source in payload['memory']['sources'].items()
                      if 'run' in source for step in source['run']['steps']
                      if f'{ref}:{step["step"].split(":")[1]}' not in allowed)
        value['source_records'][hidden] = {}
        k = deepcopy(value['targets'][0]['knowledge'])
        k['text'] = 'SYNTHETIC'
        k['evidence'].append(hidden)
        result = {'changes': [{'target': value['targets'][0]['target'], 'knowledge': k}]}
        with self.assertRaisesRegex(ValueError, 'Unavailable historical reference'):
            r.merge(result, value, candidate, payload)

    def test_missing_duplicate_and_unauthorized_targets(self):
        bads = [{'changes': []}, {'changes': self.result['changes'] * 2}]
        bad = deepcopy(self.result)
        bad['changes'][0]['target']['knowledge_index'] = 3
        bads.append(bad)
        for result in bads:
            with self.subTest(result=result), self.assertRaises(ValueError):
                r.validate_result(result, self.value)

    def test_position_types(self):
        for bad in (True, 4.0, -1, '4', None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.result['changes'][0]['target']['knowledge_index'] = bad
                r.validate_result(self.result, self.value)

    def test_empty_knowledge_is_only_null(self):
        for bad in ({}, '', [], {'text': '', 'evidence': ['diff']}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.result['changes'][0]['knowledge'] = bad
                r.validate_result(self.result, self.value)

    def test_bad_evidence(self):
        for bad in ([], ['diff', 'diff'], ['CS1'], ['Q5:999'], [None], [{}], 'diff'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.result['changes'][0]['knowledge']['evidence'] = bad
                r.validate_result(self.result, self.value)

    def test_noop_and_extra_fields_rejected(self):
        bads = []
        noop = deepcopy(self.result)
        noop['changes'][0]['knowledge'] = self.value['targets'][0]['knowledge']
        bads.append(noop)
        extra = deepcopy(self.result)
        extra['changes'][0]['operation'] = 'replace'
        bads.append(extra)
        for bad in bads:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                r.validate_result(bad, self.value)

    def test_strict_response_and_truncation(self):
        content = json.dumps(self.result)
        self.assertEqual(r.validate_response({'finish_reason': 'stop', 'content': content}, self.value), self.result)
        for bad in ('```json\n'+content+'\n```', content+' trailing', '{"changes":[],"changes":[]}',
                    '{"changes":NaN}', ''):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                r.validate_response({'finish_reason': 'stop', 'content': bad}, self.value)
        with self.assertRaises(ValueError):
            r.validate_response({'finish_reason': 'length', 'content': content}, self.value)

    def test_saved_failure_does_not_emit_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(p, 'verify', side_effect=ValueError('tampered package')):
                report = p.validate_saved(root, 'R01', root/'response.json', root/'failed')
            self.assertFalse(report['valid'])
            self.assertTrue((root/'failed/validation.json').exists())
            self.assertFalse((root/'failed/merged_candidate.json').exists())

    def test_package_saved_validation_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root/'package'
            self.assertTrue(p.prepare(package)['valid'])
            for name in p.io.ROUNDS:
                value = p.io.read(package/'cases'/name/'repair_input.json')
                target = value['targets'][0]
                result = {'changes': [{'target': target['target'], 'knowledge': {
                    **deepcopy(target['knowledge']), 'text': 'SYNTHETIC CONTRACT TEST ONLY'}}]}
                response = root/f'{name}.json'
                p.io.save(response, {'finish_reason': 'stop', 'content': json.dumps(result)})
                report = p.validate_saved(package, name, response, root/name)
                self.assertTrue(report['valid'])
                self.assertFalse(report['semantic_truth_verified'])
                candidate = p.io.read(package/'cases'/name/'candidate.json')
                merged = p.io.read(root/name/'merged_candidate.json')
                index = target['target']['knowledge_index']
                expected = deepcopy(candidate)
                expected['entries'][0]['knowledge'][index] = result['changes'][0]['knowledge']
                self.assertEqual(merged, expected)
            # Real CLI helper must persist failure but no final candidate on length.
            p.io.save(root/'length.json', {'finish_reason': 'length', 'content': '{}'})
            report = p.validate_saved(package, 'R01', root/'length.json', root/'length')
            self.assertFalse(report['valid'])
            self.assertFalse((root/'length/merged_candidate.json').exists())
            with self.assertRaises(ValueError):
                p.prepare(package)
            with self.assertRaises(ValueError):
                p.validate_saved(package, 'R01', root/'length.json', root/'length')
            path = package/'cases/R01/repair_input.json'
            value = p.io.read(path)
            value['source_records']['Q5:49']['record']['action'] = 'SYNTHETIC TAMPER'
            p.io.save(path, value)
            with self.assertRaisesRegex(ValueError, 'Frozen Repair file changed'):
                p.verify(package)


if __name__ == '__main__':
    unittest.main()
