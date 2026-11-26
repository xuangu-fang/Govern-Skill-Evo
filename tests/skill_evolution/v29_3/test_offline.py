"""No live models: authored outputs test wiring, not semantic prompt quality."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v29.benchmarks.docvqa import protocol
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29_2 import config as old_config, diagnosis as old_d, preconditioner as old_p
from src.skill_evolution.v29_2 import evolution as old_ev, stages as old_stages
from src.skill_evolution.v29_2 import editor, replay, gate, memory, grouping, actor_io
from src.skill_evolution.v29_2.campaign import CampaignAdapter as OldAdapter
from src.skill_evolution.v29_3 import config, diagnosis as d, preconditioner as p, evolution as ev, stages
from src.skill_evolution.v29_3 import evaluation, memory as runtime_memory
from src.skill_evolution.v29_3.campaign import CampaignAdapter, DEFAULT_CONFIG
from tests.skill_evolution.v29.test_actor import Base, response
from tests.skill_evolution.v29.test_campaign import snapshot
from tests.skill_evolution.v29.test_method import MethodBase, main_example
from tests.skill_evolution.v29_2.test_diagnosis import proposal
from tests.skill_evolution.v29_2.test_preconditioner import memory_view, decisions
from tests.skill_evolution.v29_2.test_editor import offline
from tests.skill_evolution.v29_2.campaign_support import bind as old_bind, Generator

ROOT = Path(__file__).resolve().parents[3]


def bind(root, **kwargs):
    data, actor, previous, original = old_bind(root, **kwargs)
    adapter = CampaignAdapter(previous.actor_adapter)
    return data, actor, adapter, config.campaign_config(adapter, module_calls=original['module_calls'])


class BindingTests(Base):
    def setUp(self):
        super().setUp()
        offline(self)
        self.data, self.actor, self.adapter, self.config = bind(self.root / 'fixture')
        self.enterContext(self.adapter.using())

    def test_config_has_only_authorized_changes(self):
        config.validate_config(self.config, executable=True)
        original = old_config.campaign_config(self.adapter, module_calls=self.config['module_calls'])
        normalized = deepcopy(self.config)
        normalized['method']['version'] = original['method']['version']
        for name in ('diagnosis', 'preconditioner'):
            normalized['method']['prompts'][name] = original['method']['prompts'][name]
        self.assertEqual(normalized, original)
        disk = json.loads(DEFAULT_CONFIG.read_text())
        baseline = json.loads((ROOT / 'experiments/configs/v29_2_docvqa_optimization160_references_v4.json').read_text())
        self.assertEqual(disk['module_calls']['editor']['max_tokens'], 32768)
        disk['module_calls']['editor']['max_tokens'] = baseline['module_calls']['editor']['max_tokens']
        disk['method'] = baseline['method']
        self.assertEqual(disk, baseline)
        self.assertEqual(config.contracts(), old_config.contracts())
        self.assertEqual(config.execution_input_views(), old_config.execution_input_views())

    def test_only_two_system_prompts_change(self):
        old, new = old_config.render_prompts(), config.render_prompts()
        self.assertEqual([name for name in old if old[name] != new[name]], ['diagnosis', 'preconditioner'])
        for name, begin, end in (
            ('diagnosis', '## Examine current evidence', '## Evidence'),
            ('preconditioner', '## Historical Memory by round', '## Full-text decisions and compilation'),
        ):
            self.assertEqual(old[name].split(begin)[0], new[name].split(begin)[0])
            self.assertEqual(old[name].split(end)[1], new[name].split(end)[1])
        for name in ('diagnosis', 'preconditioner'):
            for answer in ('Pathmark', 'Pfizer', 'FAIRWAY', '66909', 'MEXICO'):
                self.assertNotIn(answer, new[name])

    def test_prompt_design_keeps_the_agreed_decision_boundaries(self):
        diagnostic, historical = config.render_prompts()['diagnosis'], config.render_prompts()['preconditioner']
        for clause in ('Organize Updates around the common problems identified in the current task analysis',
                       'necessary dependencies of the same correction together as one complete Update',
                       'Updates may share evidence and require coordination',
                       'Multiple justified Updates may be proposed in the same round',
                       'Joint testing alone is not a reason to merge them',
                       'independently isolated effects are not required',
                       'Correcting one output discrepancy does not automatically justify also changing answer encoding',
                       'Such acceptance alone does not support making one form a general preference',
                       'Actor-visible decision relationship',
                       'express the resulting applicability boundary in Update text',
                       'without a successful example for every covered situation'):
            self.assertIn(clause, diagnostic)
        self.assertNotIn('a coherent reason for being tested together', diagnostic)
        self.assertNotIn('would reasonably warrant separate retention or withdrawal', diagnostic)
        self.assertNotIn('independently justified', diagnostic)
        for clause in ('A round has no Knowledge entries only when its entries array is empty',
                       'no Knowledge entry is explicitly associated with that Update',
                       'Replay attributed the event to a specific Update in a joint comparison',
                       'not an independently isolated causal effect or a guarantee that the association is strong',
                       'Assess its stated behavioral basis and limitations from the supplied content',
                       'Neither null attribution nor association with a different Update alone establishes irrelevance',
                       'not a preference for KEEP, REPLACE or WITHDRAW',
                       'Do not infer such a report merely from Defer',
                       'Merely naming an exception does not establish that it protects',
                       'do not require an observed success for every covered situation',
                       'limited evidence of preservation on that task, not superiority or general safety',
                       'a scoped experiment may still be justified by other evidence',
                       'Such additions need grounds related to the Original problem'):
            self.assertIn(clause, historical)
        for prompt in (diagnostic, historical):
            self.assertIn("General Skill guidance must not override the question's explicit output requirements", prompt)
            self.assertIn("scoring acceptability for that task, not a preference among them", prompt)
        self.assertNotIn('a reported clear behavioral association', historical)

    def test_versions_budgets_and_contracts_cannot_be_mixed(self):
        before = deepcopy(self.config)
        for key in ('version', 'diagnosis', 'preconditioner', 'contract', 'budget', 'actor'):
            bad = deepcopy(self.config)
            if key == 'version': bad['method']['version'] = old_config.METHOD_VERSION
            elif key in ('diagnosis', 'preconditioner'):
                bad['method']['prompts'][key] = old_config.prompt_versions()[key]
            elif key == 'contract': bad['method']['contracts']['diagnosis'] = 'other'
            elif key == 'budget': bad['module_calls']['diagnosis']['max_tokens'] = 0
            else: bad['actor']['temperature'] = 0.5
            with self.subTest(key=key), self.assertRaises(ValueError):
                config.validate_config(bad, executable=True)
        with self.assertRaises(ValueError): old_config.validate_config(self.config)
        for new, old in ((d, old_d), (p, old_p)):
            with self.assertRaises(ValueError): new.render_prompt(protocol.actor_config(), prompt_version=old.PROMPT_VERSION)
            with self.assertRaises(ValueError): old.render_prompt(protocol.actor_config(), prompt_version=new.PROMPT_VERSION)
        self.assertEqual(self.config, before)
        self.assertEqual(self.actor.seen, [])

    def test_shared_modules_and_source_manifest_are_complete(self):
        for name, module in [('grouping', grouping), ('editor', editor), ('replay', replay),
                             ('gate', gate)]:
            self.assertIs(getattr(ev, name), module)
        self.assertIs(evaluation.actor_io, actor_io)
        sources = stages._source_hashes()
        for module in (d, p, config, stages, ev, evaluation, editor, replay, gate, memory):
            self.assertIn(str(Path(module.__file__).resolve()), sources)
        for path in (d.PROMPT_PATH, p.PROMPT_PATH, old_d.PROMPT_PATH, old_p.PROMPT_PATH,
                     ROOT / 'scripts/runs/run_v29_3_campaign.py'):
            self.assertIn(str(path.resolve()), sources)

    def test_stage_logic_remains_the_same_and_history_audit_is_removed(self):
        original = (ROOT / 'src/skill_evolution/v29_2/stages.py').read_text()
        original = original.replace(
            'from . import config as settings, output_feedback as feedback, grouping, diagnosis, preconditioner, editor, replay',
            'from . import config as settings, diagnosis, preconditioner\nfrom src.skill_evolution.v29_2 import output_feedback as feedback, grouping, editor, replay')
        self.assertEqual(original, (ROOT / 'src/skill_evolution/v29_3/stages.py').read_text())
        self.assertFalse(hasattr(ev, '_audit_published'))
        self.assertIs(ev.memory, runtime_memory)

    def test_cli_preflight_has_no_credentials_execution_or_campaign_write(self):
        from scripts.runs import run_v29_3_campaign as cli
        path, root = self.root / 'config.json', self.root / 'preflight'
        ev.save(path, self.config)
        with patch.object(cli, 'DocVQADataset', return_value=self.data), \
             patch.object(cli, 'read_credentials', side_effect=AssertionError('No credentials')), \
             patch.object(cli, 'run_training', side_effect=AssertionError('No training')), \
             patch.object(cli, 'run_test', side_effect=AssertionError('No Test')):
            cli.main(['train', str(root), '--config', str(path), '--validate-only'])
        self.assertFalse(root.exists())


class CallTests(MethodBase):
    def setUp(self):
        super().setUp()
        offline(self)
        self.method = CampaignAdapter(self.adapter)
        self.enterContext(self.method.using())
        self.grouped = grouping.grouping_call(self.parent(), 'R01').complete(main_example('grouping'))

    def test_diagnosis_changes_only_system_prompt_and_version(self):
        old, new = old_d.diagnosis_call(self.grouped), d.diagnosis_call(self.grouped)
        self.assertEqual(old.input, new.input)
        self.assertEqual(old.messages[1:], new.messages[1:])
        self.assertEqual(old.contract_version, new.contract_version)
        self.assertEqual(new.prompt_version, d.PROMPT_VERSION)
        self.assertEqual(new.messages[0]['content'], d.render_prompt(protocol.actor_config()))
        self.assertEqual(old.complete(proposal()), new.complete(proposal()))
        bad = proposal(); bad['plan']['checks'] = []
        for call in (old, new):
            with self.assertRaises(ValueError): call.complete(bad)

    def test_preconditioner_preserves_history_null_attribution_and_all_actions(self):
        saved = d.diagnosis_call(self.grouped).complete(proposal())
        history = memory_view()
        history['rounds'].append({'round_id': 'empty_round', 'source_updates': [
            {'id': 'u1', 'text': 'A prior verification proposal.', 'gate_decision': 'Defer'}], 'entries': []})
        before = deepcopy((saved, history))
        old, new = old_p.preconditioner_call(saved, history), p.preconditioner_call(saved, history)
        self.assertEqual(old.input, new.input)
        self.assertEqual(old.messages[1:], new.messages[1:])
        self.assertEqual(new.contract_version, old.contract_version)
        self.assertEqual(new.messages[0]['content'], p.render_prompt(protocol.actor_config()))
        payload = json.loads(new.messages[1]['content'])
        self.assertEqual(payload['memory'], history)
        self.assertNotIn('reason', payload['plan'])
        for action in ('KEEP', 'REPLACE', 'WITHDRAW'):
            self.assertEqual(old.complete(decisions(action)), new.complete(decisions(action)))
        self.assertEqual((saved, history), before)
        bad = decisions('REPLACE'); bad['adjustments'][0]['target'] = 'u99'
        for call in (old, new):
            with self.assertRaises(ValueError): call.complete(bad)

    def test_separate_targets_keep_complete_rules_and_compile_independently(self):
        value = proposal()
        value['plan']['updates'] = [
            {'id': 'u1', 'text': '- Verify punctuation spacing after selecting the answer; preserve its words.\n',
             'basis': ['P1:1']},
            {'id': 'u2', 'text': '- Verify each digit after selecting the identifier; do not change the requested field.\n',
             'basis': ['P2:1']},
        ]
        saved = d.diagnosis_call(self.grouped).complete(value)
        output = decisions('KEEP', 'WITHDRAW')
        result = p.preconditioner_call(saved, {'rounds': []}).complete(output)
        self.assertEqual(result['effective_plan']['updates'], [value['plan']['updates'][0]])
        self.assertEqual(saved['diagnosis'], value)

    def test_stage_journal_uses_new_prompt_and_rejects_cross_version_calls(self):
        calls = config.pending_calls()
        for call in calls.values(): call.update(max_tokens=1000, timeout_seconds=1)
        options = dict(call_config=calls['diagnosis'], max_attempts=6,
                       max_input_chars=4000000, max_message_utf8_bytes=6000000)
        sent = []
        def generate(name, messages, directory, call_config):
            sent.append(deepcopy(messages))
            return {'content': json.dumps(proposal()), 'finish_reason': 'stop'}
        root = self.root / 'stage'
        new, old = d.diagnosis_call(self.grouped), old_d.diagnosis_call(self.grouped)
        stages.run_stage(root, new, generate=generate, **options)
        self.assertEqual(sent[0], new.messages)
        self.assertEqual(ev.read(root / 'identity.json')['prompt'], d.PROMPT_VERSION)
        before = snapshot(root)
        stages.run_stage(root, new, read_only=True, **options)
        with self.assertRaises(ValueError): stages.run_stage(root, old, generate=generate, resume=True, **options)
        with self.assertRaises(ValueError): old_stages.run_stage(root, new, generate=generate, resume=True, **options)
        self.assertEqual(len(sent), 1)
        self.assertEqual(before, snapshot(root))


class CampaignTests(Base):
    def setUp(self):
        super().setUp()
        offline(self)

    def test_authored_full_loop_exports_selected_skill_and_synthetic_test(self):
        from scripts.runs.run_v29_3_campaign import run_training
        data, actor, adapter, cfg = bind(self.root / 'fixture')
        root = self.root / 'campaign'
        generator = Generator()
        def generate(name, messages, directory, call_config):
            self.assertEqual(messages[0]['content'], config.render_prompts()[name])
            return generator(name, messages, directory, call_config)
        with adapter.using():
            summary = run_training(root, cfg, generate=generate)
            self.assertEqual(summary['method'], config.METHOD_VERSION)
            self.assertFalse(summary['test_started'])
            self.assertEqual(summary['selected_execution_source'], 'parent')
            first = ev.read(root / 'rounds/R01/gate/result.json')
            self.assertIsNone(first['selected_execution_source'])
            self.assertEqual(first['selection']['selected_update_ids'], ['u1'])
            self.assertEqual([item['gate_decision'] for item in first['decisions']], ['Retain', 'Reject'])
            histories = [value['memory'] for name, value in generator.inputs if name == 'preconditioner']
            self.assertEqual(histories[0], {'rounds': []})
            self.assertEqual(len(histories[1]['rounds']), 1)
            with patch.object(actor, 'generate', return_value=response('<answer>1,320</answer>')):
                test = evaluation.run_test(root, self.root / 'synthetic_test')
            self.assertEqual(test['sample_count'], len(data.splits['test']))
            self.assertEqual((self.root / 'synthetic_test/skill.md').read_bytes(), (root / 'final_skill.md').read_bytes())
        self.assertEqual(generator.calls, list(config.MODEL_MODULES) * 2)
        before = snapshot(root)
        with CampaignAdapter(DocVQAActorAdapter(data)).using():
            self.assertEqual(run_training(root, cfg, resume=True), summary)
        self.assertEqual(snapshot(root), before)

    def test_both_versions_reject_each_others_saved_campaign(self):
        data, actor, adapter, cfg = bind(self.root / 'fixture', sizes=(1,))
        for engine, owner, other_engine, other_owner, settings in (
            (old_ev, OldAdapter, ev, CampaignAdapter, old_config),
            (ev, CampaignAdapter, old_ev, OldAdapter, config),
        ):
            root = self.root / settings.METHOD_VERSION
            with owner(adapter.actor_adapter).using():
                engine.run_campaign(root, config=settings.campaign_config(adapter, module_calls=cfg['module_calls']),
                                    generate=Generator(no_change='diagnosis'))
            before, seen = snapshot(root), len(actor.seen)
            with other_owner(adapter.actor_adapter).using(), self.assertRaises(ValueError):
                other_engine.run_campaign(root, resume=True,
                                          generate=lambda *args: self.fail('No model request'))
            self.assertEqual(snapshot(root), before)
            self.assertEqual(len(actor.seen), seen)

    def test_committed_round_recovers_with_no_actor_or_method_transport(self):
        data, actor, adapter, cfg = bind(self.root / 'fixture', sizes=(1,), mode='gain')
        root, generator = self.root / 'recovery', Generator(count=1)
        def hook(stage):
            if stage == 'after_memory_commit': raise KeyboardInterrupt()
        with adapter.using(), self.assertRaises(KeyboardInterrupt):
            ev.run_campaign(root, config=cfg, generate=generator, hook=hook)
        counts = len(actor.seen), len(generator.calls)
        with CampaignAdapter(DocVQAActorAdapter(data)).using():
            self.assertEqual(ev.run_campaign(root, resume=True)['status'], 'complete')
            self.assertEqual(len(runtime_memory.load_memory(root / 'memory')['memory']['rounds']), 1)
        self.assertEqual((len(actor.seen), len(generator.calls)), counts)
