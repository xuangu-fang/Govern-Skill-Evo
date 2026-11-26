"""Offline acceptance of v25.4 using recorded messages and a synthetic train/test handoff."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.runs.v25_4 import run_v25_4_train_test as entry
from src.skill_evolution.v25_3 import stages as original
from src.skill_evolution.v25_4 import engine, stages
from src.skill_evolution.v25_4.baseline.benchmarks.spreadsheetbench import protocol
from tests.skill_evolution.v25 import support
from tests.skill_evolution.v25_3.test_campaign import Fixture


class Acceptance(unittest.TestCase):
    def test_archived_configuration_messages_and_actor(self):
        design = stages.read(entry.DESIGN)
        train, test = entry.configurations()
        rounds = entry.pipeline.EXPERIMENT / 'campaign/rounds'
        for config, key in ((train, 'training_config'), (test, 'evaluation_config')):
            old = entry.pipeline.read_config(entry.checked_file(design['baseline'][key]))
            self.assertEqual(config, {**old, 'candidate': design['candidate'],
                                      'method': {**old['method'], 'version': design['method_version']}})
        for name in train['method']['stages']:
            data = stages.read(rounds / 'R03' / name / 'input.json')
            old = original.messages_for(name, data, train['actor_profile'])
            new = stages.messages_for(name, data, train['actor_profile'])
            old_prompt = (original.PACKAGE / 'prompts' / (name + '.md')).read_text()
            new_prompt = entry.checked_file(design['stage_templates'][name]).read_text()
            self.assertTrue(old[0]['content'].startswith(old_prompt))
            self.assertEqual(new[0]['content'], new_prompt + old[0]['content'][len(old_prompt):])
            self.assertEqual(new[1:], old[1:])
        task = stages.read(rounds / 'R03/parent_runs/train_36097/trajectory.json')
        self.assertEqual(protocol.initial_messages(task['task'], task['skill'], task['workbook_preview'],
                                                   train['actor_profile']), task['initial_messages'])

    def test_recover_then_evaluate_published_subset(self):
        train, _ = entry.configurations()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = support.config(root / 'data', test=1)
            for key in ('dataset', 'batches', 'task_items', 'test_tasks', 'initial_skill'):
                train[key] = data[key]
            train.update(actor_max_workers=1, retry_delay_seconds=0)
            fixture = Fixture()
            engine.prepare(root / 'campaign', train)

            def run_campaign(path, generate, expected_config):
                return engine.run(path, generate, adapter=fixture.adapter, expected_config=expected_config)

            actor_run = entry.pipeline.actor.run

            def mock_transport(*args, **kwargs):
                return actor_run(*args, generate=fixture.adapter.generate, execute=support.fast_execute, **kwargs)

            def pipeline():
                entry.pipeline.train_test(root, train, train, fixture.generate, run_campaign=run_campaign)

            with patch.object(entry.pipeline.actor, 'run', side_effect=mock_transport):
                with patch.object(engine, '_publish', side_effect=InterruptedError):
                    with self.assertRaises(InterruptedError):
                        pipeline()
                self.assertFalse((root / 'test').exists())
                pipeline()
                self.assertEqual(fixture.calls, train['method']['stages'])
                self.assertEqual(stages.read(root / 'test/summary.json')['success'], 1)
                skill = (root / 'campaign/final_skill.md').read_bytes()
                self.assertEqual(skill, (root / 'test/final_skill.md').read_bytes())
                self.assertIn(support.NEW.encode(), skill)
                self.assertNotIn(b'Preserve all unrelated', skill)
                calls = len(fixture.adapter.generate.calls)
                pipeline()
                self.assertEqual(len(fixture.adapter.generate.calls), calls)
                self.assertEqual(fixture.calls, train['method']['stages'])
