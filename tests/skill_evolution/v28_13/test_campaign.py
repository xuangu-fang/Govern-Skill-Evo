"""Synthetic end-to-end Gate, publication and recovery tests; no model service."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from scripts.runs import run_v28_13_campaign as cli
from src.skill_evolution.v27.unnumbered_patch import actual_diff
from src.skill_evolution.v28_13 import config, memory
from tests.skill_evolution.v28_5.support import Generator, bind


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('socket.socket.connect', side_effect=AssertionError('Offline only')))

    def test_net_threshold_is_independent_of_patch_length_and_legacy_flag(self):
        # Real synthetic Actor archives drive Replay and Gate; only the
        # authored generator/transport are fake, not Gate or publication.
        for count in (1, 2):
            for shorter in (False, True):
                for pure in (False, True):
                    with self.subTest(count=count, shorter=shorter, pure=pure), tempfile.TemporaryDirectory() as tmp:
                        root = Path(tmp)
                        data, transport, _, _ = bind(root / 'fixture', rounds=1, size=count, mode='gain')
                        adapter = cli.CampaignAdapter(cli.ActorAdapter(data, transport))
                        generator = Generator(count=1)

                        def generate(name, messages, directory, settings):
                            response = generator(name, messages, directory, settings)
                            value = json.loads(response['content'])
                            if name == 'preconditioner':
                                value['adjustments'][0]['pure_simplification'] = pure
                            if name == 'editor' and shorter:
                                parent = json.loads(messages[1]['content'])['parent']
                                value['edits'][0]['patch'] = re.sub(
                                    r'^@@[^\n]*@@$', '@@', actual_diff(parent, '# Skill\n- rule u1\n'), flags=re.M)
                            response['content'] = json.dumps(value)
                            return response

                        campaign = root / 'campaign'
                        with adapter.using():
                            settings = config.campaign_config(adapter)
                            summary = cli.run_training(campaign, settings, generate=generate)
                            receipt = json.loads((campaign / 'rounds/R01/gate/result.json').read_text())
                            decision = receipt['decisions'][0]
                            self.assertEqual((decision['G'], decision['L']), (count, 0))
                            self.assertEqual(decision['delta_chars'] < 0, shorter)
                            self.assertEqual(decision['pure_simplification'], pure)
                            expected = 'Retain' if count == 2 else 'Defer'
                            self.assertEqual(decision['gate_decision'], expected)
                            self.assertEqual(receipt['selection']['selected_update_ids'], ['u1'] if count == 2 else [])
                            record = memory.load_memory(campaign / 'memory')['memory']['rounds'][0]
                            self.assertEqual(record['source_updates'][0]['gate_decision'], expected)
                            self.assertEqual(cli.run_training(campaign, settings, generate=generate, resume=True), summary)
                            self.assertEqual(generator.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'])

    def test_selective_publication_next_parent_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, transport, _, _ = bind(root / 'fixture', rounds=2, size=4)
            adapter = cli.CampaignAdapter(cli.ActorAdapter(data, transport))
            generator = Generator()
            campaign = root / 'campaign'

            def generate(name, messages, directory, settings):
                response = generator(name, messages, directory, settings)
                if name == 'editor':
                    result = json.loads(response['content'])
                    parent = json.loads(messages[1]['content'])['parent']
                    for edit in result['edits']:
                        candidate = parent.replace('## Error Avoidance\n',
                                                   f"## Error Avoidance\n\n- **Apply rule {edit['update_id']}.** Scoped synthetic guidance.\n", 1)
                        edit['patch'] = re.sub(r'^@@[^\n]*@@$', '@@', actual_diff(parent, candidate), flags=re.M)
                    response['content'] = json.dumps(result)
                return response

            with adapter.using():
                settings = config.campaign_config(adapter)
                summary = cli.run_training(campaign, settings, generate=generate)
                first = json.loads((campaign / 'rounds/R01/gate/result.json').read_text())
                self.assertEqual([(d['G'], d['L'], d['gate_decision']) for d in first['decisions']],
                                 [(2, 0, 'Retain'), (0, 2, 'Reject')])
                self.assertEqual(first['selection']['selected_update_ids'], ['u1'])
                self.assertIsNone(first['selected_execution_source'])
                second = json.loads((campaign / 'rounds/R02/round_input.json').read_text())
                self.assertEqual(second['parent'], first['selection']['selected_text'])
                self.assertIn('rule u1', second['parent'])
                self.assertNotIn('rule u2', second['parent'])
                self.assertEqual(second['parent'].count('## Workflow\n'), 1)
                self.assertEqual(second['parent'].count('## Error Avoidance\n'), 1)
                self.assertEqual(len(second['memory']['rounds']), 1)
                self.assertEqual(cli.run_training(campaign, settings, generate=generate, resume=True), summary)
                self.assertEqual(len(transport.seen), 16)

    def test_unattributed_and_offsetting_changes_defer(self):
        for attribution in ('unresolved', 'conflict'):
            with self.subTest(attribution=attribution), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                data, transport, _, _ = bind(root / 'fixture', rounds=1, size=4)
                adapter = cli.CampaignAdapter(cli.ActorAdapter(data, transport))
                with adapter.using():
                    cli.run_training(root / 'campaign', config.campaign_config(adapter),
                                     generate=Generator(attribution=attribution))
                    result = json.loads((root / 'campaign/rounds/R01/gate/result.json').read_text())
                    self.assertEqual([d['gate_decision'] for d in result['decisions']], ['Defer', 'Defer'])
                    self.assertEqual(result['selection']['selected_text'], config.initial_skill()['text'])

    def test_no_change_and_empty_patch_do_not_add_behavior(self):
        for branch in ('diagnosis', 'preconditioner', 'editor'):
            with self.subTest(branch=branch), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                data, transport, _, _ = bind(root / 'fixture', rounds=1, size=2)
                adapter = cli.CampaignAdapter(cli.ActorAdapter(data, transport))
                generator = Generator(no_change=branch)
                with adapter.using():
                    cli.run_training(root / 'campaign', config.campaign_config(adapter), generate=generator)
                    self.assertEqual((root / 'campaign/final_skill.md').read_text(), config.initial_skill()['text'])
                    self.assertNotIn('replay', generator.calls)
                    self.assertFalse((root / 'campaign/rounds/R01/candidate_runs').exists())
                    if branch == 'editor':
                        record = memory.load_memory(root / 'campaign/memory')['memory']['rounds'][0]
                        self.assertTrue(all(u['gate_decision'] is None for u in record['source_updates']))

    def test_authorized_pair_reaches_editor_and_structured_skill_is_executed(self):
        # Authored layout checks transport/patch fidelity, not model compliance.
        pair = "'New York City' not 'New York'"
        instruction = 'Apply rule u1 to the synthetic requested city; example: ' + pair
        candidate = ('# Question Answering Skill\n\n## Workflow\n\n'
                     '1. **Apply rule u1.** Identify the requested city.\n\n'
                     '## Error Avoidance\n\n- **Preserve the requested name.**\n  - ' + pair + '\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, transport, _, _ = bind(root / 'fixture', rounds=1, size=2, mode='gain')
            adapter = cli.CampaignAdapter(cli.ActorAdapter(data, transport))
            generator = Generator(count=1)

            def generate(name, messages, directory, settings):
                response = generator(name, messages, directory, settings)
                result = json.loads(response['content'])
                value = json.loads(messages[1]['content'])
                if name == 'diagnosis':
                    # The mocked author reads the actual projected outcome;
                    # raw assistant text includes <answer>, but the pair must not.
                    outcome = value['runs'][0]['outcome']
                    self.assertEqual(outcome['answer']['extracted_answer'], 'New York')
                    self.assertIn('New York City', outcome['reference_answers'])
                    self.assertNotIn('<answer>', pair)
                    result['plan']['updates'][0]['text'] = instruction
                elif name == 'preconditioner':
                    self.assertEqual(value['plan']['updates'][0]['text'], instruction)
                    result['adjustments'][0].update(action='REPLACE', text=instruction + ' Organize the authorized rule under Workflow and Error Avoidance.')
                elif name == 'editor':
                    self.assertIn(pair, value['plan']['updates'][0]['text'])
                    result['edits'][0]['patch'] = re.sub(r'^@@[^\n]*@@$', '@@',
                                                       actual_diff(value['parent'], candidate), flags=re.M)
                response['content'] = json.dumps(result)
                return response

            with adapter.using():
                cli.run_training(root / 'campaign', config.campaign_config(adapter), generate=generate)
                self.assertEqual((root / 'campaign/final_skill.md').read_text(), candidate)
                self.assertEqual((root / 'campaign/rounds/R01/editor/attempts/001/candidate.md').read_text(), candidate)

