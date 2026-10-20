"""Consumption-profile tests use synthetic evidence and mock HTTP, never live calls."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.skill_evolution.v22.compact_cycle import (
    DEFAULT_PLAN, diagnosis_input, editor_input, fusion_input, run_cycle,
    stage_messages, updated_memory, verify_cycle,
)
from src.skill_evolution.v22.compact_learning import learning_messages, prepare_legacy
from src.skill_evolution.v22.compact_learning_view import VIEW_SCHEMA
from src.skill_evolution.v22.compact_update import diagnosis_messages, editor_messages, fusion_messages
from tests.skill_evolution.v22.test_compact_cycle import (
    cycle_plan, draft, editor_output, execute_fixture, fusion_output,
    learning_output, legacy_source, read, recorded_mock_call,
)


class CompactCycleProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source = legacy_source(self.directory / "source")
        self.initial, _, self.parents = prepare_legacy(self.source)
        self.memory = updated_memory(self.initial, learning_output(self.initial))
        self.current = diagnosis_input(self.initial, self.parents)

    def test_missing_or_legacy_profile_preserves_all_original_messages(self):
        plan = draft()["plan"]
        final = {**deepcopy(self.initial), "memory": deepcopy(self.memory)}
        f_input = fusion_input(self.current, plan, self.memory)
        e_input = editor_input(self.current, plan, self.memory)
        for stage, payload, builder in (
            ("learn_initial", self.initial, learning_messages),
            ("learn_final", final, learning_messages),
            ("diagnosis", self.current, diagnosis_messages),
            ("fusion", f_input, fusion_messages),
            ("fusion_revision", f_input, fusion_messages),
            ("editor", e_input, editor_messages),
            ("editor_revision", e_input, editor_messages),
        ):
            with self.subTest(stage=stage):
                original = builder(payload)
                self.assertEqual(stage_messages({}, stage, payload), original)
                self.assertEqual(stage_messages({"evidence_view": "legacy"}, stage, payload), original)
        self.assertEqual(stage_messages({"evidence_view": "scoped_v1"}, "diagnosis", self.current),
                         diagnosis_messages(self.current))

    def test_fusion_and_editor_scope_history_without_changing_ids_or_current_evidence(self):
        memory = deepcopy(self.memory)
        memory[0]["claim"] = "P1:1 and C1:1 were a bundled historical observation."
        duplicate = deepcopy(memory[0])
        duplicate["id"] = "another-effect-with-shared-sources"
        memory.append(duplicate)
        payload = fusion_input(self.current, draft()["plan"], memory)
        before = deepcopy(payload)
        distinct_sources = {ref for effect in memory for basis in effect["basis"] for ref in basis["sources"]}
        for stage in ("fusion", "fusion_revision", "editor", "editor_revision"):
            with self.subTest(stage=stage):
                messages = stage_messages({"evidence_view": "scoped_v1"}, stage, payload)
                view = json.loads(messages[1]["content"])
                self.assertEqual(view["consumption_view"], VIEW_SCHEMA)
                self.assertEqual(view["runs"], payload["runs"])
                self.assertEqual(view["command_sets"], payload["command_sets"])
                self.assertEqual(view["sources"], payload["sources"])
                self.assertEqual(view["plan"], payload["plan"])
                self.assertEqual([effect["id"] for effect in view["memory"]], [effect["id"] for effect in memory])
                self.assertIn("H1::P1:1", view["memory"][0]["claim"])
                self.assertEqual(len(view["historical_sources"]), len(distinct_sources))
                self.assertTrue(all(key.startswith("H1::") for key in view["historical_sources"]))
                self.assertTrue(all("admissible_commands" not in row for row in view["historical_sources"].values()))
                self.assertIn("actual_update", view["memory"][0]["basis"][0])
                self.assertIn("only current sources keys", messages[0]["content"])
        self.assertEqual(payload, before)

    def test_scoped_default_does_not_rewrite_legacy_plan(self):
        self.assertEqual(DEFAULT_PLAN.name, "plan_scoped.json")
        scoped = read(DEFAULT_PLAN)
        legacy = read(DEFAULT_PLAN.with_name("plan.json"))
        self.assertEqual(scoped["evidence_view"], "scoped_v1")
        self.assertNotIn("evidence_view", legacy)
        self.assertEqual({k: v for k, v in scoped.items() if k not in {"evidence_view", "evidence_view_note"}}, legacy)
        with self.assertRaisesRegex(ValueError, "Unknown evidence"):
            stage_messages({"evidence_view": "invented"}, "fusion", {})

    def test_scoped_cycle_uses_projected_calls_but_full_validation_and_memory_inputs(self):
        seen = {}

        def generate(stage, messages, output):
            view = json.loads(messages[1]["content"])
            seen[stage] = view
            if stage.startswith("learn_"):
                value = learning_output(view, final=stage == "learn_final")
            elif stage == "diagnosis":
                value = draft()
            elif stage == "fusion":
                value = fusion_output(view)
            else:
                value = editor_output(view)
            return recorded_mock_call(stage, messages, output, value, "deepseek-v4-pro")

        plan = cycle_plan() | {"evidence_view": "scoped_v1"}
        root = self.directory / "scoped_cycle"
        result = run_cycle(self.source, root, plan, generate, execute_fixture)
        self.assertEqual(result["status"], "cycle_complete", result)
        self.assertTrue(verify_cycle(root)["cycle_complete"])
        self.assertEqual(result["cost"]["semantic_calls"], 5)
        for stage in ("learn_initial", "fusion", "editor", "learn_final"):
            self.assertEqual(seen[stage]["consumption_view"], VIEW_SCHEMA)
            saved = read(root / "inputs" / (stage + ".json"))
            self.assertNotIn("consumption_view", saved)
            self.assertNotIn("historical_sources", saved)
            call = read(root / "calls" / (stage + ".json"))
            self.assertEqual(call["steps"][0]["messages"], stage_messages(plan, stage, saved))
        self.assertNotIn("consumption_view", seen["diagnosis"])
        self.assertNotIn("memory", seen["diagnosis"])
        self.assertTrue(seen["fusion"]["historical_sources"])
        self.assertTrue(seen["editor"]["historical_sources"])
        self.assertTrue(seen["learn_final"]["historical_sources"])
        saved_input = read(root / "inputs/learn_final.json")
        expected = updated_memory(saved_input, read(root / "outputs/learn_final.json"))
        self.assertEqual(read(root / "memory_final.json"), expected)
        self.assertTrue(all(not ref.startswith("H1::") for effect in expected
                            for basis in effect["basis"] for ref in basis["sources"]))


if __name__ == "__main__":
    unittest.main()
