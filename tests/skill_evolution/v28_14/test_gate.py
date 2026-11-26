import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.runs import run_v28_14_campaign as cli
from src.skill_evolution.v28_14 import config, editor, gate, preconditioner
from tests.skill_evolution.v28_5.support import Generator, bind


class GateTests(unittest.TestCase):
    def test_decision_boundaries(self):
        cases = [
            (3, 1, 500, False, 'Retain'),
            (2, 1, 0, False, 'Defer'),
            (1, 0, -1, False, 'Defer'),
            (2, 1, 1, False, 'Defer'),
            (0, 1, -10, True, 'Reject'),
            (1, 1, -10, True, 'Defer'),
            (0, 0, -1, True, 'Defer'),
            (0, 0, -1, False, 'Defer'),
            (0, 0, 0, True, 'Defer'),
            (0, 0, 1, True, 'Defer'),
        ]
        for gains, losses, delta, pure, expected in cases:
            with self.subTest(gains=gains, losses=losses, delta=delta, pure=pure):
                self.assertEqual(gate._decision('patch', gains, losses), expected)
        self.assertIsNone(gate._decision('', 0, 0))

    def test_patch_length_measures_unicode_and_real_line_endings(self):
        header = '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n'
        self.assertEqual(editor.patch_char_delta('甲乙\r\n', header + '-甲乙\r\n+🌟\r\n', 'u1'), -1)
        remove_lf = header + '-one\n+one\n\\ No newline at end of file\n'
        self.assertEqual(editor.patch_char_delta('one\n', remove_lf, 'u1'), -1)
        self.assertEqual(editor.patch_char_delta(None, '--- /dev/null\n+++ b/SKILL.md\n@@\n+甲\n', 'u2'), 2)
        self.assertEqual(editor.patch_char_delta('unchanged', '', 'u3'), 0)

    def test_invalid_simplification_declarations(self):
        payload = {'plan': {'goal': 'Shorten.', 'updates': [{'id': 'u1', 'text': 'Shorten.'}]},
                   'memory': {'rounds': []}, 'runs': []}
        for flag, action in [(1, 'KEEP'), ('false', 'KEEP'), (True, 'WITHDRAW')]:
            with self.subTest(flag=flag, action=action):
                adjustment = {'target': 'u1', 'action': action, 'text': None, 'reason': 'Shorten the wording.',
                              'pure_simplification': flag}
                with self.assertRaisesRegex(ValueError, 'boolean|Withdrawn'):
                    preconditioner._compile({'adjustments': [adjustment]}, payload)

    def test_zero_transitions_defer_shorter_skill_even_with_legacy_simplification(self):
        old = '# Question Answering Skill'
        new = '# QA Skill'
        for pure in (False, True):
            with self.subTest(pure=pure), tempfile.TemporaryDirectory() as tmp, \
                    patch('socket.socket.connect', side_effect=AssertionError('Unexpected network call')):
                root = Path(tmp)
                data, transport, _, _ = bind(root / 'fixture', rounds=1, size=2, mode='none')
                adapter = cli.CampaignAdapter(cli.ActorAdapter(data, transport))
                generator = Generator(count=1)

                def generate(name, messages, directory, settings):
                    response = generator(name, messages, directory, settings)
                    result = json.loads(response['content'])
                    if name == 'diagnosis':
                        result['plan']['updates'][0]['text'] = 'Shorten the existing title while preserving its meaning.'
                    elif name == 'preconditioner' and pure:
                        result['adjustments'][0]['pure_simplification'] = True
                    elif name == 'editor':
                        value = json.loads(messages[1]['content'])
                        self.assertIs(value['plan']['updates'][0]['pure_simplification'], pure)
                        result['edits'][0]['patch'] = f'--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-{old}\n+{new}\n'
                    response['content'] = json.dumps(result)
                    return response

                campaign = root / 'campaign'
                with adapter.using():
                    settings = config.campaign_config(adapter)
                    summary = cli.run_training(campaign, settings, generate=generate)
                    rd = campaign / 'rounds/R01'
                    parent = (rd / 'parent.md').read_text()
                    selected = parent
                    self.assertEqual((rd / 'selected.md').read_text(), selected)
                    result = json.loads((rd / 'gate/result.json').read_text())
                    decision = 'Defer'
                    self.assertEqual(result['decisions'], [{
                        'update_id': 'u1', 'G': 0, 'L': 0, 'delta_chars': len(new) - len(old),
                        'pure_simplification': pure, 'gate_decision': decision,
                    }])
                    self.assertEqual(result['selected_execution_source'], 'parent')
                    memory = json.loads((rd / 'memory_prepared.json').read_text())
                    self.assertEqual(memory['round']['source_updates'][0]['gate_decision'], decision)
                    self.assertEqual(cli.run_training(campaign, settings, generate=generate, resume=True), summary)
                    self.assertEqual(generator.calls, ['diagnosis', 'preconditioner', 'editor'])
