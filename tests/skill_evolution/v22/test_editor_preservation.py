"""Check declarations and bindings; these tests do not prove text equivalence."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import load_skill, object_digest
from src.skill_evolution.v22.diagnosis_editor import editor_messages, validate_editor
from src.skill_evolution.v22.editor_preservation import (
    ACTOR_CAPABILITIES, ASPECTS, EDITOR_SCHEMA_V1, preservation_contract,
)
from tests.skill_evolution.v22.test_diagnosis_editor import (
    build_diagnosis, build_editor, build_evidence,
)


def build_editor_v1(diagnosis=None):
    diagnosis = diagnosis or build_diagnosis()
    editor = build_editor(diagnosis)
    editor.update(schema_version=EDITOR_SCHEMA_V1, requirements_sha256=object_digest(diagnosis))
    editor["requirement_checks"] = [{
        "proposal_id": "p1", "status": "faithful",
        "required_capabilities": ["current_observation", "current_admissible_commands"],
        "checks": [{
            "aspect": aspect, "status": "faithful",
            "excerpts": [] if aspect == "interactions" else [editor["candidate_text"]],
            "reason": "None supplied." if aspect == "interactions" else "The current visible condition and available action are retained.",
        } for aspect in ASPECTS],
    }]
    return editor


def mark_revision(editor, *, aspect="capabilities", required_capability="full_episode_history"):
    editor.update(decision="needs_revision", candidate_text=None, mappings=[], boundary_checks=[])
    row = editor["requirement_checks"][0]
    row["status"] = "needs_revision"
    row["required_capabilities"] = [required_capability]
    for check in row["checks"]:
        check["excerpts"] = []
        if check["aspect"] == aspect:
            check.update(status="needs_revision", reason="Complete prior visit status is unavailable; legal exploration is broader.")
    editor["upstream_feedback"] = [{
        "proposal_ids": ["p1"],
        "limitation": "Not-yet-visited status cannot be decided outside the two-pair actor window.",
        "counterexample": "A receptacle visited five actions ago is absent from the current actor context.",
        "suggested_revision": "Ask Diagnosis to define a visible alternative and unknown handling.",
        "scope_change": "General legal exploration would include already visited receptacles.",
    }]
    return editor


class EditorPreservationTests(unittest.TestCase):
    def setUp(self):
        self.parent, self.diagnosis, self.evidence = load_skill(), build_diagnosis(), build_evidence()
        self.editor = build_editor_v1(self.diagnosis)

    def validate(self):
        return validate_editor(self.editor, self.parent, self.diagnosis, self.evidence)

    def test_faithful_candidate_and_expression_only_both_pass(self):
        self.assertIs(self.validate(), self.editor)
        row = self.editor["requirement_checks"][0]
        row["status"] = "expression_only"
        row["checks"][0].update(status="expression_only", reason="Equivalent conditional phrasing; current visibility and admissibility unchanged.")
        self.validate()

    def test_literal_requirement_binding_rejects_changed_requirement(self):
        self.diagnosis["proposals"][0]["trigger"] += " or any unopened receptacle"
        with self.assertRaisesRegex(ValueError, "identity"):
            self.validate()

    def test_contract_covers_global_preserve_and_every_related_interaction(self):
        other = deepcopy(self.diagnosis["proposals"][0])
        other["id"] = "p2"
        self.diagnosis["proposals"].append(other)
        self.diagnosis["interactions"] = [{"proposal_ids": ["p1", "p2"], "relation": "Same action", "handling": "Do not duplicate"}]
        contract = preservation_contract(self.parent, self.diagnosis, self.evidence)
        for row in contract["proposal_sources"]:
            self.assertIn("/preserve/0/behavior", row["aspect_sources"]["preserve"])
            self.assertEqual(row["aspect_sources"]["interactions"], ["/interactions/0/relation", "/interactions/0/handling"])
        self.assertEqual(contract["requirements_sha256"], object_digest(self.diagnosis))
        self.assertEqual(contract["evidence_sha256"], object_digest(self.evidence))

    def test_missing_or_duplicate_aspect_cannot_silently_skip_obligation(self):
        original = deepcopy(self.editor)
        for mutation in ("missing", "duplicate", "unknown"):
            with self.subTest(mutation=mutation):
                self.editor = deepcopy(original)
                checks = self.editor["requirement_checks"][0]["checks"]
                if mutation == "missing":
                    checks.pop(3)
                elif mutation == "duplicate":
                    checks.append(deepcopy(checks[0]))
                else:
                    checks[0]["aspect"] = "all_good"
                with self.assertRaisesRegex(ValueError, "aspect"):
                    self.validate()

    def test_missing_duplicate_or_unknown_proposal_rejected(self):
        original = deepcopy(self.editor)
        for mutation in ("missing", "duplicate", "unknown"):
            with self.subTest(mutation=mutation):
                self.editor = deepcopy(original)
                rows = self.editor["requirement_checks"]
                if mutation == "missing":
                    rows.clear()
                elif mutation == "duplicate":
                    rows.append(deepcopy(rows[0]))
                else:
                    rows[0]["proposal_id"] = "unprovided"
                with self.assertRaises(ValueError):
                    self.validate()

    def test_absent_or_empty_actual_text_excerpt_rejected(self):
        for excerpts in (["Not actual Candidate text"], []):
            with self.subTest(excerpts=excerpts):
                self.editor["requirement_checks"][0]["checks"][0]["excerpts"] = excerpts
                with self.assertRaisesRegex(ValueError, "actual-text"):
                    self.validate()

    def test_false_aggregate_pass_rejected(self):
        self.editor["requirement_checks"][0]["checks"][0]["status"] = "needs_revision"
        with self.assertRaisesRegex(ValueError, "aggregate"):
            self.validate()

    def test_declared_substantive_departure_blocks_candidate(self):
        row = self.editor["requirement_checks"][0]
        row["status"] = row["checks"][0]["status"] = "needs_revision"
        with self.assertRaisesRegex(ValueError, "blocks release"):
            self.validate()

    def test_declared_unavailable_capability_cannot_be_claimed_faithful(self):
        self.editor["requirement_checks"][0]["required_capabilities"] = ["full_episode_history"]
        with self.assertRaisesRegex(ValueError, "unavailable capability"):
            self.validate()

    def test_not_yet_visited_to_general_exploration_returns_upstream(self):
        self.diagnosis["proposals"][0].update(
            strategy="Explore a not-yet-visited receptacle after the local interaction fails.",
            scope="Relies on the current observation and last two pairs, with no persistent state.",
        )
        self.editor = build_editor_v1(self.diagnosis)
        mark_revision(self.editor)
        for check in self.editor["requirement_checks"][0]["checks"]:
            if check["aspect"] == "strategy":
                check.update(status="needs_revision", reason="Replacing not-yet-visited with general legal exploration changes the eligible set.")
        self.validate()
        self.assertIsNone(self.editor["candidate_text"])
        self.assertIn("already visited", self.editor["upstream_feedback"][0]["scope_change"])

    def test_blocked_output_cannot_release_draft_or_fake_excerpt(self):
        mark_revision(self.editor)
        self.editor["requirement_checks"][0]["checks"][0]["excerpts"] = ["Unreleased draft"]
        with self.assertRaisesRegex(ValueError, "no released text"):
            self.validate()
        self.editor["requirement_checks"][0]["checks"][0]["excerpts"] = []
        self.editor["candidate_text"] = "A draft."
        with self.assertRaisesRegex(ValueError, "no candidate"):
            self.validate()

    def test_feedback_and_revision_checks_must_agree(self):
        mark_revision(self.editor)
        self.editor["requirement_checks"][0]["required_capabilities"] = ["current_observation"]
        self.editor["requirement_checks"][0]["status"] = "faithful"
        for check in self.editor["requirement_checks"][0]["checks"]:
            check["status"] = "faithful"
        with self.assertRaisesRegex(ValueError, "feedback must match"):
            self.validate()

    def test_unknown_capabilities_are_not_silently_granted(self):
        self.editor["requirement_checks"][0]["required_capabilities"] = ["a_new_memory_tool"]
        with self.assertRaisesRegex(ValueError, "capability"):
            self.validate()

    def test_no_change_checks_actual_parent(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(self.editor["candidate_text"], encoding="utf-8")
            self.parent = load_skill(path)
            self.editor.update(decision="no_change", candidate_text=None)
            self.validate()

    def test_v0_prompt_is_byte_compatible_and_v0_output_still_valid(self):
        self.assertEqual(object_digest(editor_messages(self.parent, self.diagnosis, self.evidence)),
                         "17aee31ac55c008f3a12927de40c9758e68eb22ef3bc4234e3dbe2be51d4e6d8")
        validate_editor(build_editor(self.diagnosis), self.parent, self.diagnosis, self.evidence)

    def test_v1_prompt_binds_sources_capabilities_and_no_extra_review(self):
        messages = editor_messages(self.parent, self.diagnosis, self.evidence, schema_version=EDITOR_SCHEMA_V1)
        payload = json.loads(messages[1]["content"].split("\n", 1)[1])
        self.assertEqual(payload["preservation_contract"]["actor_capabilities"], ACTOR_CAPABILITIES)
        self.assertEqual(payload["preservation_contract"]["requirements_sha256"], object_digest(self.diagnosis))
        self.assertIn("not in an extra review call", messages[0]["content"])
        self.assertIn("NOT an expression-only change", messages[0]["content"])
        self.assertIn("not proof of", messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
