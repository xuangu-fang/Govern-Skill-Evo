"""SearchQA v28.15 acceptance using authored patches and the real selection code."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import re
import tempfile
import unittest

from scripts.runs import run_v28_15_campaign as cli
from src.skill_evolution.v27.unnumbered_patch import actual_diff
from src.skill_evolution.v28_15 import config, editor, gate


def select(parent, revisions, gains):
    updates, edits, selected = [], [], []
    for position, (revision, gain) in enumerate(zip(revisions, gains, strict=True), start=1):
        uid = f'u{position}'
        instruction, candidate = revision
        updates.append({'id': uid, 'text': instruction, 'pure_simplification': False})
        patch = re.sub(r'^@@[^\n]*@@$', '@@', actual_diff(parent, candidate), flags=re.MULTILINE)
        edits.append({'update_id': uid, 'patch': patch, 'reason': instruction})
        if gate._decision(patch, gain, 0) == 'Retain':
            selected.append(uid)
    payload = {'parent': parent, 'plan': {'goal': 'Organize the supplied guidance.', 'updates': updates}}
    return editor.construct_selected({'edits': edits}, payload, selected)


class AcceptanceTests(unittest.TestCase):
    def test_only_third_workflow_step_survives(self):
        parent = config.initial_skill()['text']
        steps = ['Read the clue.', 'Identify the relation.', 'Determine the answer boundary.', 'Check the chosen form.']
        revisions = []
        for step in steps:
            body = f'- **{step}**\n'
            if step == steps[2]:
                body += "  - 'Alpha' not 'Alpha unit' (clue supplies the unit)\n"
            revisions.append((step, parent.replace('## Workflow\n', '## Workflow\n\n' + body)))
        result = select(parent, revisions, [1, 1, 2, 1])
        self.assertEqual(result['selected_update_ids'], ['u3'])
        self.assertEqual(result['selected_text'], revisions[2][1])

    def test_spelling_move_with_condition_and_example_is_atomic(self):
        boundary = '- **Choose the answer boundary.** Keep words needed to identify the target.\n'
        spelling = ("- **Check spelling.** Keep a hyphen when the passage uses it.\n"
                    "  - 'A-B' not 'AB' (passage uses the hyphen)\n")
        workflow = '# Question Answering Skill\n\n## Workflow\n\n'
        errors = '\n## Error Avoidance\n'
        parent = workflow + boundary + spelling + errors
        moved = workflow + boundary + errors + '\n' + spelling
        revisions = [('Move the complete spelling check and example under Error Avoidance.', moved)]
        for gains, expected_ids, expected_text in [(2, ['u1'], moved), (1, [], parent)]:
            with self.subTest(gains=gains):
                result = select(parent, revisions, [gains])
                self.assertEqual(result['selected_update_ids'], expected_ids)
                self.assertEqual(result['selected_text'], expected_text)

    def test_formal_config_and_read_only_preflight(self):
        baseline = cli.ROOT / 'experiments/configs/v28_14_searchqa_train600_batch60.json'
        previous = json.loads(baseline.read_text())
        expected = deepcopy(previous)
        expected['method']['version'] = 'v28_15_campaign_v1'
        expected['method']['prompts'].update(
            preconditioner='v28_15_searchqa_preconditioner_section_ownership_v1',
            editor='v28_15_searchqa_editor_workflow_bullets_v1')
        expected['initial_skill']['source'] = str(config.DEFAULT_CONFIG.with_name('v28_15_searchqa_initial_skill.md'))
        self.assertEqual(json.loads(config.DEFAULT_CONFIG.read_text()), expected)
        self.assertEqual(config.initial_skill(), expected['initial_skill'])
        self.assertEqual(config.prompt_versions(), expected['method']['prompts'])
        for name in ('diagnosis', 'replay'):
            old = cli.ROOT / f'docs/methods/v28_14/prompts/{name}.md'
            self.assertEqual(config.MODULES[name].PROMPT_PATH.read_bytes(), old.read_bytes())
        self.assertEqual(Path(gate.__file__).read_bytes(),
                         (cli.ROOT / 'src/skill_evolution/v28_14/gate.py').read_bytes())
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()) as output:
            destination = Path(tmp) / 'campaign'
            cli.main(['train', str(destination), '--config', str(config.DEFAULT_CONFIG), '--validate-only'])
            self.assertFalse(destination.exists())
            self.assertEqual(json.loads(output.getvalue())['batch_sizes'], [60] * 10)
