"""Version isolation, unchanged algorithms and the exact ablation boundary."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v29_2 import config as baseline, grouping, preconditioner as old_p
from src.skill_evolution.v29_4 import config, diagnosis, preconditioner, editor, replay, gate, memory, stages
from src.skill_evolution.v29_4 import evolution as ev, evaluation, output_feedback, facts
from src.skill_evolution.v29_4.campaign import CampaignAdapter, DEFAULT_CONFIG
from src.skill_evolution.v29.benchmarks.docvqa import protocol
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from tests.skill_evolution.v29.test_actor import Base
from .campaign_support import bind, Generator
from .helpers import offline

ROOT = Path(__file__).resolve().parents[3]


class BindingTests(Base):
    def setUp(self):
        super().setUp()
        offline(self)
        self.data, self.actor, self.adapter, self.config = bind(self.root / 'fixture', sizes=(1,), mode='gain')
        self.enterContext(self.adapter.using())

    def test_four_stage_config_and_frozen_production_budgets(self):
        config.validate_config(self.config, executable=True)
        expected = ('diagnosis', 'preconditioner', 'editor', 'replay')
        self.assertEqual(config.MODEL_MODULES, expected)
        self.assertEqual(tuple(config.pending_calls()), expected)
        for table in (config.prompt_versions(), config.contracts(), config.execution_input_views()):
            self.assertNotIn('grouping', table)
        original = json.loads((ROOT / 'experiments/configs/v29_2_docvqa_optimization160_references_v4.json').read_text())
        actual = json.loads(DEFAULT_CONFIG.read_text())
        old_method, new_method = original.pop('method'), actual.pop('method')
        original['module_calls'].pop('grouping')
        self.assertEqual(original['module_calls']['editor']['max_tokens'], 16384)
        self.assertEqual(actual['module_calls']['editor']['max_tokens'], 32768)
        original['module_calls']['editor']['max_tokens'] = 32768
        self.assertEqual(actual, original)
        for section in ('prompts', 'contracts', 'execution_input_views'):
            old_method[section].pop('grouping')
        old_method['version'] = new_method['version']
        old_method['stage_contract'] = new_method['stage_contract']
        for section in ('prompts', 'contracts', 'execution_input_views'):
            for module in ('diagnosis', 'preconditioner'):
                old_method[section][module] = new_method[section][module]
        self.assertEqual(new_method, old_method)

    def test_old_and_mixed_versions_or_grouping_config_fail_before_requests(self):
        with self.assertRaises(ValueError): baseline.validate_config(self.config)
        old_calls = deepcopy(self.config['module_calls']); old_calls['grouping'] = deepcopy(old_calls['diagnosis'])
        old_config = baseline.campaign_config(self.adapter, module_calls=old_calls)
        with self.assertRaises(ValueError): config.validate_config(old_config)
        for key in ('version', 'stage_contract', 'prompts', 'contracts', 'execution_input_views', 'module_calls'):
            value = deepcopy(self.config)
            if key == 'module_calls': value[key]['grouping'] = deepcopy(value[key]['diagnosis'])
            elif key in ('version', 'stage_contract'): value['method'][key] = old_config['method'][key]
            else: value['method'][key]['grouping'] = old_config['method'][key]['grouping']
            with self.subTest(key=key), self.assertRaises(ValueError): config.validate_config(value)
        self.assertEqual(self.actor.seen, [])

    def test_only_required_prompts_change_and_cross_execution_is_not_a_threshold(self):
        old, new = baseline.render_prompts(), config.render_prompts()
        self.assertEqual(set(old) - set(new), {'grouping'})
        self.assertEqual([k for k in new if new[k] != old[k]], ['diagnosis', 'preconditioner'])
        self.assertEqual(new['editor'], old['editor'])
        self.assertEqual(new['replay'], old['replay'])
        for phrase in ('relevant and available successes, failures and counterexamples',
                       'A single execution can also support a reasonable proposal',
                       'Not every execution needs to produce an Update'):
            self.assertIn(phrase, new['diagnosis'])
        self.assertIn('Input contains exactly parent, runs and shared_initial.', new['diagnosis'])
        for name in ('diagnosis', 'preconditioner'):
            self.assertNotIn('grouping', new[name].lower())
            self.assertNotIn('Group:', new[name])
            self.assertNotIn('G1', new[name])
        # Proposal construction and historical reasoning stay v29.2, not v29.3.
        start, end = '## Construct complete, scoped Updates', '## Evidence'
        self.assertEqual(new['diagnosis'].split(start)[1].split(end)[0], old['diagnosis'].split(start)[1].split(end)[0])
        start, end = '## Relate historical edits', '## Explicit references'
        self.assertEqual(new['preconditioner'].split(start)[1].split(end)[0], old['preconditioner'].split(start)[1].split(end)[0])

    def test_downstream_algorithms_are_unchanged_and_use_new_upstream(self):
        for module in ('editor', 'replay', 'gate', 'memory'):
            trees = []
            for version in ('v29_2', 'v29_4'):
                tree = ast.parse((ROOT / 'src/skill_evolution' / version / f'{module}.py').read_text())
                trees.append({node.name: ast.dump(node) for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))})
            self.assertEqual(trees[0], trees[1], module)
        self.assertIs(editor.preconditioner, preconditioner)
        self.assertIs(replay.editor, editor)
        self.assertIs(gate.editor, editor)
        self.assertIs(gate.replay, replay)
        self.assertIs(memory.gate, gate)
        self.assertIs(memory.preconditioner, preconditioner)
        self.assertIs(evaluation.ev, ev)
        self.assertIs(output_feedback.diagnosis, diagnosis)

    def test_manifest_covers_actual_implementations_and_reused_resources(self):
        sources = stages._source_hashes()
        for module in (config, diagnosis, preconditioner, editor, replay, gate, memory, stages,
                       ev, evaluation, output_feedback, facts):
            self.assertIn(str(Path(module.__file__).resolve()), sources)
        for module in config.MODULES.values():
            self.assertIn(str(module.PROMPT_PATH.resolve()), sources)
        for name in ('actor_io.py', 'explicit_references.py', 'execution_references.py', 'replay_input_view.py'):
            self.assertIn(str(ROOT / 'src/skill_evolution/v29_2' / name), sources)
        self.assertNotIn(str(grouping.PROMPT_PATH.resolve()), sources)
        self.assertNotIn(str(Path(grouping.__file__).resolve()), sources)

    def test_full_round_never_calls_or_archives_grouping(self):
        generator = Generator(count=1); campaign = self.root / 'campaign'
        with patch.object(grouping, 'grouping_call', side_effect=AssertionError('No Grouping')):
            ev.run_campaign(campaign, config=self.config, generate=generator)
        self.assertEqual(generator.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'])
        self.assertFalse((campaign / 'rounds/R01/grouping').exists())
        self.assertEqual(set(ev.read(campaign / 'implementation.json')['prompts']), set(config.MODEL_MODULES))
        for name in config.MODEL_MODULES:
            saved = ev.read(campaign / 'rounds/R01' / name / 'input.json')
            def check(value):
                if isinstance(value, dict):
                    self.assertNotIn('grouping', value)
                    for item in value.values(): check(item)
                elif isinstance(value, list):
                    for item in value: check(item)
            check(saved)

    def test_config_prevents_cross_version_resume(self):
        from src.skill_evolution.v29_2 import evolution as old_ev
        from src.skill_evolution.v29_2.campaign import CampaignAdapter as OldAdapter
        from tests.skill_evolution.v29_2.campaign_support import bind as old_bind
        root = self.root / 'new'
        ev.initialize(root, self.config)
        with OldAdapter(self.adapter.actor_adapter).using(), self.assertRaises(ValueError):
            old_ev.run_campaign(root, resume=True)
        _, _, old_adapter, old_config = old_bind(self.root / 'old_data', sizes=(1,))
        old_root = self.root / 'old'
        with old_adapter.using(): old_ev.initialize(old_root, old_config)
        with self.assertRaises(ValueError): ev.run_campaign(old_root, resume=True)
