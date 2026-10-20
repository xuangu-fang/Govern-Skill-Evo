"""Bounded Train construction with recorded synthetic HTTP; no live calls."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.adapters.alfworld.skill_runtime import load_skill
from src.skill_evolution.v22 import train_response_update as target
from tests.skill_evolution.v22.test_compact_cycle import draft, recorded_mock_call
from tests.skill_evolution.v22.test_consume_fixed_plan import edit, fixture, identity, increment, read


class TrainResponseUpdateTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        history, self.current, _ = fixture()
        self.memory = history["memory"]

    def run_case(self, name="construction", *, bad_stage=None, stop=None, both_formatting=False,
                 wrong_watch=False, response_model="deepseek-v4-pro", changed=False):
        inputs, calls, texts = {}, [], {}

        def generate(stage, messages, output):
            calls.append(stage)
            payload = json.loads(messages[1]["content"])
            inputs[stage] = deepcopy(payload)
            if stage == bad_stage:
                value = '{"truncated":'
            elif stage == "diagnosis":
                value = draft()
                if stop in {"no_change", "need_evidence"}:
                    value.update(decision=stop, plan=None)
            elif stage.endswith("_proposal"):
                value = increment(payload) if changed and stage.startswith("conditioned") else identity()
                if stage == stop:
                    value.update(decision="needs_revision", open=[{"about": ["intent"], "reason": "Fixture unresolved evidence."}])
            else:
                value = edit(payload, stop=stage == stop)
                if both_formatting and stage == "direct_editor":
                    first, second = "Choose an available useful action.", "Preserve recovery."
                    value["candidate_text"] = "1. " + first + "\n2. " + second
                    value["mappings"] = [{"requirements": ["u1"], "side": "candidate", "excerpt": first + " " + second}]
                    value["watch"] = deepcopy(payload["plan"]["watch"]) + [
                        {"id": "new_watch", "about": ["u1"], "question": "Does the fixture preserve recovery?"}]
                    if wrong_watch:
                        value["watch"][0]["question"] += " Different meaning."
                texts[stage] = value.get("candidate_text")
            return recorded_mock_call(stage, messages, output, value, "deepseek-v4-pro", response_model=response_model)

        root = self.root / name
        report = target.construct(root, self.current, self.memory, generate)
        return root, report, calls, inputs, texts

    def test_shared_initial_information_and_editor_policy_with_changed_requirements(self):
        before = deepcopy((self.current, self.memory))
        root, report, calls, inputs, _ = self.run_case(changed=True)
        self.assertEqual(report["status"], "constructed", report)
        self.assertEqual(calls, list(target.STAGES))
        self.assertEqual(inputs["direct_proposal"], inputs["conditioned_proposal"])
        self.assertEqual(read(root / "calls/direct_proposal.json")["steps"][0]["messages"][1],
                         read(root / "calls/conditioned_proposal.json")["steps"][0]["messages"][1])
        self.assertEqual(inputs["direct_editor"]["memory"], inputs["conditioned_editor"]["memory"])
        self.assertNotEqual(inputs["direct_editor"]["plan"], inputs["conditioned_editor"]["plan"])
        self.assertNotIn("memory", inputs["diagnosis"])
        self.assertTrue(report["branches"]["conditioned"]["requirements_changed"])
        self.assertEqual(report["branches"]["conditioned"]["history_cited"], [self.memory[0]["id"]])
        self.assertEqual(before, (self.current, self.memory))
        for arm, ready in report["ready_arms"].items():
            skill = load_skill(root / ready["skill_file"])
            self.assertEqual(skill["skill_id"], ready["skill_id"])
            self.assertTrue((root / f"candidates/{arm}/actual.diff").is_file())
            self.assertEqual(read(root / f"candidates/{arm}/observation_plan.json")["watch"],
                             read(root / f"{arm}_plan.json")["watch"])
        self.assertEqual(report["cost"]["semantic_calls"], 5)

    def test_both_formatting_normalizations_preserve_raw_candidate_and_new_watch(self):
        root, report, _, _, texts = self.run_case(both_formatting=True)
        self.assertEqual(report["status"], "constructed", report)
        branch = report["branches"]["direct"]
        self.assertEqual(branch["removed_exact_watch_echoes"], 1)
        self.assertEqual(branch["extra_exact_mapping_spans"], 1)
        raw, normalized = read(root / "raw_outputs/direct_editor.json"), read(root / "outputs/direct_editor.json")
        self.assertEqual(raw["candidate_text"], normalized["candidate_text"])
        self.assertEqual((root / "candidates/direct/SKILL.md").read_text(), texts["direct_editor"])
        self.assertEqual(normalized["watch"], [raw["watch"][1]])
        watch = read(root / "candidates/direct/observation_plan.json")["watch"]
        self.assertEqual([row["id"] for row in watch], ["w1", "new_watch"])
        self.assertEqual({k: v for k, v in raw.items() if k not in {"mappings", "watch"}},
                         {k: v for k, v in normalized.items() if k not in {"mappings", "watch"}})

    def test_changed_watch_is_not_repaired_and_other_arm_can_finish(self):
        root, report, calls, _, _ = self.run_case(both_formatting=True, wrong_watch=True)
        self.assertEqual(report["status"], "comparison_incomplete")
        self.assertEqual(report["branches"]["direct"]["status"], "error")
        self.assertEqual(set(report["ready_arms"]), {"conditioned"})
        self.assertFalse((root / "candidates/direct").exists())
        self.assertTrue((root / "raw_outputs/direct_editor.json").exists())
        self.assertEqual(calls.count("direct_editor"), 1)

    def test_bad_response_and_semantic_stop_never_retry(self):
        for stage in ("direct_proposal", "direct_editor", "conditioned_editor"):
            with self.subTest(stage=stage):
                root, report, calls, _, _ = self.run_case(name=stage, bad_stage=stage)
                self.assertEqual(report["status"], "comparison_incomplete")
                self.assertEqual(calls.count(stage), 1)
                self.assertEqual((root / f"raw_outputs/{stage}.txt").read_text(), '{"truncated":')
                self.assertTrue((root / f"calls/{stage}.json").exists())
                self.assertNotIn(stage.split("_")[0], report["ready_arms"])
        for stage in ("direct_proposal", "direct_editor"):
            _, report, calls, _, _ = self.run_case(name=stage + "_stop", stop=stage)
            self.assertEqual(report["branches"]["direct"]["status"], "needs_revision")
            self.assertEqual(set(report["ready_arms"]), {"conditioned"})
            self.assertEqual(calls.count(stage), 1)

    def test_diagnosis_stop_is_preserved_without_candidates(self):
        for decision in ("no_change", "need_evidence"):
            root, report, calls, _, _ = self.run_case(name=decision, stop=decision)
            self.assertEqual(report["status"], decision)
            self.assertEqual(calls, ["diagnosis"])
            self.assertEqual(report["ready_arms"], {})
            self.assertFalse((root / "initial_plan.json").exists())
            self.assertEqual(list((root / "candidates").iterdir()), [])

    def test_input_boundary_existing_root_and_call_record_validation(self):
        for task in ("val:0001", "test:0001"):
            current = deepcopy(self.current)
            current["runs"]["P1"]["task_id"] = task
            callback = mock.Mock()
            out = self.root / task.replace(":", "_")
            with self.assertRaises(ValueError):
                target.construct(out, current, self.memory, callback)
            callback.assert_not_called()
            self.assertFalse(out.exists())
        root, _, _, _, _ = self.run_case()
        with self.assertRaises(FileExistsError):
            target.construct(root, self.current, self.memory, mock.Mock())
        _, report, calls, _, _ = self.run_case(name="wrong_model", response_model="unexpected-model")
        self.assertEqual(report["status"], "error")
        self.assertEqual(calls, ["diagnosis"])
        self.assertIn("model mismatch", report["validation_error"])

    def test_unrecorded_callback_output_cannot_publish_candidate(self):
        root = self.root / "unrecorded"
        callback = mock.Mock(return_value=json.dumps(draft()))
        report = target.construct(root, self.current, self.memory, callback)
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["error_type"], "FileNotFoundError")
        self.assertEqual(report["ready_arms"], {})
        self.assertEqual(callback.call_count, 1)

    def test_editor_no_change_preserves_fixed_parent_without_new_candidate(self):
        parent_file = self.root / "existing_parent.md"
        parent_file.write_text("Choose an available useful action.")
        current = deepcopy(self.current)
        current["parent"] = load_skill(parent_file)
        current["runs"]["P1"]["skill_id"] = current["parent"]["skill_id"]

        def generate(stage, messages, output):
            if stage == "diagnosis":
                value = draft()
            elif stage.endswith("_proposal"):
                value = identity()
            else:
                value = {"decision": "no_change", "reason": "Parent already realizes the requirement.",
                         "candidate_text": None, "mappings": [{"requirements": ["u1"], "side": "parent",
                         "excerpt": current["parent"]["text"]}], "issues": [], "watch": []}
            return recorded_mock_call(stage, messages, output, value, "deepseek-v4-pro")

        root = self.root / "editor_no_change"
        report = target.construct(root, current, self.memory, generate)
        self.assertEqual(report["status"], "constructed", report)
        self.assertEqual(list((root / "candidates").iterdir()), [])
        for arm in report["ready_arms"].values():
            self.assertEqual(arm["decision"], "no_change")
            self.assertEqual(arm["skill_id"], current["parent"]["skill_id"])
            self.assertEqual((root / arm["skill_file"]).read_bytes(), parent_file.read_bytes())


if __name__ == "__main__":
    unittest.main()
