"""Version isolation and the four-prompt-only experimental boundary."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v29_5 import config as baseline
from src.skill_evolution.v29_2 import grouping
from src.skill_evolution.v29_6 import config, diagnosis, preconditioner, editor, replay, gate, memory, stages
from src.skill_evolution.v29_6 import evolution as ev, evaluation, output_feedback, facts
from src.skill_evolution.v29_6.campaign import CampaignAdapter, DEFAULT_CONFIG
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

    def test_config_changes_only_method_stage_and_four_prompt_identities(self):
        config.validate_config(self.config, executable=True)
        old = json.loads((ROOT / 'experiments/configs/v29_5_docvqa_optimization160.json').read_text())
        new = json.loads(DEFAULT_CONFIG.read_text())
        old['method']['version'] = 'v29_6_campaign_v1'
        old['method']['stage_contract'] = 'v29_6_stages_v1'
        for name in ('diagnosis', 'preconditioner', 'editor', 'replay'):
            old['method']['prompts'][name] = f'v29_6_docvqa_{name}_v1'
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
        for name in ('diagnosis', 'preconditioner', 'editor', 'replay'):
            mixed = deepcopy(self.config)
            mixed['method']['prompts'][name] = old_config['method']['prompts'][name]
            with self.subTest(prompt=name), self.assertRaises(ValueError): config.validate_config(mixed)
        self.assertEqual(self.actor.seen, [])

    def test_four_local_prompts_match_design_and_change_from_baseline(self):
        old, new = baseline.render_prompts(), config.render_prompts()
        self.assertEqual(set(old), set(new))
        self.assertEqual([k for k in new if new[k] != old[k]], list(config.MODEL_MODULES))
        prompt_root = ROOT / 'src/skill_evolution/v29_6/prompts'
        for name in config.MODEL_MODULES:
            module = config.MODULES[name]
            self.assertEqual(module.PROMPT_PATH, prompt_root / f'{name}.md')
            self.assertEqual(module.PROMPT_VERSION, f'v29_6_docvqa_{name}_v1')
            designed = (ROOT / f'docs/methods/v29_6/prompts/{name}.md').read_bytes()
            self.assertEqual(module.PROMPT_PATH.read_bytes(), designed)
            self.assertEqual(new[name], designed.decode())
        for name, suffix in (
            ('diagnosis', '## Decisions and exact output'),
            ('preconditioner', '## Full-text decisions and compilation'),
            ('editor', '## Exact unnumbered patch'),
        ):
            self.assertEqual(new[name].split(suffix)[1], old[name].split(suffix)[1])
        self.assertEqual(new['replay'].split('## Relate each hard transition')[0],
                         old['replay'].split('## Relate each hard transition')[0])

    def test_algorithms_and_local_upstream_bindings_are_preserved(self):
        for path in (ROOT / 'src/skill_evolution/v29_6').glob('*.py'):
            if path.name == 'campaign.py': continue  # Resource manifest changes deliberately.
            old = (ROOT / 'src/skill_evolution/v29_5' / path.name).read_text()
            new = path.read_text().replace('v29.6', 'v29.5')
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
        self.assertNotIn(str(baseline.MODULES['replay'].PROMPT_PATH.resolve()), sources)
        self.assertFalse(any('/v29_5/' in path for path in sources))

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
        for name, module in config.MODULES.items():
            stage = campaign / 'rounds/R01' / name
            self.assertEqual(ev.read(stage / 'identity.json')['prompt'], module.PROMPT_VERSION)
            self.assertEqual((stage / 'attempts/001/prompt.md').read_bytes(), module.PROMPT_PATH.read_bytes())

    def test_replay_prompt_is_required_in_its_local_package(self):
        missing = self.root / 'missing_replay.md'
        with patch.object(replay, 'PROMPT_PATH', missing), self.assertRaises(FileNotFoundError):
            config.render_prompts()
        self.assertEqual(self.actor.seen, [])

    def test_v29_5_and_v29_6_cannot_resume_each_others_campaigns(self):
        from src.skill_evolution.v29_5 import evolution as old_ev
        from src.skill_evolution.v29_5.campaign import CampaignAdapter as OldAdapter
        old_config = baseline.campaign_config(self.adapter, module_calls=self.config['module_calls'])
        new_root, old_root = self.root / 'new', self.root / 'old'
        ev.initialize(new_root, self.config)
        with OldAdapter(self.adapter.actor_adapter).using():
            with self.assertRaises(ValueError): old_ev.run_campaign(new_root, resume=True)
            old_ev.initialize(old_root, old_config)
        with self.assertRaises(ValueError): ev.run_campaign(old_root, resume=True)
        self.assertEqual(self.actor.seen, [])
