"""Offline round integration: real contracts and persisted traces, no API or game."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.adapters.alfworld.skill_runtime import (
    build_skill_messages, context_fingerprint, digest, execution_fingerprint,
    load_skill, make_record, object_digest, write_record,
)
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v22.diagnosis_editor import DIAGNOSIS_SCHEMA, EDITOR_SCHEMA
from src.skill_evolution.v22.evidence import load_prior_parent_attempts, prepare_evidence
from src.skill_evolution.v22.model_call import semantic_call
from src.skill_evolution.v22.run_round import DEFAULT_PLAN, run_round, validate_plan


class RoundTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = json.loads(DEFAULT_PLAN.read_text(encoding="utf-8"))
        self.plan["editor_schema"] = "v22.editor.v0"  # Historical path remains reproducible.
        self.plan.update(model="offline-model", max_steps_per_episode=2)
        self.items = [{"id": task, "gamefile": "private/game.tw-pddl"}
                      for task in self.plan["task_ids"]]
        self.manifest = self.root / "items.json"
        write_record(self.manifest, self.items)
        self.game = self.root / "game.tw-pddl"
        self.game.write_text("Hidden game data must never enter learner evidence.")
        self.parents = [self.record(item) for item in self.items]
        self.paths = [self.root / f"parent-{i}.json" for i in range(len(self.parents))]
        self.save_parents()
        self.run_dir = self.root / "round"
        self.executed = []
        self.generated = []
        self.diagnosis, self.editor = self.proposals()

    def record(self, item, skill=None, *, partial=False, usage=None, retries=0):
        record = make_record(
            item=item, split="train", purpose="learning", skill=skill or load_skill(),
            model=self.plan["model"], max_steps=self.plan["max_steps_per_episode"],
            gamefile=self.game, manifest_path=self.manifest,
            versions={"alfworld": "offline"}, backend_id="offline-backend")
        observation = "Your task is to: inspect a closed cabinet."
        admissible = ["look", "open cabinet 1"]
        messages = build_skill_messages(observation, admissible, "inspect a closed cabinet.", [], record["skill"])
        event = {"step": 1, "phase": "requesting" if partial else "executed",
                 "messages": messages, "admissible_commands": admissible}
        protocol = record["protocol"]
        parameters = {"model": record["model"], "temperature": protocol["temperature"],
                      "max_tokens": protocol["max_tokens"], "reasoning_effort": protocol["reasoning_effort"],
                      "thinking": {"type": protocol["thinking"]}, "stream": False}
        event["transport_attempts"] = [{
            "attempt": i + 1, "status": "error" if partial else "responded",
            "http_status": 429 if i < retries else (None if partial else 200),
            "usage": usage if i == retries and not partial else None,
            "request_parameters": parameters,
            "request_sha256": object_digest({**parameters, "messages": messages}),
        } for i in range(retries + 1)]
        if not partial:
            event.update(model_response={"content": "<action>look</action>",
                         "response_model": record["model"], "usage": usage,
                         "api_attempts": retries + 1, "transport_retries": retries},
                         action="look", fallback=None, action_in_admissible_commands=True,
                         observation="The cabinet remains closed.", reward=0, won=False, done=True)
        record.update(initial_observation=observation, initial_admissible_commands=admissible,
                      status="error" if partial else "environment_ended", finished_at="offline-finished", steps=[event])
        if partial:
            record["error_stage"] = "model_request"
        verify_record(record)
        return record

    def save_parents(self):
        for path, record in zip(self.paths, self.parents):
            write_record(path, record)

    def proposals(self):
        refs = [{"run_id": self.parents[0]["run_id"], "step": 1}]
        boundary = {"scenario": "Hypothetical: no open action is available",
                    "expected_behavior": "Keep using admissible actions",
                    "reasoning": "The preference is conditional", "evidence_refs": []}
        diagnosis = {
            "schema_version": DIAGNOSIS_SCHEMA, "decision": "revise",
            "rationale": "A local inspection preference may help; this is an untested explanation.",
            "goals": [{"id": "g1", "behavior": "Inspect relevant closed receptacles", "evidence_refs": refs}],
            "preserve": [{"behavior": "Use available actions", "evidence_refs": refs}],
            "decision_gaps": [{"id": "d1", "visible_context": "An open action was visible",
                               "observed_decision": "look", "observed_consequence": "Cabinet stayed closed",
                               "evidence_refs": refs}],
            "hypotheses": [{"gap_ids": ["d1"], "explanation": "Inspection may need a local preference",
                            "skill_changeable": True, "alternatives": ["Random action choice"],
                            "uncertainties": ["No counterfactual execution"], "evidence_refs": refs}],
            "proposals": [{"id": "p1", "goal_ids": ["g1"], "gap_ids": ["d1"],
                           "trigger": "Relevant closed cabinet with an admissible open action",
                           "strategy": "Prefer opening over unchanged look", "scope": "Current visible cabinet",
                           "preserve": ["Available actions only"], "expected_effect": "Useful new observation",
                           "uncertainties": ["Could still fail"], "evidence_refs": refs}],
            "interactions": [], "boundary_checks": [boundary], "missing_evidence": [],
        }
        text = "When a relevant closed cabinet has an admissible open action, prefer opening it over an unchanged look.\n"
        editor = {
            "schema_version": EDITOR_SCHEMA, "decision": "candidate", "rationale": "Implements the local preference",
            "candidate_text": text, "mappings": [{"proposal_id": "p1", "excerpts": [text],
                                                   "explanation": "Condition and action remain local"}],
            "boundary_checks": [deepcopy(boundary)], "unresolved_expectations": ["Execution effect is unknown"],
            "upstream_feedback": [],
        }
        return diagnosis, editor

    def generator(self, stage, messages, output, *, usage=None, retries=0, failure=None):
        self.generated.append(stage)
        session = mock.Mock()
        if failure is not None:
            session.post.side_effect = failure
        else:
            content = self.diagnosis if stage == "diagnosis" else self.editor
            response = mock.Mock(status_code=200, ok=True)
            response.json.return_value = {
                "model": self.plan["model"], "choices": [{"message": {"content": json.dumps(content)}}],
                "usage": usage,
            }
            session.post.side_effect = [mock.Mock(status_code=429, ok=False) for _ in range(retries)] + [response]
        with mock.patch("src.adapters.alfworld.run_task_upstream.time.sleep"):
            return semantic_call(stage, messages, session=session, endpoint="https://offline.invalid", key="not-a-key",
                                 model=self.plan["model"], output=output)

    def execute(self, parent, skill, output_root, *, partial=False, usage=None, retries=0):
        snapshot = load_skill(skill)
        self.executed.append((parent["run_id"], snapshot))
        record = self.record(parent["task"], snapshot, partial=partial, usage=usage, retries=retries)
        path = output_root / record["run_id"] / "trajectory.json"
        path.parent.mkdir(parents=True)
        write_record(path, record)
        return path

    def run_one(self, generate=None, execute=None):
        return run_round(self.plan, self.paths, self.run_dir, generate or self.generator, execute or self.execute)

    def test_plan_rejects_changed_scope_and_unimplemented_budgets(self):
        mutations = {
            "parent_skill": "fixed", "split": "val", "purpose": "smoke", "memory": "history",
            "fusion": "transform", "adoption": "auto", "semantic_retries": 1, "parent_episodes": 1,
            "candidate_episodes_max": 3, "method_calls": {"diagnosis": 2, "editor_max": 1},
            "max_tokens_per_request": 1, "environment_seed": 7, "temperature_request": 0,
            "thinking": "disabled", "reasoning_effort": "low", "transport_attempts_per_request_max": 7,
            "max_steps_per_episode": 51,
        }
        validate_plan(self.plan)
        for key, value in mutations.items():
            with self.subTest(key=key):
                plan = {**self.plan, key: value}
                with self.assertRaises(ValueError):
                    validate_plan(plan)
        for tasks in ([], ["val:0000", "val:0001"], ["train:0000", "train:0000"]):
            with self.subTest(tasks=tasks), self.assertRaises(ValueError):
                validate_plan({**self.plan, "task_ids": tasks})

    def test_rejects_non_learning_or_non_noskill_parent_before_calls(self):
        skill_file = self.root / "existing.md"
        skill_file.write_text("Use available actions.")
        fixed = self.record(self.items[0], load_skill(skill_file))
        variants = [fixed]
        for split, purpose in (("train", "smoke"), ("val", "selection"), ("test", "final")):
            record = deepcopy(self.parents[0])
            record.update(split=split, purpose=purpose,
                          access={"learning_allowed": split == "train", "selection_allowed": split == "val", "final_only": split == "test"})
            record["task"]["id"] = split + ":0000"
            record["context_fingerprint"] = context_fingerprint(record)
            record["execution_fingerprint"] = execution_fingerprint(record)
            verify_record(record)
            variants.append(record)
        generate, execute = mock.Mock(), mock.Mock()
        for record in variants:
            with self.subTest(skill=record["skill"]["mode"], purpose=record["purpose"]):
                write_record(self.paths[0], record)
                with self.assertRaisesRegex(ValueError, "No Skill"):
                    self.run_one(generate, execute)
                self.assertFalse(self.run_dir.exists())
        generate.assert_not_called()
        execute.assert_not_called()

    def test_rejects_task_order_model_and_episode_budget_drift(self):
        for change in ({"task_ids": list(reversed(self.plan["task_ids"]))},
                       {"model": "other"}, {"max_steps_per_episode": 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                prepare_evidence(self.paths, {**self.plan, **change})
        write_record(self.paths[0], self.record(self.items[0], partial=True))
        with self.assertRaisesRegex(ValueError, "must be complete"):
            prepare_evidence(self.paths, self.plan)

    def test_diagnosis_stop_never_calls_editor_or_executes_candidate(self):
        for decision, expected in (("no_change", "no_change"), ("need_evidence", "needs_evidence")):
            with self.subTest(decision=decision):
                self.run_dir = self.root / decision
                self.generated.clear()
                self.diagnosis.update(decision=decision, proposals=[], interactions=[],
                                      missing_evidence=["Need a relevant opening observation"] if decision == "need_evidence" else [])
                execute = mock.Mock()
                report = self.run_one(execute=execute)
                self.assertEqual(report["status"], expected)
                self.assertEqual(self.generated, ["diagnosis"])
                execute.assert_not_called()
                self.assertFalse((self.run_dir / "candidate").exists())
                self.assertEqual(json.loads((self.run_dir / "report.json").read_text()), report)
                self.assertEqual(report["cost"]["semantic_calls"], 1)

    def test_editor_substantive_feedback_is_a_normal_stop(self):
        self.editor.update(decision="needs_revision", candidate_text=None, mappings=[], boundary_checks=[],
                           upstream_feedback=[{"proposal_ids": ["p1"], "limitation": "Cannot maintain a global notebook",
                                               "counterexample": "Older visits leave the actor history",
                                               "suggested_revision": "Use current observations", "scope_change": "Local scope only"}])
        execute = mock.Mock()
        report = self.run_one(execute=execute)
        self.assertEqual(report["status"], "needs_revision")
        self.assertEqual(self.generated, ["diagnosis", "editor"])
        execute.assert_not_called()
        self.assertEqual(json.loads((self.run_dir / "editor.json").read_text())["upstream_feedback"], self.editor["upstream_feedback"])
        self.assertFalse((self.run_dir / "candidate").exists())

    def test_generation_failure_is_preserved_as_error_without_semantic_retry(self):
        execute = mock.Mock()
        report = self.run_one(generate=lambda *args: self.generator(*args, failure=TimeoutError("private endpoint")), execute=execute)
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["error_type"], "TimeoutError")
        self.assertEqual(self.generated, ["diagnosis"])
        execute.assert_not_called()
        call = json.loads((self.run_dir / "calls/diagnosis.json").read_text())
        self.assertEqual(call["status"], "error")
        self.assertEqual(report["cost"]["semantic_calls"], 1)
        self.assertEqual(report["cost"]["http_attempts_with_unknown_usage"], 3)
        self.assertNotIn("private endpoint", json.dumps(report) + json.dumps(call))
        self.assertFalse((self.run_dir / "diagnosis.json").exists())

    def test_invalid_model_output_stops_as_error_and_keeps_raw_response(self):
        self.diagnosis = {"decision": "revise"}
        execute = mock.Mock()
        report = self.run_one(execute=execute)
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["error_type"], "ValueError")
        execute.assert_not_called()
        call = json.loads((self.run_dir / "calls/diagnosis.json").read_text())
        self.assertEqual(json.loads(call["steps"][0]["model_response"]["content"]), self.diagnosis)
        self.assertEqual(self.generated, ["diagnosis"])

    def test_one_snapshot_runs_on_declared_tasks_with_diff_and_source_lineage(self):
        report = self.run_one()
        self.assertEqual(report["status"], "candidate_evaluated")
        self.assertEqual([run for run, _ in self.executed], [r["run_id"] for r in self.parents])
        self.assertEqual(self.executed[0][1], self.executed[1][1])
        self.assertEqual([row["task_id"] for row in report["comparisons"]], self.plan["task_ids"])
        self.assertTrue(all(row["conditions"]["recorded_conditions_match"] for row in report["comparisons"]))
        self.assertEqual(report["adoption"]["decision"], "staging_only")
        lineage = json.loads((self.run_dir / "candidate/lineage.json").read_text())
        self.assertEqual(lineage["candidate"], self.executed[0][1])
        self.assertEqual(lineage["parent"], load_skill())
        diff = (self.run_dir / "candidate/actual.diff").read_bytes()
        self.assertIn(b"--- parent/NoSkill", diff)
        self.assertIn(b"+When a relevant closed cabinet", diff)
        self.assertEqual(lineage["diff_sha256"], digest(diff))
        for source, path, parent in zip(lineage["sources"], self.paths, self.parents):
            self.assertEqual(source["path"], str(path.resolve()))
            self.assertEqual(source["sha256"], digest(path.read_bytes()))
            self.assertEqual(source["run_id"], parent["run_id"])
        evidence_text = (self.run_dir / "evidence.json").read_text()
        self.assertNotIn(str(self.game), evidence_text)
        self.assertNotIn("Hidden game data", evidence_text)

    def test_partial_candidate_is_incomplete_and_never_adopted(self):
        report = self.run_one(execute=lambda *args: self.execute(*args, partial=True))
        self.assertEqual(report["status"], "evaluation_incomplete")
        self.assertEqual(len(self.executed), 2)
        self.assertEqual(report["adoption"]["decision"], "staging_only")
        for row in report["comparisons"]:
            self.assertFalse(row["candidate_audit"]["episode_complete"])
            self.assertIsNone(row["candidate_native_success"])
            self.assertIn("incomplete_episode", row["conditions"]["differences"])

    def test_source_mutation_stops_before_candidate_execution(self):
        def generate(stage, messages, output):
            result = self.generator(stage, messages, output)
            if stage == "editor":
                self.paths[0].write_text(self.paths[0].read_text() + " ")
            return result
        execute = mock.Mock()
        report = self.run_one(generate=generate, execute=execute)
        self.assertEqual(report["status"], "error")
        self.assertIn("Source trajectory changed", report["validation_error"])
        execute.assert_not_called()

    def test_candidate_mutation_between_tasks_stops_further_execution(self):
        def execute(parent, skill, output):
            path = self.execute(parent, skill, output)
            skill.write_text("A different Skill must never silently enter the second task.")
            return path
        report = self.run_one(execute=execute)
        self.assertEqual(report["status"], "error")
        self.assertIn("Candidate changed", report["validation_error"])
        self.assertEqual(len(self.executed), 1)
        self.assertEqual(report["cost"]["environment_requests"], 3)

    def test_execution_exception_keeps_persisted_partial_candidate_in_cost(self):
        def execute(parent, skill, output):
            self.execute(parent, skill, output, partial=True)
            raise RuntimeError("private process details")
        report = self.run_one(execute=execute)
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["error_type"], "RuntimeError")
        self.assertEqual(report["adoption"]["decision"], "staging_only")
        self.assertEqual(len(self.executed), 1)
        self.assertEqual(report["cost"]["environment_requests"], 3)
        self.assertEqual(report["cost"]["http_attempts"], 5)
        self.assertNotIn("private process details", json.dumps(report))
        partial = list((self.run_dir / "candidate_runs").glob("*/skill_*/trajectory.json"))
        self.assertEqual(len(partial), 1)
        self.assertFalse(verify_record(json.loads(partial[0].read_text()))["episode_complete"])

    def test_cost_includes_parent_method_candidate_retry_and_unknown_usage(self):
        known = {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
        self.parents[0] = self.record(self.items[0], usage=known, retries=1)
        self.parents[1] = self.record(self.items[1])
        self.save_parents()
        self.diagnosis, self.editor = self.proposals()
        report = self.run_one(
            generate=lambda *args: self.generator(*args, usage=known, retries=1),
            execute=lambda *args: self.execute(*args, usage=known, retries=1))
        self.assertEqual(report["status"], "candidate_evaluated")
        cost = report["cost"]
        self.assertEqual(cost["environment_requests"], 4)
        self.assertEqual(cost["semantic_calls"], 2)
        self.assertEqual(cost["http_attempts"], 11)
        self.assertEqual(cost["requests_with_unknown_usage"], 1)
        self.assertEqual(cost["http_attempts_with_unknown_usage"], 6)
        self.assertEqual(cost["reported_usage"], {"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25})

    def test_prior_parent_recovery_requires_failure_identity_hash_and_bounded_budget(self):
        path = self.root / "prior.json"
        prior = self.record(self.items[0], partial=True)
        prior["error_type"] = "ReadTimeout"
        write_record(path, prior)
        plan = {**self.plan, "prior_parent_attempts": [{"path": str(path), "sha256": digest(path.read_bytes())}],
                "parent_attempts_per_task_max": 2, "total_environment_request_slots_max": 10,
                "recovery_reason": "One infrastructure retry", "supersedes_plan_sha256": object_digest(self.plan)}
        self.assertEqual(load_prior_parent_attempts(plan, self.parents), [prior])
        for mutate in (lambda p: p.update(total_environment_request_slots_max=8),
                       lambda p: p.update(parent_attempts_per_task_max=3),
                       lambda p: p["prior_parent_attempts"].append(deepcopy(p["prior_parent_attempts"][0]))):
            variant = deepcopy(plan)
            mutate(variant)
            with self.assertRaises(ValueError):
                load_prior_parent_attempts(variant, self.parents)
        path.write_text(path.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "changed"):
            load_prior_parent_attempts(plan, self.parents)
        for record in (self.parents[0], {**prior, "error_type": "ValueError"}):
            write_record(path, record)
            plan["prior_parent_attempts"][0]["sha256"] = digest(path.read_bytes())
            with self.assertRaises(ValueError):
                load_prior_parent_attempts(plan, self.parents)

    def configure_v1(self):
        from tests.skill_evolution.v22.test_editor_preservation import build_editor_v1
        self.plan.pop("editor_schema", None)  # New default must be v1.
        self.editor = build_editor_v1(self.diagnosis)

    def test_new_editor_contract_binds_observation_plan_before_execution(self):
        from src.skill_evolution.v22.verify_round import verify_round
        self.configure_v1()
        def execute(parent, skill, output):
            observation = json.loads((self.run_dir / "observation_plan.json").read_text())
            lineage = json.loads((self.run_dir / "candidate/lineage.json").read_text())
            self.assertEqual(lineage["observation_plan_sha256"], object_digest(observation))
            return self.execute(parent, skill, output)
        report = self.run_one(execute=execute)
        self.assertEqual(report["editor_schema"], "v22.editor.v1")
        self.assertEqual(report["status"], "candidate_evaluated")
        self.assertTrue(verify_round(self.run_dir)["round_complete"])

    def test_new_editor_declared_capability_conflict_stops_before_release(self):
        from tests.skill_evolution.v22.test_editor_preservation import mark_revision
        from src.skill_evolution.v22.verify_round import verify_round
        self.configure_v1()
        mark_revision(self.editor)
        execute = mock.Mock()
        report = self.run_one(execute=execute)
        self.assertEqual(report["status"], "needs_revision")
        execute.assert_not_called()
        self.assertFalse((self.run_dir / "candidate").exists())
        self.assertTrue(verify_round(self.run_dir)["round_complete"])

    def test_new_editor_cannot_silently_return_legacy_output(self):
        self.plan.pop("editor_schema", None)
        execute = mock.Mock()
        report = self.run_one(execute=execute)
        self.assertEqual(report["status"], "error")
        self.assertIn("downgrade", report["validation_error"])
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
