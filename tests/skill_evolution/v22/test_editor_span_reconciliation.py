"""Formatting-only citation recovery; no model or environment execution."""

from copy import deepcopy
import unittest

from src.skill_evolution.v22.editor_span_reconciliation import normalize_numbered_spans
from tests.skill_evolution.v22.test_compact_update import editor, payload


class EditorSpanReconciliationTests(unittest.TestCase):
    def example(self, first="Preserve the first obligation.", second="Continue the second obligation.", gap="\n7. "):
        value = editor()
        value["candidate_text"] = "1. Use an exact current admissible action.\n6. " + first + gap + second
        value["mappings"][1]["excerpt"] = first + " " + second
        return value

    def test_observed_rule_six_to_rule_seven_case_only_splits_citation(self):
        first = ("For multi-object goals, transfer each carried required object to the named destination before "
                 "going to collect another exemplar. Do not return a carried required target to its source.")
        second = ("Continue until the action observation explicitly confirms the required transfer, such as a "
                  "'You move ... to ...' message.")
        value, context = self.example(first, second), payload()
        before, before_context = deepcopy(value), deepcopy(context)
        result = normalize_numbered_spans(value, context)
        self.assertEqual([row["excerpt"] for row in result["mappings"][1:]], [first, second])
        self.assertEqual(result["mappings"][0], value["mappings"][0])
        self.assertTrue(all(row["requirements"] == ["u2"] and row["side"] == "candidate"
                            for row in result["mappings"][1:]))
        self.assertEqual({key: val for key, val in result.items() if key != "mappings"},
                         {key: val for key, val in value.items() if key != "mappings"})
        self.assertEqual(value, before)
        self.assertEqual(context, before_context)
        self.assertEqual(normalize_numbered_spans(result, context), result)

    def test_omitted_words_semantic_changes_and_nonlist_gaps_are_rejected(self):
        for gap in ("\n7. Never continue. ", "\n", "\n- ", "  ", "\n7: ", "\n7.\n"):
            with self.subTest(gap=gap):
                with self.assertRaises(ValueError):
                    normalize_numbered_spans(self.example(gap=gap), payload())
        value = self.example()
        value["mappings"][1]["excerpt"] = value["mappings"][1]["excerpt"].replace("Preserve", "Ignore")
        with self.assertRaises(ValueError):
            normalize_numbered_spans(value, payload())

    def test_ambiguous_formatting_matches_are_rejected(self):
        value = self.example()
        value["candidate_text"] += "\n" + value["candidate_text"]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            normalize_numbered_spans(value, payload())

    def test_already_exact_mappings_are_unchanged_and_deepcopied(self):
        value = editor()
        value["candidate_text"] += "\n" + value["candidate_text"]
        result = normalize_numbered_spans(value, payload())
        self.assertEqual(result, value)
        result["mappings"][0]["requirements"].append("u2")
        self.assertNotEqual(result, value)

    def test_multiple_numbered_boundaries_preserve_exact_join(self):
        value = self.example(second="Continue the second obligation.\n8. Preserve recovery.")
        value["mappings"][1]["excerpt"] = value["mappings"][1]["excerpt"].replace("\n8. ", " ")
        result = normalize_numbered_spans(value, payload())
        self.assertEqual(len(result["mappings"]), 4)
        self.assertEqual(" ".join(row["excerpt"] for row in result["mappings"][1:]),
                         value["mappings"][1]["excerpt"])

    def test_other_editor_constraints_are_still_checked(self):
        value = self.example()
        value["mappings"][1]["requirements"] = ["u999"]
        with self.assertRaises(ValueError):
            normalize_numbered_spans(value, payload())
        value = self.example()
        value["mappings"][1]["side"] = "parent"
        with self.assertRaisesRegex(ValueError, "Only Candidate"):
            normalize_numbered_spans(value, payload())


if __name__ == "__main__":
    unittest.main()
