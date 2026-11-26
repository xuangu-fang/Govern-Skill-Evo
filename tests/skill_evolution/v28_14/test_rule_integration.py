"""Authored integration scenarios; do not claim that an LLM follows the prose."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from scripts.runs import run_v28_14_campaign as cli
from src.skill_evolution.v27.unnumbered_patch import actual_diff
from src.skill_evolution.v28_14 import config, editor, preconditioner
from tests.skill_evolution.v28_5.support import Generator, bind


PARENT = '''# Question Answering Skill

## Workflow

## Error Avoidance

- **Stop after the slot.** Omit supplied categories.
  - 'a label' not 'a label category'

- **Preserve spelling.** Follow the supplied spelling.

- **Give the missing name.** Omit a supplied title fragment.

- **Return the short term.** Omit an unnecessary relation.

- **Keep necessary words.** Preserve words that identify the requested object.
'''
INTEGRATED = '''- **Apply rule u1: choose the answer boundary.** Omit a supplied category, title fragment or unnecessary relation. If words are needed to identify the requested object, keep them.
  - 'a label' not 'a label category'
'''
OLD = [
    "- **Stop after the slot.** Omit supplied categories.\n  - 'a label' not 'a label category'\n",
    '- **Give the missing name.** Omit a supplied title fragment.\n',
    '- **Return the short term.** Omit an unnecessary relation.\n',
    '- **Keep necessary words.** Preserve words that identify the requested object.\n',
]
INSTRUCTION = (
    'Home: replace Stop after the slot. Contribution: integrate the supported answer-boundary choice. '
    'Replace that entry with one rule covering supplied categories, title fragments and unnecessary relations; '
    'retain the exception for words needed to identify the object and the existing label example. '
    'Delete Give the missing name, Return the short term and Keep necessary words after integrating their meaning. '
    'Preserve the independent spelling rule and both section headings.'
)


def consolidated(parent):
    value = parent.replace(OLD[0], INTEGRATED)
    for old in OLD[1:]:
        value = value.replace(old, '')
    return value


def delta(parent, candidate):
    return re.sub(r'^@@[^\n]*@@$', '@@', actual_diff(parent, candidate), flags=re.M)


class RuleIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('socket.socket.connect', side_effect=AssertionError('Offline only')))

    def test_duplicate_withdrawal_preserves_ids_and_atomic_replacement_scope(self):
        original = {'goal': 'Integrate the answer-boundary decision.', 'updates': [
            {'id': 'u1', 'text': 'Revise the answer boundary.', 'basis': ['P1:1']},
            {'id': 'u2', 'text': 'Restate the same complete contribution.', 'basis': ['P1:1']},
            {'id': 'u3', 'text': 'Add an independent workflow action.', 'basis': ['P1:1']},
        ]}
        adjustments = {'adjustments': [
            {'target': 'u1', 'action': 'REPLACE', 'text': INSTRUCTION, 'reason': 'One complete supported decision.'},
            {'target': 'u2', 'action': 'WITHDRAW', 'text': None, 'reason': 'Its contribution is already covered.'},
            {'target': 'u3', 'action': 'KEEP', 'text': None, 'reason': 'An independent contribution needs no examples.'},
        ]}
        effective = preconditioner._compile(adjustments, {'plan': original, 'runs': [], 'memory': {'rounds': []}})
        self.assertEqual([u['id'] for u in effective['updates']], ['u1', 'u3'])
        self.assertEqual([u['basis'] for u in effective['updates']], [['P1:1'], ['P1:1']])
        payload = {'parent': PARENT, 'plan': {'goal': effective['goal'], 'updates': [
            {'id': u['id'], 'text': u['text'], 'pure_simplification': False} for u in effective['updates']]}}
        independent = '1. **Resolve the requested object.** Use the supplied relation.\n'
        output = {'edits': [
            {'update_id': 'u1', 'patch': delta(PARENT, consolidated(PARENT)), 'reason': 'Complete authorized replacement.'},
            {'update_id': 'u3', 'patch': delta(PARENT, PARENT.replace('## Workflow\n', '## Workflow\n\n' + independent)),
             'reason': 'Independent action; preserve other guidance.'},
        ]}
        for ids in ([], ['u1'], ['u3'], ['u1', 'u3']):
            with self.subTest(ids=ids):
                value = editor.construct_selected(output, payload, ids)['selected_text']
                self.assertIn('- **Preserve spelling.** Follow the supplied spelling.', value)
                self.assertEqual(value.count('## Workflow'), 1)
                self.assertEqual(value.count('## Error Avoidance'), 1)
                self.assertEqual(independent in value, 'u3' in ids)
                if 'u1' in ids:
                    self.assertIn(INTEGRATED, value)
                    for old in OLD:
                        self.assertNotIn(old, value)
                else:
                    for old in OLD:
                        self.assertIn(old, value)

    def test_authorized_merge_is_executed_selected_and_recovered(self):
        # Initial Parent is a synthetic fixture, not the formal empty template
        # or an existing experiment's learned Skill. Fake responses drive the
        # real stage, archive, patch, Gate and Memory code.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, transport, _, _ = bind(root / 'fixture', rounds=1, size=4)
            adapter = cli.CampaignAdapter(cli.ActorAdapter(data, transport))
            generator = Generator()

            def generate(name, messages, directory, settings):
                response = generator(name, messages, directory, settings)
                result = json.loads(response['content'])
                value = json.loads(messages[1]['content'])
                if name == 'preconditioner':
                    result['adjustments'][0].update(action='REPLACE', text=INSTRUCTION)
                elif name == 'editor':
                    self.assertEqual(value['plan']['updates'][0]['text'], INSTRUCTION)
                    result['edits'][0]['patch'] = delta(value['parent'], consolidated(value['parent']))
                response['content'] = json.dumps(result)
                return response

            with patch.object(config, 'initial_skill', return_value={'source': 'synthetic-only', 'text': PARENT}), adapter.using():
                settings = config.campaign_config(adapter)
                campaign = root / 'campaign'
                summary = cli.run_training(campaign, settings, generate=generate)
                result = json.loads((campaign / 'rounds/R01/gate/result.json').read_text())
                self.assertEqual(result['selection']['selected_update_ids'], ['u1'])
                self.assertEqual([d['gate_decision'] for d in result['decisions']], ['Retain', 'Reject'])
                self.assertEqual((campaign / 'final_skill.md').read_text(), consolidated(PARENT))
                self.assertIsNone(result['selected_execution_source'])
                self.assertEqual(cli.run_training(campaign, settings, generate=generate, resume=True), summary)
                self.assertEqual(generator.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'])

