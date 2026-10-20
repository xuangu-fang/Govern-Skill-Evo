"""Offline representation tests, not tests of LLM understanding or ALFWorld validity."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from views import (compact, editor_role_view, history_cards, lossless_pack,
                   lossless_unpack, sha, walk)
import capacity

ROOT = Path(__file__).resolve().parents[5]
ART = ROOT / 'artifacts/methods/v22'


class LosslessViewTests(unittest.TestCase):
    def assert_roundtrip(self, original):
        before = deepcopy(original)
        packed = lossless_pack(original)
        restored = lossless_unpack(packed)
        self.assertEqual(restored, original)
        self.assertEqual(original, before, 'Input must never be mutated')
        # Sorting keys tests exact JSON types/values, including null, as well as structure.
        self.assertEqual(json.dumps(restored, sort_keys=True, ensure_ascii=False),
                         json.dumps(original, sort_keys=True, ensure_ascii=False))
        return packed, restored

    def test_nine_actual_08_messages_roundtrip(self):
        roots = [(capacity.R1, ['classification', 'diagnosis', 'main_editor', 'post_gate_learning']),
                 (capacity.D, capacity.STAGES)]
        for root, stages in roots:
            for stage in stages:
                with self.subTest(round=root.name, stage=stage):
                    messages = json.loads((root / 'messages' / (stage + '.json')).read_text())
                    view = json.loads(messages[-1]['content'])
                    self.assert_roundtrip(view)

    def test_five_counterfactual_v3_views_roundtrip(self):
        for stage in capacity.STAGES:
            with self.subTest(stage=stage):
                view = capacity.view_for(stage, capacity.BASE[stage])
                self.assert_roundtrip(view)

    def test_missing_and_null_are_distinct_after_table_factoring(self):
        rows = [{'very_long_repeated_field_name': i, 'other_long_repeated_field_name': None,
                 'sometimes_missing_field_name': None} if i % 2 else
                {'very_long_repeated_field_name': i, 'other_long_repeated_field_name': None}
                for i in range(12)]
        packed, restored = self.assert_roundtrip({'steps': rows})
        self.assertTrue(any(isinstance(x, dict) and '@table' in x for x in walk(packed)))
        self.assertNotIn('sometimes_missing_field_name', restored['steps'][0])
        self.assertIsNone(restored['steps'][1]['sometimes_missing_field_name'])

    def test_event_source_rule_only_for_exact_complete_mapping(self):
        base = {'runs': {'P1': {'steps': [{'step': 2}, {'step': 7}]}},
                'sources': {'P1:0': {'kind': 'event', 'run': 'P1', 'step': 0},
                            'P1:2': {'kind': 'event', 'run': 'P1', 'step': 2},
                            'P1:7': {'kind': 'event', 'run': 'P1', 'step': 7},
                            'capabilities': {'kind': 'capabilities'}}}
        self.assertTrue(self.assert_roundtrip(base)[0]['event_source_rule'])
        missing = deepcopy(base); del missing['sources']['P1:7']
        self.assertFalse(self.assert_roundtrip(missing)[0]['event_source_rule'])
        extra = deepcopy(base); extra['sources']['P1:7']['side'] = 'parent'
        self.assertFalse(self.assert_roundtrip(extra)[0]['event_source_rule'])
        wrong = deepcopy(base); wrong['sources']['P1:7']['run'] = 'C1'
        self.assertFalse(self.assert_roundtrip(wrong)[0]['event_source_rule'])

    def test_same_text_is_not_same_parent_candidate_event(self):
        observation = 'The identical visible observation remains here, but paths differ.'
        view = {'runs': {'P1': {'run_id': 'parent-run', 'steps': [{'step': 1, 'observation': observation, 'action': 'look'}]},
                         'C1': {'run_id': 'candidate-run', 'steps': [{'step': 4, 'observation': observation, 'action': 'open'}]}},
                'pairs': [{'parent': 'P1', 'candidate': 'C1'}]}
        packed, restored = self.assert_roundtrip(view)
        self.assertIn(observation, packed['text_pool'])
        self.assertEqual(list(restored['runs']), ['P1', 'C1'])
        self.assertEqual(restored['runs']['P1']['steps'][0]['step'], 1)
        self.assertEqual(restored['runs']['C1']['steps'][0]['step'], 4)
        self.assertNotEqual(restored['runs']['P1']['run_id'], restored['runs']['C1']['run_id'])

    def test_reserved_reference_syntax_rejected_instead_of_interpreted(self):
        for reserved in ('@text', '@object', '@missing', '@table', '@concat'):
            with self.subTest(reserved=reserved), self.assertRaises(AssertionError):
                lossless_pack({'literal_input': {reserved: 0}})

    def test_observation_fragments_preserve_exact_whitespace_and_punctuation(self):
        shared = 'Repeated literal observation with enough characters for fragment reuse.'
        observations = [shared + '  Two spaces!\tTab follows?\r\nCRLF remains.\n\nBlank line. 中文。',
                        shared + '\nOne newline; then unique detail.',
                        '  Leading spaces.\n' + shared + ' Trailing spaces   ']
        view = {'runs': {'P1': {'initial_observation': observations[0],
                                'steps': [{'step': i, 'observation': text,
                                           'observation_before': observations[0]}
                                          for i, text in enumerate(observations, 1)]}}}
        packed, restored = self.assert_roundtrip(view)
        self.assertTrue(any(isinstance(x, dict) and '@concat' in x for x in walk(packed)))
        for expected, step in zip(observations, restored['runs']['P1']['steps']):
            self.assertEqual(step['observation'].encode('utf-8'), expected.encode('utf-8'))
        self.assertEqual(restored['runs']['P1']['initial_observation'], observations[0])

    def test_command_atoms_preserve_menu_order_multiplicity_and_short_commands(self):
        first, second = 'navigate to a distinct candidate', 'inspect the available container'
        view = {'command_sets': {'forward': [first, second, 'look', '3', first],
                                 'reverse': [second, first, '3', 'look'], 'empty': []},
                'runs': {'P1': {'initial_commands': 'forward', 'steps': []},
                         'C1': {'initial_commands': 'reverse', 'steps': []}}}
        packed, restored = self.assert_roundtrip(view)
        self.assertEqual(packed['command_pool'], [first, second])
        self.assertNotEqual(restored['command_sets']['forward'], restored['command_sets']['reverse'])
        self.assertEqual(restored['command_sets']['forward'].count(first), 2)
        self.assertEqual(restored['command_sets']['reverse'][2], '3')
        self.assertEqual(restored['command_sets']['empty'], [])

    def test_real_learning_path_events_commands_and_history_survive(self):
        original = capacity.view_for('post_gate_learning', capacity.BASE['post_gate_learning'])
        packed, restored = self.assert_roundtrip(original)
        self.assertTrue(packed['event_source_rule'])
        self.assertEqual(len(restored['runs']), 20)
        for alias, run in restored['runs'].items():
            self.assertIn(run['initial_commands'], restored['command_sets'])
            for event in run['steps']:
                self.assertEqual(restored['sources'][f"{alias}:{event['step']}"],
                                 {'kind': 'event', 'run': alias, 'step': event['step']})
                self.assertIn(event['commands'], restored['command_sets'])
        for effect in restored['memory']:
            for basis in effect['basis']:
                self.assertIn(basis['actual_update_ref'], restored['historical_updates'])
                for ref in basis['sources']:
                    self.assertIn(ref, restored['historical_sources'])

    def test_counterevidence_and_unknown_limits_preserved_verbatim(self):
        view = {'memory': [{'id': 'm1', 'claim': 'SYNTHETIC: update helped when alternatives were visible.',
                            'limits': ['SYNTHETIC counterexample: repeated unchanged observations worsened looping.',
                                       'SYNTHETIC: a missing opportunity is untested, not evidence of failure.'],
                            'basis': [{'response': 'SYNTHETIC: joint response only; independent benefit unknown.'}]},
                           {'id': 'm2', 'claim': 'SYNTHETIC contradictory interpretation: under the same conditions the update worsened looping.',
                            'limits': ['SYNTHETIC contradiction unresolved.'], 'basis': []}]}
        self.assert_roundtrip(view)

    def test_editor_role_is_explicitly_incomplete_but_preserves_effective_plan(self):
        view = capacity.view_for('main_editor', capacity.BASE['main_editor'])
        before = deepcopy(view)
        role = editor_role_view(view)
        self.assertEqual(view, before)
        self.assertEqual(role['plan'], view['plan'])
        self.assertEqual(role['parent'], view['parent'])
        self.assertEqual(role['capabilities'], view['capabilities'])
        self.assertEqual(role['base_protocol'], view['base_protocol'])
        self.assertLess(sum(len(r['steps']) for r in role['runs'].values()),
                        sum(len(r['steps']) for r in view['runs'].values()))
        self.assertIn('not proof of absence', role['coverage']['omissions'])
        for req in role['plan']['requirements']:
            for ref in req['basis']:
                self.assertIn(ref, role['sources'])
        for run in role['runs'].values():
            self.assertTrue(run['coverage']['not_shown_does_not_mean_absent'])
        self.assert_roundtrip(role)

    def test_editor_explicit_effect_keeps_basis_context_and_all_limits(self):
        view = capacity.view_for('main_editor', capacity.BASE['main_editor'])
        effect = view['memory'][0]
        view['plan']['requirements'][0]['basis'].append(effect['id'])
        role = editor_role_view(view)
        self.assertEqual(role['memory'], [effect])
        for basis in effect['basis']:
            self.assertEqual(role['historical_updates'][basis['actual_update_ref']],
                             view['historical_updates'][basis['actual_update_ref']])
            for ref in basis['sources']:
                self.assertEqual(role['historical_sources'][ref], view['historical_sources'][ref])

    def test_history_cards_cannot_be_counted_as_historical_response_evidence(self):
        view = capacity.view_for('fusion', capacity.BASE['fusion'])
        cards = history_cards(view)
        for original, reduced in zip(view['memory'], cards['memory']):
            self.assertEqual(original['claim'], reduced['claim'])
            self.assertEqual(original['limits'], reduced['limits'])
            self.assertNotIn('basis', reduced)
            self.assertEqual(reduced['basis_archive_digest'], sha(original['basis']))
        self.assertNotIn('historical_updates', cards)
        self.assertNotIn('historical_sources', cards)
        self.assertIn('NOT available', cards['history_coverage']['raw_basis'])
        self.assertIn('Not sufficient alone', cards['history_coverage']['warning'])

    def test_synthetic_max_steps_are_capacity_only_not_real_executions(self):
        payload = capacity.scenario_payload('post_gate_learning', 12, 5, 'wide50', 'growing_effects')
        self.assertTrue(payload['synthetic_fixture']['not_executed'])
        self.assertEqual(len(payload['runs']), 24)
        self.assertTrue(all(len(run['steps']) == 50 for run in payload['runs'].values()))
        self.assertTrue(all(run['run_id'].startswith('synthetic:') for run in payload['runs'].values()))
        # This tests reversible fixture representation only; synthetic opportunities
        # cannot establish actual behavioral fidelity, classification, or causation.
        self.assert_roundtrip(capacity.view_for('post_gate_learning', payload))


if __name__ == '__main__':
    unittest.main(verbosity=2)
