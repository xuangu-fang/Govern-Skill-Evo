"""First-round structural independence with the new empty section template."""
import itertools
import json
import re
import unittest

from scripts.runs import run_v28_14_campaign as cli
from src.skill_evolution.v27.unnumbered_patch import actual_diff
from src.skill_evolution.v28_14 import config, editor


class InitialTemplateTests(unittest.TestCase):
    def test_template_is_version_local_and_has_no_learned_content(self):
        initial = config.initial_skill()
        self.assertEqual(initial['text'], '# Question Answering Skill\n\n## Workflow\n\n## Error Avoidance\n')
        self.assertEqual(initial['source'], str(cli.ROOT / 'experiments/configs/v28_14_searchqa_initial_skill.md'))
        saved = json.loads(config.DEFAULT_CONFIG.read_text())
        self.assertEqual(saved['initial_skill'], initial)
        previous = json.loads((cli.ROOT / 'experiments/configs/v28_13_searchqa_train600_batch60.json').read_text())
        self.assertNotEqual(previous['initial_skill']['source'], initial['source'])
        self.assertEqual(previous['initial_skill']['text'],
                         (cli.ROOT / 'experiments/configs/v28_13_searchqa_initial_skill.md').read_text())

    def test_every_first_round_subset_preserves_shared_headings(self):
        parent = config.initial_skill()['text']
        # Two updates share a section and insertion gap; the third belongs
        # to the other section. No patch creates or owns the shared headings.
        additions = {
            'u1': ('## Error Avoidance\n', '- **Avoid one error.**\n'),
            'u2': ('## Error Avoidance\n', '- **Avoid another error.**\n'),
            'u3': ('## Workflow\n', '1. **Resolve the requested object.**\n'),
        }
        payload = {'parent': parent, 'plan': {'goal': 'Add independent synthetic guidance.', 'updates': [
            {'id': uid, 'text': 'Add the scoped guidance.', 'pure_simplification': False} for uid in additions]}}
        result = {'edits': []}
        for uid, (heading, body) in additions.items():
            candidate = parent.replace(heading, heading + '\n' + body, 1)
            delta = re.sub(r'^@@[^\n]*@@$', '@@', actual_diff(parent, candidate), flags=re.M)
            result['edits'].append({'update_id': uid, 'patch': delta, 'reason': 'Use existing headings.'})
        for count in range(4):
            for chosen in itertools.combinations(additions, count):
                with self.subTest(chosen=chosen):
                    selected = editor.construct_selected(result, payload, list(chosen))['selected_text']
                    self.assertEqual(selected.count('## Workflow\n'), 1)
                    self.assertEqual(selected.count('## Error Avoidance\n'), 1)
                    self.assertLess(selected.index('## Workflow'), selected.index('## Error Avoidance'))
                    for uid, (_, body) in additions.items():
                        self.assertEqual(body in selected, uid in chosen)
                    if not chosen:
                        self.assertEqual(selected, parent)

