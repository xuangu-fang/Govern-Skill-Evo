from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.skill_evolution.skilladam.alfworld.trajectory_feedback import archive


class FeedbackArchiveTest(unittest.TestCase):
    def test_checkpoint_is_bound_to_its_training_round_and_full_evaluation_id(self):
        with TemporaryDirectory() as directory:
            output = Path(directory).resolve() / 'training'
            results = output.parent / 'experiment/results'
            run = Path('retest/R01')
            raw = output / 'evaluations' / run
            raw.mkdir(parents=True)
            index = results / run / 'summary.json'
            index.parent.mkdir(parents=True)
            skill = 'retained after round one'
            parent = output / 'shared_actor/iter_001/training_rollout_0/actor_skill.md'
            parent.parent.mkdir(parents=True)
            parent.write_text(skill)
            (results / 'R01_skill.md').write_text(skill)
            digest = sha256(skill.encode()).hexdigest()
            (raw / 'inputs.json').write_text(json.dumps(dict(training=str(output), round='R01', skill_sha256=digest)))
            (raw / 'summary.json').write_text('{}')
            verified = dict(run_id='R01', training_run=output.name, final_skill='../final_skill.md', success=117)
            entry = dict(run_id=run.as_posix(), training_run=output.name, round='R01', skill_sha256=digest,
                         evaluated_skill='../../R01_skill.md', success=117)
            index.write_text(json.dumps(entry))
            training = dict(iterations=[{}, {}])

            def read_reports():
                return list(archive.checkpoint_evaluations(output, results, training, 'final', [], {}))

            with patch.object(archive, 'read_evaluation', return_value=verified) as reader:
                self.assertEqual(read_reports(), [entry])
                reader.assert_called_once_with(raw, output.name, [], {}, skill)
            parent.write_text('different training Skill')
            with self.assertRaisesRegex(ValueError, 'Skill differs'):
                read_reports()
            index.unlink()
            with self.assertRaisesRegex(ValueError, 'index differs'):
                read_reports()
