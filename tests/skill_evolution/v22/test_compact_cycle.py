"""A synthetic two-task cycle checks lineage/routing, never research effectiveness.

All HTTP and environment responses in this file are fixtures. No live calls occur.
"""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.adapters.alfworld.skill_runtime import (
    build_skill_messages, execution_fingerprint, load_skill, make_record, write_record,
)
from src.skill_evolution.v22.compact_cycle import cycle_cost, run_cycle, verify_cycle
from src.skill_evolution.v22.model_call import semantic_call
from src.skill_evolution.v22.run_round import DEFAULT_PLAN, run_round
from tests.skill_evolution.v22.test_diagnosis_editor import build_diagnosis, build_editor
from tests.skill_evolution.v22.test_verify_round import change


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def recorded_mock_call(stage, messages, output, value, model, response_model=None):
    session = mock.Mock()
    session.post.return_value.status_code = 200
    session.post.return_value.ok = True
    session.post.return_value.json.return_value = {
        "model": response_model or model, "choices": [{"message": {"content": value if isinstance(value, str) else json.dumps(value)},
                                    "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
    }
    raw = semantic_call(stage, messages, session=session, endpoint="https://fixture.invalid",
                        key="fixture-not-a-secret", model=model, output=output)
    assert session.post.call_count == 1
    return raw


def execute_fixture(parent, skill_path, output_root):
    record = deepcopy(parent)
    record.update(run_id=output_root.parent.parent.name + ":" + parent["task"]["id"], skill=load_skill(skill_path))
    record["execution_fingerprint"] = execution_fingerprint(record)
    record["steps"][0]["messages"] = build_skill_messages(
        record["initial_observation"], record["initial_admissible_commands"], "inspect the room.", [], record["skill"])
    path = output_root / "skill_fixture/trajectory.json"
    path.parent.mkdir(parents=True)
    write_record(path, record)
    return path


def legacy_source(directory):
    """Keep real old validators, hashes and protocol; only observations are synthetic."""
    directory.mkdir()
    plan = read(DEFAULT_PLAN)
    plan.update(editor_schema="v22.editor.v0", task_ids=["train:0000", "train:0012"],
                parent_episodes=2, candidate_episodes_max=2)
    manifest = directory / "items.json"
    items = [{"id": key, "gamefile": "fixture"} for key in plan["task_ids"]]
    write_record(manifest, items)
    game = directory / "game.tw-pddl"
    game.write_text("synthetic game bytes; never executed")
    paths = []
    for index, item in enumerate(items):
        parent = make_record(item=item, split="train", purpose="learning", skill=load_skill(),
                             model=plan["model"], max_steps=50, gamefile=game, manifest_path=manifest,
                             versions={"alfworld": "fixture"}, backend_id="fixture")
        observation, admissible = "Your task is to: inspect the room.", ["look"]
        parent.update(run_id="run-a" if index == 0 else "run-b", initial_observation=observation,
                      initial_admissible_commands=admissible, status="success", won=True, finished_at="fixture")
        parent["steps"] = [{"step": 1, "phase": "executed", "messages": build_skill_messages(
            observation, admissible, "inspect the room.", [], parent["skill"]), "admissible_commands": admissible,
            "model_response": {"content": "<action>look</action>", "response_model": plan["model"],
                               "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}},
            "action": "look", "fallback": None, "action_in_admissible_commands": True,
            "observation": "Synthetic completion", "reward": 1, "won": True, "done": True}]
        path = directory / f"parent_{index}.json"
        write_record(path, parent)
        paths.append(path)
    diagnosis = build_diagnosis()
    edit = build_editor(diagnosis)

    def generate(stage, messages, output):
        return recorded_mock_call(stage, messages, output, diagnosis if stage == "diagnosis" else edit, plan["model"])

    source = directory / "legacy_round"
    result = run_round(plan, paths, source, generate, execute_fixture)
    assert result["status"] == "candidate_evaluated", result
    return source


def cycle_plan():
    return {"schema_version": "v22.compact_cycle_plan.v1", "actor_model": "deepseek-v4-flash",
            "evolution_model": "deepseek-v4-pro", "parent": "reuse_source_no_skill", "adoption": "staging_only",
            "task_ids": ["train:0000", "train:0012"], "max_steps_per_episode": 50,
            "candidate_episodes_max": 2, "semantic_calls_max": 7, "construction_revision_pairs_max": 1,
            "semantic_retries": 0, "candidate_retries": 0}


def learning_output(payload, *, final=False):
    refs = [f"{alias}:1" for alias in payload["runs"]]
    return {"findings": [{"id": "f1", "about": [row["id"] for row in payload["plan"]["watch"]] + ["intent"],
                          "observation": "Synthetic two-task execution contains a recorded legal action; no real semantic claim.",
                          "refs": refs}], "open": [],
            "memory_delta": [{"replace": [row["id"] for row in payload["memory"]] if final else [],
                              "claim": "Synthetic revised scoped response" if final else "Synthetic scoped response",
                              "limits": ["Fixture only: no causal, generalization, or semantic evidence."], "findings": ["f1"]}]}


def draft():
    return {"decision": "revise", "reason": "Synthetic independent draft from Parent evidence.",
            "plan": {"intent": "Use available actions and preserve the task objective.",
                     "requirements": [{"id": "u1", "text": "Choose an available useful action.", "basis": ["P1:1"]}],
                     "watch": [{"id": "w1", "about": ["u1"], "question": "Do unavailable actions occur?"}], "open": []}}


def fusion_output(payload, revision=False):
    new_id, watch_id = ("u3", "w3") if revision else ("u2", "w2")
    return {"decision": "ready", "reason": "Synthetic supported-delta fixture, not evidence of a real improvement.",
            "changes": [{"from": [row["id"] for row in payload["plan"]["requirements"]],
                         "to": [{"id": new_id, "text": "Choose an exact currently admissible action using visible conditions."}],
                         "basis": [payload["memory"][0]["id"]], "reason": "Apply the fixture's scoped response and limits.", "disposition": "replace"}],
            "watch_changes": [{"from": [row["id"] for row in payload["plan"]["watch"]],
                               "to": [{"id": watch_id, "about": [new_id], "question": "Do unavailable actions or lost useful opportunities occur?"}]}],
            "open": []}


def editor_output(payload, needs_revision=False):
    ids = [row["id"] for row in payload["plan"]["requirements"]]
    text = "Choose an exact currently admissible action using visible conditions."
    return {"decision": "needs_revision" if needs_revision else "candidate", "reason": "Synthetic construction decision.",
            "candidate_text": None if needs_revision else text,
            "mappings": [] if needs_revision else [{"requirements": ids, "side": "candidate", "excerpt": text}],
            "issues": [{"about": ids, "reason": "Synthetic ambiguous trigger requires upstream clarification."}] if needs_revision else [],
            "watch": []}


class CompactCycleIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source = legacy_source(self.directory / "source")

    def cycle(self, *, mode="normal", name="cycle", fail_stage=None, response_model="deepseek-v4-pro"):
        inputs, executions = {}, []

        def generate(stage, messages, output):
            payload = json.loads(messages[1]["content"])
            inputs[stage] = deepcopy(payload)
            if stage == fail_stage:
                value = '{"malformed":'
            elif stage.startswith("learn_"):
                value = learning_output(payload, final=stage == "learn_final")
            elif stage == "diagnosis":
                value = draft()
            elif stage.startswith("fusion"):
                value = fusion_output(payload, revision=stage == "fusion_revision")
            else:
                value = editor_output(payload, needs_revision=(mode in {"revise_once", "stop_after_revision"} and stage == "editor")
                                      or (mode == "stop_after_revision" and stage == "editor_revision"))
            return recorded_mock_call(stage, messages, output, value, "deepseek-v4-pro", response_model=response_model)

        def execute(parent, skill, root):
            executions.append(deepcopy(parent))
            return execute_fixture(parent, skill, root)

        root = self.directory / name
        result = run_cycle(self.source, root, cycle_plan(), generate, execute)
        return root, result, inputs, executions

    def test_real_protocol_mock_cycle_preserves_independent_draft_and_scoped_history(self):
        source_files = {path: path.read_bytes() for path in self.source.rglob("*") if path.is_file()}
        root, result, inputs, executions = self.cycle()
        self.assertEqual(result["status"], "cycle_complete", result)
        self.assertTrue(verify_cycle(root)["cycle_complete"])
        self.assertEqual(result["stages"], ["learn_initial", "diagnosis", "fusion", "editor", "learn_final"])
        self.assertEqual(result["cost"]["semantic_calls"], 5)
        self.assertEqual(len(executions), 2)
        independent = inputs["diagnosis"]
        for forbidden in ("candidate", "memory", "plan", "actual_diff"):
            self.assertNotIn(forbidden, independent)
        self.assertTrue(all(alias.startswith("P") for alias in independent["runs"]))
        self.assertTrue(all(alias.startswith("P") or alias in {"skill:parent", "capabilities", "base_protocol"}
                            for alias in independent["sources"]))
        initial, effective = read(root / "initial_plan.json"), read(root / "effective_plan.json")
        self.assertNotEqual(initial["requirements"][0]["text"], effective["requirements"][0]["text"])
        learned_id = read(root / "memory_initial.json")[0]["id"]
        self.assertIn(learned_id, effective["requirements"][0]["basis"])
        self.assertEqual(inputs["editor"]["plan"], effective)
        self.assertEqual(read(root / "memory_final.json")[0]["supersedes"], [learned_id])
        self.assertEqual(source_files, {path: path.read_bytes() for path in source_files})

    def test_semantic_format_failures_do_not_publish_final_memory_or_retry(self):
        for stage in ("learn_initial", "fusion", "learn_final"):
            with self.subTest(stage=stage):
                root, result, _, _ = self.cycle(name="fail_" + stage, fail_stage=stage)
                self.assertEqual(result["status"], "error")
                self.assertFalse((root / "memory_final.json").exists())
                self.assertEqual(result["stages"][-1], stage)
                self.assertEqual(result["stages"].count(stage), 1)
                self.assertEqual(result["cost"]["semantic_calls"], len(result["stages"]))
                self.assertTrue((root / "calls" / (stage + ".json")).exists())
                self.assertTrue(verify_cycle(root)["artifact_valid"])
                self.assertFalse(verify_cycle(root)["cycle_complete"])

    def test_one_upstream_pair_can_repair_construction(self):
        root, result, inputs, executions = self.cycle(mode="revise_once")
        self.assertEqual(result["status"], "cycle_complete", result)
        self.assertEqual(result["cost"]["semantic_calls"], 7)
        self.assertEqual(inputs["fusion_revision"]["editor_feedback"]["decision"], "needs_revision")
        self.assertEqual(inputs["editor_revision"]["plan"], read(root / "effective_plan_revision.json"))
        self.assertEqual(len(executions), 2)
        self.assertTrue(verify_cycle(root)["cycle_complete"])

    def test_upstream_format_failure_is_not_an_editor_semantic_stop(self):
        root, result, _, executions = self.cycle(mode="revise_once", fail_stage="fusion_revision")
        self.assertEqual(result["status"], "error", result)
        self.assertEqual(result["active_stage"], "fusion_revision")
        self.assertEqual(result["stages"][-1], "fusion_revision")
        self.assertFalse(executions)
        self.assertFalse((root / "memory_final.json").exists())
        self.assertTrue(verify_cycle(root)["artifact_valid"])
        self.assertFalse(verify_cycle(root)["cycle_complete"])

    def test_second_editor_block_stops_without_execution_or_final_memory(self):
        root, result, _, executions = self.cycle(mode="stop_after_revision")
        self.assertEqual(result["status"], "needs_revision", result)
        self.assertEqual(result["stages"][-1], "editor_revision")
        self.assertEqual(result["cost"]["semantic_calls"], 6)
        self.assertFalse(executions)
        self.assertFalse((root / "candidate").exists())
        self.assertFalse((root / "memory_final.json").exists())
        self.assertTrue(verify_cycle(root)["artifact_valid"])

    def test_actor_and_evolution_models_have_distinct_boundaries(self):
        root, result, _, executions = self.cycle()
        self.assertEqual(result["status"], "cycle_complete", result)
        self.assertEqual({record["model"] for record in executions}, {"deepseek-v4-flash"})
        for path in (root / "calls").glob("*.json"):
            call = read(path)
            self.assertEqual(call["model"], "deepseek-v4-pro")
            self.assertEqual(call["steps"][0]["model_response"]["response_model"], "deepseek-v4-pro")
        bad_root, bad, _, ran = self.cycle(name="wrong_model", response_model="deepseek-v4-flash")
        self.assertEqual(bad["status"], "error")
        self.assertFalse(ran)
        self.assertFalse((bad_root / "memory_initial.json").exists())

    def test_input_candidate_and_source_tampering_are_rejected(self):
        for mutation in ("initial_plan", "diagnosis_input", "candidate", "source"):
            with self.subTest(mutation=mutation):
                root, result, _, _ = self.cycle(name="tamper_" + mutation)
                self.assertEqual(result["status"], "cycle_complete", result)
                if mutation == "initial_plan":
                    change(root / "initial_plan.json", lambda value: value.update(intent="Post-hoc rewritten target"))
                elif mutation == "diagnosis_input":
                    change(root / "inputs/diagnosis.json", lambda value: value.update(memory=[{"claim": "Leaked Candidate success"}]))
                elif mutation == "candidate":
                    (root / "candidate/SKILL.md").write_text("Unrecorded obligation")
                else:
                    source = Path(read(root / "manifest.json")["source_files"][0]["path"])
                    source.write_bytes(source.read_bytes() + b"\n")
                with self.assertRaises(ValueError):
                    verify_cycle(root)

    def test_failure_or_zero_stage_cannot_be_relabelled_complete(self):
        for empty in (False, True):
            with self.subTest(empty=empty):
                root, result, _, _ = self.cycle(name="false_complete_" + str(empty), fail_stage="learn_initial")
                self.assertEqual(result["status"], "error")
                if empty:
                    (root / "calls/learn_initial.json").unlink()
                    (root / "inputs/learn_initial.json").unlink()
                    change(root / "report.json", lambda value: value.update(stages=[], cost=cycle_cost(root)))
                change(root / "report.json", lambda value: value.update(status="cycle_complete", active_stage=None))
                with self.assertRaisesRegex(ValueError, "Terminal status"):
                    verify_cycle(root)

    def test_comparison_summary_must_match_recorded_execution(self):
        for mutation in ("missing", "steps"):
            with self.subTest(mutation=mutation):
                root, result, _, _ = self.cycle(name="bad_comparison_" + mutation)
                self.assertEqual(result["status"], "cycle_complete", result)
                if mutation == "missing":
                    change(root / "report.json", lambda value: value.update(comparisons=[]))
                else:
                    change(root / "report.json", lambda value: value["comparisons"][0].update(candidate_actions=999))
                with self.assertRaises(ValueError):
                    verify_cycle(root)


if __name__ == "__main__":
    unittest.main()
