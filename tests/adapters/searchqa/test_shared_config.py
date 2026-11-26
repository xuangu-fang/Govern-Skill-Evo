"""Comparison preflight ignores v28 methods but still rejects shared-data drift."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from src.adapters.searchqa import skilladam as m

CONFIGS = (m.DEFAULT_CONFIG,
           m.ROOT / 'experiments/configs/searchqa_skilladam600_batch30_epoch1_deepseek_flash.json')
SHARED = ('actor', 'optimization_splits', 'optimization_pool', 'batches', 'initial_skill')


class SharedConfigTests(unittest.TestCase):
    def prepare_with(self, path, *, reference=None, config=None):
        original_read = m.read
        reference_path = m.ROOT / original_read(path)['v28_config']

        def read(selected):
            if selected == reference_path and reference is not None:
                return deepcopy(reference)
            if selected == path and config is not None:
                return deepcopy(config)
            return original_read(selected)

        with patch.object(m, 'read', side_effect=read):
            return m.prepare(path)

    def test_only_shared_reference_fields_are_needed_for_both_batch_sizes(self):
        for path in CONFIGS:
            with self.subTest(config=path.name):
                reference = m.read(m.ROOT / m.read(path)['v28_config'])
                shared = {key: reference[key] for key in SHARED}
                _, dataset, initial, native, _, snapshot = self.prepare_with(path, reference=shared)
                self.assertEqual(initial, shared['initial_skill']['text'])
                self.assertEqual(snapshot['batches'], shared['batches'])
                self.assertEqual(dataset.batches, shared['batches'])
                self.assertEqual(native.gate_profile, 'main-result')

    def test_shared_reference_mismatches_still_fail(self):
        mutations = {
            'actor': lambda r: r['actor'].update(max_tokens=1),
            'split': lambda r: r.update(optimization_splits=['test']),
            'pool': lambda r: r.update(optimization_pool='other'),
            'order': lambda r: r['batches'].reverse(),
            'missing_batch': lambda r: r['batches'].pop(),
            'initial_skill': lambda r: r['initial_skill'].update(text='different initial Skill'),
        }
        for path in CONFIGS:
            reference = m.read(m.ROOT / m.read(path)['v28_config'])
            for name, mutate in mutations.items():
                with self.subTest(config=path.name, mismatch=name):
                    bad = deepcopy(reference); mutate(bad)
                    with self.assertRaisesRegex(ValueError, 'differs from v28'):
                        self.prepare_with(path, reference=bad)

    def test_worker_limits_and_native_gate_remain_enforced(self):
        for path in CONFIGS:
            config = m.read(path)
            for key in ('workers', 'test_workers', 'gate_profile'):
                with self.subTest(config=path.name, mismatch=key):
                    bad = deepcopy(config)
                    if key == 'gate_profile':
                        bad['native'][key] = 'v28_em_only'
                    else:
                        bad[key] = 1
                    with self.assertRaises(ValueError):
                        self.prepare_with(path, config=bad)
