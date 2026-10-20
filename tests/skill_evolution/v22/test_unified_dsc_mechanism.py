"""Offline checks of update/response representation and handoffs.

Plans, transformations and interpretations below are authored fixtures. Passing these
tests does not establish model inference quality, faithful natural-language editing,
or real behavioral benefit. No model API or environment is started.
"""

from copy import deepcopy
import json
import unittest

from src.skill_evolution.v22.compact_learning import coverage_index, resolve_source
from src.skill_evolution.v22.compact_update import DIAGNOSIS_SHAPE, EDITOR_SHAPE, FUSION_SHAPE
from src.skill_evolution.v22.continual_state import finish_round, gate_round, open_round
from src.skill_evolution.v22.effective_memory import EFFECTIVE_SHAPE, effective_consumption_payload
from src.skill_evolution.v22.grouped_representation import build_grouping_input, freeze_grouping
from src.skill_evolution.v22.grouped_update import (
    PROFILE as LEGACY_PROFILE,
    accept_diagnosis, compile_update, diagnosis_payload, grouped_messages,
    learn_grouped_memory, prepare_current, prepare_grouped_learning, realize_editor,
    update_payload,
)
from src.skill_evolution.v22.unified_dsc import PROFILE
from tests.skill_evolution.v22 import test_grouped_update as fixtures


