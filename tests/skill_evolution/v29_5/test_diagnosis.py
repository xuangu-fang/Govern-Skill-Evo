"""Direct evidence, source validation and removed Group permissions."""
from copy import deepcopy
import json
from unittest.mock import patch

from src.skill_evolution.v29_2 import grouping, diagnosis as old_d
from src.skill_evolution.v29_5 import diagnosis as d, facts, preconditioner as p, output_feedback
from src.skill_evolution.v29_5.campaign import CampaignAdapter
from tests.skill_evolution.v29.test_method import MethodBase, main_example
from .helpers import proposal, decisions, memory_view, offline


class DiagnosisTests(MethodBase):
    def setUp(self):
        super().setUp()
        offline(self)
        self.method = CampaignAdapter(self.adapter)
        self.enterContext(self.method.using())
        self.records = self.parent()
        self.saved = facts.build_parent_bundle(self.records, 'R01')

    def test_complete_batch_is_preserved_without_model_preanalysis(self):
        with patch.object(grouping, 'grouping_call', side_effect=AssertionError('No Grouping')):
            saved = facts.build_parent_bundle(self.records, 'R01')
            call = d.diagnosis_call(saved)
            result = call.complete(proposal())
        self.assertEqual(set(saved), {'facts', 'background', 'sources', 'round_id'})
        self.assertEqual(result['facts'], saved['facts'])
        self.assertEqual(result['round_id'], 'R01')
        self.assertEqual([r['outcome']['score']['hard'] for r in saved['facts']['runs']], [0, 1])
        self.assertEqual(set(json.loads(call.messages[1]['content'])), {'parent', 'runs', 'shared_initial'})
        self.assertNotIn('grouping', result)

    def test_single_execution_and_shared_evidence_do_not_require_case_categories(self):
        records, _ = self.batch(self.skill, ['<answer>1,200</answer>'], 'parent', self.tasks[:1])
        saved = facts.build_parent_bundle(records, 'R02')
        value = proposal()
        value['plan']['updates'][0]['basis'] = ['P1:1']
        value['plan']['updates'].append({'id': 'u2', 'text': 'Preserve requested qualifiers.', 'basis': ['P1:1']})
        self.assertEqual(d.diagnosis_call(saved).complete(value)['diagnosis'], value)

    def test_every_group_source_is_rejected_in_diagnosis(self):
        for token in ('G1', '`Group:G1`', 'Group:G1', '`Group:custom`'):
            for field in ('reason', 'goal', 'text', 'basis'):
                value = proposal()
                if field == 'reason': value[field] += ' ' + token
                elif field == 'goal': value['plan'][field] += ' ' + token
                elif field == 'text': value['plan']['updates'][0][field] += ' ' + token
                else: value['plan']['updates'][0][field].append(token)
                with self.subTest(token=token, field=field), self.assertRaises(ValueError):
                    d.diagnosis_call(self.saved).complete(value)
        with self.assertRaises(ValueError):
            d.diagnosis_call(self.saved).complete({'decision': 'no_change', 'reason': 'See G1.', 'plan': None})

    def test_grouping_handoff_and_extra_model_fields_are_rejected(self):
        old = grouping.grouping_call(self.records, 'R01').complete(main_example('grouping'))
        with self.assertRaises(ValueError): d.diagnosis_call(old)
        with self.assertRaises((ValueError, KeyError)): old_d.diagnosis_call(self.saved)
        for key in ('grouping', 'memory', 'candidate'):
            payload = deepcopy(self.saved['facts']); payload[key] = {}
            with self.subTest(key=key), self.assertRaises(ValueError): d.validate_input(payload)

    def test_source_checks_preserve_complete_order_and_identity(self):
        for records in (self.records[:1], self.records[::-1], self.records + self.records[:1]):
            with self.assertRaises(ValueError): facts.build_parent_bundle(records, 'R01')
        for field in ('parent', 'response', 'score', 'source', 'background', 'missing', 'order'):
            value = deepcopy(self.saved)
            if field == 'parent': value['facts']['parent'] += ' forged'
            elif field == 'response': value['facts']['runs'][0]['attempts'][0]['assistant']['content'] = 'forged'
            elif field == 'score': value['facts']['runs'][0]['outcome']['score']['hard'] = 1
            elif field == 'source': value['sources'][0]['run_id'] = 'forged'
            elif field == 'background': value['background']['temperature'] = 0
            elif field == 'missing': value['facts']['runs'].pop()
            else: value['facts']['runs'].reverse()
            with self.subTest(field=field), self.assertRaises(ValueError): d.diagnosis_call(value)

    def test_completion_rechecks_saved_actor_sources(self):
        call = d.diagnosis_call(self.saved)
        with patch.object(self.method, 'source_record', side_effect=ValueError('archive changed')):
            with self.assertRaisesRegex(ValueError, 'archive changed'): call.complete(proposal())

    def test_success_counterexample_handoff_is_whole_runs(self):
        diagnosed = d.diagnosis_call(self.saved).complete(proposal())
        selected = p.preconditioner_input(diagnosed, memory_view())
        self.assertEqual(selected['runs'], self.saved['facts']['runs'])
        self.assertEqual(selected['memory'], memory_view())
        self.assertNotIn('grouping', selected)

    def test_plan_prose_still_selects_runs_but_reason_does_not(self):
        value = proposal(); value['plan']['updates'][0]['basis'] = ['P1:1']
        value['reason'] += ' Preserve P2:1.'
        self.assertEqual([r['ref'] for r in d.referenced_runs(value, self.saved['facts'])], ['P1'])
        value['plan']['goal'] += ' Preserve P2:1.'
        self.assertEqual(d.referenced_runs(value, self.saved['facts']), self.saved['facts']['runs'])

    def test_execution_scope_and_slash_lists_are_preserved(self):
        value = proposal(); value['reason'] += ' Compare P1/P2 and P1:1/P2:outcome.'
        d.diagnosis_call(self.saved).complete(value)
        for token in ('P99:1', 'P1/P99', 'Q1', 'P1/Q1', 'R03/P1/P2', 'Memory:M1'):
            bad = deepcopy(value); bad['reason'] += ' ' + token
            with self.subTest(token=token), self.assertRaises(ValueError): d.diagnosis_call(self.saved).complete(bad)

    def test_preconditioner_rejects_groups_in_reason_and_replacement(self):
        diagnosed = d.diagnosis_call(self.saved).complete(proposal())
        call = p.preconditioner_call(diagnosed, memory_view())
        for field in ('reason', 'text'):
            for token in ('G1', '`Group:G1`', 'Group:G1', '`Group:custom`'):
                value = decisions('REPLACE'); value['adjustments'][0][field] += ' ' + token
                with self.subTest(field=field, token=token), self.assertRaises(ValueError): call.complete(value)

    def test_preconditioner_actions_and_basis_are_unchanged(self):
        diagnosed = d.diagnosis_call(self.saved).complete(proposal())
        for action in ('KEEP', 'REPLACE', 'WITHDRAW'):
            result = p.preconditioner_call(diagnosed, memory_view()).complete(decisions(action))
            if action == 'WITHDRAW': self.assertIsNone(result['effective_plan'])
            else:
                self.assertEqual(result['effective_plan']['goal'], proposal()['plan']['goal'])
                self.assertEqual(result['effective_plan']['updates'][0]['basis'], proposal()['plan']['updates'][0]['basis'])
                self.assertEqual(result['effective_plan']['updates'][0]['text'],
                                 decisions(action)['adjustments'][0]['text'] if action == 'REPLACE'
                                 else proposal()['plan']['updates'][0]['text'])

    def test_source_failures_are_never_model_output_feedback(self):
        saved = deepcopy(self.saved); saved['facts']['parent'] += ' forged'
        for fn, args in ((facts.validate_parent_bundle, (saved,)), (d.diagnosis_input, (saved,))):
            with self.assertRaises(ValueError) as error:
                output_feedback.output_call('source', fn, *args)
            self.assertNotIsInstance(error.exception, output_feedback.OutputValidationError)
        bad = proposal(); bad['plan']['updates'][0]['basis'].append('G1')
        with self.assertRaises(output_feedback.OutputValidationError):
            output_feedback.output_call('diagnosis', d.diagnosis_call(self.saved).complete, bad)
