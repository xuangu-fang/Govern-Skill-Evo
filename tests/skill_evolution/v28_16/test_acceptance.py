"""Offline acceptance for the first learned SearchQA rules."""
from contextlib import redirect_stdout
from io import StringIO
from itertools import combinations
import json
from pathlib import Path
import re
import tempfile
import unittest

from scripts.runs import run_v28_16_campaign as cli
from src.skill_evolution.v27.unnumbered_patch import actual_diff
from src.skill_evolution.v28_16 import config, editor, gate
from tests.skill_evolution.v28_5.support import Generator, bind, response


TITLE = '# Question Answering Skill\n\n'
MARKER = '(No learned rules yet. Rules will be added through the reflection process.)\n'
INITIAL = TITLE + MARKER
IDS = ('u1', 'u2', 'u3', 'u4')


def delta(parent, modified):
    return re.sub(r'^@@[^\n]*@@$', '@@', actual_diff(parent, modified), flags=re.M)


def rule(uid, batch):
    return f'- **Rule {uid} from {batch}.** Use the relevant cue.\n  - Example: {uid}.\n'


def inputs(parent, patches):
    updates = [{'id': uid, 'text': f'Apply rule {uid}.', 'pure_simplification': False} for uid in patches]
    edits = [{'update_id': uid, 'patch': p, 'reason': 'Implement the rule.'} for uid, p in patches.items()]
    return {'edits': edits}, {'parent': parent, 'plan': {'goal': 'Choose the requested answer.', 'updates': updates}}


class TemplateTests(unittest.TestCase):
    def test_subsets_and_reordered_responses(self):
        patches = {uid: delta(INITIAL, INITIAL + rule(uid, 'first')) for uid in IDS}
        output, payload = inputs(INITIAL, patches)
        for reverse in (False, True):
            if reverse:
                output['edits'].reverse()
            full = editor.construct_candidate(output, payload)
            for n in range(5):
                for ids in combinations(IDS, n):
                    with self.subTest(reverse=reverse, ids=ids):
                        selected = editor.construct_selected(output, payload, list(reversed(ids)))
                        expected = TITLE + ''.join(rule(uid, 'first') for uid in ids) if ids else INITIAL
                        self.assertEqual(selected['selected_text'].encode(), expected.encode())
                        self.assertEqual(selected['actual_diff'], actual_diff(INITIAL, expected))
                        self.assertEqual(selected['selected_update_ids'], list(ids))
                        if n == 4:
                            self.assertEqual(full['candidate_text'], expected)
                            self.assertEqual(full['actual_diff'], selected['actual_diff'])
        for uid in IDS:
            self.assertEqual(editor.patch_char_delta(INITIAL, patches[uid], uid), len(rule(uid, 'first')))

    def test_empty_blocked_and_post_initial_parents(self):
        addition = delta(INITIAL, INITIAL + rule('u1', 'first'))
        result, payload = inputs(INITIAL, {'u1': addition, 'u2': ''})
        self.assertEqual(editor.construct_selected(result, payload, ['u2'])['selected_text'], INITIAL)
        for patch_value, status in [('', 'no_change'), (None, 'needs_revision')]:
            result, payload = inputs(INITIAL, {'u1': patch_value, 'u2': '' if patch_value == '' else addition})
            full = editor.construct_candidate(result, payload)
            self.assertEqual(full['editor_status'], status)
            self.assertIsNone(full['candidate_text'])
        for parent in (INITIAL.replace('\n', '\r\n'), TITLE + '- Existing rule.\n' + MARKER):
            updated = parent + rule('u1', 'later')
            result, payload = inputs(parent, {'u1': delta(parent, updated)})
            self.assertEqual(editor.construct_candidate(result, payload)['candidate_text'], updated)

    def test_invalid_initial_edits_follow_output_validation_path(self):
        from src.skill_evolution.v28_16 import output_feedback
        bad = [TITLE + rule('u1', 'first'), INITIAL.replace('Answering', 'Solving'),
               INITIAL.replace(MARKER, '- Early insertion.\n' + MARKER), INITIAL + '  \n',
               INITIAL + '-  \n', INITIAL + '- Rule but missing LF', INITIAL + '- Rule\n' + MARKER]
        for modified in bad:
            with self.subTest(modified=modified):
                result, payload = inputs(INITIAL, {'u1': delta(INITIAL, modified)})
                with self.assertRaises(output_feedback.OutputValidationError):
                    output_feedback.output_call('editor', editor.construct_candidate, result, payload)

    def test_formal_bindings_against_frozen_baselines(self):
        snapshot = cli.ROOT / 'experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261109_010205/frozen.json'
        self.assertEqual(config.initial_skill()['text'].encode(), json.loads(snapshot.read_text())['initial_skill'].encode())
        self.assertEqual(config.initial_skill()['text'], INITIAL)
        old = config.DEFAULT_CONFIG.with_name('v28_15_searchqa_train600_batch60.json')
        expected = json.loads(old.read_text())
        expected['initial_skill'] = {'text': INITIAL, 'source': str(old.with_name('v28_searchqa_initial_skill.md'))}
        expected['method']['version'] = 'v28_16_campaign_v1'
        expected['method']['prompts'].update(preconditioner='v28_16_searchqa_preconditioner_rule_ownership_v2',
                                            editor='v28_16_searchqa_editor_title_bullets_v2')
        expected['method']['contracts']['editor'] = 'v28_16_editor_initial_rule_composition_v1'
        self.assertEqual(json.loads(config.DEFAULT_CONFIG.read_text()), expected)
        self.assertEqual(Path(gate.__file__).read_bytes(), (cli.ROOT / 'src/skill_evolution/v28_15/gate.py').read_bytes())
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()) as output:
            target = Path(tmp) / 'absent'
            cli.main(['train', str(target), '--config', str(config.DEFAULT_CONFIG), '--validate-only'])
            self.assertEqual(json.loads(output.getvalue())['batch_sizes'], [60] * 10)
            self.assertFalse(target.exists())


