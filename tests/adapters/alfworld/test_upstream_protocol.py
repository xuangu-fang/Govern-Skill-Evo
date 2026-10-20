"""Pin observable upstream contracts, including candidate actions and budgets."""

import contextlib
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

from src.adapters.alfworld.run_task_upstream import (
    PROTOCOL_ROOT, build_messages, chat, project_action, run_episode,
)


class ProtocolTests(unittest.TestCase):
    def test_pinned_prompts_match_recorded_source_bytes(self):
        source = json.loads((PROTOCOL_ROOT / "source.json").read_text())
        for filename, metadata in source["files"].items():
            self.assertEqual(hashlib.sha256((PROTOCOL_ROOT / filename).read_bytes()).hexdigest(), metadata["sha256"])

    def test_first_step_has_real_candidates_no_hidden_plan_or_skill(self):
        messages = build_messages("Your task is to: put apple in fridge.", ["help", "go to fridge 1"], "put apple in fridge.", [])
        self.assertEqual(len(messages), 2)
        self.assertIn("['go to fridge 1']", messages[1]["content"])
        self.assertIn("<think>", messages[1]["content"])
        self.assertNotIn("Skill Knowledge", messages[1]["content"])

    def test_window_uses_only_last_two_pre_action_observations(self):
        history = [{"observation": f"obs{i}", "action": f"action{i}"} for i in range(4)]
        prompt = build_messages("current", ["look"], "goal", history)[1]["content"]
        self.assertNotIn("obs0", prompt)
        self.assertNotIn("obs1", prompt)
        self.assertIn("[Observation 3: 'obs2', Action 3: 'action2']", prompt)
        self.assertIn("[Observation 4: 'obs3', Action 4: 'action3']", prompt)
        self.assertIn("You are now at step 5", prompt)
        self.assertIn("Your task is to: goal", prompt)

    def test_missing_action_falls_back_without_terminating_episode(self):
        self.assertEqual(project_action("go to desk 1"), ("look", "missing_action_tag"))
        self.assertEqual(project_action(""), ("look", "empty_content"))
        self.assertEqual(project_action("<think>x</think><action>MOVE Apple 1 TO Desk 1</action><action>look</action>"), ("move apple 1 to desk 1", None))

    def test_fiftieth_step_success_is_counted_and_failed_run_stops_at_fifty(self):
        class Env:
            def __init__(self, win): self.steps = 0; self.win = win
            def reset(self): return SimpleNamespace(feedback="Your task is to: goal", admissible_commands=["look"])
            def step(self, action):
                self.steps += 1
                won = self.win and self.steps == 50
                return SimpleNamespace(feedback=f"obs{self.steps}", won=won, admissible_commands=["look"]), int(won), won
        with TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            for win in [False, True]:
                env = Env(win); record = {"steps": [], "won": False}
                run_episode(env, lambda messages: {"content": "<action>look</action>"}, record, Path(directory) / "trace.json")
                self.assertEqual(env.steps, 50)
                self.assertEqual(record["status"], "success" if win else "step_limit")

    def test_request_matches_pinned_settings_and_reasoning_is_not_reinjected(self):
        session = mock.Mock()
        session.post.return_value.ok = True
        session.post.return_value.status_code = 200
        session.post.return_value.json.return_value = {"model": "deepseek-v4-flash", "choices": [{"message": {"content": "<action>look</action>", "reasoning_content": "abc"}, "finish_reason": "stop"}]}
        result = chat(session, "http://localhost/chat/completions", "test-key", "deepseek-v4-flash", [])
        body = session.post.call_args.kwargs["json"]
        self.assertEqual(body["temperature"], 1)
        self.assertEqual(body["max_tokens"], 16384)
        self.assertEqual(body["reasoning_effort"], "medium")
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(result["reasoning_content_chars"], 3)
        self.assertNotIn("reasoning_content", result)


if __name__ == "__main__":
    unittest.main()
