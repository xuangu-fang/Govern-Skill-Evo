"""Lossless representation checks; no model inference or environment execution."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from src.skill_evolution.v22 import p1_input, contract_alignment
from src.skill_evolution.v22.grouped_update import grouped_messages
from src.skill_evolution.v22.grouped_representation import grouping_messages
from src.adapters.alfworld.skill_runtime import object_digest
from tests.skill_evolution.v22 import test_unified_dsc_mechanism as fixtures

ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / 'experiments/methods/v22/16_input_scalability').is_dir())
ART = ROOT / 'artifacts/methods/v22'


class P1InputTests(unittest.TestCase):
    def roundtrip(self, value):
        before = deepcopy(value)
        encoded = p1_input.encode(value)
        restored = p1_input.decode(encoded)
        self.assertEqual(value, before, 'Encoder must not mutate archived evidence')
        self.assertEqual(restored, value)
        self.assertEqual(json.dumps(restored, ensure_ascii=False, sort_keys=True),
                         json.dumps(value, ensure_ascii=False, sort_keys=True))
        return encoded, restored

    def test_all_nine_actual_08_stage_messages(self):
        paths = list((ART / '08_grouped_continual_live_20261015/rounds/r1/messages').glob('*.json'))
        paths += list((ART / '08_grouped_continual_fusion_resumed_20261015/rounds/r2/messages').glob('*.json'))
        self.assertEqual(len(paths), 9)
        for path in paths:
            with self.subTest(path=str(path)):
                original = json.loads(path.read_text())
                value = json.loads(original[1]['content'])
                self.roundtrip(value)
                encoded_messages = p1_input.encode_messages(original)
                self.assertEqual(p1_input.decode(json.loads(encoded_messages[1]['content'])), value)
                self.assertEqual(encoded_messages[0]['content'], original[0]['content']+'\n'+p1_input.INSTRUCTIONS)

    def test_all_seven_actual_09_probe_messages_and_input_payloads(self):
        cases = ART / '09_unified_dsc_model_validation_20261015/cases'
        messages = sorted(cases.glob('*/messages.json'))
        self.assertEqual(len(messages), 7)
        for path in messages:
            with self.subTest(case=path.parent.name):
                self.roundtrip(json.loads(json.loads(path.read_text())[1]['content']))
                self.roundtrip(json.loads((path.parent / 'payload.json').read_text()))

    def test_complete_event_sources_are_implicit_only_on_exact_mapping(self):
        value = {'runs': {'P1': {'steps': [{'step': 2}, {'step': 7}]}},
                 'sources': {'P1:0': {'kind': 'event', 'run': 'P1', 'step': 0},
                             'P1:2': {'kind': 'event', 'run': 'P1', 'step': 2},
                             'P1:7': {'kind': 'event', 'run': 'P1', 'step': 7},
                             'capabilities': {'kind': 'capabilities'}}}
        self.assertTrue(self.roundtrip(value)[0]['event_source_rule'])
        for mutation in ('missing', 'extra_metadata', 'wrong_side'):
            edited = deepcopy(value)
            if mutation == 'missing': del edited['sources']['P1:7']
            elif mutation == 'extra_metadata': edited['sources']['P1:7']['side'] = 'parent'
            else: edited['sources']['P1:7']['run'] = 'C1'
            self.assertFalse(self.roundtrip(edited)[0]['event_source_rule'])

    def test_missing_null_empty_false_and_zero_remain_distinct(self):
        rows = [{'step': i, 'long_repeated_observation_field': '',
                 'long_repeated_null_value_field': None, 'long_repeated_boolean_field': False,
                 'long_repeated_numeric_field': 0,
                 **({'only_sometimes_present_field': None} if i % 2 else {})}
                for i in range(20)]
        encoded, restored = self.roundtrip({'steps': rows})
        self.assertTrue(any(isinstance(x, dict) and '@table' in x for x in p1_input.walk(encoded)))
        self.assertNotIn('only_sometimes_present_field', restored['steps'][0])
        self.assertIsNone(restored['steps'][1]['only_sometimes_present_field'])

    def test_exact_observation_fragments_keep_spaces_unicode_and_line_endings(self):
        prefix = 'A repeated observation fragment longer than forty-eight characters remains unchanged.'
        values = [prefix+'  Double spaces!\tTab?\r\nCRLF.\n\n中文。', prefix+'\nOne newline.',
                  '  Leading spaces.\n'+prefix+' Trailing spaces   ']
        value = {'runs': {'P1': {'initial_observation': values[0],
                               'steps': [{'step': i, 'observation': obs, 'observation_before': values[0]}
                                         for i, obs in enumerate(values, 1)]}}}
        encoded, restored = self.roundtrip(value)
        self.assertTrue(any(isinstance(x, dict) and '@concat' in x for x in p1_input.walk(encoded)))
        for original, step in zip(values, restored['runs']['P1']['steps']):
            self.assertEqual(original.encode(), step['observation'].encode())

    def test_full_pre_action_menu_order_and_duplicates_survive(self):
        one, two = 'inspect a newly visible alternative', 'continue the permitted operation'
        value = {'command_sets': {'a': [one, two, 'look', '3', one],
                                  'b': [two, one, '3', 'look'], 'empty': []},
                 'runs': {'P1': {'initial_commands': 'a', 'steps': [{'step': 1, 'commands': 'b'}]},
                          'C1': {'initial_commands': 'b', 'steps': []}}}
        encoded, restored = self.roundtrip(value)
        self.assertEqual(encoded['command_pool'], [one, two])
        self.assertEqual(restored['command_sets']['a'].count(one), 2)
        self.assertEqual(restored['runs']['P1']['steps'][0]['commands'], 'b')

    def test_shared_text_never_merges_execution_side_step_or_result(self):
        text = 'The same observation is presented on independent execution paths.'
        value = {'runs': {'P1': {'run_id': 'parent', 'task_id': 'task', 'success': False,
                                'steps': [{'step': 1, 'observation': text, 'action': 'inspect'}]},
                          'C1': {'run_id': 'candidate', 'task_id': 'task', 'success': True,
                                'steps': [{'step': 4, 'observation': text, 'action': 'continue'}]}},
                 'pairs': [{'parent': 'P1', 'candidate': 'C1'}]}
        encoded, restored = self.roundtrip(value)
        self.assertIn(text, encoded['text_pool'])
        self.assertNotEqual(restored['runs']['P1']['run_id'], restored['runs']['C1']['run_id'])
        self.assertFalse(restored['runs']['P1']['success'])
        self.assertTrue(restored['runs']['C1']['success'])

    def test_literal_reserved_metadata_is_lossless_without_new_update_blocker(self):
        for name in ('@text', '@object', '@missing', '@table', '@concat'):
            with self.subTest(name=name):
                value = {'literal_metadata': {name: 0}, 'steps': [{'step': 1, 'observation': 'literal'}]}
                encoded, restored = self.roundtrip(value)
                self.assertTrue(encoded['literal'])
                self.assertEqual(encoded['evidence'], value)
                self.assertEqual(restored, value)
        self.assertNotIn('literal', self.roundtrip({'steps': [{'step': 1}]})[0])

    def test_history_claim_counterexample_unknown_joint_attribution_and_namespace(self):
        value = {'memory': [{'id': 'm1', 'claim': 'Update helped when a fresh alternative existed.',
                             'limits': ['Untested with no fresh alternative; absence is not failure.',
                                        'Counterexample: repeated observations worsened progress.'],
                             'basis': [{'actual_update_ref': 'historical:round1:update',
                                        'sources': ['historical:round1:P1:3'],
                                        'response': 'Joint response only; isolated contribution unknown.'}]},
                            {'id': 'm2', 'claim': 'Conflicting interpretation: continuation harmed progress.',
                             'limits': ['Conflict remains unresolved.'], 'basis': []}],
                 'historical_updates': {'historical:round1:update': {'diff': '+continue conditionally\n'}},
                 'historical_sources': {'historical:round1:P1:3': {'run_id': 'old-parent', 'step': 3}}}
        self.roundtrip(value)

    def test_malformed_encoded_table_does_not_silently_truncate(self):
        value = p1_input.encode({'steps': [{'long_repeated_column': i, 'second_long_column': None} for i in range(20)]})
        table = next(x for x in p1_input.walk(value) if isinstance(x, dict) and '@table' in x)
        table['rows'][0].append('unexpected')
        with self.assertRaises(ValueError): p1_input.decode(value)


class P1StageIntegrationTests(unittest.TestCase):
    setUp = fixtures.UnifiedDscMechanismTests.setUp
    record = fixtures.UnifiedDscMechanismTests.record
    batch = fixtures.UnifiedDscMechanismTests.batch
    inputs = fixtures.UnifiedDscMechanismTests.inputs
    edit = fixtures.UnifiedDscMechanismTests.edit
    round_fixture = fixtures.UnifiedDscMechanismTests.round_fixture

    def test_every_stage_uses_v3_behavior_with_only_version_and_codec_change(self):
        old = self.round_fixture(profile=contract_alignment.PROFILE)
        new = deepcopy(old)
        for key in ('current', 'update', 'payload'):
            new[key]['update_profile'] = p1_input.PROFILE
        new['payload']['binding_sha256'] = object_digest({key: value for key, value in new['payload'].items()
                                                         if key != 'binding_sha256'})
        for stage, key in [('diagnosis', 'current'), ('fusion', 'update'), ('editor', 'update'), ('learn', 'payload')]:
            with self.subTest(stage=stage):
                a = grouped_messages(stage, old[key]); b = grouped_messages(stage, new[key])
                self.assertEqual(b[0]['content'], a[0]['content'].replace(contract_alignment.PROFILE, p1_input.PROFILE)+'\n'+p1_input.INSTRUCTIONS)
                decoded = p1_input.decode(json.loads(b[1]['content']))
                expected = json.loads(a[1]['content'])
                expected['update_profile'] = p1_input.PROFILE
                if stage == 'learn': expected['binding_sha256'] = new[key]['binding_sha256']
                self.assertEqual(decoded, expected)
                self.assertNotIn(p1_input.VIEW_SCHEMA, a[1]['content'])
        payload = {'experiences': [{'task_ref': 'T1', 'steps': [{'step': 1, 'observation': 'visible'}]}]}
        a = grouping_messages(payload, self.prompt)
        b = grouping_messages(payload, self.prompt, profile=p1_input.PROFILE)
        self.assertEqual(p1_input.decode(json.loads(b[1]['content'])), payload)
        self.assertEqual(b[0]['content'], a[0]['content']+'\n'+p1_input.INSTRUCTIONS)


if __name__ == '__main__':
    unittest.main(verbosity=2)
