"""Synthetic execution only; verify selected prompts and version isolation."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from unittest.mock import patch

from scripts.runs import run_v29_campaign as shared_cli, run_v29_1_campaign as cli
from src.skill_evolution.v29 import evolution, modules, stages
from src.skill_evolution.v29.campaign import CampaignAdapter as V29Adapter
from src.skill_evolution.v29.config import campaign_config, validate_config
from src.skill_evolution.v29.benchmarks.docvqa import prompting, protocol as p
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
from src.skill_evolution.v29_1.campaign import CampaignAdapter, DEFAULT_CONFIG, PROMPT_ROOT, PROMPT_VERSIONS
from tests.skill_evolution.v29 import test_campaign as inherited_campaign
from tests.skill_evolution.v29 import campaign_support as support
from tests.skill_evolution.v29.test_actor import Base, FIVE, response
from tests.skill_evolution.v29.test_campaign import snapshot
from tests.skill_evolution.v29.test_method import MethodBase, main_example


def bind(root, **kwargs):
    data, transport, original, config = support.bind(root, **kwargs)
    adapter = CampaignAdapter(original.actor_adapter)
    return data, transport, adapter, campaign_config(adapter, module_calls=config['module_calls'])


class InheritedCampaignTests(inherited_campaign.CampaignTests):
    """Exercise the same acceptance/recovery scenarios with the v29.1 binding."""
    def setUp(self):
        super().setUp()
        self.enterContext(patch.object(inherited_campaign, 'bind', bind))
        self.enterContext(patch.object(inherited_campaign, 'CampaignAdapter', CampaignAdapter))


class PromptBindingTests(MethodBase):
    def test_same_inputs_and_contracts_only_two_system_prompts_change(self):
        grouped = modules.grouping_call(self.parent(), 'R02').complete(main_example('grouping'))
        old_diagnosis = modules.diagnosis_call(grouped)
        diagnosed = old_diagnosis.complete(main_example('diagnosis'))
        from src.skill_evolution.v27.contracts import memory
        old_preconditioner = modules.preconditioner_call(diagnosed, memory.empty_memory())
        adapter = CampaignAdapter(self.adapter)
        adapter.register_archive(self.parent_dir)
        with adapter.using():
            new_diagnosis = modules.diagnosis_call(grouped)
            self.assertEqual(new_diagnosis.complete(main_example('diagnosis')), diagnosed)
            new_preconditioner = modules.preconditioner_call(diagnosed, memory.empty_memory())
            self.assertEqual(new_preconditioner.complete(main_example('preconditioner')),
                             old_preconditioner.complete(main_example('preconditioner')))
            for old, new in ((old_diagnosis, new_diagnosis), (old_preconditioner, new_preconditioner)):
                self.assertEqual(old.input, new.input)
                self.assertEqual(old.messages[1:], new.messages[1:])
                self.assertNotEqual(old.messages[0], new.messages[0])
                self.assertEqual(new.messages[0]['content'], (PROMPT_ROOT / f'{new.name}.md').read_text())
            for name in prompting.PROMPT_VERSIONS:
                expected = PROMPT_ROOT / f'{name}.md' if name in ('diagnosis', 'preconditioner') else FIVE / 'prompts' / f'{name}.md'
                self.assertEqual(prompting.render(name, p.actor_config()), expected.read_text())
            self.assertEqual(prompting.prompt_versions(), PROMPT_VERSIONS)
            with self.assertRaises(ValueError):
                prompting.render('diagnosis', p.actor_config(), prompt_version=prompting.PROMPT_VERSIONS['diagnosis'])
        self.assertEqual(prompting.prompt_versions(), prompting.PROMPT_VERSIONS)
        self.assertEqual(prompting.render('diagnosis', p.actor_config()), (FIVE / 'prompts/diagnosis.md').read_text())


class RuntimeTests(Base):
    def test_formal_config_changes_only_method_and_two_prompt_ids(self):
        original = stages.read(p.ROOT / 'experiments/configs/v29_docvqa_optimization160.json')
        revised = stages.read(DEFAULT_CONFIG)
        restored = deepcopy(revised)
        restored['method']['version'] = original['method']['version']
        for name in ('diagnosis', 'preconditioner'):
            restored['method']['prompts'][name] = original['method']['prompts'][name]
        self.assertEqual(restored, original)
        actor = DocVQAActorAdapter(DocVQADataset())
        for adapter, accepted, rejected in ((V29Adapter(actor), original, revised),
                                             (CampaignAdapter(actor), revised, original)):
            with adapter.using():
                validate_config(accepted, executable=True)
                with self.assertRaises(ValueError): validate_config(rejected, executable=True)

    def test_cli_validate_only_uses_new_prompts_without_credentials_or_output(self):
        output = self.root / 'not_created'
        rendered = []
        original = prompting.render
        def render(name, *args, **kwargs):
            text = original(name, *args, **kwargs)
            rendered.append((name, text))
            return text
        stream = io.StringIO()
        with patch.object(shared_cli, 'read_credentials', side_effect=AssertionError('No credentials')), \
             patch.object(shared_cli, 'ChatTransport', side_effect=AssertionError('No transport')), \
             patch.object(prompting, 'render', render), redirect_stdout(stream):
            cli.main(['train', str(output), '--validate-only', '--env-file', 'absent.env'])
        report = json.loads(stream.getvalue())
        self.assertEqual(report['method'], 'v29_1_campaign_v1')
        self.assertEqual(report['prompts'], PROMPT_VERSIONS)
        self.assertEqual(report['batch_sizes'], [15] * 10 + [10])
        self.assertEqual((report['train_workers'], report['test_workers']), (15, 60))
        self.assertEqual(len(rendered), 5)
        self.assertEqual(dict(rendered)['diagnosis'], (PROMPT_ROOT / 'diagnosis.md').read_text())
        self.assertFalse(output.exists())

    def test_cli_rejects_other_version_before_credentials(self):
        with patch.object(shared_cli, 'read_credentials', side_effect=AssertionError('No credentials')):
            with self.assertRaises(ValueError):
                cli.main(['train', str(self.root / 'new'), '--config',
                          str(p.ROOT / 'experiments/configs/v29_docvqa_optimization160.json')])
            with self.assertRaises(ValueError):
                shared_cli.main(['train', str(self.root / 'old'), '--config', str(DEFAULT_CONFIG)])
        self.assertFalse((self.root / 'new').exists())
        self.assertFalse((self.root / 'old').exists())

    def test_cli_rejects_missing_prompt_before_credentials(self):
        output = self.root / 'not_created'
        with patch('src.skill_evolution.v29_1.campaign.PROMPT_ROOT', self.root / 'missing'), \
             patch.object(shared_cli, 'read_credentials', side_effect=AssertionError('No credentials')):
            with self.assertRaises(FileNotFoundError):
                cli.main(['train', str(output)])
        self.assertFalse(output.exists())

    def test_cli_train_test_and_resume_route_through_v29_1(self):
        data, transport, _, config = bind(self.root / 'fixture', rounds=1, batch_size=1)
        config_file = self.root / 'config.json'; stages.save(config_file, config)
        root, output = self.root / 'campaign', self.root / 'evaluation'
        generator = support.Generator()
        with patch.object(shared_cli, 'DocVQADataset', return_value=data), \
             patch.object(shared_cli, 'read_credentials', return_value={'OPENAI_API_KEY': 'synthetic-only'}), \
             patch.object(shared_cli, 'ChatTransport', return_value=transport), \
             patch.object(shared_cli, 'HTTPGenerator', return_value=generator), redirect_stdout(io.StringIO()):
            cli.main(['train', str(root), '--config', str(config_file)])
            self.assertEqual(stages.read(root / 'config.json')['method']['version'], 'v29_1_campaign_v1')
            self.assertEqual(len(transport.seen), 2)
            cli.main(['train', str(root), '--config', str(config_file), '--resume'])
            self.assertEqual(len(transport.seen), 2)
            before = snapshot(root)
            cli.main(['test', str(root), '--output', str(output)])
            self.assertEqual(len(transport.seen), 3)
            cli.main(['test', str(root), '--output', str(output), '--resume'])
            self.assertEqual(len(transport.seen), 3)
            self.assertEqual(snapshot(root), before)
        self.assertEqual(generator.calls, ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'])

    def test_cross_version_resume_and_audit_reject_without_requests_or_state_changes(self):
        for source_type, other_type in ((V29Adapter, CampaignAdapter), (CampaignAdapter, V29Adapter)):
            data, transport, fixture, fixture_config = bind(self.root / source_type.__module__.split('.')[-2], rounds=1, batch_size=1)
            adapter = source_type(fixture.actor_adapter)
            config = campaign_config(adapter, module_calls=fixture_config['module_calls'])
            root = self.root / ('run_' + source_type.__module__.split('.')[-2])
            generator = support.Generator()
            with adapter.using(): evolution.run_campaign(root, config=config, generate=generator)
            before = snapshot(root); calls = (len(transport.seen), len(generator.calls))
            with other_type(DocVQAActorAdapter(data, transport)).using():
                with self.assertRaises(ValueError): evolution.run_campaign(root, resume=True, generate=generator)
                with self.assertRaises(ValueError): evolution.final_parent(root)
            self.assertEqual(snapshot(root), before)
            self.assertEqual(calls, (len(transport.seen), len(generator.calls)))

    def test_saved_stage_identity_and_messages_use_v29_1(self):
        data, transport, adapter, config = bind(self.root / 'fixture', rounds=1, batch_size=1)
        root = self.root / 'campaign'; generator = support.Generator()
        with adapter.using(): evolution.run_campaign(root, config=config, generate=generator)
        for name, messages in zip(generator.calls, generator.messages):
            folder = root / 'rounds/R01' / name
            self.assertEqual(stages.read(folder / 'identity.json')['prompt'], PROMPT_VERSIONS[name])
            self.assertEqual(stages.read(folder / 'base_messages.json'), messages)
            self.assertEqual(messages[0]['content'], adapter.resource(f'{name}.md').read_text())
        before = snapshot(root)
        with CampaignAdapter(DocVQAActorAdapter(data)).using(): evolution.final_parent(root)
        self.assertEqual(snapshot(root), before)

    def test_full_schedule_then_374_synthetic_test_cases_and_completed_resume(self):
        data, transport, adapter, config = bind(self.root / 'fixture', sizes=[15] * 10 + [10])
        data.splits['test'] = [f'synthetic:test{i}' for i in range(374)]
        for task in data.splits['test']: data.rows[task] = ('Held-out synthetic question?', ['secret'], 'test')
        root, output = self.root / 'campaign', self.root / 'evaluation'
        generator = support.Generator(no_change='diagnosis')
        with adapter.using(), redirect_stdout(io.StringIO()):
            summary = shared_cli.run_training(root, config, generate=generator)
            self.assertEqual(summary['rounds_completed'], 11)
            self.assertFalse(summary['test_started'])
            self.assertEqual(len(transport.seen), 160)
            self.assertEqual(shared_cli.run_training(root, config, generate=generator, resume=True), summary)
            self.assertEqual(len(transport.seen), 160)
            before = snapshot(root)
            transport.generate = lambda *args: response('<answer>secret</answer>')
            result = shared_cli.run_test(root, output)
            self.assertEqual(result['sample_count'], 374)
            self.assertEqual(result['success_count'], 374)
            self.assertEqual(len(transport.seen), 534)
            self.assertEqual((output / 'skill.md').read_text(), (root / 'final_skill.md').read_text())
            self.assertEqual(stages.read(output / 'evaluation.json')['tasks'], data.splits['test'])
            self.assertEqual(shared_cli.run_test(root, output, resume=True), result)
            self.assertEqual(len(transport.seen), 534)
            self.assertEqual(snapshot(root), before)
        self.assertEqual(generator.calls, ['grouping', 'diagnosis'] * 11)

    def test_incomplete_training_cannot_start_test(self):
        _, transport, adapter, config = bind(self.root / 'fixture')
        root, output = self.root / 'campaign', self.root / 'evaluation'
        with adapter.using():
            evolution.initialize(root, config)
            with self.assertRaises(ValueError): shared_cli.run_test(root, output)
        self.assertFalse(output.exists())
        self.assertEqual(transport.seen, [])
