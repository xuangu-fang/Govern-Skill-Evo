import unittest
from benchmark_v5.sc import pilot_budget, pilot_low, pilot


class BudgetProtocol(unittest.TestCase):
    def test_only_output_limit_and_run_classification_change_from_low(self):
        before, after = pilot_low.low_config(), pilot_budget.budget_config()
        self.assertEqual(before['limits']['max_tokens_per_call'],8192)
        self.assertEqual(after['limits']['max_tokens_per_call'],16384)
        self.assertEqual(after['limits']['completion_tokens'],32768)
        after['limits']['max_tokens_per_call']=before['limits']['max_tokens_per_call']
        after['classification']=before['classification']
        self.assertEqual(before,after)
        self.assertEqual(pilot.config()['limits']['max_tokens_per_call'],8192)

    def test_run_destination_is_separate(self):
        self.assertNotEqual(pilot_budget.DEST,pilot_low.DEST)
        self.assertNotEqual(pilot_budget.DEST,pilot.DEST)
