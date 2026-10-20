"""Fixed-draft routing tests with synthetic evidence and recorded mock HTTP.

These tests do not run models or environments, or establish semantic correctness.
"""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.adapters.alfworld.skill_runtime import digest, load_skill, write_record
from src.skill_evolution.v22 import consume_fixed_plan as consumption
from tests.skill_evolution.v22.test_compact_cycle import draft, recorded_mock_call
from tests.skill_evolution.v22.test_compact_learning_view import fixture as history_fixture
from tests.skill_evolution.v22.test_verify_round import change


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fixture():
    initial = draft()["plan"]
    payload = {"schema_version": "synthetic-learning", "parent": load_skill(),
               "candidate": {"skill_id": "fixture-prior-candidate", "text": "Choose useful legal actions."},
               "actual_diff": "+Choose useful legal actions.", "plan": deepcopy(initial),
               "watch_origin": "synthetic_pre_execution", "capabilities": "Current visible actions only.",
               "command_sets": {"a1": ["look"]}, "runs": {}, "sources": {},
               "pairs": [{"task_id": "train:0000", "parent": "P1", "candidate": "C1",
                          "recorded_conditions_match": True, "differences": []}],
               "memory": history_fixture()["memory"]}
    for alias in ("P1", "C1"):
        payload["runs"][alias] = {
            "run_id": "fixture-" + alias, "task_id": "train:0000",
            "skill_id": "none" if alias == "P1" else "fixture-prior-candidate",
            "execution_fingerprint": "fixture-" + alias, "status": "success",
            "episode_complete": True, "native_success": True,
            "initial_observation": "Visible fixture room.", "initial_commands": "a1",
            "steps": [{"step": 1, "phase": "executed", "action": "look", "commands": "a1",
                       "action_in_admissible_commands": True, "observation": "Fixture completion.",
                       "reward": 1, "done": True, "won": True}],
        }
        payload["sources"][alias + ":1"] = {"kind": "event", "run": alias, "step": 1}
    payload["sources"].update({"skill:parent": {"kind": "skill", "side": "parent"},
                               "skill:candidate": {"kind": "skill", "side": "candidate"},
                               "capabilities": {"kind": "capabilities"}})
    current = {"parent": load_skill(), "capabilities": payload["capabilities"],
               "runs": {"P1": deepcopy(payload["runs"]["P1"])},
               "command_sets": deepcopy(payload["command_sets"]),
               "base_protocol": {"system_prompt": "Synthetic base protocol."},
               "sources": {key: deepcopy(payload["sources"][key])
                           for key in ("P1:1", "skill:parent", "capabilities")}}
    return payload, current, initial


def knowledge_output():
    return {"findings": [{"id": "f1", "about": ["w1", "intent"],
                          "observation": "Synthetic source-backed scoped observation; not research evidence.",
                          "refs": ["P1:1", "C1:1"]}], "open": [],
            "memory_delta": [{"replace": ["old-context:m1"],
                              "claim": "Synthetic reconciled observation under the recorded conditions.",
                              "limits": ["Synthetic single condition; no causal or generalized effect."],
                              "findings": ["f1"], "retire_limits": []}]}


def identity():
    return {"decision": "ready", "reason": "The initial requirement already covers this synthetic decision.",
            "changes": [], "watch_changes": [], "open": []}


def increment(payload):
    return {"decision": "ready", "reason": "Synthetic bounded construction, not measured benefit.",
            "changes": [{"from": ["u1"],
                         "to": [{"id": "u2", "text": "Choose an exact currently admissible useful action; preserve recovery."}],
                         "basis": [payload["memory"][0]["id"]],
                         "reason": "Apply the scoped fixture observation, retaining its limitations.",
                         "disposition": "replace"}],
            "watch_changes": [{"from": ["w1"], "to": [{"id": "w2", "about": ["u2"],
                               "question": "Are useful actions or recovery opportunities lost?"}]}],
            "open": []}


