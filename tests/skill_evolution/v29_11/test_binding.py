"""Check v29.11 prompt isolation, stage contracts, and offline CLI validation."""
import json
from unittest.mock import patch

from scripts.runs import run_v29_11_campaign as cli
from src.skill_evolution.v29.benchmarks.docvqa import protocol
from src.skill_evolution.v29_10 import config as baseline
from src.skill_evolution.v29_10.campaign import DEFAULT_CONFIG as BASELINE_CONFIG
from src.skill_evolution.v29_11 import config, diagnosis, editor, facts, preconditioner, stages
from src.skill_evolution.v29_11.campaign import CampaignAdapter, DEFAULT_CONFIG
from tests.skill_evolution.v29.test_method import MethodBase
from tests.skill_evolution.v29_8.helpers import offline, proposal


class BindingTests(MethodBase):
    def setUp(self):
        super().setUp()
        offline(self)
        self.method = CampaignAdapter(self.adapter)
        self.enterContext(self.method.using())

    def test_only_two_prompt_identities_and_method_change(self):
        old = json.loads(BASELINE_CONFIG.read_text())
        new = json.loads(DEFAULT_CONFIG.read_text())
        old['method']['version'] = 'v29_11_campaign_v1'
        old['method']['prompts']['diagnosis'] = 'v29_11_docvqa_diagnosis_v1'
        old['method']['prompts']['preconditioner'] = 'v29_11_docvqa_preconditioner_v1'
        self.assertEqual(new, old)
        self.assertEqual(new['method'], config.method_config())
        prompts = config.render_prompts()
        reference = baseline.render_prompts()
        endpoint = protocol.ACTOR['endpoint']
        for name, prompt in prompts.items():
            self.assertNotIn(endpoint, prompt)
            if name in ('editor', 'replay'):
                self.assertEqual(prompt, reference[name].replace(f' through {endpoint}', ''))
            else:
                self.assertNotEqual(prompt, reference[name].replace(f' through {endpoint}', ''))

    def test_cli_preflight_with_formal_config_is_read_only(self):
        campaign = self.root / 'not_created'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('credential access')), \
             patch.object(cli, 'run_training', side_effect=AssertionError('training started')), \
             patch.object(cli, 'run_test', side_effect=AssertionError('evaluation started')):
            cli.main(['train', str(campaign), '--config', str(DEFAULT_CONFIG), '--validate-only'])
            with self.assertRaisesRegex(ValueError, 'Method version'):
                cli.main(['train', str(campaign), '--config', str(BASELINE_CONFIG), '--validate-only'])
        self.assertFalse(campaign.exists())

    def test_invalid_actor_config_is_rejected(self):
        background = protocol.actor_config()
        with self.assertRaises(ValueError):
            preconditioner.render_prompt({**background, 'max_tokens': 1})

    def test_verified_stage_and_editor_handoff(self):
        saved = facts.build_parent_bundle(self.parent(), 'R01')
        old_diagnosis = baseline.diagnosis.diagnosis_call(saved)
        new_diagnosis = stages._verified_call(diagnosis.diagnosis_call(saved))
        self.assertEqual(new_diagnosis.messages[0]['content'], diagnosis.PROMPT_PATH.read_text())
        self.assertEqual(new_diagnosis.messages[1:], old_diagnosis.messages[1:])
        self.assertEqual(new_diagnosis.contract_version, old_diagnosis.contract_version)
        with self.assertRaisesRegex(ValueError, 'prompt/contract version'):
            stages._verified_call(old_diagnosis)
        diagnosed = new_diagnosis.complete(proposal())
        self.assertEqual(diagnosed, old_diagnosis.complete(proposal()))
        memory = {'rounds': []}
        old_call = baseline.preconditioner.preconditioner_call(diagnosed, memory)
        call = stages._verified_call(preconditioner.preconditioner_call(diagnosed, memory))
        self.assertEqual(call.contract_version, old_call.contract_version)
        self.assertEqual(call.messages[0]['content'], preconditioner.PROMPT_PATH.read_text())
        self.assertEqual(call.messages[1:], old_call.messages[1:])
        with self.assertRaisesRegex(ValueError, 'prompt/contract version'):
            stages._verified_call(old_call)
        updates = diagnosed['diagnosis']['plan']['updates']
        for action in ('KEEP', 'REPLACE', 'WITHDRAW'):
            with self.subTest(action=action):
                decisions = {'adjustments': [
                    {'target': u['id'], 'action': action, 'text': u['text'] + ' Use the visible cue.'
                     if action == 'REPLACE' else None, 'reason': 'Authored offline adjustment.'}
                    for u in updates]}
                actual = call.complete(decisions)
                expected = old_call.complete(decisions)
                self.assertEqual(actual, expected)
                if action == 'WITHDRAW':
                    self.assertIsNone(actual['effective_plan'])
                else:
                    messages = editor.editor_call(actual).messages
                    self.assertEqual(messages[0], {'role': 'system', 'content': editor.PROMPT_PATH.read_text()})
                    self.assertEqual(messages[1:], baseline.editor.editor_call(expected).messages[1:])
