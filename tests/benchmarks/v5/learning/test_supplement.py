import unittest
from copy import deepcopy
from benchmark_v5.learning.protocol import config
from benchmark_v5.learning.supplement import amended_config

class Supplement(unittest.TestCase):
    def test_only_wait_and_metadata_change(self):
        before=config();saved=deepcopy(before);after=amended_config(before)
        self.assertEqual(before,saved)
        self.assertEqual(after['limits']['timeout_seconds'],600)
        after['limits']['timeout_seconds']=180
        after['protocol_id']=before['protocol_id'];del after['amendment']
        self.assertEqual(after,before)
