"""Final Test entrypoint acceptance; synthetic actors only, network forbidden."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from unittest.mock import patch

from scripts.runs import run_v29_5_campaign as cli
from src.skill_evolution.v27.transport import RequestFailure
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
from src.skill_evolution.v29_2 import actor_io
from src.skill_evolution.v29_5 import evaluation, evolution as ev, config as settings
from src.skill_evolution.v29_5.campaign import CampaignAdapter
from tests.skill_evolution.v29.test_actor import Base, response
from tests.skill_evolution.v29.test_campaign import snapshot
from .helpers import offline
from .campaign_support import bind, Generator


class EvaluationTests(Base):
    def setUp(self):
        super().setUp(); offline(self)
        self.data, self.transport, self.adapter, self.config = bind(self.root / 'fixture', sizes=(2,))
        self.campaign = self.root / 'campaign'
        self.output = self.root / 'test_output'
        self.enterContext(self.adapter.using())

    def train(self, generator=None):
        result = cli.run_training(self.campaign, self.config, generate=generator or Generator())
        self.transport.generate = lambda *args: response('<answer>secret</answer>')
        return result

    def test_selected_subset_is_executed_only_on_held_out_test_and_history_is_untouched(self):
        training = self.train()
        self.assertIsNone(training['selected_execution_source'])
        expected = (self.campaign / 'final_skill.md').read_bytes()
        self.assertIn(b'rule u1', expected); self.assertNotIn(b'rule u2', expected)
        before = snapshot(self.campaign); calls = len(self.transport.seen)
        result = cli.run_test(self.campaign, self.output)
        self.assertEqual(result['sample_count'], len(self.data.splits['test']))
        self.assertEqual((result['success_count'], result['hard'], result['anls']), (1, 1.0, 1.0))
        self.assertEqual(len(self.transport.seen), calls + 1)
        self.assertEqual((self.output / 'skill.md').read_bytes(), expected)
        identity = ev.read(self.output / 'evaluation.json')
        self.assertEqual(identity['tasks'], self.data.splits['test'])
        records = ev.read(self.output / 'runs/records.json')
        self.assertTrue(all(r['task']['split'] == 'test' and r['provenance']['role'] == 'evaluation'
                            and r['execution']['skill'].encode() == expected for r in records))
        self.assertEqual(snapshot(self.campaign), before)
        frozen = snapshot(self.output)
        # Fresh process with no transports can validate a completed evaluation.
        with CampaignAdapter(DocVQAActorAdapter(self.data)).using():
            self.assertEqual(cli.run_test(self.campaign, self.output, resume=True), result)
        self.assertEqual(snapshot(self.output), frozen)
        self.assertEqual(snapshot(self.campaign), before)

    def test_incomplete_training_cannot_create_output_or_request(self):
        ev.initialize(self.campaign, self.config)
        with self.assertRaisesRegex(ValueError, 'not complete'):
            cli.run_test(self.campaign, self.output)
        self.assertFalse(self.output.exists()); self.assertEqual(self.transport.seen, [])

    def test_preflight_creates_no_evaluation_and_needs_no_credentials(self):
        self.adapter.actor_adapter.workers = 15
        self.train(); calls = len(self.transport.seen); before = snapshot(self.campaign)
        with patch.object(cli, 'DocVQADataset', return_value=self.data), \
             patch.object(cli, 'read_credentials', side_effect=AssertionError('No credential read')), \
             patch.object(cli, 'ChatTransport', side_effect=AssertionError('No transport')), \
             patch.object(cli, 'run_test', side_effect=AssertionError('No Test execution')), \
             redirect_stdout(io.StringIO()) as out:
            cli.main(['test', str(self.campaign), '--output', str(self.output), '--validate-only'])
        self.assertEqual(json.loads(out.getvalue())['test_count'], 1)
        self.assertFalse(self.output.exists()); self.assertEqual(len(self.transport.seen), calls)
        self.assertEqual(snapshot(self.campaign), before)

    def test_cli_test_dispatches_without_creating_optimizer_transport(self):
        self.adapter.actor_adapter.workers = 15
        self.train()
        with patch.object(cli, 'DocVQADataset', return_value=self.data), \
             patch.object(cli, 'read_credentials', return_value={'OPENAI_API_KEY': 'offline-placeholder'}), \
             patch.object(cli, 'ChatTransport', return_value=self.transport), \
             patch.object(cli, 'HTTPGenerator', side_effect=AssertionError('No optimizer transport')), \
             redirect_stdout(io.StringIO()) as out:
            cli.main(['test', str(self.campaign), '--output', str(self.output)])
        self.assertEqual(json.loads(out.getvalue())['sample_count'], 1)

    def test_cli_test_requires_output_and_cannot_override_campaign_config(self):
        for args in (['test', str(self.campaign)],
                     ['test', str(self.campaign), '--output', str(self.output), '--config', 'other.json']):
            with self.assertRaises(ValueError): cli.main(args)
        self.assertFalse(self.output.exists())

    def test_output_must_be_separate_from_training_and_data(self):
        self.train(); before = len(self.transport.seen)
        for path in (self.campaign, self.campaign / 'evaluation', self.root,
                     self.data.root, self.data.root / 'evaluation'):
            with self.subTest(path=path), self.assertRaises(ValueError): cli.run_test(self.campaign, path)
        self.assertEqual(len(self.transport.seen), before)

    def test_resume_identity_and_artifacts_cannot_be_changed_or_reinitialized(self):
        self.train(); cli.run_test(self.campaign, self.output); before = len(self.transport.seen)
        with self.assertRaises(ValueError): cli.run_test(self.campaign, self.output)
        for path in (self.output / 'evaluation.json', self.output / 'skill.md',
                     self.output / 'runs/records.json', self.output / 'summary.json'):
            original = path.read_bytes()
            if path.suffix == '.md': path.write_bytes(original + b'forged')
            else: ev.save(path, {'forged': True})
            with self.subTest(path=path), self.assertRaises((ValueError, KeyError, TypeError)):
                cli.run_test(self.campaign, self.output, resume=True)
            path.write_bytes(original)
        identity = (self.output / 'evaluation.json').read_bytes()
        (self.output / 'evaluation.json').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing Test identity'):
            cli.run_test(self.campaign, self.output, resume=True)
        (self.output / 'evaluation.json').write_bytes(identity)
        self.assertEqual(len(self.transport.seen), before)

    def test_changed_export_is_rejected_before_test(self):
        self.train(); before = len(self.transport.seen)
        (self.campaign / 'final_skill.md').write_text('forged')
        with self.assertRaisesRegex(ValueError, 'Exported Skill differs'):
            cli.run_test(self.campaign, self.output)
        self.assertFalse(self.output.exists()); self.assertEqual(len(self.transport.seen), before)

    def test_interrupted_tasks_resume_without_repeating_completed_answers(self):
        self.data.rows['synthetic:test2'] = ('Second held-out question?', ['secret'], 'test')
        self.data.splits['test'].append('synthetic:test2')
        self.adapter.actor_adapter.test_workers = 1
        self.train()
        def interrupt(messages, slot):
            if messages[1]['content'][0]['text'].startswith('Second'): raise KeyboardInterrupt()
            return response('<answer>secret</answer>')
        self.transport.generate = interrupt
        with self.assertRaises(KeyboardInterrupt): cli.run_test(self.campaign, self.output)
        self.assertFalse((self.output / 'summary.json').exists())
        calls = len(self.transport.seen)
        self.transport.generate = lambda *args: response('<answer>secret</answer>')
        result = cli.run_test(self.campaign, self.output, resume=True)
        self.assertEqual(len(self.transport.seen), calls + 1)
        self.assertEqual((result['sample_count'], result['success_count'], result['api_requests']), (2, 2, 3))

    def test_saved_response_is_recovered_without_resampling(self):
        self.train()
        def interrupted(messages, slot):
            ev.save(slot / 'response.json', response('<answer>secret</answer>'))
            raise KeyboardInterrupt()
        self.transport.generate = interrupted
        with self.assertRaises(KeyboardInterrupt): cli.run_test(self.campaign, self.output)
        calls = len(self.transport.seen)
        result = cli.run_test(self.campaign, self.output, resume=True)
        self.assertEqual(len(self.transport.seen), calls)
        self.assertEqual((result['hard'], result['api_requests']), (1.0, 1))

    def test_incomplete_http_body_and_six_request_limit(self):
        self.train()
        def interrupted(messages, slot):
            if int(slot.name) < 6: raise RequestFailure('Synthetic retryable failure')
            (slot / 'http_response.txt').write_text('{partial')
            raise KeyboardInterrupt()
        self.transport.generate = interrupted
        before = len(self.transport.seen)
        with self.assertRaises(KeyboardInterrupt): cli.run_test(self.campaign, self.output)
        self.assertEqual(len(self.transport.seen), before + 6)
        for _ in range(2):
            with self.assertRaisesRegex(RequestFailure, 'budget exhausted'):
                cli.run_test(self.campaign, self.output, resume=True)
        self.assertFalse((self.output / 'summary.json').exists())
        self.assertEqual(len(self.transport.seen), before + 6)
        self.assertEqual((self.output / 'runs/actor/0001/attempts/006/http_response.incomplete.txt').read_text(), '{partial')

    def test_identity_and_summary_publication_interruptions_are_recoverable(self):
        self.train(); original = ev.save
        for artifact in ('evaluation.json', 'summary.json'):
            output = self.root / artifact.replace('.', '_')
            def interrupt(path, value):
                if path.name == artifact:
                    path.with_suffix('.tmp').write_text('{partial')
                    raise KeyboardInterrupt()
                return original(path, value)
            with patch.object(ev.stages, 'save', interrupt), self.assertRaises(KeyboardInterrupt):
                cli.run_test(self.campaign, output)
            calls = len(self.transport.seen)
            result = cli.run_test(self.campaign, output, resume=True)
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(len(self.transport.seen), calls + (1 if artifact == 'evaluation.json' else 0))

    def test_crlf_selected_skill_is_unchanged_in_test_messages_and_archive(self):
        original = Generator(count=1)
        def generate(name, *args):
            result = original(name, *args)
            if name == 'editor':
                value = json.loads(result['content'])
                value['edits'][0]['patch'] = value['edits'][0]['patch'].replace(
                    'scoped amount guidance.\n', 'scoped amount guidance.\r\n+  Preserve the requested field role.\n')
                result['content'] = json.dumps(value)
            return result
        self.train(generate)
        expected = (self.campaign / 'final_skill.md').read_bytes(); self.assertIn(b'\r\n', expected)
        cli.run_test(self.campaign, self.output)
        self.assertEqual((self.output / 'skill.md').read_bytes(), expected)
        record = ev.read(self.output / 'runs/records.json')[0]
        self.assertEqual(record['execution']['skill'].encode(), expected)
        # The existing Actor template strips surrounding whitespace; interior
        # CRLF must survive, while archives preserve even the trailing newline.
        self.assertIn(expected.decode().strip(), self.transport.seen[-1][0]['content'])

    def test_final_flag_and_split_are_required_for_evaluation(self):
        for flag, role, tasks in ((False, 'evaluation', self.data.splits['test']),
                                  (True, 'parent', self.data.splits['train']),
                                  (True, 'evaluation', self.data.splits['train'])):
            with self.assertRaises(ValueError):
                actor_io.actor_batch(self.adapter.actor_adapter, tasks, self.skill_file, self.output,
                    {'split': 'test' if role == 'evaluation' else 'train', 'role': role}, final=flag)
        self.assertFalse(self.output.exists()); self.assertEqual(self.transport.seen, [])

    def test_production_config_matches_reference_budgets_and_passes_offline_preflight(self):
        root = Path(__file__).resolve().parents[3]
        config = ev.read(root / 'experiments/configs/v29_5_docvqa_optimization160.json')
        old = ev.read(root / 'experiments/configs/v29_1_docvqa_optimization160.json')
        with CampaignAdapter(DocVQAActorAdapter(DocVQADataset())).using():
            settings.validate_config(config, executable=True)
        expected_calls = {k: dict(v) for k, v in old['module_calls'].items() if k != 'grouping'}
        self.assertEqual(expected_calls['editor']['max_tokens'], 16384)
        expected_calls['editor']['max_tokens'] = 32768
        self.assertEqual(config['module_calls'], expected_calls)
        self.assertEqual(config['actor'], old['actor'])
        self.assertEqual(config['batches'], old['batches'])
        self.assertEqual(config['method'], settings.method_config())
        self.assertEqual(list(map(len, config['batches'])), [15] * 10 + [10])
        output = self.root / 'never_started'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('No credentials')), \
             redirect_stdout(io.StringIO()):
            cli.main(['train', str(output), '--config', str(root / 'experiments/configs/v29_5_docvqa_optimization160.json'),
                      '--validate-only'])
        self.assertFalse(output.exists())
