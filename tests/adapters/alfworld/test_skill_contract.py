"""Skill identity, feedback permissions and paired-execution audit invariants."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.run_task_upstream import build_messages
from src.adapters.alfworld.skill_runtime import (
    build_skill_messages, context_fingerprint, execution_fingerprint, load_skill,
    make_record, object_digest, validate_access,
)
from src.adapters.alfworld.verify_skill_run import compare_records, learning_feedback, verify_record


class SkillContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill_file = self.root / "skill.md"
        self.skill_file.write_bytes(b"Use visible actions.\r\n")
        self.game = self.root / "game.tw-pddl"
        self.game.write_text("hidden environment data", encoding="utf-8")
        self.item = {"id": "train:0000", "gamefile": "private/game.tw-pddl", "task_type": "example"}
        self.manifest = self.root / "items.json"
        self.manifest.write_text(json.dumps([self.item]), encoding="utf-8")

    def record(self, skill=None):
        record = make_record(item=self.item, split="train", purpose="smoke", skill=skill or load_skill(),
                             model="example-model", max_steps=1, gamefile=self.game,
                             manifest_path=self.manifest, versions={"alfworld": "example"}, backend_id="example")
        observation = "Your task is to: inspect the room."
        admissible = ["look", "help"]
        messages = build_skill_messages(observation, admissible, "inspect the room.", [], record["skill"])
        record.update(initial_observation=observation, initial_admissible_commands=admissible,
                      status="step_limit", finished_at="example")
        record["steps"] = [{"step": 1, "phase": "executed", "messages": messages,
                            "admissible_commands": admissible,
                            "model_response": {"content": "<action>look</action>", "response_model": "example-model",
                                               "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}},
                            "action": "look", "fallback": None, "action_in_admissible_commands": True,
                            "observation": "room", "reward": 0, "won": False, "done": False}]
        return record

    def test_no_skill_leaves_upstream_messages_unchanged(self):
        for history in ([], [{"observation": "before", "action": "look"}]):
            self.assertEqual(build_skill_messages("now", ["look"], "goal", history, load_skill()),
                             build_messages("now", ["look"], "goal", history))

    def test_skill_is_a_byte_exact_snapshot_and_path_is_not_identity(self):
        skill = load_skill(self.skill_file)
        self.assertEqual(skill["text"], "Use visible actions.\r\n")
        copy = self.root / "copy.md"
        copy.write_bytes(self.skill_file.read_bytes())
        self.assertEqual(load_skill(copy)["skill_id"], skill["skill_id"])
        self.skill_file.write_text("later change", encoding="utf-8")
        self.assertIn("Use visible actions.\r\n", build_skill_messages("now", ["look"], "goal", [], skill)[0]["content"])
        self.assertNotEqual(load_skill(self.skill_file)["skill_id"], skill["skill_id"])

    def test_empty_missing_or_non_utf8_skill_is_not_no_skill(self):
        for content in (b"", b" \n", b"\xff"):
            self.skill_file.write_bytes(content)
            with self.assertRaises(ValueError):
                load_skill(self.skill_file)
        with self.assertRaises(FileNotFoundError):
            load_skill(self.root / "missing.md")

    def test_only_declared_purpose_split_pairs_are_allowed(self):
        valid = {("train", "smoke"), ("train", "learning"), ("val", "selection"), ("test", "final")}
        for split in ("train", "val", "test"):
            for purpose in ("smoke", "learning", "selection", "final"):
                if (split, purpose) in valid:
                    validate_access(split, purpose)
                else:
                    with self.assertRaises(ValueError):
                        validate_access(split, purpose)

    def test_pair_may_change_skill_but_not_execution_conditions(self):
        left = self.record()
        right = self.record(load_skill(self.skill_file))
        self.assertNotEqual(left["execution_fingerprint"], right["execution_fingerprint"])
        self.assertEqual(left["context_fingerprint"], right["context_fingerprint"])
        self.assertTrue(compare_records(left, right)["recorded_conditions_match"])
        right["initial_observation"] = "Your task is to: another goal."
        right["steps"][0]["messages"] = build_skill_messages(right["initial_observation"], ["look", "help"], "another goal.", [], right["skill"])
        self.assertIn("initial_observation", compare_records(left, right)["differences"])

    def test_tampered_skill_prompt_fingerprint_or_success_is_rejected(self):
        record = self.record(load_skill(self.skill_file))
        mutations = [lambda r: r["skill"].update(text="different"),
                     lambda r: r["steps"][0]["messages"][0].update(content="missing Skill"),
                     lambda r: r.update(model="other"),
                     lambda r: r.update(status="success", won=True)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                changed = deepcopy(record)
                mutate(changed)
                with self.assertRaises(ValueError):
                    verify_record(changed)

    def test_failed_request_is_auditable_but_not_a_complete_comparison(self):
        left = self.record()
        partial = deepcopy(left)
        partial.update(status="error", error_stage="model_request")
        partial["steps"][0] = {key: value for key, value in partial["steps"][0].items()
                               if key in ("step", "messages", "admissible_commands")}
        partial["steps"][0]["phase"] = "requesting"
        report = verify_record(partial)
        self.assertFalse(report["episode_complete"])
        self.assertIsNone(report["native_success"])
        self.assertEqual(report["requests_with_unknown_usage"], 1)
        self.assertIn("incomplete_episode", compare_records(left, partial)["differences"])

    def test_http_body_and_parameter_drift_is_rejected(self):
        record = self.record()
        event = record["steps"][0]
        event["model_response"].update(api_attempts=1, transport_retries=0)
        parameters = {"model": record["model"], "temperature": 1.0, "max_tokens": 16384,
                      "reasoning_effort": "medium", "thinking": {"type": "enabled"}, "stream": False}
        event["transport_attempts"] = [{"attempt": 1, "status": "responded", "http_status": 200,
                                         "usage": event["model_response"]["usage"],
                                         "request_parameters": parameters,
                                         "request_sha256": object_digest({**parameters, "messages": event["messages"]})}]
        verify_record(record)
        changed = deepcopy(record)
        changed["steps"][0]["transport_attempts"][0]["request_parameters"]["max_tokens"] = 1
        with self.assertRaisesRegex(ValueError, "Request parameters"):
            verify_record(changed)
        changed = deepcopy(record)
        changed["steps"][0]["transport_attempts"][0]["request_sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "Request body hash"):
            verify_record(changed)
        changed = deepcopy(record)
        changed["steps"][0]["transport_attempts"][0]["status"] = "error"
        with self.assertRaisesRegex(ValueError, "successful HTTP"):
            verify_record(changed)
        changed = deepcopy(record)
        changed["steps"][0]["model_response"]["api_attempts"] = 2
        with self.assertRaisesRegex(ValueError, "response count"):
            verify_record(changed)

    def test_interruption_after_response_before_projection_keeps_response(self):
        record = self.record()
        record.update(status="interrupted", error_stage="model_request")
        event = record["steps"][0]
        event["phase"] = "responded"
        for key in ("action", "fallback", "action_in_admissible_commands", "observation", "reward", "won", "done"):
            event.pop(key)
        report = verify_record(record)
        self.assertFalse(report["episode_complete"])
        self.assertEqual(report["steps_executed"], 0)
        self.assertEqual(report["reported_usage"]["total_tokens"], 5)

    def test_learning_export_excludes_paths_and_rejects_selection_and_test(self):
        record = self.record(load_skill(self.skill_file))
        feedback = learning_feedback(record)
        text = json.dumps(feedback)
        self.assertNotIn(str(self.root), text)
        self.assertNotIn("game.tw-pddl", text)
        self.assertNotIn("hidden environment data", text)
        self.assertEqual(feedback["execution_context"]["max_steps"], 1)
        feedback["steps"][0]["action"] = "changed"
        self.assertEqual(record["steps"][0]["action"], "look")
        for split, purpose in (("val", "selection"), ("test", "final")):
            changed = deepcopy(record)
            changed.update(split=split, purpose=purpose)
            changed["task"]["id"] = split + ":0000"
            changed["access"] = {"learning_allowed": False, "selection_allowed": split == "val", "final_only": split == "test"}
            changed["context_fingerprint"] = context_fingerprint(changed)
            changed["execution_fingerprint"] = execution_fingerprint(changed)
            verify_record(changed)
            with self.assertRaises(ValueError):
                learning_feedback(changed)


if __name__ == "__main__":
    unittest.main()