class UnifiedDscMechanismTests(unittest.TestCase):
    # Reuse synthetic record construction, without inheriting/rerunning its tests.
    setUp = fixtures.GroupedUpdateTests.setUp
    record = fixtures.GroupedUpdateTests.record
    batch = fixtures.GroupedUpdateTests.batch

    def inputs(self, context, parents, profile=PROFILE):
        current = prepare_current(context, parents, profile=profile)
        source = build_grouping_input(current, context["round_id"])
        members = [ref for ref, _ in sorted(source["bindings"].items(),
                                            key=lambda item: item[1]["parent_alias"])]
        grouping = freeze_grouping({"groups": [
            {"group_id": "G1", "decision_problem": "When evidence needs refreshing",
             "members": members[:1], "shared_basis": "Visible validity conditions",
             "important_differences": []},
            {"group_id": "G2", "decision_problem": "When operations change prerequisites",
             "members": members[1:], "shared_basis": "Dependency changes and continuing work",
             "important_differences": []},
        ]}, source, self.prompt)
        current = diagnosis_payload(context, parents, grouping, profile=profile)
        group = lambda name: f"group:{context['round_id']}:{name}"
        plan = {
            "intent": "Use valid visible prerequisites while preserving unrelated progress.",
            "requirements": [
                {"id": "u1", "text": "Inspect prerequisites when visible evidence is absent or stale; otherwise reuse valid evidence.",
                 "basis": [group("G1"), "P1:1"]},
                {"id": "u2", "text": "After a dependency-changing operation, revalidate its affected prerequisite before dependent work.",
                 "basis": [group("G2"), "P2:1"]},
                {"id": "u3", "text": "Preserve unrelated successful work.",
                 "basis": [group("G2"), "P3:1"]},
            ],
            "watch": [
                {"id": "w_joint", "about": ["u1", "u2"],
                 "question": "Are checks conditional on validity and restored after a dependency change?"},
                {"id": "w_other", "about": ["u3"], "question": "Is unrelated progress preserved?"},
            ], "open": [],
        }
        if context["parent"]["mode"] != "none":
            # An authored scope refinement makes the second-round diff real;
            # the fixture is not asking the Editor to re-emit its Parent as new.
            plan["requirements"][0]["text"] = (
                "Inspect only the affected prerequisite when its visible evidence is absent or stale; preserve other valid evidence.")
        accept_diagnosis({"decision": "revise", "reason": "Authored generic fixture.", "plan": plan}, current)
        return grouping, current, update_payload(context, current, plan)

    def edit(self, update, *, extra_watch=False):
        rows = update["plan"]["requirements"]
        text = "\n".join(row["text"] for row in rows) + "\n"
        editor = {"decision": "candidate", "reason": "Authored realization of the supplied update.",
                  "candidate_text": text, "issues": [], "watch": [],
                  "mappings": [{"requirements": [row["id"]], "side": "candidate", "excerpt": row["text"]}
                               for row in rows]}
        if extra_watch:
            editor["watch"] = [{"id": "w_editor", "about": [rows[0]["id"]],
                                "question": "Was permission strengthened into an obligation?"}]
        candidate, plan = realize_editor(editor, update)
        return candidate, plan, editor

    def round_fixture(self, context=None, *, profile=PROFILE, extra_watch=False):
        context = context or self.context
        parents = self.batch(context, context["parent"], [False, True, False])
        grouping, current, update = self.inputs(context, parents, profile)
        candidate, plan, editor = self.edit(update, extra_watch=extra_watch)
        candidates = self.batch(context, candidate, [True, True, False])
        gate = gate_round(context, candidate, parents, candidates)
        payload = prepare_grouped_learning(context, grouping, plan, candidate, parents, candidates, gate,
                                           editor=editor, profile=profile)
        return {"context": context, "parents": parents, "grouping": grouping, "current": current,
                "update": update, "candidate": candidate, "plan": plan, "editor": editor,
                "candidates": candidates, "gate": gate, "payload": payload}

    def response(self, payload, *, two_findings=False):
        findings = [{"id": "f1", "about": ["w_joint"], "refs": ["P1:1", "C1:1"],
                     "observation": "Authored conditional joint response; no isolated contribution is identified."}]
        if two_findings:
            findings.append({"id": "f2", "about": ["u2"], "refs": ["P2:1", "C2:1", "diff", "editor"],
                             "observation": "Authored realization comparison, using the same actual update."})
        opens = [{"about": [row["id"]], "reason": "Synthetic trace does not assess this preservation question."}
                 for row in payload["plan"]["watch"] if row["id"] != "w_joint"]
        return {"findings": findings, "open": opens, "memory_delta": [
            {"replace": [], "claim": "Conditional inspection and revalidation have a joint observed response.",
             "limits": ["Changed dependencies and unavailable evidence remain untested.",
                        "Bundle response does not identify individual causal contributions."],
             "findings": [row["id"] for row in findings], "retire_limits": []},
        ]}

    def next_context(self, first, memory, receipt):
        state = finish_round(self.state, first["context"], first["candidate"], first["gate"], memory, receipt)
        return open_round(state, [row["id"] for row in self.items[3:]])

    def test_keep_retains_an_executable_update_and_can_produce_candidate(self):
        parents = self.batch(self.context, self.context["parent"], [False] * 3)
        _, current, update = self.inputs(self.context, parents)
        original = deepcopy(update)
        keep = {"decision": "ready", "reason": "The authored initial conditions remain suitable.",
                "changes": [], "watch_changes": [], "open": []}
        plan = compile_update(keep, update)
        self.assertEqual(plan, original["plan"])
        candidate, _, editor = self.edit(update_payload(self.context, current, plan))
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["text"], editor["candidate_text"])
        self.assertNotEqual(candidate["skill_id"], self.context["parent"]["skill_id"])
        self.assertEqual(update, original)

    def test_authored_direction_scale_and_coupling_keep_goal_sources_and_watch(self):
        first = self.round_fixture()
        memory, receipt = learn_grouped_memory(first["payload"], self.response(first["payload"]))
        context = self.next_context(first, memory, receipt)
        parents = self.batch(context, context["parent"], [False, True, False])
        _, _, update = self.inputs(context, parents)
        cases = [
            ("direction", ["u1"], "Use a fresh visible status receipt to establish the prerequisite before dependent work; query only when that receipt is absent or stale.", ["u2", "s"]),
            ("scale_narrow", ["u1"], "Check only the affected prerequisite when its visible evidence is stale.", ["u2", "s"]),
            ("scale_expand", ["u1"], "Check the affected prerequisite when evidence is stale or absent, before dependent work.", ["u2", "s"]),
            ("coupling", ["u1", "u2"], "Reuse valid visible evidence until a dependency-changing operation; then check the affected prerequisite before dependent work.", ["s"]),
        ]
        original = deepcopy(update)
        for name, replaced, text, watched in cases:
            with self.subTest(case=name):
                fusion = {"decision": "ready", "reason": "Authored condition-response comparison, not model inference.",
                          "changes": [{"from": replaced, "to": [{"id": "s", "text": text}],
                                       "basis": [memory[0]["id"]], "disposition": "replace",
                                       "reason": "The fixture supplies this limited response relation and alternative."}],
                          "watch_changes": [{"from": ["w_joint"], "to": [
                              {"id": "w_transformed", "about": watched,
                               "question": "When the stated conditions arise, do checks and dependent work retain their order?"}]}],
                          "open": []}
                plan = compile_update(fusion, update)
                transformed = next(row for row in plan["requirements"] if row["id"] == "s")
                expected_basis = list(dict.fromkeys(
                    [ref for row in update["plan"]["requirements"] if row["id"] in replaced for ref in row["basis"]]
                    + [memory[0]["id"]]))
                self.assertEqual(transformed, {"id": "s", "text": text, "basis": expected_basis})
                self.assertEqual(plan["intent"], update["plan"]["intent"])
                self.assertIn(update["plan"]["requirements"][2], plan["requirements"])
                self.assertIn(update["plan"]["watch"][1], plan["watch"])
                self.assertEqual(plan["watch"][-1]["about"], watched)
        self.assertEqual(update, original)

    def test_profile_reuses_all_model_output_shapes(self):
        round_ = self.round_fixture()
        for stage, payload, shape in (
            ("diagnosis", round_["current"], DIAGNOSIS_SHAPE),
            ("fusion", round_["update"], FUSION_SHAPE),
            ("editor", round_["update"], EDITOR_SHAPE),
            ("learn", round_["payload"], EFFECTIVE_SHAPE),
        ):
            with self.subTest(stage=stage):
                messages = grouped_messages(stage, payload)
                self.assertEqual(len(messages), 2)
                encoded_shape = messages[0]["content"].rsplit("\nOutput shape: ", 1)[1]
                self.assertEqual(json.loads(encoded_shape), shape)
                self.assertEqual(json.loads(messages[1]["content"])["update_profile"], PROFILE)

    def test_watch_closure_persists_effective_joint_update_and_actual_realization(self):
        round_ = self.round_fixture(extra_watch=True)
        payload = round_["payload"]
        before = deepcopy(payload)
        memory, _ = learn_grouped_memory(payload, self.response(payload))
        basis = memory[0]["basis"][0]
        self.assertEqual(set(basis["finding"]["refs"]), {"P1:1", "C1:1"})
        self.assertEqual(basis["sources"]["watch:w_joint"], round_["plan"]["watch"][0])
        for row in round_["plan"]["requirements"][:2]:
            self.assertEqual(basis["sources"]["requirement:" + row["id"]], row)
            for ref in row["basis"]:
                self.assertEqual(basis["sources"][ref], resolve_source(payload, ref))
        self.assertEqual(basis["sources"]["intent"], round_["plan"]["intent"])
        self.assertNotIn("requirement:u3", basis["sources"])
        self.assertNotIn("P3:1", basis["sources"])
        actual = basis["actual_update"]["update_context"]
        self.assertEqual(actual["actual_diff"], payload["actual_diff"])
        self.assertEqual(actual["editor"]["mappings"], round_["editor"]["mappings"])
        self.assertEqual(resolve_source(payload, "editor"), actual["editor"])
        self.assertEqual(payload, before)

    def test_consumption_shares_actual_update_and_keeps_history_out_of_current_aliases(self):
        round_ = self.round_fixture()
        payload = round_["payload"]
        memory, _ = learn_grouped_memory(payload, self.response(payload, two_findings=True))
        source = {**deepcopy(payload), "memory": memory}
        before = deepcopy(source)
        view = effective_consumption_payload(source)
        self.assertEqual(set(view["historical_updates"]), {"H1"})
        self.assertEqual(view["runs"], source["runs"])
        self.assertEqual(view["sources"], source["sources"])
        bases = view["memory"][0]["basis"]
        self.assertEqual(len(bases), 2)
        self.assertTrue(all(row["actual_update_ref"] == "H1" and "actual_update" not in row for row in bases))
        for row in bases:
            self.assertTrue(all(ref.startswith("H1::") for ref in row["sources"]))
        sources = view["historical_sources"]
        self.assertEqual(sources["H1::requirement:u1"]["id"], "H1::u1")
        self.assertEqual(sources["H1::watch:w_joint"]["about"], ["H1::u1", "H1::u2"])
        self.assertEqual(sources["H1::C1:1"]["run_id"], payload["runs"]["C1"]["run_id"])
        self.assertEqual(sources["H1::diff"], {"actual_update_ref": "H1", "path": ["update_context", "actual_diff"]})
        self.assertEqual(sources["H1::editor"], {"actual_update_ref": "H1", "path": ["update_context", "editor"]})
        # Count the full shared diff only in the historical projection: current
        # input legitimately has its own actual diff and binding context.
        history = {key: view[key] for key in ("historical_updates", "historical_sources", "memory")}
        def occurrences(value, needle):
            if isinstance(value, dict):
                return sum(occurrences(child, needle) for child in value.values())
            if isinstance(value, list):
                return sum(occurrences(child, needle) for child in value)
            return int(value == needle)
        self.assertEqual(occurrences(history, payload["actual_diff"]), 1)
        self.assertEqual(source, before)

    def test_revision_keeps_old_context_and_authored_untested_remainder(self):
        first = self.round_fixture()
        memory, receipt = learn_grouped_memory(first["payload"], self.response(first["payload"]))
        old = deepcopy(memory[0])
        second = self.round_fixture(self.next_context(first, memory, receipt))
        response = self.response(second["payload"])
        delta = response["memory_delta"][0]
        delta.update(replace=[old["id"]], claim="Response now covers changed dependencies; unavailable evidence remains unknown.",
                     limits=["Unavailable evidence remains untested."],
                     retire_limits=[{"effect_id": old["id"], "index": 0,
                                     "reason": "Authored partial revision covers dependency changes; new limits retain the uncovered clause.",
                                     "findings": ["f1"]}])
        revised, _ = learn_grouped_memory(second["payload"], response)
        effect = revised[0]
        self.assertEqual(effect["basis"][0], old["basis"][0])
        self.assertEqual(effect["limits"], [old["limits"][1], "Unavailable evidence remains untested."])
        self.assertEqual(effect["retired_limits"][0]["limit"], old["limits"][0])
        self.assertEqual(effect["supersedes"], [old["id"]])
        view = effective_consumption_payload({**second["payload"], "memory": revised})
        self.assertEqual(set(view["historical_updates"]), {"H1", "H2"})
        self.assertNotEqual(view["historical_sources"]["H1::C1:1"]["run_id"],
                            view["historical_sources"]["H2::C1:1"]["run_id"])
        self.assertEqual(view["historical_updates"]["H1"]["candidate_skill_id"], first["candidate"]["skill_id"])
        self.assertEqual(view["historical_updates"]["H2"]["parent_skill_id"], first["candidate"]["skill_id"])

    def test_untriggered_questions_can_remain_open_without_negative_effect(self):
        payload = self.round_fixture()["payload"]
        response = {"findings": [], "open": [
            {"about": [row["id"]], "reason": "The synthetic trace supplies no relevant decision opportunity; response remains untested."}
            for row in payload["plan"]["watch"]], "memory_delta": []}
        memory, _ = learn_grouped_memory(payload, response)
        self.assertEqual(memory, [])
        coverage = coverage_index(response, payload)
        for row in coverage.values():
            self.assertEqual(row["status"], "addressed_with_limits")
            self.assertEqual(row["findings"], [])
            self.assertEqual(row["runs"], [])
            self.assertEqual(set(row["not_assessed_runs"]), set(payload["runs"]))

    def test_legacy_profile_keeps_existing_payload_and_inline_memory_contract(self):
        round_ = self.round_fixture(profile=LEGACY_PROFILE)
        payload = round_["payload"]
        default_current = prepare_current(round_["context"], round_["parents"])
        explicit_current = prepare_current(round_["context"], round_["parents"], profile=LEGACY_PROFILE)
        self.assertEqual(default_current, explicit_current)
        self.assertNotIn("update_profile", payload)
        self.assertNotIn("editor", payload["sources"])
        self.assertNotIn("editor", payload["update_context"])
        response = self.response(payload)
        memory, _ = learn_grouped_memory(payload, response)
        self.assertEqual(set(memory[0]["basis"][0]["sources"]), {"P1:1", "C1:1"})
        view = effective_consumption_payload({**payload, "memory": memory})
        self.assertNotIn("historical_updates", view)
        self.assertIn("actual_update", view["memory"][0]["basis"][0])
        self.assertNotIn("actual_update_ref", view["memory"][0]["basis"][0])

    def test_learning_rejects_editor_text_mapping_and_bound_context_mismatch(self):
        round_ = self.round_fixture(extra_watch=True)
        args = [round_[key] for key in ("context", "grouping", "plan", "candidate", "parents", "candidates", "gate")]
        with self.assertRaisesRegex(ValueError, "actual Editor mapping"):
            prepare_grouped_learning(*args, profile=PROFILE)
        changed = deepcopy(round_["editor"])
        changed["mappings"][0]["excerpt"] = "This text was never written."
        with self.assertRaisesRegex(ValueError, "mapping.excerpt"):
            prepare_grouped_learning(*args, editor=changed, profile=PROFILE)
        changed = deepcopy(round_["editor"])
        changed["candidate_text"] += "An extra actual obligation.\n"
        with self.assertRaisesRegex(ValueError, "Editor text differs"):
            prepare_grouped_learning(*args, editor=changed, profile=PROFILE)
        changed = deepcopy(round_["editor"])
        changed["watch"][0]["question"] = "A different unsaved question."
        with self.assertRaisesRegex(ValueError, "Editor watch"):
            prepare_grouped_learning(*args, editor=changed, profile=PROFILE)
        for field in ("actual_diff", "editor"):
            payload = deepcopy(round_["payload"])
            if field == "actual_diff":
                payload["update_context"][field] += "changed"
            else:
                payload["update_context"][field]["mappings"] = []
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "Prepared learning input changed"):
                learn_grouped_memory(payload, self.response(round_["payload"]))

    def test_all_withdrawn_has_explicit_watch_destination_and_no_edit_response(self):
        parents = self.batch(self.context, self.context["parent"], [False] * 3)
        grouping, _, update = self.inputs(self.context, parents)
        fusion = {"decision": "ready", "reason": "Authored complete withdrawal with no remaining justified update.",
                  "changes": [{"from": ["u1", "u2", "u3"], "to": [], "basis": ["P1:1"],
                               "reason": "No remaining executable update in this fixture.", "disposition": "withdraw"}],
                  "watch_changes": [{"from": ["w_joint", "w_other"], "to": [
                      {"id": "w_none", "about": ["intent"], "question": "What remains unresolved without a new edit?"}]}],
                  "open": []}
        plan = compile_update(fusion, update)
        self.assertEqual(plan["requirements"], [])
        self.assertEqual(plan["watch"][0]["about"], ["intent"])
        legacy = deepcopy(update)
        legacy.pop("update_profile")
        with self.assertRaisesRegex(ValueError, "no active requirements"):
            compile_update(fusion, legacy)
        gate = gate_round(self.context, None, parents, [])
        payload = prepare_grouped_learning(self.context, grouping, plan, None, parents, [], gate, profile=PROFILE)
        self.assertIsNone(payload["update_context"]["editor"])
        self.assertNotIn("diff", payload["sources"])
        response = {"findings": [], "open": [{"about": ["w_none"], "reason": "No Candidate was constructed or executed."}],
                    "memory_delta": []}
        memory, _ = learn_grouped_memory(payload, response)
        self.assertEqual(memory, [])
        self.assertEqual(gate["decision"], "RETAIN")


if __name__ == "__main__":
    unittest.main()
