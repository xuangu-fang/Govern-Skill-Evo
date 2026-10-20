"""Offline checks for shared imports and historical Actor subprocess selection."""
import importlib
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src import _ROOT
from src.skill_evolution.v22 import bounded_evaluation, continual_runtime

REVISION = Path(__file__).resolve().parents[3]


class RevisionImportTests(unittest.TestCase):
    def test_shared_modules_and_historical_overrides_are_selected(self):
        for name, base in (
            ("src.skill_evolution.v22.contract_alignment", REVISION),
            ("src.skill_evolution.v22.grouped_update", REVISION),
            ("src.adapters.alfworld.skill_runtime", REVISION),
            ("src.adapters.alfworld.run_task_skill", REVISION),
            ("src.skill_evolution.v22.continual_runner", _ROOT),
            ("src.adapters.alfworld.run_task", _ROOT),
        ):
            with self.subTest(module=name):
                module = importlib.import_module(name)
                self.assertEqual(Path(module.__file__).resolve(),
                                 base.joinpath(*name.split(".")).with_suffix(".py"))

    def test_actor_child_uses_the_revision_without_running_an_episode(self):
        real_run = subprocess.run

        def inspect_child(command, *, cwd, **kwargs):
            self.assertEqual(command[1:3], ["-m", "src.adapters.alfworld.run_task_skill"])
            probe = real_run(
                [sys.executable, "-B", "-c",
                 "import src.adapters.alfworld.run_task_skill as actor; print(actor.__file__)"],
                cwd=cwd, capture_output=True, text=True, check=True,
            )
            self.assertEqual(Path(probe.stdout.strip()).resolve(),
                             REVISION / "src/adapters/alfworld/run_task_skill.py")
            output = Path(command[command.index("--output-root") + 1]) / "skill_probe"
            output.mkdir()
            (output / "trajectory.json").write_text("{}")
            return subprocess.CompletedProcess(command, 0)

        with TemporaryDirectory() as temporary, \
                patch.object(bounded_evaluation.subprocess, "run", side_effect=inspect_child):
            result = bounded_evaluation.execute_episode(
                "train:0001", "train", "learning", None, Path(temporary) / "episode",
                {"actor_model": "offline-test", "max_steps_per_episode": 1},
                Path(temporary) / "unused.env",
            )
            self.assertTrue(result.is_file())

    def test_runtime_sources_include_actual_override_and_shared_files(self):
        plan = _ROOT / "experiments/methods/v22/08_grouped_continual/config/plan.json"
        with TemporaryDirectory() as temporary:
            frozen = continual_runtime.freeze_runtime(
                continual_runtime.load_bundle(plan), Path(temporary), offline=True,
            )
            sources = {Path(row["path"]).resolve() for row in frozen["sources"]}
            self.assertIn(REVISION / "src/skill_evolution/v22/contract_alignment.py", sources)
            self.assertIn(REVISION / "src/adapters/alfworld/skill_runtime.py", sources)
            self.assertIn(_ROOT / "src/skill_evolution/v22/continual_runner.py", sources)
            self.assertNotIn(_ROOT / "src/adapters/alfworld/skill_runtime.py", sources)
