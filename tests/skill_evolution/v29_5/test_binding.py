"""Version isolation and the three-prompt-only experimental boundary."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v29_4 import config as baseline
from src.skill_evolution.v29_2 import grouping
from src.skill_evolution.v29_5 import config, diagnosis, preconditioner, editor, replay, gate, memory, stages
from src.skill_evolution.v29_5 import evolution as ev, evaluation, output_feedback, facts
from src.skill_evolution.v29_5.campaign import CampaignAdapter, DEFAULT_CONFIG
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

    def test_config_changes_only_method_stage_and_three_prompt_identities(self):
        config.validate_config(self.config, executable=True)
        old = json.loads((ROOT / 'experiments/configs/v29_4_docvqa_optimization160.json').read_text())
        new = json.loads(DEFAULT_CONFIG.read_text())
        old['method']['version'] = 'v29_5_campaign_v1'
        old['method']['stage_contract'] = 'v29_5_stages_v1'
        for name in ('diagnosis', 'preconditioner', 'editor'):
            old['method']['prompts'][name] = f'v29_5_docvqa_{name}_v1'
        self.assertEqual(new, old)
        self.assertEqual(config.MODEL_MODULES, ('diagnosis', 'preconditioner', 'editor', 'replay'))
        self.assertEqual(config.contracts(), baseline.contracts())
        self.assertEqual(config.execution_input_views(), baseline.execution_input_views())
        self.assertTrue(all(v['max_tokens'] == 32768 for v in new['module_calls'].values()))

    def test_old_and_mixed_versions_fail_before_requests(self):
        old_config = baseline.campaign_config(self.adapter, module_calls=self.config['module_calls'])
        with self.assertRaises(ValueError): baseline.validate_config(self.config)
        with self.assertRaises(ValueError): config.validate_config(old_config)
        for key in ('version', 'stage_contract', 'prompts'):
            mixed = deepcopy(self.config)
            mixed['method'][key] = old_config['method'][key]
            with self.subTest(key=key), self.assertRaises(ValueError): config.validate_config(mixed)
        for name in ('diagnosis', 'preconditioner', 'editor'):
            mixed = deepcopy(self.config)
            mixed['method']['prompts'][name] = old_config['method']['prompts'][name]
            with self.subTest(prompt=name), self.assertRaises(ValueError): config.validate_config(mixed)
        self.assertEqual(self.actor.seen, [])

    def test_three_local_prompts_change_and_replay_stays_identical(self):
        old, new = baseline.render_prompts(), config.render_prompts()
        self.assertEqual(set(old), set(new))
        self.assertEqual([k for k in new if new[k] != old[k]], ['diagnosis', 'preconditioner', 'editor'])
        prompt_root = ROOT / 'src/skill_evolution/v29_5/prompts'
        for name in ('diagnosis', 'preconditioner', 'editor'):
            self.assertEqual(config.MODULES[name].PROMPT_PATH, prompt_root / f'{name}.md')
        for phrase in ('relevant and available successes, failures and counterexamples',
                       'A single execution can also support a reasonable proposal',
                       'Not every execution needs to produce an Update'):
            self.assertIn(phrase, new['diagnosis'])
        # Runtime, evidence, output and patch contracts remain literal baseline text.
        for name, prefix, suffix in (
            ('diagnosis', '## Examine current evidence', '## Evidence'),
            ('preconditioner', '## Frozen proposal and available input', '## Full-text decisions and compilation'),
            ('editor', '## Input and implementation scope', '## Exact unnumbered patch'),
        ):
            self.assertEqual(new[name].split(prefix)[0], old[name].split(prefix)[0])
            self.assertEqual(new[name].split(suffix)[1], old[name].split(suffix)[1])

    def test_algorithms_and_local_upstream_bindings_are_preserved(self):
        for path in (ROOT / 'src/skill_evolution/v29_5').glob('*.py'):
            if path.name == 'campaign.py': continue  # Resource manifest changes deliberately.
            old = (ROOT / 'src/skill_evolution/v29_4' / path.name).read_text()
            new = path.read_text().replace('v29.5', 'v29.4')
            def definitions(value):
                return {n.name: ast.dump(n) for n in ast.parse(value).body
                        if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
            self.assertEqual(definitions(old), definitions(new), path.name)
        self.assertIs(editor.preconditioner, preconditioner)
        self.assertIs(replay.editor, editor)
        self.assertIs(gate.editor, editor)
        self.assertIs(gate.replay, replay)
        self.assertIs(memory.gate, gate)
        self.assertIs(memory.preconditioner, preconditioner)
        self.assertIs(evaluation.ev, ev)
        self.assertIs(output_feedback.diagnosis, diagnosis)

    def test_manifest_covers_local_code_prompts_and_reused_resources(self):
        sources = stages._source_hashes()
        for module in (config, diagnosis, preconditioner, editor, replay, gate, memory, stages,
                       ev, evaluation, output_feedback, facts):
            self.assertIn(str(Path(module.__file__).resolve()), sources)
        for module in config.MODULES.values():
            self.assertIn(str(module.PROMPT_PATH.resolve()), sources)
        for name in ('actor_io.py', 'explicit_references.py', 'execution_references.py', 'replay_input_view.py'):
            self.assertIn(str(ROOT / 'src/skill_evolution/v29_2' / name), sources)
        self.assertNotIn(str(baseline.MODULES['editor'].PROMPT_PATH.resolve()), sources)
        self.assertNotIn(str(grouping.PROMPT_PATH.resolve()), sources)
        self.assertFalse(any('/v29_4/' in path for path in sources))

    def test_full_round_loads_local_prompts_and_never_calls_grouping(self):
        generator = Generator(count=1)
        campaign = self.root / 'campaign'
        def generate(name, messages, directory, call_config):
            self.assertEqual(messages[0]['content'], config.render_prompts()[name])
            return generator(name, messages, directory, call_config)
        with patch.object(grouping, 'grouping_call', side_effect=AssertionError('No Grouping')):
            ev.run_campaign(campaign, config=self.config, generate=generate)
        self.assertEqual(generator.calls, list(config.MODEL_MODULES))
        self.assertFalse((campaign / 'rounds/R01/grouping').exists())
        self.assertEqual(ev.read(campaign / 'implementation.json')['prompts'], config.render_prompts())

    def test_v29_4_and_v29_5_cannot_resume_each_others_campaigns(self):
        from src.skill_evolution.v29_4 import evolution as old_ev
        from src.skill_evolution.v29_4.campaign import CampaignAdapter as OldAdapter
        old_config = baseline.campaign_config(self.adapter, module_calls=self.config['module_calls'])
        new_root, old_root = self.root / 'new', self.root / 'old'
        ev.initialize(new_root, self.config)
        with OldAdapter(self.adapter.actor_adapter).using():
            with self.assertRaises(ValueError): old_ev.run_campaign(new_root, resume=True)
            old_ev.initialize(old_root, old_config)
        with self.assertRaises(ValueError): ev.run_campaign(old_root, resume=True)
        self.assertEqual(self.actor.seen, [])
