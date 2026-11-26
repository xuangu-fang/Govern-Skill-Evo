"""Full-training and held-out Test launchers with synthetic transports only."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from unittest.mock import patch

from scripts.runs import run_v29_campaign as cli
from src.skill_evolution.v29 import evolution as ev
from .test_actor import Base, response
from .test_campaign import snapshot
from .campaign_support import bind, Generator


class EntrypointTests(Base):
    def test_formal_entry_runs_all_batches_exports_final_and_never_starts_test(self):
        data, transport, adapter, config = bind(self.root / 'fixture', sizes=[15] * 10 + [10])
        root = self.root / 'campaign'; generator = Generator(no_change='diagnosis')
        with adapter.using(), redirect_stdout(io.StringIO()):
            result = cli.run_training(root, config, generate=generator)
            self.assertEqual(result['rounds_completed'], 11)
            self.assertEqual(result['state']['next_round'], 12)
            self.assertEqual(len(transport.seen), 160)
            self.assertEqual((root / 'final_skill.md').read_text(), config['initial_skill'])
            calls = len(generator.calls)
            self.assertEqual(cli.run_training(root, config, generate=generator, resume=True), result)
            self.assertEqual(len(transport.seen), 160)
            self.assertEqual(len(generator.calls), calls)
            with self.assertRaises(ValueError): cli.run_training(root, config, generate=generator)
        self.assertFalse(result['test_started'])

    def test_formal_entry_resumes_without_repeating_completed_round(self):
        _, transport, adapter, config = bind(self.root / 'fixture')
        root = self.root / 'campaign'; generator = Generator(no_change='diagnosis')
        def interrupted(name, *args):
            if name == 'grouping' and generator.calls.count('grouping') == 1:
                raise KeyboardInterrupt('Synthetic R02 interruption')
            return generator(name, *args)
        with adapter.using(), redirect_stdout(io.StringIO()):
            with self.assertRaises(KeyboardInterrupt):
                cli.run_training(root, config, generate=interrupted)
            self.assertEqual(ev.read(root / 'state.json')['next_round'], 2)
            self.assertFalse((root / 'training_summary.json').exists())
            result = cli.run_training(root, config, generate=generator, resume=True)
            self.assertEqual(result['rounds_completed'], 2)
            self.assertEqual(len(transport.seen), 4)

    def test_validate_only_needs_no_credentials_or_output(self):
        directory = self.root / 'never_created'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('Must not read credentials')), \
             patch.object(cli, 'ChatTransport', side_effect=AssertionError('Must not create transport')), \
             redirect_stdout(io.StringIO()):
            cli.main(['train', str(directory), '--validate-only', '--env-file', 'absent.env'])
        self.assertFalse(directory.exists())

    def test_test_requires_complete_training_before_any_request(self):
        _, transport, adapter, config = bind(self.root / 'fixture')
        root = self.root / 'campaign'; output = self.root / 'evaluation'
        with adapter.using():
            ev.initialize(root, config)
            with self.assertRaises(ValueError): cli.run_test(root, output)
        self.assertFalse(output.exists())
        self.assertEqual(transport.seen, [])

    def test_test_uses_only_final_skill_and_held_out_tasks_and_resumes_read_only(self):
        data, transport, adapter, config = bind(self.root / 'fixture', rounds=1)
        root = self.root / 'campaign'; output = self.root / 'evaluation'
        with adapter.using(), redirect_stdout(io.StringIO()):
            cli.run_training(root, config, generate=Generator())
            before = snapshot(root); calls = len(transport.seen)
            result = cli.run_test(root, output)
            self.assertEqual(result['sample_count'], len(data.splits['test']))
            self.assertEqual(len(transport.seen), calls + len(data.splits['test']))
            self.assertEqual((output / 'skill.md').read_text(), (root / 'final_skill.md').read_text())
            self.assertEqual(ev.read(output / 'evaluation.json')['tasks'], data.splits['test'])
            self.assertEqual(cli.run_test(root, output, resume=True), result)
            self.assertEqual(len(transport.seen), calls + len(data.splits['test']))
            self.assertEqual(snapshot(root), before)
            records = ev.read(output / 'runs/records.json')
            self.assertTrue(all(r['provenance']['role'] == 'evaluation' for r in records))
            with self.assertRaises(ValueError): cli.run_test(root, output)
            with self.assertRaises(ValueError): cli.run_test(root, root / 'test')

    def test_interrupted_test_has_no_partial_score_and_reuses_finished_answers(self):
        data, transport, adapter, config = bind(self.root / 'fixture', rounds=1)
        data.rows['synthetic:test2'] = ('Second held-out question?', ['secret'], 'test')
        data.splits['test'].append('synthetic:test2')
        adapter.actor_adapter.test_workers = 1
        root = self.root / 'campaign'; output = self.root / 'evaluation'
        with adapter.using(), redirect_stdout(io.StringIO()):
            cli.run_training(root, config, generate=Generator(no_change='diagnosis'))
            def interrupted(messages, slot):
                if messages[1]['content'][0]['text'].startswith('Second'):
                    raise KeyboardInterrupt('Synthetic Test interruption')
                return response('<answer>secret</answer>')
            transport.generate = interrupted
            with self.assertRaises(KeyboardInterrupt): cli.run_test(root, output)
            self.assertFalse((output / 'summary.json').exists())
            calls = len(transport.seen)
            transport.generate = lambda *args: response('<answer>secret</answer>')
            result = cli.run_test(root, output, resume=True)
            self.assertEqual(len(transport.seen), calls + 1)
            self.assertEqual(result['success_count'], 2)
            self.assertEqual(result['sample_count'], 2)
            self.assertEqual(result['api_requests'], 3)
