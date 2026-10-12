import unittest
from benchmark_v5.learning.cases import heldout_cases,world_for
from benchmark_v5.learning.interface_revision import build
from benchmark_v5.learning.evaluation import evaluate

class InterfaceRevision(unittest.TestCase):
    def test_typed_tools_remove_ambiguous_prediction(self):
        for c in heldout_cases():
            env=build(c,world_for(c['kind']));names={t['name'] for t in env.catalog()}
            self.assertNotIn('record_prediction',names)
            self.assertIn('predict_return' if c['kind']=='LS1' else 'predict_documents',names)
            public=env.request().get('policy',env.request().get('public_policy'))
            self.assertIn('自行选择新的非空字符串',public)

    def test_ls_multiple_predictions_are_canonical_and_immutable(self):
        c=heldout_cases()[0];env=build(c,world_for('LS1'))
        for item,released in zip(c['allowed_returns'],(True,False)):
            self.assertNotIn('error',env.call('predict_return',dict(item_id=item,refund_cents=6000,available_on_acceptance=released)))
        self.assertEqual(evaluate(env.audit())['prediction_correct'],2)
        self.assertFalse(evaluate(env.audit())['S'])
        self.assertIn('error',env.call('predict_return',dict(item_id=c['allowed_returns'][0],refund_cents=1,available_on_acceptance=True)))

    def test_lg_prediction_has_one_boolean_schema(self):
        c=heldout_cases()[7];env=build(c,world_for('LG1'))
        self.assertIn('error',env.call('predict_documents',{'available_documents_sufficient':'false'}))
        env.call('predict_documents',{'available_documents_sufficient':False})
        self.assertEqual(evaluate(env.audit())['prediction_correct'],1)
        self.assertFalse(evaluate(env.audit())['full_service'])
