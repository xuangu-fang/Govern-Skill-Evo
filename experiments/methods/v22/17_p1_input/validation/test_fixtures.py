"""Offline fixture checks. Never invoke a model, gateway or environment."""
import json
from copy import deepcopy
import unittest

from fixtures import (build_cases, validate_output, source_manifest, REAL, read,
                      GROUP_PROMPT, V3, V4, object_digest, digest)
from src.skill_evolution.v22.grouped_representation import grouping_messages
from src.skill_evolution.v22.grouped_update import grouped_messages
from src.skill_evolution.v22.p1_input import decode
from src.skill_evolution.v22.effective_memory import effective_consumption_payload


class FrozenProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {case["id"]: case for case in build_cases()}

    def test_eight_fixed_probes_and_unchanged_budgets(self):
        self.assertEqual(len(self.cases), 8)
        self.assertEqual(sum(c["parameters"]["max_tokens"] for c in self.cases.values()), 327680)
        self.assertEqual(sum(c["profile"] == V4 for c in self.cases.values()), 5)
        self.assertTrue(all(c["parameters"]["model"] == "deepseek-v4-pro" for c in self.cases.values()))

    def test_matched_learning_uses_real_old_candidate(self):
        for key in ("learning_p1", "learning_v3"):
            value = self.cases[key]["payload"]
            self.assertEqual(value["candidate"]["sha256"], read(REAL / "candidate.json")["sha256"])
            self.assertEqual(value["plan"], read(REAL / "execution_plan.json"))
            self.assertEqual(len(value["pairs"]), 10)
            self.assertEqual(len(value["runs"]), 20)
            self.assertEqual(value["memory"], read(REAL / "memory_before.json"))
            self.assertEqual(value["update_context"]["editor"]["mappings"], read(REAL / "outputs/main_editor.json")["mappings"])
        self.assertEqual(len(source_manifest()), 36)

    def test_controls_share_all_underlying_facts(self):
        for stage in ("diagnosis", "fusion", "learning"):
            a = deepcopy(self.cases[stage + "_p1"]["payload"])
            b = deepcopy(self.cases[stage + "_v3"]["payload"])
            for value in (a, b):
                value.pop("update_profile", None)
                value.pop("binding_sha256", None)
            self.assertEqual(a, b)

    def test_every_p1_view_roundtrips(self):
        for case in self.cases.values():
            payload, stage = case["payload"], case["stage"]
            if case["profile"] != V4:
                continue
            messages = (grouping_messages(payload, GROUP_PROMPT.read_text(), profile=V4)
                        if stage == "classification" else grouped_messages(stage, payload))
            expected = payload if stage in ("classification", "diagnosis") else effective_consumption_payload(payload)
            self.assertEqual(decode(json.loads(messages[1]["content"])), expected)

    def test_old_valid_outputs_still_have_legal_sources(self):
        for name, output in [("diagnosis_p1", "diagnosis"), ("fusion_p1", "fusion"), ("editor_p1", "main_editor")]:
            validate_output(self.cases[name], read(REAL / f"outputs/{output}.json"))
        case = self.cases["classification_p1"]
        frozen = validate_output(case, read(REAL / "outputs/classification.json"))
        system = grouping_messages(case["payload"], GROUP_PROMPT.read_text(), profile=V4)[0]["content"]
        self.assertEqual(frozen["prompt_sha256"], digest(system.encode()))
        self.assertEqual(frozen["input_sha256"], object_digest(case["classification_binding"]))


if __name__ == "__main__":
    unittest.main()
