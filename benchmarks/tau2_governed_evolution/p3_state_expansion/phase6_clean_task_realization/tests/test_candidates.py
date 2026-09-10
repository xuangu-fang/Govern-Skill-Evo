"""Static contracts and detached evaluator fixtures; no domain tools are called."""

import copy
import json
import unittest
from pathlib import Path

from tau2.data_model.tasks import Task

from benchmarks.tau2_governed_evolution.p3_state_expansion.phase6_clean_task_realization import (
    benchmark_adapter as adapter,
)
from benchmarks.tau2_governed_evolution.p3_state_expansion.phase6_clean_task_realization.build_candidates import (
    FORMAL,
    leakage,
    sha256,
)


HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[3]


def load(path):
    return json.loads(path.read_text())


class Phase6Candidates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = load(REPO / "external/tau2-bench/data/tau2/domains/retail/db.json")
        cls.tasks = load(HERE / "tasks/candidate_tasks.json")
        cls.specs = load(HERE / "evaluators/goal_specs.json")

    def expected_final(self, spec):
        final = copy.deepcopy(self.db)
        source = final["orders"][spec["source_order_id"]]
        upstream = spec["upstream"]
        resource = final["users"][spec["user_id"]]["payment_methods"][spec["resource_id"]]
        if upstream["kind"] == "cancel_pending_order":
            source["status"] = "cancelled"
            source["cancel_reason"] = upstream["reason"]
            source["payment_history"].append({
                "transaction_type": "refund", "amount": spec["resource"]["credit"],
                "payment_method_id": spec["resource_id"],
            })
        elif upstream["kind"] == "modify_pending_order_payment":
            amount = source["payment_history"][0]["amount"]
            source["payment_history"].extend([
                {"transaction_type": "payment", "amount": amount,
                 "payment_method_id": upstream["new_payment_method_id"]},
                {"transaction_type": "refund", "amount": amount,
                 "payment_method_id": spec["resource_id"]},
            ])
        else:
            self.apply_item_change(source, upstream["item_change"], spec["resource_id"])
        target = final["orders"][spec["downstream_order_id"]]
        self.apply_item_change(target, spec["downstream"]["item_change"], spec["resource_id"])
        resource["balance"] = spec["resource"]["expected_final_balance"]
        return final

    def apply_item_change(self, order, change, resource_id):
        index = next(i for i, item in enumerate(order["items"])
                     if item["item_id"] == change["old_item_id"])
        old = order["items"][index]
        variant = self.db["products"][change["product_id"]]["variants"][change["new_item_id"]]
        difference = round(variant["price"] - old["price"], 2)
        order["items"][index] = {"name": old["name"], "product_id": old["product_id"],
                                 "item_id": variant["item_id"], "price": variant["price"],
                                 "options": copy.deepcopy(variant["options"])}
        order["payment_history"].append({
            "transaction_type": "payment" if difference > 0 else "refund",
            "amount": abs(difference), "payment_method_id": resource_id,
        })
        order["status"] = "pending (item modified)"

    def test_schema_ids_and_candidate_boundary(self):
        formal_ids = {task["id"] for task in load(FORMAL / "tasks/expanded_tasks.json")}
        self.assertEqual(len(self.tasks), 3)
        self.assertEqual(len({task["id"] for task in self.tasks}), 3)
        self.assertFalse(formal_ids.intersection(task["id"] for task in self.tasks))
        for task in self.tasks:
            self.assertEqual(Task.model_validate(task).id, task["id"])
            self.assertIsNone(task["evaluation_criteria"])

    def test_learner_safe_requests(self):
        for index, task in enumerate(self.tasks, 1):
            request = load(HERE / "requests" / f"{task['id']}.json")
            self.assertEqual(leakage(request), [])
            self.assertEqual(request["task_context"]["task_id"], f"T{index:03d}")
            poison = copy.deepcopy(task)
            poison["description"]["notes"] = "P3 state expansion stale-state construction metadata"
            poison["mechanism"] = "Mutation-Induced Resource Refresh Dependency"
            self.assertEqual(adapter.build_task_request(poison, f"T{index:03d}", request["tools"]), request)

    def test_success_final_state_and_stale_failure(self):
        for task in self.tasks:
            spec = self.specs[task["id"]]
            final = self.expected_final(spec)
            result = adapter.evaluate_success(task, self.db, final)
            self.assertTrue(result["success"])
            self.assertFalse(result["compliance_evaluated"])
            stale = copy.deepcopy(final)
            stale["orders"][spec["downstream_order_id"]] = copy.deepcopy(
                self.db["orders"][spec["downstream_order_id"]]
            )
            stale["users"][spec["user_id"]]["payment_methods"][spec["resource_id"]]["balance"] = (
                spec["resource"]["after_upstream"]
            )
            self.assertFalse(adapter.evaluate_success(task, self.db, stale)["success"])

    def test_formal_benchmark_hashes_preserved(self):
        provenance = load(HERE / "p3_realization_provenance.json")
        hashes = provenance["formal_benchmark_preservation_sha256"]
        self.assertEqual(sha256(FORMAL / "expanded_benchmark_manifest.json"),
                         hashes["expanded_benchmark_manifest.json"])
        self.assertEqual(sha256(FORMAL / "tasks/expanded_tasks.json"),
                         hashes["tasks/expanded_tasks.json"])


if __name__ == "__main__":
    unittest.main()
