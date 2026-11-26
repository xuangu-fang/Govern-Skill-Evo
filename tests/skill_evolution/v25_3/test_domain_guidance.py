"""Offline checks for domain placement and preserved method contracts."""
import unittest

from src.skill_evolution.v25_3 import PACKAGE, ROOT
from src.skill_evolution.v25_3.campaign import configuration
from src.skill_evolution.v25_3.stages import messages_for


PROMPTS = PACKAGE / 'prompts'
BEFORE = ROOT / 'docs/methods/v25_3/revisions/spreadsheet_domain_v1/before'


def shared_domain(name):
    value = (PROMPTS / (name + '.md')).read_text()
    return value.split('## SpreadsheetBench domain guidance\n', 1)[1].split('\n## ', 1)[0]


class DomainGuidanceTests(unittest.TestCase):
    def test_shared_domain_is_identical_and_complete(self):
        domain = shared_domain('diagnosis')
        self.assertEqual(domain, shared_domain('preconditioner'))
        for concept in ('rule_missing', 'rule_wrong', 'rule_ignored', 'data_exploration',
                        'code_error', 'effective_exploration', 'applied_rule', 'iterative_recovery',
                        'governing inputs', 'ws.append()', 'current runs', 'fixed coordinates'):
            self.assertIn(concept, domain)

    def test_preconditioner_action_contract_is_preserved(self):
        original = (BEFORE / 'preconditioner.md').read_text()
        current = (PROMPTS / 'preconditioner.md').read_text()
        self.assertEqual(current.splitlines()[-1], original.splitlines()[-1])

    def test_diagnosis_and_replay_output_contracts_are_preserved(self):
        for name in ('diagnosis', 'replay'):
            original = (BEFORE / (name + '.md')).read_text().splitlines()
            current = (PROMPTS / (name + '.md')).read_text()
            self.assertEqual(current.splitlines()[-1], original[-1])
        self.assertEqual((PROMPTS / 'editor.md').read_bytes(), (BEFORE / 'editor.md').read_bytes())

    def test_execution_facts_have_only_the_formula_requirement_addition(self):
        old = (BEFORE / 'execution_context.md').read_text()
        new = (PROMPTS / 'execution_context.md').read_text()
        addition = ('\nWhen a task requires a formula, preserve that formula requirement in every proposed'
                    '\nsolution and fallback, including under cached-value scoring.')
        self.assertEqual(new.replace(addition, ''), old)
        diagnosis = (PROMPTS / 'diagnosis.md').read_text()
        replay = (PROMPTS / 'replay.md').read_text()
        self.assertNotIn('Workbooks may extend beyond the preview.', diagnosis)
        self.assertNotIn('Scoring reads cached values;', replay)
        self.assertNotIn('Truncated coordinates cannot identify every error.', replay)

    def test_rendered_messages_route_guidance_by_role(self):
        profile = configuration()['actor_profile']
        payload = {'parent': 'Existing guidance', 'runs': []}
        for name in ('diagnosis', 'preconditioner', 'editor', 'replay'):
            messages = messages_for(name, payload, profile)
            system = messages[0]['content']
            self.assertEqual(len(messages), 2)
            self.assertEqual(system.count('## SpreadsheetBench domain guidance'),
                             int(name in ('diagnosis', 'preconditioner')))
            self.assertEqual(system.count('## SpreadsheetBench event interpretation'), int(name == 'replay'))
            self.assertEqual(system.count('## SpreadsheetBench Execution Context'), int(name != 'editor'))
            self.assertNotIn('{{', system)
            if name != 'editor':
                self.assertIn('When a task requires a formula, preserve that formula requirement', system)


if __name__ == '__main__':
    unittest.main()
