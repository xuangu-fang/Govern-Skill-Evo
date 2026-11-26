"""Offline v29.2 version/budget preflight; no campaign or credentials created."""
from copy import deepcopy
from unittest.mock import patch

from src.skill_evolution.v29 import config as old_config
from src.skill_evolution.v29_2 import config as c, editor, gate, memory
from tests.skill_evolution.v29.test_actor import Base
from tests.skill_evolution.v29.campaign_support import bind
from tests.skill_evolution.v29_2.test_editor import offline


class ConfigTests(Base):
    def setUp(self):
        super().setUp()
        offline(self)
        self.data, self.transport, self.adapter, self.old = bind(self.root / 'fixture')
        self.enterContext(self.adapter.using())
        self.config = c.campaign_config(self.adapter, module_calls=self.old['module_calls'])

    def test_versions_are_new_and_grouping_actor_scoring_are_preserved(self):
        c.validate_config(self.config, executable=True)
        self.assertEqual(self.config['method']['prompts']['grouping'], c.GROUPING_PROMPT)
        self.assertEqual(self.config['method']['prompts']['editor'], editor.PROMPT_VERSION)
        self.assertEqual(self.config['method']['contracts']['memory'], memory.FORMAT)
        self.assertEqual(self.config['gate_rule'], gate.CONTRACT_VERSION)
        self.assertEqual(self.config['actor'], self.old['actor'])
        self.assertEqual(set(self.config['module_calls']), set(c.MODEL_MODULES))
        self.assertNotIn('gate_metric', self.config)

    def test_pending_budgets_are_allowed_only_for_nonexecutable_preflight(self):
        pending = c.campaign_config(self.adapter)
        c.validate_config(pending)
        with self.assertRaises(ValueError): c.validate_config(pending, executable=True)
        for key in ('max_tokens', 'timeout_seconds'):
            bad = deepcopy(self.config); bad['module_calls']['editor'][key] = None
            with self.assertRaises(ValueError): c.validate_config(bad)

    def test_execution_view_versions_cannot_be_missing_stale_or_mixed(self):
        self.assertEqual(self.config['method']['execution_input_views'], c.execution_input_views())
        for kind in ('missing', 'grouping', 'diagnosis', 'preconditioner', 'extra'):
            bad = deepcopy(self.config)
            if kind == 'missing': del bad['method']['execution_input_views']
            else: bad['method']['execution_input_views'][kind] = 'old_complete_execution_v1'
            with self.subTest(kind=kind), self.assertRaises(ValueError): c.validate_config(bad)

    def test_old_versions_and_model_calls_for_gate_memory_are_rejected(self):
        with self.assertRaises(ValueError): c.validate_config(self.old)
        for kind in ('version', 'prompt', 'contract', 'gate_rule', 'gate', 'memory', 'missing'):
            bad = deepcopy(self.config)
            if kind == 'version': bad['method']['version'] = 'v29_1_campaign_v1'
            elif kind == 'prompt': bad['method']['prompts']['editor'] = 'v29_docvqa_editor_v1'
            elif kind == 'contract': bad['method']['contracts']['editor'] = 'unnumbered_diff_v1'
            elif kind == 'gate_rule': bad['gate_rule'] = 'v29_docvqa_hard_strict_increase_v1'
            elif kind == 'missing': del bad['module_calls']['replay']
            else: bad['module_calls'][kind] = deepcopy(bad['module_calls']['editor'])
            with self.subTest(kind=kind), self.assertRaises(ValueError): c.validate_config(bad)

    def test_stale_preconditioner_citation_versions_are_rejected(self):
        self.assertEqual(self.config['method']['prompts']['preconditioner'],
                         'v29_2_docvqa_preconditioner_v4')
        self.assertEqual(self.config['method']['contracts']['preconditioner'],
                         'v29_2_preconditioner_actions_v3')
        for section, version in [('prompts', 'v29_2_docvqa_preconditioner_v2'),
                                 ('contracts', 'v29_2_preconditioner_actions_v1')]:
            bad = deepcopy(self.config)
            bad['method'][section]['preconditioner'] = version
            with self.subTest(section=section), self.assertRaises(ValueError):
                c.validate_config(bad)

    def test_invalid_budgets_timeouts_and_context_capacity_are_rejected(self):
        for name in c.MODEL_MODULES:
            for key, value in (('max_tokens', True), ('max_tokens', 0), ('max_tokens', 1.5),
                               ('timeout_seconds', False), ('timeout_seconds', -1),
                               ('timeout_seconds', float('nan')), ('context_window_tokens', True),
                               ('context_window_tokens', 10)):
                bad = deepcopy(self.config); bad['module_calls'][name][key] = value
                with self.subTest(name=name, key=key, value=value), self.assertRaises(ValueError): c.validate_config(bad)
        good = deepcopy(self.config)
        good['module_calls']['replay']['context_window_tokens'] = 1000000
        c.validate_config(good, executable=True)

    def test_actor_method_settings_and_retry_bounds_are_frozen(self):
        for kind in ('actor', 'actor_bool', 'model', 'temperature', 'thinking', 'attempts', 'delay', 'capacity', 'semantic'):
            bad = deepcopy(self.config)
            if kind == 'actor': bad['actor']['max_tokens'] += 1
            elif kind == 'actor_bool': bad['actor']['temperature'] = True
            elif kind in ('model', 'temperature', 'thinking'):
                bad['module_calls']['diagnosis'][kind] = {'model': 'other', 'temperature': True, 'thinking': {}}[kind]
            elif kind == 'attempts': bad['max_attempts'] = 7
            elif kind == 'delay': bad['retry_delay_seconds'] = 0
            elif kind == 'capacity': bad['max_input_chars'] = True
            else: bad['method']['semantic_resampling'] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError): c.validate_config(bad)

    def test_schedule_data_and_test_isolation_are_checked(self):
        for kind in ('order', 'duplicate', 'unknown', 'test', 'empty', 'pool', 'initial', 'scorer'):
            bad = deepcopy(self.config)
            if kind == 'order': bad['batches'].reverse()
            elif kind == 'duplicate': bad['batches'][0][1] = bad['batches'][0][0]
            elif kind == 'unknown': bad['batches'][0][0] = 'missing'
            elif kind == 'test': bad['batches'][0][0] = self.data.splits['test'][0]
            elif kind == 'empty': bad['batches'] = []
            elif kind == 'pool': bad['optimization_pool'] = 'other'
            elif kind == 'initial': bad['initial_skill'] = 'other'
            else: bad['scorer_profile'] = 'other'
            with self.subTest(kind=kind), self.assertRaises(ValueError): c.validate_config(bad)

    def test_validation_is_read_only_detached_and_does_not_touch_transport(self):
        files = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        before = deepcopy(self.config)
        with patch.object(self.adapter, 'actor_batch', side_effect=AssertionError('No Actor preflight')):
            c.validate_config(self.config, executable=True)
        self.assertEqual(self.config, before)
        self.assertEqual(files, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(self.transport.seen, [])
        other = c.campaign_config(self.adapter, module_calls=self.config['module_calls'])
        other['module_calls']['editor']['max_tokens'] = 7
        self.assertEqual(self.config, before)
        old_config.validate_config(self.old, executable=True)
