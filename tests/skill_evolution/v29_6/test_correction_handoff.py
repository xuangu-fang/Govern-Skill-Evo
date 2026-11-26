"""Authored corrections test lossless handoff and patches, not model reasoning quality."""
from copy import deepcopy
import json

from src.skill_evolution.v29_6 import diagnosis, preconditioner, editor, facts
from src.skill_evolution.v29_6.campaign import CampaignAdapter
from tests.skill_evolution.v29.test_method import MethodBase
from .helpers import offline, diff, output


class CorrectionHandoffTests(MethodBase):
    def setUp(self):
        super().setUp()
        offline(self)
        self.method = CampaignAdapter(self.adapter)
        self.enterContext(self.method.using())
        self.parent_text = (
            '# Skill\n'
            '- Prefer a field labeled Total for every amount question.\n'
            '\n## Preservation\n'
            '- Preserve requested date granularity.\n'
            '\n## Fallback\n'
            '- Ignore requested amount roles when a Total label exists.\n'
        )
        records, _ = self.batch(self.parent_text,
                               ['<answer>1,200</answer>', '<answer>12 May 2021</answer>'], 'parent')
        self.saved = facts.build_parent_bundle(records, 'R01')
        # Original states the behavioral proposal; Preconditioner supplies old-rule treatment.
        self.original = (
            'For amount questions, select the amount with the requested field role.\n\n'
            'Do not choose a different role solely because its field is labeled Total. '
            'Preserve requested date granularity.\n'
        )
        self.replacement = (
            'Replace the unconditional Total preference: select the amount with the requested field role; '
            'a Total label is supporting evidence only when its role matches.\n\n'
            'Remove the fallback that ignores the requested role. '
            'Preserve requested date granularity and do not require extra image-wide checking.\n'
        )

    def diagnosed(self, extra=False):
        updates = [{'id': 'u1', 'text': self.original, 'basis': ['P1:1', 'P2:outcome']}]
        if extra:
            updates += [{'id': 'u2', 'text': 'Preserve requested date granularity.', 'basis': ['P2:1']},
                        {'id': 'u3', 'text': 'Add an independent numeric check.', 'basis': ['P1:1']}]
        return diagnosis.diagnosis_call(self.saved).complete({
            'decision': 'revise', 'reason': 'The current response supports a scoped repair; visual cause is unknown.',
            'plan': {'goal': 'Correct amount-role selection while preserving date answers.', 'updates': updates}})

    def prepared(self, action='REPLACE', extra=False):
        diagnosed = self.diagnosed(extra)
        original = deepcopy(diagnosed)
        adjustments = [{'target': 'u1', 'action': action,
                        'text': self.replacement if action == 'REPLACE' else None,
                        'reason': 'Private adjustment rationale; not an Editor implementation channel.'}]
        if extra:
            adjustments += [{'target': 'u2', 'action': 'KEEP', 'text': None, 'reason': 'Preserve the supported branch.'},
                            {'target': 'u3', 'action': 'WITHDRAW', 'text': None, 'reason': 'No justified increment.'}]
            adjustments.reverse()
        result = preconditioner.preconditioner_call(diagnosed, {'rounds': []}).complete({'adjustments': adjustments})
        self.assertEqual(diagnosed, original)
        return result

    def test_keep_and_replace_transmit_complete_strategy_without_reasons_or_new_fields(self):
        for action, text in [('KEEP', self.original), ('REPLACE', self.replacement)]:
            with self.subTest(action=action):
                prepared = self.prepared(action, extra=True)
                effective = prepared['effective_plan']
                self.assertEqual([u['id'] for u in effective['updates']], ['u1', 'u2'])
                self.assertEqual(effective['goal'], prepared['diagnosis']['plan']['goal'])
                self.assertEqual(effective['updates'][0], {'id': 'u1', 'text': text, 'basis': ['P1:1', 'P2:outcome']})
                payload = json.loads(editor.editor_call(prepared).messages[1]['content'])
                self.assertEqual(set(payload), {'parent', 'plan'})
                self.assertEqual(payload['plan']['updates'], [{'id': u['id'], 'text': u['text']}
                                                              for u in effective['updates']])
                self.assertNotIn('Private adjustment rationale', json.dumps(payload))

    def test_one_correction_revises_and_deletes_in_multiple_hunks(self):
        prepared = self.prepared()
        patch = diff(
            ' # Skill\n'
            '-- Prefer a field labeled Total for every amount question.\n'
            '+- Select the requested amount role; use a Total label only when its role matches.\n'
            '@@\n'
            ' ## Fallback\n'
            '-- Ignore requested amount roles when a Total label exists.\n'
        )
        result = editor.editor_call(prepared).complete(output(patch))
        self.assertEqual(result['editor_status'], 'candidate')
        self.assertEqual(result['candidate_text'], self.parent_text.replace(
            '- Prefer a field labeled Total for every amount question.\n',
            '- Select the requested amount role; use a Total label only when its role matches.\n'
        ).replace('- Ignore requested amount roles when a Total label exists.\n', ''))
        self.assertEqual(result['effective_plan'], prepared['effective_plan'])
        self.assertEqual([e['update_id'] for e in result['editor']['edits']], ['u1'])

    def test_mixed_changed_and_already_satisfied_updates_preserve_mapping(self):
        prepared = self.prepared(extra=True)
        patch = diff('-' + self.parent_text.splitlines(True)[1] +
                     '+- Match the requested amount role before choosing a Total field.\n' +
                     '@@\n-- Ignore requested amount roles when a Total label exists.\n')
        result = editor.editor_call(prepared).complete(output(patch, ''))
        self.assertEqual(result['editor_status'], 'candidate')
        self.assertEqual([e['update_id'] for e in result['editor']['edits']], ['u1', 'u2'])
        self.assertIn('- Preserve requested date granularity.\n', result['candidate_text'])

    def test_essential_blocker_stops_construction_and_all_withdraw_has_no_plan(self):
        prepared = self.prepared()
        blocked = editor.editor_call(prepared).complete(output(None))
        self.assertEqual(blocked['editor_status'], 'needs_revision')
        self.assertIsNone(blocked['candidate_text'])
        withdrawn = self.prepared('WITHDRAW')
        self.assertIsNone(withdrawn['effective_plan'])
        with self.assertRaises(ValueError): editor.editor_call(withdrawn)
