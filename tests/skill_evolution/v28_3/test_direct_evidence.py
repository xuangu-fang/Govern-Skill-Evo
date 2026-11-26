"""Direct full-batch analysis and evidence boundaries, using synthetic SearchQA."""
from copy import deepcopy
import json
from unittest.mock import patch

from src.skill_evolution.v28_2 import grouping as old_grouping
from src.skill_evolution.v28_3 import diagnosis, facts, preconditioner, output_feedback
from tests.skill_evolution.v28.runtime_support import Base
from .support import bind, Generator, no_hashes
from .test_editor import offline


class DirectEvidenceTests(Base):
    def setUp(self):
        super().setUp(); offline(self); self.enterContext(no_hashes())
        self.data, self.actor, self.adapter, self.config = bind(self.root / 'fixture', rounds=1, size=3)
        self.enterContext(self.adapter.using())
        self.folder = self.root / 'parents'
        self.records = self.adapter.actor_batch(self.data.batches[0], self.skill, self.folder,
                                               {'split': 'train', 'role': 'parent'})
        self.adapter.register_archive(self.folder)
        self.saved = facts.build_parent_bundle(self.records, 'R01')
        self.proposal = {'decision': 'revise', 'reason': 'P1:1 supports a scoped correction.',
                         'plan': {'goal': 'Preserve the requested entity.', 'updates': [
                             {'id': 'u1', 'text': 'Preserve question-required qualifiers.', 'basis': ['P1:1']}]}}

    def test_complete_success_and_failure_batch_without_grouping(self):
        with patch.object(old_grouping, 'grouping_call', side_effect=AssertionError('No Grouping')):
            call = diagnosis.diagnosis_call(self.saved)
            result = call.complete(self.proposal)
        self.assertEqual(set(self.saved), {'facts', 'background', 'sources', 'round_id'})
        self.assertEqual(set(json.loads(call.messages[1]['content'])), {'parent', 'runs', 'shared_initial'})
        self.assertEqual([r['outcome']['score']['em'] for r in result['facts']['runs']], [0.0, 1.0, 0.0])
        self.assertNotIn('grouping', result)

    def test_all_group_citations_rejected_in_all_diagnosis_fields(self):
        for token in ('G1', '`Group:G1`', 'Group:G1', '`Group:custom`'):
            for field in ('reason', 'goal', 'text', 'basis'):
                value = deepcopy(self.proposal)
                if field == 'reason': value[field] += ' ' + token
                elif field == 'goal': value['plan'][field] += ' ' + token
                elif field == 'text': value['plan']['updates'][0][field] += ' ' + token
                else: value['plan']['updates'][0][field].append(token)
                with self.subTest(token=token, field=field):
                    self.reject(diagnosis.diagnosis_call(self.saved).complete, value)
        self.reject(diagnosis.diagnosis_call(self.saved).complete,
                    {'decision': 'no_change', 'reason': 'See G1.', 'plan': None})

    def test_old_handoffs_and_additional_input_fields_rejected(self):
        value = deepcopy(self.saved); value['grouping'] = {'groups': []}
        self.reject(diagnosis.diagnosis_call, value)
        for key in ('grouping', 'memory', 'candidate'):
            value = deepcopy(self.saved['facts']); value[key] = {}
            self.reject(diagnosis.validate_input, value)

    def test_sources_order_skill_scores_and_context_are_rechecked(self):
        for records in (self.records[:1], self.records[::-1], self.records + self.records[:1]):
            self.reject(facts.build_parent_bundle, records, 'R01')
        for field in ('parent', 'response', 'score', 'source', 'background', 'context'):
            value = deepcopy(self.saved)
            if field == 'parent': value['facts']['parent'] += ' forged'
            elif field == 'response': value['facts']['runs'][0]['attempts'][0]['assistant']['content'] = 'forged'
            elif field == 'score': value['facts']['runs'][0]['outcome']['score']['em'] = 1.0
            elif field == 'source': value['sources'][0]['run_id'] = 'forged'
            elif field == 'background': value['background']['temperature'] = 0
            else: value['facts']['runs'][0]['initial']['task']['context'] += ' forged'
            with self.subTest(field=field): self.reject(diagnosis.diagnosis_call, value)
        call = diagnosis.diagnosis_call(self.saved)
        with patch.object(self.adapter, 'source_record', side_effect=ValueError('archive changed')):
            self.reject(call.complete, self.proposal)

    def test_plan_prose_selects_whole_runs_reason_does_not(self):
        value = deepcopy(self.proposal); value['reason'] += ' Preserve P2:1.'
        self.assertEqual([r['ref'] for r in diagnosis.referenced_runs(value, self.saved['facts'])], ['P1'])
        value['plan']['goal'] += ' Preserve P2:1.'
        saved = diagnosis.diagnosis_call(self.saved).complete(value)
        selected = preconditioner.preconditioner_input(saved, {'rounds': []})
        self.assertEqual(selected['runs'], self.saved['facts']['runs'][:2])
        self.assertNotIn('reason', selected); self.assertNotIn('grouping', selected)

    def test_preconditioner_rejects_group_sources_and_unselected_runs(self):
        saved = diagnosis.diagnosis_call(self.saved).complete(self.proposal)
        call = preconditioner.preconditioner_call(saved, {'rounds': []})
        for field in ('reason', 'text'):
            for token in ('G1', '`Group:G1`', 'Group:G1', '`Group:custom`', 'P2:1'):
                item = {'target': 'u1', 'action': 'REPLACE', 'text': 'Preserve scoped names.',
                        'reason': 'P1:1 supports this correction.'}
                item[field] += ' ' + token
                with self.subTest(field=field, token=token): self.reject(call.complete, {'adjustments': [item]})

    def test_source_errors_are_fatal_group_output_errors_are_retryable(self):
        value = deepcopy(self.saved); value['facts']['parent'] += ' forged'
        for fn in (facts.validate_parent_bundle, diagnosis.diagnosis_input):
            with self.assertRaises(ValueError) as caught:
                output_feedback.output_call('source', fn, value)
            self.assertNotIsInstance(caught.exception, output_feedback.OutputValidationError)
        value = deepcopy(self.proposal); value['plan']['updates'][0]['basis'].append('G1')
        with self.assertRaises(output_feedback.OutputValidationError):
            output_feedback.output_call('diagnosis', diagnosis.diagnosis_call(self.saved).complete, value)

    def test_one_execution_can_support_multiple_complete_updates(self):
        data, _, adapter, config = bind(self.root / 'single', rounds=1, size=1)
        with adapter.using():
            folder = self.root / 'single_parents'
            records = adapter.actor_batch(data.batches[0], self.skill, folder, {'split': 'train', 'role': 'parent'})
            adapter.register_archive(folder)
            call = diagnosis.diagnosis_call(facts.build_parent_bundle(records, 'single_R01'))
            output = Generator(count=2)(call.name, call.messages, self.root / 'R01/x/attempts/001',
                                        config['module_calls']['diagnosis'])
            self.assertEqual(len(call.complete_text(output['content'])['diagnosis']['plan']['updates']), 2)
