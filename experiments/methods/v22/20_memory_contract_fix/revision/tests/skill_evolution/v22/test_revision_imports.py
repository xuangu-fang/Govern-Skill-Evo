"""Offline checks for memory_contract, shared contract modules and Actor child imports."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import src
from src import _ROOT

_BASE = _ROOT / "experiments/methods/v22/12_contract_alignment/revision"
_P1 = _ROOT / "experiments/methods/v22/17_p1_input/revision"
_FIX = _ROOT / "experiments/methods/v22/20_memory_contract_fix/revision"
from src.skill_evolution.v22 import bounded_evaluation, continual_runtime

REVISION = Path(src.__file__).resolve().parents[1]


class RevisionImportTests(unittest.TestCase):
    def test_memory_contract_overrides_and_shared_modules_are_selected(self):
        for name, base in (
            ("src.skill_evolution.v22.memory_contract", REVISION),
            ("src.skill_evolution.v22.continual_runtime", _FIX),
            ("src.skill_evolution.v22.continual_runner", _P1),
            ("src.skill_evolution.v22.grouped_update", _FIX),
            ("src.skill_evolution.v22.contract_alignment", _BASE),
            ("src.adapters.alfworld.skill_runtime", _BASE),
            ("src.adapters.alfworld.run_task_skill", _BASE),
            ("src.adapters.alfworld.run_task", _ROOT),
        ):
            with self.subTest(module=name):
                module = importlib.import_module(name)
                self.assertEqual(Path(module.__file__).resolve(),
                                 base.joinpath(*name.split(".")).with_suffix(".py"))

    def test_actor_child_keeps_memory_contract_and_the_historical_adapter(self):
        real_run = subprocess.run

        def inspect_child(command, *, cwd, **kwargs):
            self.assertEqual(command[1:3], ["-m", "src.adapters.alfworld.run_task_skill"])
            probe = real_run(
                [sys.executable, "-B", "-c",
                 "import json; import src.adapters.alfworld.run_task_skill as actor; "
                 "from src.skill_evolution.v22 import memory_contract; "
                 "print(json.dumps([actor.__file__, memory_contract.__file__]))"],
                cwd=cwd, capture_output=True, text=True, check=True,
            )
            actor, memory_contract = map(Path, json.loads(probe.stdout))
            self.assertEqual(actor.resolve(), _BASE / "src/adapters/alfworld/run_task_skill.py")
            self.assertEqual(memory_contract.resolve(), REVISION / "src/skill_evolution/v22/memory_contract.py")
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

    def test_runtime_sources_cover_memory_contract_contract_and_shared_modules(self):
        plan = _ROOT / "experiments/methods/v22/08_grouped_continual/config/plan.json"
        with TemporaryDirectory() as temporary:
            frozen = continual_runtime.freeze_runtime(
                continual_runtime.load_bundle(plan),
                Path(temporary), offline=True,
            )
            sources = {Path(row["path"]).resolve() for row in frozen["sources"]}
            self.assertIn(REVISION / "src/skill_evolution/v22/memory_contract.py", sources)
            self.assertIn(_P1 / "src/skill_evolution/v22/continual_runner.py", sources)
            self.assertIn(_FIX / "src/skill_evolution/v22/grouped_update.py", sources)
            self.assertIn(_BASE / "src/skill_evolution/v22/contract_alignment.py", sources)
            self.assertIn(_BASE / "src/adapters/alfworld/skill_runtime.py", sources)
            self.assertIn(_ROOT / "src/adapters/alfworld/run_task.py", sources)
            self.assertNotIn(_ROOT / "src/skill_evolution/v22/continual_runner.py", sources)
