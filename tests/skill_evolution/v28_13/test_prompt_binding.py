"""Verify that the campaign sends the reviewed prompts through its normal stage calls."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.runs import run_v28_13_campaign as cli
from src.skill_evolution.v28_13 import config
from tests.skill_evolution.v28_5.support import Generator, bind


class PromptBindingTests(unittest.TestCase):
    def test_synthetic_round_sends_reviewed_text_and_resumes_without_generation(self):
        with tempfile.TemporaryDirectory() as tmp, patch('socket.socket.connect',
                                                        side_effect=AssertionError('Network disabled')):
            root = Path(tmp)
            data, transport, _, _ = bind(root / 'fixture', rounds=1, size=2)
            adapter = cli.CampaignAdapter(cli.ActorAdapter(data, transport))
            generator = Generator()
            campaign = root / 'campaign'

            def generate(name, messages, directory, settings):
                source = cli.ROOT / 'docs/methods/v28_13/prompts' / f'{name}.md'
                self.assertEqual(messages[0]['content'], source.read_text(encoding='utf-8'))
                return generator(name, messages, directory, settings)

            with adapter.using():
                settings = config.campaign_config(adapter)
                summary = cli.run_training(campaign, settings, generate=generate)
                self.assertEqual(summary['method'], 'v28_13_campaign_v1')
                self.assertEqual(generator.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'])
                self.assertEqual(cli.prepare_test(campaign, root / 'evaluation')['tasks'], data.splits['test'])
                self.assertEqual(cli.run_training(campaign, settings, generate=generate, resume=True), summary)
                self.assertEqual(len(generator.calls), 4)