class CampaignTests(unittest.TestCase):
    def test_defer_then_partial_first_adoption_recovery_and_later_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            campaign = root / 'campaign'
            data, transport, _, _ = bind(root / 'fixture', rounds=3, size=2)
            adapter = cli.CampaignAdapter(cli.ActorAdapter(data, transport))
            chosen = TITLE + rule('u3', 'R02')
            revised = chosen.replace('relevant cue', 'revised cue')
            generator = Generator(count=4)

            def answer(messages, directory):
                skill = messages[0]['content']
                good = any(cue in skill for cue in ('u1 from R01', 'u1 from R02', 'revised cue'))
                return response('<answer>New York City</answer>' if good else '<answer>New York</answer>')

            def generate(name, messages, directory, settings):
                prompt = cli.ROOT / 'docs/methods/v28_16/prompts' / f'{name}.md'
                self.assertEqual(messages[0]['content'], prompt.read_text())
                raw = generator(name, messages, directory, settings)
                parsed = json.loads(raw['content'])
                batch = directory.parents[2].name
                if name == 'editor':
                    parent = json.loads(messages[1]['content'])['parent']
                    self.assertEqual(parent, chosen if batch == 'R03' else INITIAL)
                    for item in parsed['edits']:
                        uid = item['update_id']
                        if batch == 'R03':
                            item['patch'] = delta(chosen, revised) if uid == 'u3' else ''
                        else:
                            item['patch'] = delta(parent, parent + rule(uid, batch))
                elif name == 'replay':
                    for i, item in enumerate(parsed['entries'][0]['knowledge']):
                        item['update_id'] = IDS[i] if batch == 'R01' else 'u3'
                raw['content'] = json.dumps(parsed)
                return raw

            def interrupt(stage):
                if stage == 'memory':
                    raise InterruptedError('After R02 Gate journal')

            transport.generate = answer
            with adapter.using():
                settings = config.campaign_config(adapter)
                cli.ev.run_round(campaign, config=settings, generate=generate)
                with self.assertRaises(InterruptedError):
                    cli.ev.run_round(campaign, generate=generate, hook=interrupt)
                summary = cli.run_training(campaign, settings, generate=generate, resume=True)
                self.assertEqual(summary['rounds_completed'], 3)
                self.assertEqual(generator.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'] * 3)
                for batch, parent, selected, ids, source in [
                    ('R01', INITIAL, INITIAL, [], 'parent'), ('R02', INITIAL, chosen, ['u3'], None),
                    ('R03', chosen, revised, ['u3'], 'candidate')]:
                    rd = campaign / 'rounds' / batch
                    candidate = revised if batch == 'R03' else TITLE + ''.join(rule(uid, batch) for uid in IDS)
                    self.assertEqual((rd / 'parent.md').read_text(), parent)
                    attempt = rd / 'editor/attempts/001'
                    self.assertEqual((attempt / 'candidate.md').read_text(), candidate)
                    self.assertEqual((attempt / 'actual.diff').read_text(), actual_diff(parent, candidate))
                    result = json.loads((rd / 'gate/result.json').read_text())
                    self.assertEqual(result['selection']['selected_update_ids'], ids)
                    self.assertEqual(result['selection']['actual_diff'], actual_diff(parent, selected))
                    self.assertEqual(result['selected_execution_source'], source)
                    self.assertEqual((rd / 'selected.md').read_text(), selected)
                self.assertEqual((campaign / 'final_skill.md').read_text(), revised)
                self.assertEqual(cli.run_training(campaign, settings, resume=True, generate=generate), summary)
                self.assertEqual(len(generator.calls), 12)
