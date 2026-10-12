from copy import deepcopy
import unittest

from benchmark_v5.sa.environment import Environment, canonical, replay
from benchmark_v5.sa.evaluation import evaluate, learning_observation, training_feedback
from benchmark_v5.sa.fixtures import case, development, order, training_fixture, training_plan
from benchmark_v5.sa.offline import Client, compatible, execute_plan, feasible_plan, observed_batches, validate
from benchmark_v5.sa.rules import World


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.env = Environment(case("unit", [order("a", quantity=2), order("b", quantity=2)]))
        self.c = Client(self.env.call)

    def test_public_contract_contains_recipe_not_world(self):
        self.assertEqual(self.c("read_recipes")["recipe_minutes"], 6)
        public = canonical([self.env.request(), self.env.catalog(), self.c("read_status")])
        for private in ("fixture_minutes", "fall_minutes", "per_unit_handling", "overlap", "world\"", "setup_end"):
            self.assertNotIn(private, public)
        self.assertEqual(self.env.call("audit", {}), {"error": "UNKNOWN_TOOL_OR_INVALID_ARGUMENTS"})

    def test_initial_observation_does_not_reveal_different_hidden_worlds(self):
        other = Environment(self.env.case, World(10, 8, 4, False, True, False))
        self.assertEqual(self.env.request(), other.request())
        self.assertEqual(self.env.catalog(), other.catalog())

    def test_query_draft_edit_cancel_do_not_advance_time(self):
        self.c("draft_batch", batch_id="x", allocations={"a": 1})
        self.c("draft_batch", batch_id="x", allocations={"a": 2, "b": 2})
        self.c("read_status")
        self.c("read_log")
        self.c("cancel_batch", batch_id="x")
        self.assertEqual(self.env.state["now"], 0)
        self.assertEqual(self.env.state["setting"], ["flat", "low"])
        self.assertEqual(self.env.state["completed"], {"a": [], "b": []})

    def test_bad_quantities_and_capacity_atomic(self):
        for allocation in ({"a": True}, {"a": -1}, {"a": 1.5}, {}, {"alien": 1}, {"a": 3, "b": 3}):
            before = deepcopy(self.env.state)
            result = self.env.call("draft_batch", dict(batch_id="x", allocations=allocation, operation_id="bad"))
            self.assertIn("error", result)
            self.assertEqual(before, self.env.state)

    def test_reservations_prevent_double_production(self):
        self.c("draft_batch", batch_id="x", allocations={"a": 2})
        result = self.env.call("draft_batch", dict(batch_id="y", allocations={"a": 1}, operation_id="bad"))
        self.assertEqual(result["error"], "QUANTITY_ALREADY_COMPLETED_OR_RESERVED")
        self.c("cancel_batch", batch_id="x")
        self.c("draft_batch", batch_id="y", allocations={"a": 2})

    def test_incompatible_recipe_rejected_not_hidden_compliance(self):
        env = Environment(development()[0])
        r = env.call("draft_batch", dict(batch_id="x", allocations={"o1": 1, "o2": 1}, operation_id="x"))
        self.assertEqual(r["error"], "INCOMPATIBLE_SETTINGS")
        self.assertIsNone(evaluate(env.audit())["C"])

    def test_idempotency_and_payload_conflict(self):
        args = dict(batch_id="x", allocations={"a": 2}, operation_id="same")
        a = self.env.call("draft_batch", args)
        self.assertEqual(self.env.call("draft_batch", args), a)
        self.assertIn("error", self.env.call("cancel_batch", dict(batch_id="x", operation_id="same")))
        self.assertEqual(self.env.state["batches"]["x"]["phase"], "DRAFT")

    def test_no_future_end_time_before_execution(self):
        env = Environment(development()[0]); c = Client(env.call)
        c("draft_batch", batch_id="x", allocations={"o1": 4})
        c("start_batch", batch_id="x")
        self.assertEqual(c("read_status")["now"], 0)
        self.assertEqual(c("read_log"), [])
        self.assertNotIn("processing", canonical(c("read_status")))
        c("advance")
        self.assertEqual(c("read_log")[0]["end"], 4)

    def test_safe_cancel_after_setup_preserves_time_and_setting(self):
        env = Environment(development()[0]); c = Client(env.call)
        c("draft_batch", batch_id="x", allocations={"o1": 4})
        c("start_batch", batch_id="x")
        self.assertIn("error", env.call("cancel_batch", dict(batch_id="x", operation_id="during")))
        c("advance"); c("cancel_batch", batch_id="x")
        self.assertEqual(env.state["now"], 4)
        self.assertEqual(env.state["setting"], ["flat", "high"])
        self.assertEqual(env.state["completed"]["o1"], [])
        c("draft_batch", batch_id="y", allocations={"o1": 4})
        self.assertEqual(c("start_batch", batch_id="y")["phase"], "READY")
        c("advance")
        self.assertEqual(env.state["now"], 14)

    def test_started_job_cannot_be_undone_after_delivery(self):
        self.c("draft_batch", batch_id="x", allocations={"a": 2})
        self.c("start_batch", batch_id="x"); self.c("advance")
        self.assertIn("error", self.env.call("cancel_batch", dict(batch_id="x", operation_id="cancel")))
        self.assertEqual(self.env.state["completed"]["a"][0]["quantity"], 2)

    def test_material_release_failure_does_not_consume_time(self):
        env = Environment(development()[3]); c = Client(env.call)
        c("draft_batch", batch_id="x", allocations={"o2": 2})
        self.assertEqual(env.call("start_batch", dict(batch_id="x", operation_id="s"))["error"], "MATERIAL_NOT_RELEASED")
        self.assertEqual(env.state["now"], 0)
        c("wait_until", minute=12)
        c("start_batch", batch_id="x"); c("advance")
        self.assertEqual(env.state["now"], 22)

    def test_shift_interrupt_does_not_leak_expected_duration_or_create_output(self):
        env = Environment(case("short", [order("a", due=7)], shift_end=7)); c = Client(env.call)
        c("draft_batch", batch_id="x", allocations={"a": 4}); c("start_batch", batch_id="x")
        self.assertEqual(c("advance"), dict(batch_id="x", phase="INTERRUPTED", at=7))
        self.assertEqual(env.state["completed"]["a"], [])
        self.assertNotIn("10", canonical(c("read_log")))
        self.assertFalse(evaluate(env.audit())["S"])

    def test_active_wait_rejected_and_clock_cannot_go_back(self):
        self.c("wait_until", minute=5)
        self.assertIn("error", self.env.call("wait_until", dict(minute=4, operation_id="back")))
        self.c("draft_batch", batch_id="x", allocations={"a": 2}); self.c("start_batch", batch_id="x")
        self.assertIn("error", self.env.call("wait_until", dict(minute=20, operation_id="skip")))
        self.assertEqual(self.env.state["now"], 5)

    def test_batched_and_separate_outcomes_have_expected_times(self):
        c = development()[2]
        merged = execute_plan(c, [{"o1": 2, "o2": 2}])
        split = execute_plan(c, [{"o1": 2}, {"o2": 2}])
        self.assertTrue(evaluate(merged)["S"])
        self.assertFalse(evaluate(split)["S"])
        self.assertEqual((merged["final"]["now"], split["final"]["now"]), (10, 20))

    def test_deadline_equal_is_success(self):
        a = execute_plan(case("equal", [order("a", due=10)]), [{"a": 4}])
        self.assertEqual(evaluate(a), dict(S=True, C=None, SC=None))

    def test_receipt_cannot_claim_future_or_wrong_quantity(self):
        self.c("finish", receipt={"a": dict(quantity=2, completed_at=10), "b": dict(quantity=2, completed_at=10)})
        self.assertFalse(evaluate(self.env.audit())["S"])
        self.assertIn("error", self.env.call("wait_until", dict(minute=10, operation_id="after")))

    def test_grader_rejects_false_receipt_even_with_delivery(self):
        audit = execute_plan(development()[2], [{"o1": 2, "o2": 2}])
        audit["final"]["receipt"]["o1"]["completed_at"] = 9
        self.assertFalse(evaluate(audit)["S"])
        with self.assertRaises(ValueError): replay(audit)

    def test_finish_response_is_not_a_grader_oracle(self):
        self.assertEqual(self.c("finish", receipt={}), {"closed": True})
        self.assertFalse(evaluate(self.env.audit())["S"])

    def test_train_feedback_same_score_and_dev_blocked(self):
        a = execute_plan(training_fixture(), training_plan())
        self.assertEqual(training_feedback(a)["scores"], evaluate(a))
        observation = learning_observation(a)
        self.assertNotIn("fixture_minutes", canonical(observation))
        self.assertNotIn("survivors", canonical(observation))
        a["case"]["split"] = "engineering_dev"
        with self.assertRaises(ValueError): training_feedback(a)
        with self.assertRaises(ValueError): learning_observation(a)

    def test_replay_detects_event_and_clock_tampering(self):
        a = execute_plan(development()[2], [{"o1": 2, "o2": 2}])
        self.assertEqual(replay(a).audit(), a)
        a["events"][0]["result"]["now"] = 99
        with self.assertRaises(ValueError): replay(a)

    def test_returned_observation_cannot_mutate_service(self):
        self.c("read_status")["orders"][0]["quantity"] = 999
        self.env.audit()["world"]["fall_minutes"] = 0
        self.assertEqual(self.env.orders["a"]["quantity"], 2)
        self.assertEqual(self.env.world.fall_minutes, 8)

    def test_evidence_identifiability_and_insufficient_prefix(self):
        obs = observed_batches(learning_observation(execute_plan(training_fixture(), training_plan())))
        self.assertEqual(len(compatible(obs[:1])), 64)
        self.assertEqual(compatible(obs), [World()])
        no_joint = [o for o in obs if not (o["before"][0] != o["after"][0] and o["before"][1] != o["after"][1])]
        self.assertEqual(len(compatible(no_joint)), 2)

    def test_feature_not_order_identity_drives_law(self):
        original = development()[4]
        renamed = deepcopy(original)
        renamed["orders"].reverse()
        for i, row in enumerate(renamed["orders"]): row["id"] = f"new-{i}"
        a = execute_plan(renamed, feasible_plan(renamed, World()))
        self.assertTrue(evaluate(a)["S"])

    def test_impossible_goal_not_disguised_as_reference_success(self):
        c = case("impossible", [order("a", due=5)])
        self.assertIsNone(feasible_plan(c, World()))

    def test_offline_suite_replays_and_does_not_call_models(self):
        result, traces, _ = validate()
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["fixtures"], 7)
        self.assertTrue(result["all_replayed"])
        self.assertTrue(all(row["reference"]["S"] for row in result["outcomes"]))
        self.assertGreater(len(traces), 7)


if __name__ == "__main__":
    unittest.main()
