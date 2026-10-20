"""Historical alias boundaries, using synthetic evidence and no external calls."""

from copy import deepcopy
import unittest

from src.skill_evolution.v22.compact_learning_view import _rewrite, scoped_learning_payload
from src.skill_evolution.v22.contract_alignment import PROFILE, VIEW_SCHEMA
from tests.skill_evolution.v22.test_memory_identity import learn, payload, response, consume


class HistoryPunctuationTests(unittest.TestCase):
    def test_v3_final_projection_preserves_generation_identity_after_reordering(self):
        memory = learn('alpha', [], response('C1: first response.'), profile=PROFILE)
        memory = learn('beta', memory, response('H1::C1: earlier; C1: current response.'), profile=PROFILE)
        before = deepcopy(memory)
        view = consume(list(reversed(memory)), PROFILE)
        self.assertEqual(view['consumption_view'], VIEW_SCHEMA)
        self.assertEqual(view['historical_contexts'], {'H1': 'beta', 'H2': 'alpha'})
        self.assertEqual(view['memory'][0]['claim'], 'H2::C1: earlier; H1::C1: current response.')
        self.assertEqual(view['memory'][1]['claim'], 'H2::C1: first response.')
        self.assertEqual(memory, before)

    def test_known_run_and_event_aliases_before_prose_colons(self):
        text = "C5: response; C5:4: detail; C5:4 remains an event; u1: condition."
        aliases = {"C5:4", "u1"}
        self.assertEqual(
            _rewrite(text, "H2", aliases, qualify_punctuation=True),
            "H2::C5: response; H2::C5:4: detail; H2::C5:4 remains an event; H2::u1: condition.",
        )
        # Old profiles keep their exact projection, including the known omission.
        self.assertEqual(
            _rewrite(text, "H2", aliases),
            "C5: response; C5:4: detail; H2::C5:4 remains an event; u1: condition.",
        )

    def test_qualified_unknown_and_namespace_aliases_are_not_guessed(self):
        text = "H1::C5: H1::C5:4: history_unknown::C5: C99: u99: C5::other C5:missing"
        self.assertEqual(_rewrite(text, "H2", {"C5:4"}, qualify_punctuation=True), text)
        self.assertEqual(_rewrite("C5:", "H2", {"C5:4"}, qualify_punctuation=True), "H2::C5:")

    def test_scoped_projection_qualifies_explanations_without_mutating_evidence(self):
        value = response("C1: the visible prerequisite was refreshed.", ["C1: untested transfer remains."])
        value["findings"][0]["observation"] = "C1: observed a conditional response."
        memory = learn("historical", [], value)
        # Literal observations are evidence, not model-authored source references.
        memory[0]["basis"][0]["sources"]["C1:1"]["observation"] = "C1: literal observation text."
        source = payload("current", memory)
        original = deepcopy(source)
        legacy = scoped_learning_payload(source)
        aligned = scoped_learning_payload(source, qualify_punctuation=True)
        self.assertEqual(legacy["memory"][0]["claim"], value["memory_delta"][0]["claim"])
        self.assertEqual(aligned["memory"][0]["claim"], "H1::C1: the visible prerequisite was refreshed.")
        self.assertEqual(aligned["memory"][0]["limits"], ["H1::C1: untested transfer remains."])
        self.assertEqual(aligned["memory"][0]["basis"][0]["finding"]["observation"],
                         "H1::C1: observed a conditional response.")
        self.assertEqual(aligned["historical_sources"]["H1::C1:1"]["observation"],
                         "C1: literal observation text.")
        self.assertEqual(aligned["runs"], legacy["runs"])
        self.assertEqual(aligned["pairs"], legacy["pairs"])
        self.assertEqual(source, original)


if __name__ == "__main__":
    unittest.main()
