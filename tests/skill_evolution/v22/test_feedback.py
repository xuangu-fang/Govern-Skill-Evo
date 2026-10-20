"""Replay integration checks with synthetic traces and one recorded mock HTTP call.

The fixture assessments only exercise contracts; they are not semantic evidence.
"""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.adapters.alfworld.skill_runtime import object_digest, write_record
from src.skill_evolution.v22.feedback import (
    prepare_feedback, run_facts, run_feedback, verify_feedback, visible_run,
)
from src.skill_evolution.v22.model_call import semantic_call
from src.skill_evolution.v22.replay_contract import SCHEMA
from tests.skill_evolution.v22.test_verify_round import change, make_round


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_assessment(payload):
    """Populate the contract from the input, never infer real-world correctness."""
    observations = []
    for target in payload["observation_plan"]["targets"]:
        for pair in payload["facts"]["pairs"]:
            complete = pair["comparison_eligible"]
            observations.append({
                "target_id": target["id"], "task_id": pair["task_id"],
                "parent_opportunity": "reached", "candidate_opportunity": "reached" if complete else "unknown",
                "opportunity_reason": "Synthetic fixture only; no substantive behavioral conclusion.",
                "parent_behavior": "The fixture executes look.",
                "candidate_behavior": "The fixture executes look." if complete else "No completed Candidate action.",
                "candidate_behavior_status": "other_branch" if complete else "unknown",
                "response_kind": "observed_preservation" if complete else "unknown",
                "response": "Synthetic preservation of the saved action." if complete else "Incomplete evidence.",
                "parent_refs": [{"run_id": pair["parent_run_id"], "step": 1}],
                "candidate_refs": [{"run_id": pair["candidate_run_id"], "step": 1 if complete else 0}],
                "unknowns": ["Synthetic data cannot establish semantic validity or causal effects."],
            })
    return {
        "schema_version": SCHEMA, "summary": "Synthetic assessment, not an experimental result.",
        "realization": [{"proposal_id": proposal["id"], "status": "unknown",
                         "requirement_excerpt": proposal["strategy"],
                         "candidate_excerpts": [payload["candidate"]["text"]],
                         "assessment": "Exact text binding only; equivalence is not established."}
                        for proposal in payload["requirements"]["proposals"]],
        "observations": observations, "relations": [],
        "expectation_checks": [{"index": i, "status": "unknown", "assessment": "Fixture does not resolve this expectation.",
                                "evidence_refs": []}
                               for i, _ in enumerate(payload["observation_plan"]["editor_unresolved_expectations"])],
        "unexpected_changes": [], "untested": ["Actual task behavior and transfer remain untested."], "followups": [],
    }


class FeedbackIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def build(self, mode="candidate", name="case"):
        target = self.root / name
        target.mkdir()
        return make_round(target)(mode)

    def execute(self, source, output=None, response=None, failure=None, mutate_assessment=None):
        output = output or source.parent / "feedback"
        payload, _, model = prepare_feedback(source)
        assessment = fixture_assessment(payload)
        if mutate_assessment:
            mutate_assessment(assessment)
        raw = json.dumps(assessment) if response is None else response
        session = mock.Mock()
        if failure is not None:
            session.post.side_effect = failure
        else:
            session.post.return_value.status_code = 200
            session.post.return_value.ok = True
            session.post.return_value.json.return_value = {
                "model": model, "choices": [{"message": {"content": raw}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20},
            }

        def generate(stage, messages, call_output):
            return semantic_call(stage, messages, session=session, endpoint="https://private.invalid",
                                 key="private-secret", model=model, output=call_output)

        result = run_feedback(source, output, generate)
        return output, result, session

    def test_round_trip_preserves_source_and_separates_incremental_cost(self):
        source = self.build()
        _, bindings, _ = prepare_feedback(source)
        before = {entry["path"]: Path(entry["path"]).read_bytes() for entry in bindings}
        output, report, session = self.execute(source)
        self.assertEqual(report["status"], "feedback_ready")
        self.assertEqual(session.post.call_count, 1)
        audit = verify_feedback(output)
        self.assertTrue(audit["artifact_valid"] and audit["feedback_ready"])
        self.assertEqual(before, {path: Path(path).read_bytes() for path in before})
        package = read(output / "package.json")
        self.assertEqual(package["facts"]["source_round_cost"], read(source / "report.json")["cost"])
        cost = package["incremental_cost"]
        self.assertEqual(cost["semantic_calls"], 1)
        self.assertEqual(cost["environment_requests"], 0)
        self.assertEqual(cost["http_attempts"], 1)
        self.assertEqual(cost["reported_usage"]["total_tokens"], 20)
        self.assertFalse(package["learning_boundary"]["memory_written"])
        self.assertFalse(package["learning_boundary"]["adoption_changed"])
        self.assertNotIn("private-secret", (output / "calls/replay.json").read_text())

    def test_legacy_questions_are_reconstructed_without_retrospective_approval(self):
        source = self.build()
        # Reconstruct the historical v0 layout, before observation plans existed.
        plan = read(source / "plan.json")
        del plan["editor_schema"]
        write_record(source / "plan.json", plan)
        change(source / "report.json", lambda value: (value.pop("editor_schema"), value.update(plan_sha256=object_digest(plan))))
        change(source / "candidate/lineage.json", lambda value: value.pop("observation_plan_sha256"))
        (source / "observation_plan.json").unlink()
        payload, _, _ = prepare_feedback(source)
        self.assertEqual(payload["observation_plan_origin"], "reconstructed_from_frozen_pre_execution_artifacts")
        self.assertEqual(payload["editor_preservation"]["status"], "not_recorded_legacy")
        self.assertEqual(payload["editor_preservation"]["checks"], [])
        self.assertEqual([t["id"] for t in payload["observation_plan"]["targets"]], ["goal:g1", "preserve:0"])

    def test_new_observation_questions_are_bound_to_execution_lineage(self):
        source = self.build()
        payload, _, _ = prepare_feedback(source)
        self.assertEqual(payload["observation_plan_origin"], "saved_before_execution")
        change(source / "observation_plan.json", lambda value: value["targets"][0].update(behavior="Outcome-chosen question"))
        with self.assertRaises(ValueError):
            prepare_feedback(source)

    def test_visible_data_omits_actor_messages_reasoning_and_hidden_state(self):
        source = self.build()
        source_path = Path(read(source / "sources.json")[0]["path"])
        record = read(source_path)
        record["hidden_evaluator_state"] = "HIDDEN_ORACLE_MARKER"
        record["steps"][0]["model_response"]["reasoning_content"] = "PRIVATE_REASONING_MARKER"
        safe = visible_run(record)
        serialized = json.dumps(safe)
        for forbidden in ("messages", "model_response", "reasoning_content", "gamefile", "hidden_evaluator_state"):
            self.assertNotIn('"' + forbidden + '"', serialized)
        self.assertNotIn("HIDDEN_ORACLE_MARKER", serialized)
        self.assertNotIn("PRIVATE_REASONING_MARKER", serialized)
        self.assertNotIn(str(source.parent), serialized)
        payload, _, _ = prepare_feedback(source)
        self.assertNotIn(str(source.parent), json.dumps(payload))
        self.assertEqual(safe["steps"][0]["observation_before"], record["initial_observation"])

    def test_mechanical_action_facts_do_not_invent_semantic_success(self):
        source = self.build()
        record = read(Path(read(source / "sources.json")[0]["path"]))
        facts = run_facts(record)
        self.assertEqual(facts["look_action_steps"], [1])
        self.assertEqual(facts["non_admissible_action_steps"], [])
        bad = deepcopy(record)
        bad["steps"][0].update(action="open cabinet 99", action_in_admissible_commands=False,
                                observation="Nothing happens.")
        bad["steps"][0]["model_response"]["content"] = "<action>open cabinet 99</action>"
        facts = run_facts(bad)
        self.assertEqual(facts["non_admissible_action_steps"], [1])
        self.assertEqual(facts["literal_nothing_happens_steps"], [1])
        self.assertFalse(facts["native_success"])
        self.assertEqual(facts["action_count"], 1)

    def test_transport_failure_is_recorded_once_without_package_or_zeroed_usage(self):
        output, report, session = self.execute(self.build(), failure=TimeoutError("private transport contents"))
        self.assertEqual(report["status"], "error")
        self.assertEqual(session.post.call_count, 1)
        self.assertEqual(report["incremental_cost"]["requests_with_unknown_usage"], 1)
        self.assertEqual(report["incremental_cost"]["http_attempts_with_unknown_usage"], 1)
        self.assertFalse((output / "package.json").exists())
        self.assertFalse((output / "assessment.json").exists())
        self.assertFalse(verify_feedback(output)["feedback_ready"])
        self.assertNotIn("private transport contents", (output / "calls/replay.json").read_text())

    def test_malformed_response_is_retained_without_retry_or_package(self):
        output, report, session = self.execute(self.build(), response='{"incomplete":')
        self.assertEqual(report["status"], "error")
        self.assertEqual(session.post.call_count, 1)
        self.assertEqual(report["incremental_cost"]["reported_usage"]["total_tokens"], 20)
        self.assertFalse((output / "package.json").exists())
        self.assertEqual(read(output / "calls/replay.json")["steps"][0]["model_response"]["content"], '{"incomplete":')
        self.assertFalse(verify_feedback(output)["feedback_ready"])

    def test_tampered_source_input_package_reference_and_call_are_rejected(self):
        for mutation in ("source", "input", "package", "reference", "call", "extra_call"):
            with self.subTest(mutation=mutation):
                source = self.build(name=mutation)
                output, report, _ = self.execute(source)
                self.assertEqual(report["status"], "feedback_ready")
                if mutation == "source":
                    path = Path(read(source / "sources.json")[0]["path"])
                    path.write_bytes(path.read_bytes() + b"\n")
                elif mutation == "input":
                    change(output / "input.json", lambda value: value["facts"]["pairs"][0]["candidate"].update(action_count=99))
                elif mutation == "package":
                    change(output / "package.json", lambda value: value["learning_boundary"].update(memory_written=True))
                elif mutation == "reference":
                    change(output / "assessment.json", lambda value: value["observations"][0]["candidate_refs"][0].update(step=99))
                elif mutation == "call":
                    change(output / "calls/replay.json", lambda value: value["steps"][0]["transport_attempts"][0].update(request_sha256="wrong"))
                else:
                    write_record(output / "calls/retry.json", read(output / "calls/replay.json"))
                with self.assertRaises(ValueError):
                    verify_feedback(output)

    def test_output_cannot_be_inside_source_round(self):
        source = self.build()
        for output in (source, source / "feedback"):
            with self.subTest(output=output):
                generate = mock.Mock()
                with self.assertRaisesRegex(ValueError, "outside"):
                    run_feedback(source, output, generate)
                generate.assert_not_called()
        self.assertFalse((source / "feedback").exists())

    def test_partial_candidate_keeps_observations_unknown(self):
        source = self.build("partial")
        payload, _, _ = prepare_feedback(source)
        pair = payload["facts"]["pairs"][0]
        self.assertFalse(pair["comparison_eligible"])
        self.assertFalse(pair["candidate"]["episode_complete"])
        self.assertIsNone(pair["candidate"]["native_success"])
        self.assertEqual(pair["candidate"]["action_count"], 0)
        output, report, _ = self.execute(source)
        self.assertEqual(report["status"], "feedback_ready")
        self.assertTrue(verify_feedback(output)["feedback_ready"])
        self.assertTrue(all(row["response_kind"] == "unknown" for row in read(output / "assessment.json")["observations"]))
        bad_output, bad_report, session = self.execute(
            source, output=source.parent / "bad_feedback",
            mutate_assessment=lambda value: value["observations"][0].update(response_kind="observed_preservation"))
        self.assertEqual(bad_report["status"], "error")
        self.assertEqual(session.post.call_count, 1)
        self.assertFalse((bad_output / "package.json").exists())
        self.assertFalse(verify_feedback(bad_output)["feedback_ready"])


if __name__ == "__main__":
    unittest.main()
