"""Authored correction fixtures test handoff/composition, not model judgment quality."""
from copy import deepcopy
import json
import re

from src.skill_evolution.v27.unnumbered_patch import actual_diff
from src.skill_evolution.v28_4 import diagnosis, preconditioner, editor, facts
from tests.skill_evolution.v28.runtime_support import Base
from .support import bind, no_hashes
from .test_editor import offline


PARENT = ('# Answer Decisions\n'
          '- Return the shortest name.\n'
          '- Preserve a full name when the question asks for it.\n'
          '- Always uppercase names.\n'
          '- Preserve requested measurement units.\n')
REVISED = '- Return the smallest sufficient name; preserve the full name when explicitly requested.\n'
UNRELATED = '- Preserve requested measurement units.\n'


def delta(parent, candidate):
    return re.sub(r'^@@[^\n]*@@$', '@@', actual_diff(parent, candidate), flags=re.MULTILINE)


class CorrectionHandoffTests(Base):
    def setUp(self):
        super().setUp()
        offline(self)
        self.enterContext(no_hashes())
        self.data, self.actor, self.adapter, self.config = bind(self.root, rounds=1, size=1)
        self.enterContext(self.adapter.using())
        self.skill.write_text(PARENT)
        folder = self.root / 'parent_runs'
        parents = self.adapter.actor_batch(self.data.batches[0], self.skill, folder,
                                          {'split': 'train', 'role': 'parent'})
        self.adapter.register_archive(folder)
        self.bundle = facts.build_parent_bundle(parents, 'R01')

    def diagnose(self, texts):
        return diagnosis.diagnosis_call(self.bundle).complete({
            'decision': 'revise', 'reason': 'DIAGNOSIS_REASON_ONLY: a supported correction hypothesis.',
            'plan': {'goal': 'Correct name guidance while preserving explicit requirements.',
                     'updates': [{'id': f'u{i}', 'text': text, 'basis': ['P1:0', 'P1:1']}
                                 for i, text in enumerate(texts, 1)]}})

    def keep(self, saved):
        return preconditioner.preconditioner_call(saved, {'rounds': []}).complete({
            'adjustments': [{'target': u['id'], 'action': 'KEEP', 'text': None,
                             'reason': 'Authored fixture: preserve this complete correction.'}
                            for u in saved['diagnosis']['plan']['updates']]})

    def test_add_revise_consolidate_replace_delete_use_same_contract(self):
        shortest = '- Return the shortest name.\n'
        full = '- Preserve a full name when the question asks for it.\n'
        upper = '- Always uppercase names.\n'
        cases = [
            ('add', 'Add a conditional temporal check when the question specifies a date; preserve other guidance.',
             PARENT + '- When the question specifies a date, select the relation at that date.\n'),
            ('revise', 'Revise the shortest-name rule to preserve the full name when explicitly requested; retain units.',
             PARENT.replace(shortest, REVISED)),
            ('consolidate', 'Consolidate the shortest-name and explicit-full-name rules into one conditional decision; retain the explicit-full-name exception and units.',
             PARENT.replace(shortest + full, REVISED)),
            ('replace', 'Replace the uppercase-name requirement with preservation of the name form explicitly requested; preserve other rules.',
             PARENT.replace(upper, '- Preserve the name form explicitly requested.\n')),
            ('delete', 'Remove the unconditional uppercase-name requirement; preserve the full-name condition and units.',
             PARENT.replace(upper, '')),
        ]
        for operation, text, candidate in cases:
            with self.subTest(operation=operation):
                original = self.diagnose([text]); frozen = deepcopy(original)
                adjusted = self.keep(original)
                call = editor.editor_call(adjusted)
                payload = json.loads(call.messages[1]['content'])
                self.assertEqual(payload['plan']['updates'], [{'id': 'u1', 'text': text}])
                result = call.complete({'edits': [{'update_id': 'u1', 'patch': delta(PARENT, candidate),
                                                   'reason': 'Implement the authored correction.'}]})
                self.assertEqual(result['candidate_text'], candidate)
                self.assertIn(UNRELATED, result['candidate_text'])
                self.assertEqual(editor.select_skill(result, ['u1'])['selected_text'], candidate)
                self.assertEqual(original, frozen)

    def test_replace_transmits_old_rule_treatment_and_exceptions_without_reasons(self):
        original = self.diagnose(['Revise the shortest-name rule for explicit full-name questions.'])
        call = preconditioner.preconditioner_call(original, {'rounds': []})
        self.assertNotIn('DIAGNOSIS_REASON_ONLY', json.dumps(call.messages))
        text = ('Replace the shortest-name rule and consolidate its full-name exception: return the smallest '
                'sufficient name, preserving the full name when explicitly requested. Preserve units and other guidance.')
        adjusted = call.complete({'adjustments': [{'target': 'u1', 'action': 'REPLACE', 'text': text,
                                                   'reason': 'PRECONDITIONER_REASON_ONLY: keep the supported exception.'}]})
        effective = adjusted['effective_plan']['updates'][0]
        self.assertEqual(effective, {**original['diagnosis']['plan']['updates'][0], 'text': text})
        ed = editor.editor_call(adjusted)
        payload = json.loads(ed.messages[1]['content'])
        self.assertEqual(set(payload), {'parent', 'plan'})
        self.assertEqual(payload['plan']['updates'], [{'id': 'u1', 'text': text}])
        self.assertNotIn('REASON_ONLY', json.dumps(ed.messages))
        self.assertNotIn('basis', payload['plan']['updates'][0])
        candidate = PARENT.replace('- Return the shortest name.\n- Preserve a full name when the question asks for it.\n', REVISED)
        result = ed.complete({'edits': [{'update_id': 'u1', 'patch': delta(PARENT, candidate),
                                         'reason': 'Consolidated the two related clauses with their valid exception.'}]})
        self.assertEqual(result['candidate_text'], candidate)
        self.assertNotIn('- Return the shortest name.\n', candidate)

    def test_rule_consolidation_does_not_merge_update_ids_or_patches(self):
        adjusted = self.keep(self.diagnose([
            'Consolidate shortest-name and full-name guidance, retaining the explicit-full-name condition.',
            'Delete the unconditional uppercase-name requirement; preserve all other behavior.',
        ]))
        first = PARENT.replace('- Return the shortest name.\n- Preserve a full name when the question asks for it.\n', REVISED)
        second = PARENT.replace('- Always uppercase names.\n', '')
        edits = {'edits': [{'update_id': 'u2', 'patch': delta(PARENT, second), 'reason': 'Remove the restriction.'},
                           {'update_id': 'u1', 'patch': delta(PARENT, first), 'reason': 'Consolidate the name clauses.'}]}
        call = editor.editor_call(adjusted)
        result = call.complete(edits)
        self.assertEqual(result['candidate_text'], first.replace('- Always uppercase names.\n', ''))
        self.assertEqual(editor.select_skill(result, ['u1'])['selected_text'], first)
        self.assertEqual(editor.select_skill(result, ['u2'])['selected_text'], second)
        self.assertEqual(editor.select_skill(result, [])['selected_text'], PARENT)
        bad = deepcopy(edits); bad['edits'][0]['update_id'] = 'merged'
        self.reject(call.complete, bad)

    def test_no_new_operation_fields_or_organizational_schema_constraints(self):
        # More than five Updates and a non-Workflow heading remain structurally legal.
        original = self.diagnose([f'When applicable condition {i} holds, preserve its supported qualifier.'
                                  for i in range(8)])
        adjusted = self.keep(original)
        self.assertEqual(len(adjusted['effective_plan']['updates']), 8)
        self.assertEqual(editor.editor_input(adjusted)['parent'], PARENT)
        bad = deepcopy(original['diagnosis'])
        bad['plan']['updates'][0]['operation'] = 'revise'
        self.reject(diagnosis.diagnosis_call(self.bundle).complete, bad)
        bad = deepcopy(original['diagnosis']); bad['plan']['updates'][0]['rule_id'] = 'shortest'
        self.reject(diagnosis.diagnosis_call(self.bundle).complete, bad)

    def test_no_change_withdraw_empty_and_blocker_remain_distinct(self):
        call = diagnosis.diagnosis_call(self.bundle)
        unchanged = call.complete({'decision': 'no_change', 'plan': None,
                                   'reason': 'No supported behavioral correction is available.'})
        self.assertIsNone(unchanged['diagnosis']['plan'])
        original = self.diagnose(['Preserve requested measurement units.'])
        withdrawn = preconditioner.preconditioner_call(original, {'rounds': []}).complete({
            'adjustments': [{'target': 'u1', 'action': 'WITHDRAW', 'text': None,
                             'reason': 'The original Parent already provides this behavior.'}]})
        self.assertIsNone(withdrawn['effective_plan'])
        ed = editor.editor_call(self.keep(original))
        satisfied = ed.complete({'edits': [{'update_id': 'u1', 'patch': '',
                                           'reason': 'The original Parent explicitly preserves requested units.'}]})
        self.assertEqual(satisfied['editor_status'], 'no_change')
        blocked = ed.complete({'edits': [{'update_id': 'u1', 'patch': None,
                                         'reason': 'Authored blocker fixture: an essential choice is unresolved.'}]})
        self.assertEqual(blocked['editor_status'], 'needs_revision')
        self.assertIsNone(blocked['candidate_text'])
