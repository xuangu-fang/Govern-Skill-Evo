"""Exercise fixed Skill execution and failure preservation without model calls."""

import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

from src.adapters.alfworld import run_task_skill
from src.adapters.alfworld.run_task_upstream import build_messages, chat
from src.adapters.alfworld.skill_runtime import load_skill, object_digest, write_record


class FakeEnvironment:
    def __init__(self, *, win=False, done=False, fail=None):
        self.count = 0
        self.win = win
        self.done = done
        self.fail = fail

    def reset(self):
        return SimpleNamespace(feedback="Your task is to: test goal", admissible_commands=["look"])

    def step(self, action):
        if self.fail:
            raise self.fail
        self.count += 1
        return SimpleNamespace(feedback=f"observation {self.count}", won=self.win,
                               admissible_commands=["look"]), int(self.win), self.done or self.win


class SkillEpisodeTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "trajectory.json"

    def run_episode(self, env=None, generate=None, skill=None, max_steps=3):
        record = {"steps": [], "won": False, "skill": skill or load_skill(),
                  "protocol": {"max_steps": max_steps}, "status": "starting"}
        with contextlib.redirect_stdout(io.StringIO()):
            run_task_skill.run_episode(env or FakeEnvironment(), generate or (
                lambda messages: {"content": "<action>look</action>"}), record, self.output)
        self.assertEqual(json.loads(self.output.read_text()), record)
        self.assertIn("finished_at", record)
        return record

    def test_fixed_skill_is_in_every_request_and_history_is_pre_action(self):
        skill_file = Path(self.directory.name) / "skill.md"
        skill_file.write_text("If something fails, inspect the current state.\n")
        skill = load_skill(skill_file)
        calls = []

        def generate(messages):
            saved = json.loads(self.output.read_text())
            self.assertEqual(saved["steps"][-1]["phase"], "requesting")
            self.assertEqual(saved["active_phase"], "model_request")
            calls.append(messages)
            return {"content": "<action>look</action>"}

        record = self.run_episode(generate=generate, skill=skill)
        self.assertEqual(record["status"], "step_limit")
        self.assertEqual(len(calls), 3)
        for messages in calls:
            self.assertIn(skill["text"], messages[0]["content"])
        self.assertIn("Observation 1: 'Your task is to: test goal'", calls[1][1]["content"])
        self.assertIn("Observation 2: 'observation 1'", calls[2][1]["content"])
        self.assertEqual(record["initial_admissible_commands"], ["look"])
        self.assertTrue(all(event["phase"] == "executed" for event in record["steps"]))

    def test_no_skill_preserves_upstream_prompt_and_success(self):
        record = self.run_episode(env=FakeEnvironment(win=True))
        self.assertEqual(record["status"], "success")
        self.assertTrue(record["won"])
        self.assertEqual(record["steps"][0]["messages"], build_messages(
            "Your task is to: test goal", ["look"], "test goal", []))

    def test_api_failure_keeps_request_without_inventing_response_or_usage(self):
        def generate(messages):
            raise RuntimeError("secret provider response")
        record = self.run_episode(generate=generate)
        self.assertEqual(record["status"], "error")
        self.assertEqual(record["error_stage"], "model_request")
        self.assertEqual(record["steps"][0]["phase"], "requesting")
        self.assertNotIn("model_response", record["steps"][0])
        self.assertNotIn("secret provider response", self.output.read_text())
        self.assertFalse(record["won"])

    def test_environment_failure_keeps_response_and_pre_action_record(self):
        outer = self

        class FailingEnvironment(FakeEnvironment):
            def step(self, action):
                saved = json.loads(outer.output.read_text())
                outer.assertEqual(saved["steps"][0]["phase"], "responded")
                outer.assertEqual(saved["steps"][0]["action"], action)
                raise RuntimeError("private environment details")

        record = self.run_episode(env=FailingEnvironment())
        self.assertEqual(record["error_stage"], "environment_step")
        self.assertEqual(record["steps"][0]["phase"], "responded")
        self.assertNotIn("observation", record["steps"][0])
        self.assertNotIn("private environment details", self.output.read_text())

    def test_normal_failure_and_interruption_are_distinct(self):
        ended = self.run_episode(env=FakeEnvironment(done=True))
        self.assertEqual(ended["status"], "environment_ended")
        self.assertFalse(ended["won"])
        interrupted = self.run_episode(env=FakeEnvironment(fail=KeyboardInterrupt()))
        self.assertEqual(interrupted["status"], "interrupted")
        self.assertEqual(interrupted["error_stage"], "environment_step")
        self.assertEqual(interrupted["steps"][0]["phase"], "responded")

    def test_reset_error_preserves_an_empty_error_run(self):
        env = FakeEnvironment()
        env.reset = mock.Mock(side_effect=ValueError("private reset details"))
        record = self.run_episode(env=env)
        self.assertEqual(record["error_stage"], "reset")
        self.assertEqual(record["steps"], [])
        self.assertNotIn("private reset details", self.output.read_text())

    def test_transport_retries_are_saved_without_headers_or_endpoint(self):
        session = mock.Mock()
        first = mock.Mock(status_code=429, ok=False)
        second = mock.Mock(status_code=200, ok=True)
        second.json.return_value = {"model": "test", "choices": [{"message": {
            "content": "<action>look</action>"}}], "usage": {"total_tokens": 12}}
        session.post.side_effect = [first, second]
        record = {"steps": [], "won": False, "skill": load_skill(),
                  "protocol": {"max_steps": 1}, "status": "starting"}
        recorder = run_task_skill.RecordingSession(session, record, self.output)
        with mock.patch("src.adapters.alfworld.run_task_upstream.time.sleep"), contextlib.redirect_stdout(io.StringIO()):
            run_task_skill.run_episode(FakeEnvironment(), lambda messages: chat(
                recorder, "https://private.example/chat/completions", "secret-key", "test", messages),
                record, self.output)
        attempts = record["steps"][0]["transport_attempts"]
        self.assertEqual([entry["http_status"] for entry in attempts], [429, 200])
        self.assertIsNone(attempts[0]["usage"])
        self.assertEqual(attempts[1]["usage"], {"total_tokens": 12})
        body = {**attempts[0]["request_parameters"], "messages": record["steps"][0]["messages"]}
        self.assertEqual(attempts[0]["request_sha256"], object_digest(body))
        saved = self.output.read_text()
        self.assertNotIn("secret-key", saved)
        self.assertNotIn("private.example", saved)

    def test_transport_failure_keeps_unknown_usage(self):
        record = {"steps": [{"phase": "requesting"}]}
        write_record(self.output, record)
        session = mock.Mock()
        session.post.side_effect = TimeoutError("secret timeout URL")
        recorder = run_task_skill.RecordingSession(session, record, self.output)
        with self.assertRaises(TimeoutError):
            recorder.post("private endpoint", json={"messages": [], "model": "test"})
        attempt = json.loads(self.output.read_text())["steps"][0]["transport_attempts"][0]
        self.assertEqual(attempt["status"], "error")
        self.assertIsNone(attempt["usage"])
        self.assertNotIn("secret timeout URL", self.output.read_text())

    def test_dry_run_checks_interfaces_without_credentials_or_output(self):
        root = Path(self.directory.name)
        (root / "train").mkdir()
        (root / "train/items.json").write_text(json.dumps([{"id": "train:0000", "gamefile": "game.tw-pddl"}]))
        (root / "game.tw-pddl").write_text("test")
        output_root = root / "unused_output"
        with mock.patch.object(run_task_skill, "SPLIT_ROOT", root), \
                mock.patch.dict("os.environ", {"ALFWORLD_DATA": str(root)}, clear=True), \
                mock.patch.object(run_task_skill, "load_dotenv") as dotenv, \
                mock.patch.object(run_task_skill, "installed_versions", return_value={"alfworld": "test", "textworld": "test"}), \
                mock.patch.object(run_task_skill, "environment_modules") as modules, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_task_skill.main(["--dry-run", "--output-root", str(output_root)]), 0)
        dotenv.assert_not_called()
        modules.assert_called_once()
        self.assertFalse(output_root.exists())

    def test_environment_setup_failure_leaves_a_safe_error_record(self):
        root = Path(self.directory.name)
        (root / "train").mkdir()
        (root / "train/items.json").write_text(json.dumps([{"id": "train:0000", "gamefile": "game.tw-pddl"}]))
        (root / "game.tw-pddl").write_text("test")
        output_root = root / "setup_failure"
        with mock.patch.object(run_task_skill, "SPLIT_ROOT", root), \
                mock.patch.dict("os.environ", {"ALFWORLD_DATA": str(root), "OPENAI_API_KEY": "private-key",
                                                "OPENAI_BASE_URL": "https://private.example"}, clear=True), \
                mock.patch.object(run_task_skill, "load_dotenv"), \
                mock.patch.object(run_task_skill, "environment_modules", side_effect=ImportError("private details")), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_task_skill.main(["--output-root", str(output_root)]), 1)
        outputs = list(output_root.glob("*/trajectory.json"))
        self.assertEqual(len(outputs), 1)
        record = json.loads(outputs[0].read_text())
        self.assertEqual(record["status"], "error")
        self.assertEqual(record["error_stage"], "environment_setup")
        self.assertEqual(record["steps"], [])
        self.assertFalse(record["won"])
        for secret in ("private-key", "private.example", "private details"):
            self.assertNotIn(secret, outputs[0].read_text())


if __name__ == "__main__":
    unittest.main()
