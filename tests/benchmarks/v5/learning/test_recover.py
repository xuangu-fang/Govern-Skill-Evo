import unittest
from benchmark_v5.learning.recover import classify_learning,blocked_result

class Recovery(unittest.TestCase):
    def test_truncation_is_not_an_empty_learned_state(self):
        r={'usage':{'completion_tokens':8192},'deviations':['length'],'attempts':[]}
        self.assertEqual(classify_learning(r),'learning_budget_invalid')
    def test_missing_response_is_measurement_failure(self):
        self.assertEqual(classify_learning({'attempts':[{'error':'TimeoutError'}]}),'learning_transport_or_measurement_invalid')
    def test_not_executed_is_not_zero_business_score(self):
        r=blocked_result({'id':'LS-H1__processed'},'learning_budget_invalid')
        self.assertFalse(r['executed']);self.assertIsNone(r['score']);self.assertEqual(r['api_attempts'],0)