def edit(payload, *, stop=False):
    requirements = payload["plan"]["requirements"]
    return {"decision": "needs_revision" if stop else "candidate",
            "reason": "Synthetic construction decision.",
            "candidate_text": None if stop else "\n".join(row["text"] for row in requirements),
            "mappings": [] if stop else [{"requirements": [row["id"]], "side": "candidate", "excerpt": row["text"]}
                                           for row in requirements],
            "issues": [{"about": [requirements[0]["id"]], "reason": "Synthetic unresolved condition needs upstream revision."}] if stop else [],
            "watch": []}


class FixedConsumptionTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.source = self.directory / "immutable-source"
        self.source.mkdir()
        self.source_cycle = self.directory / "immutable-cycle"
        self.source_cycle.mkdir()
        write_record(self.source / "manifest.json", {"source_cycle": str(self.source_cycle)})
        self.bound_file = self.source / "source.json"
        write_record(self.bound_file, {"fixture": "Immutable synthetic source; never executed."})
        self.bindings = [{"path": str(path), "sha256": digest(path.read_bytes())}
                         for path in sorted(self.source.iterdir())]
        self.payload, self.current, self.initial = fixture()
        self.plan = {"schema_version": "v22.fixed_consumption_plan.v1",
                     "source_completion": "immutable-source", "evolution_model": "deepseek-v4-pro",
                     "semantic_calls_max": 5, "semantic_retries": 0, "new_environment_episodes": 0,
                     "branch_order": ["current", "history"]}

        def prepare(source, plan):
            self.assertEqual(Path(source), self.source)
            self.assertEqual(plan, self.plan)
            return deepcopy((self.payload, self.current, self.initial, self.bindings))

        patcher = mock.patch.object(consumption, "prepare", side_effect=prepare)
        patcher.start()
        self.addCleanup(patcher.stop)

    def operation(self, name="operation", *, fail_stage=None, invalid_ref=False,
                  stop_stage=None, transform=False, construct=True):
        calls, inputs = [], {}

        def generate(stage, messages, output):
            calls.append(stage)
            payload = json.loads(messages[1]["content"])
            inputs[stage] = deepcopy(payload)
            if stage == fail_stage:
                value = '{"incomplete":'
            elif stage == "memory":
                value = knowledge_output()
                if invalid_ref:
                    value["findings"][0]["refs"] = ["C1:999"]
            elif stage.endswith("fusion"):
                value = increment(payload) if transform and stage == "history_fusion" else identity()
                if stage == stop_stage:
                    value.update(decision="needs_revision", reason="Shared intent needs Diagnosis revision.",
                                 open=[{"about": ["intent"], "reason": "The common goal is unresolved."}])
            else:
                value = edit(payload, stop=stage == stop_stage)
            return recorded_mock_call(stage, messages, output, value, "deepseek-v4-pro")

        root = self.directory / name
        report = consumption.learn(self.source, root, deepcopy(self.plan), generate)
        if construct and report["status"] == "memory_ready":
            self.assertEqual(consumption.verify(root)["status"], "memory_ready")
            report = consumption.construct(root, generate)
        return root, report, calls, inputs, generate

    def test_identity_constructs_two_branches_without_history_leak_or_environment(self):
        original = deepcopy((self.payload, self.current, self.initial))
        bound = self.bound_file.read_bytes()
        root, report, calls, inputs, generate = self.operation()
        self.assertEqual(report["status"], "consumption_checked", report)
        self.assertEqual(consumption.verify(root)["status"], "consumption_checked")
        self.assertEqual(calls, list(consumption.STAGES))
        self.assertEqual(report["cost"]["semantic_calls"], 5)
        self.assertEqual(report["cost"]["http_attempts"], 5)
        self.assertEqual(report["cost"]["environment_requests"], 0)
        self.assertEqual(report["environment_executions"], 0)
        self.assertFalse(list(root.rglob("trajectory.json")))
        for field in ("plan", "runs", "sources", "parent", "base_protocol", "command_sets"):
            self.assertEqual(inputs["current_fusion"][field], inputs["history_fusion"][field])
        self.assertEqual(inputs["current_fusion"]["plan"], self.initial)
        for stage in ("current_fusion", "current_editor"):
            self.assertEqual(inputs[stage]["memory"], [])
            self.assertEqual(inputs[stage]["historical_sources"], {})
            self.assertNotIn("old-clean", json.dumps(inputs[stage]))
            self.assertNotIn("fixture-prior-candidate", json.dumps(inputs[stage]))
        self.assertTrue(inputs["history_fusion"]["memory"])
        # An identity has no Memory-backed requirement; Editor need not reread history.
        self.assertEqual(inputs["history_editor"]["memory"], [])
        for branch in consumption.BRANCHES:
            self.assertFalse(report["branches"][branch]["requirements_changed"])
            self.assertFalse(read(root / branch / "lineage.json")["executed"])
        self.assertEqual((self.payload, self.current, self.initial), original)
        self.assertEqual(self.bound_file.read_bytes(), bound)
        with self.assertRaises(ValueError):
            consumption.construct(root, generate)
        self.assertEqual(len(calls), 5)

    def test_history_increment_keeps_initial_plan_and_binds_actual_text(self):
        root, report, _, inputs, _ = self.operation(transform=True)
        self.assertEqual(report["status"], "consumption_checked", report)
        self.assertEqual(read(root / "initial_plan.json"), self.initial)
        self.assertEqual(read(root / "current_plan.json"), self.initial)
        effective = read(root / "history_plan.json")
        self.assertEqual(effective["intent"], self.initial["intent"])
        self.assertTrue(report["branches"]["history"]["requirement_text_changed"])
        effect = read(root / "memory_effective.json")[0]["id"]
        self.assertEqual(report["branches"]["history"]["history_ids_cited_in_changes"], [effect])
        self.assertEqual(inputs["history_editor"]["plan"], effective)
        self.assertEqual([m["id"] for m in inputs["history_editor"]["memory"]], [effect])
        self.assertEqual((root / "history/SKILL.md").read_text(), effective["requirements"][0]["text"])
        self.assertTrue(consumption.verify(root)["artifact_valid"])

    def test_revision_only_profile_does_not_change_fixed_construction_plan(self):
        self.plan["memory_profile"] = "revision_only_v1"
        value = knowledge_output()
        value["findings"][0]["about"] = ["intent"]
        with mock.patch(__name__ + ".knowledge_output", return_value=value):
            root, report, calls, inputs, _ = self.operation()
        self.assertEqual(report["status"], "consumption_checked", report)
        self.assertEqual(inputs["memory"]["plan"]["watch"], [])
        self.assertNotIn("command_sets", inputs["memory"])
        self.assertEqual(inputs["current_fusion"]["plan"], self.initial)
        self.assertEqual(inputs["history_fusion"]["plan"], self.initial)
        self.assertEqual(calls, list(consumption.STAGES))
        self.assertTrue(consumption.verify(root)["artifact_valid"])

    def test_fusion_and_editor_revision_routes_stop_without_forced_candidate(self):
        for stage in ("current_fusion", "history_editor"):
            with self.subTest(stage=stage):
                root, report, calls, _, _ = self.operation(name=stage, stop_stage=stage)
                branch = stage.split("_", 1)[0]
                self.assertEqual(report["status"], "consumption_checked", report)
                self.assertEqual(report["branches"][branch]["status"], "needs_revision")
                self.assertFalse((root / branch / "SKILL.md").exists())
                if stage.endswith("fusion"):
                    self.assertNotIn(branch + "_editor", calls)
                self.assertTrue(consumption.verify(root)["artifact_valid"])
                self.assertLessEqual(len(calls), 5)

    def test_learning_failure_does_not_publish_memory_or_start_branches(self):
        for invalid_ref in (False, True):
            with self.subTest(invalid_ref=invalid_ref):
                root, report, calls, _, generate = self.operation(
                    name="learning_" + str(invalid_ref), invalid_ref=invalid_ref,
                    fail_stage=None if invalid_ref else "memory")
                self.assertEqual(report["status"], "error", report)
                self.assertEqual(calls, ["memory"])
                self.assertFalse((root / "memory_effective.json").exists())
                self.assertTrue(consumption.verify(root)["artifact_valid"])
                with self.assertRaises(ValueError):
                    consumption.construct(root, generate)
                self.assertEqual(calls, ["memory"])

    def test_failed_branch_does_not_retry_or_block_independent_branch(self):
        for stage in ("current_fusion", "current_editor", "history_editor"):
            with self.subTest(stage=stage):
                root, report, calls, _, _ = self.operation(name="fail_" + stage, fail_stage=stage)
                failed = stage.split("_", 1)[0]
                other = "history" if failed == "current" else "current"
                self.assertEqual(report["status"], "comparison_incomplete", report)
                self.assertEqual(report["branches"][failed]["status"], "error")
                self.assertEqual(report["branches"][other]["status"], "candidate")
                self.assertFalse((root / failed / "SKILL.md").exists())
                self.assertTrue((root / other / "SKILL.md").exists())
                self.assertEqual(calls.count(stage), 1)
                self.assertEqual(report["cost"]["semantic_calls"], len(calls))
                self.assertTrue(consumption.verify(root)["artifact_valid"])
                self.assertEqual(report["cost"]["environment_requests"], 0)

    def test_unfinished_or_failed_operation_cannot_be_relabelled_complete(self):
        for failure in (None, "memory", "current_fusion"):
            with self.subTest(failure=failure):
                root, _, _, _, _ = self.operation(name="false_complete_" + str(failure),
                                                  fail_stage=failure, construct=failure is not None)
                change(root / "report.json", lambda value: value.update(status="consumption_checked"))
                with self.assertRaises(ValueError):
                    consumption.verify(root)

    def test_failed_branch_cannot_be_relabelled_as_a_valid_semantic_decision(self):
        root, report, _, _, _ = self.operation(fail_stage="current_fusion")
        self.assertEqual(report["status"], "comparison_incomplete")
        change(root / "report.json", lambda value: value["branches"]["current"].update(status="needs_revision"))
        with self.assertRaises(ValueError):
            consumption.verify(root)

    def test_output_cannot_be_written_inside_either_immutable_source(self):
        for protected in (self.source, self.source_cycle):
            with self.subTest(protected=protected.name):
                generate = mock.Mock(side_effect=AssertionError("No call is permitted before source protection."))
                with self.assertRaises(ValueError):
                    consumption.learn(self.source, protected / "nested-output", self.plan, generate)
                generate.assert_not_called()
                self.assertFalse((protected / "nested-output").exists())

    def test_saved_source_input_candidate_report_and_cost_tampering_are_rejected(self):
        for target in ("source", "input", "candidate", "lineage", "report", "cost", "memory", "reference"):
            with self.subTest(target=target):
                root, report, _, _, _ = self.operation(name="tamper_" + target, transform=True)
                self.assertEqual(report["status"], "consumption_checked", report)
                original_source = self.bound_file.read_bytes()
                try:
                    if target == "source":
                        self.bound_file.write_bytes(original_source + b"\n")
                    elif target == "input":
                        change(root / "inputs/current_fusion.json", lambda value: value.update(memory=self.payload["memory"]))
                    elif target == "candidate":
                        (root / "history/SKILL.md").write_text("Unrecorded obligation.")
                    elif target == "lineage":
                        change(root / "history/lineage.json", lambda value: value.update(executed=True))
                    elif target == "report":
                        change(root / "report.json", lambda value: value["branches"]["history"].update(requirements_changed=False))
                    elif target == "cost":
                        change(root / "report.json", lambda value: value["cost"].update(semantic_calls=1))
                    elif target == "memory":
                        change(root / "memory_effective.json", lambda value: value[0].update(limits=[]))
                    else:
                        change(root / "outputs/history_fusion.json", lambda value: value["changes"][0].update(basis=["missing-effect"]))
                    with self.assertRaises(ValueError):
                        consumption.verify(root)
                finally:
                    self.bound_file.write_bytes(original_source)


if __name__ == "__main__":
    unittest.main()
