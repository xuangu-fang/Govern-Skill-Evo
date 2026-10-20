"""Frozen 8+8 configuration and adapter wiring; no external requests or games."""

from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.skill_evolution.v22.bounded_evaluation import execute_episode
from src.skill_evolution.v22.continual_runtime import load_bundle, live_dependencies


PLAN = Path("experiments/methods/v22/11_unified_dsc_stream/config/plan.json").resolve()


class StreamRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.plan = json.loads(PLAN.read_text())
        for row, field in ((self.plan["data"], "task_manifest"),
                           (self.plan["classification"], "prompt_file")):
            row[field] = str((PLAN.parent / row[field]).resolve())
        for row in self.plan["preparation_materials"]:
            row["path"] = str((PLAN.parent / row["path"]).resolve())
        self.path = self.root / "plan.json"

    def bundle(self, value=None):
        self.path.write_text(json.dumps(value or self.plan))
        return load_bundle(self.path)

    def test_approved_budget_and_native_nonoverlapping_tasks(self):
        bundle = self.bundle()
        self.assertEqual(len(bundle["task_items"]), 16)
        self.assertEqual(bundle["plan"]["gate"]["required_pairs"], 8)
        self.assertEqual(bundle["plan"]["budget"]["http_attempts_max"], 9609)
        self.assertEqual(bundle["plan"]["budget"]["environment_episodes_max"], 32)
        history = json.loads((PLAN.parent / "task_inventory.json").read_text())
        self.assertEqual(set(bundle["task_items"]), {row["id"] for row in history["ranked_unused_candidates"]})

    def test_budget_or_preparation_drift_is_rejected(self):
        edits = (
            lambda p: p["models"]["semantic_requests"]["fusion"].update(max_tokens=16384),
            lambda p: p["models"]["semantic_requests"]["diagnosis"].update(transport_policy="legacy"),
            lambda p: p["budget"].update(http_attempts_max=12054),
            lambda p: p["budget"].update(actor_output_tokens_max=26214400),
            lambda p: p["preparation_materials"][0].update(sha256="0" * 64),
        )
        for edit in edits:
            changed = deepcopy(self.plan)
            edit(changed)
            with self.subTest(edit=repr(edit)), self.assertRaises(ValueError):
                self.bundle(changed)

    def test_live_closures_forward_each_declared_budget_and_actor_archival(self):
        bundle = self.bundle()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fixture", "OPENAI_BASE_URL": "https://example.invalid"}), \
                patch("src.skill_evolution.v22.continual_runtime.semantic_call", return_value="{}") as call, \
                patch("src.skill_evolution.v22.continual_runtime.execute_episode", return_value=Path("fixture")) as execute:
            generate, episode = live_dependencies(bundle, self.root / "absent.env")
            for stage, options in self.plan["models"]["semantic_requests"].items():
                generate(stage, [{"role": "user", "content": "synthetic"}], self.root / (stage + ".json"))
                for key, expected in options.items():
                    self.assertEqual(call.call_args.kwargs[key], expected)
            episode(next(iter(bundle["task_items"].values())), None, self.root / "episode")
            self.assertIs(execute.call_args.args[5]["archive_responses"], True)

    def test_actor_subprocess_receives_opt_in_archival_flag(self):
        output = self.root / "episode"

        def fake_process(command, **kwargs):
            directory = output / "skill_fixture"
            directory.mkdir()
            (directory / "trajectory.json").write_text("{}")
            return SimpleNamespace(returncode=0)

        with patch("src.skill_evolution.v22.bounded_evaluation.subprocess.run", side_effect=fake_process) as run:
            execute_episode("train:0019", "train", "learning", None, output,
                            {"actor_model": "deepseek-v4-flash", "max_steps_per_episode": 50,
                             "archive_responses": True}, self.root / "absent.env")
        self.assertIn("--archive-responses", run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
