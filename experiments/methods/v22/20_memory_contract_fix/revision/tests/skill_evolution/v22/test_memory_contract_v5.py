"""Format clarification, existing validator, unchanged evidence/old messages."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from src.adapters.alfworld.skill_runtime import object_digest
from src.skill_evolution.v22 import memory_contract as fix, p1_input, unified_dsc
from src.skill_evolution.v22.effective_memory import validate_effective_learning, apply_effective_memory
from src.skill_evolution.v22.grouped_update import grouped_messages
from src.skill_evolution.v22.grouped_representation import grouping_messages
from tests.skill_evolution.v22 import test_effective_memory as effective_fixture
from tests.skill_evolution.v22 import test_unified_dsc_mechanism as unified_fixture

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'experiments/methods/v22/17_p1_input').is_dir())


class RetirementExampleTests(unittest.TestCase):
    setUp = effective_fixture.EffectiveMemoryTests.setUp
    correction = effective_fixture.EffectiveMemoryTests.correction

    def example(self):
        value = self.correction()
        value['memory_delta'] = [deepcopy(fix.RETIREMENT_EXAMPLE)]
        return value

    def test_exact_nonempty_example_passes_unchanged_validator(self):
        self.assertEqual(validate_effective_learning(self.example(), self.payload), self.example())

    def test_empty_retirement_keeps_existing_limits_and_sources(self):
        value = self.example(); value['memory_delta'][0]['retire_limits'] = []
        result = apply_effective_memory(self.memory, value, 'new', self.payload)[0]
        self.assertEqual(result['limits'][:2], self.memory[0]['limits'])
        self.assertEqual(result['basis'][0], self.memory[0]['basis'][0])
        self.assertEqual(result['retired_limits'], [])

    def test_partial_retirement_keeps_unverified_remainder(self):
        value = self.example()
        result = apply_effective_memory(self.memory, value, 'new', self.payload)[0]
        self.assertIn('The remaining condition is still untested.', result['limits'])
        self.assertIn('Untested scope must remain unknown.', result['limits'])
        self.assertNotIn('Wrong inherited factual assertion.', result['limits'])
        self.assertEqual(result['retired_limits'][0]['effect_id'], 'old:m1')

    def test_alias_keys_and_invalid_links_still_rejected(self):
        for edit in (
            lambda d: d['retire_limits'][0].update(effect=d['retire_limits'][0].pop('effect_id')),
            lambda d: d['retire_limits'][0].update(limit_index=d['retire_limits'][0].pop('index')),
            lambda d: d.update(replace=[]),
            lambda d: d['retire_limits'][0].update(index=True),
            lambda d: d['retire_limits'][0].update(findings=['missing']),
        ):
            value = self.example(); edit(value['memory_delta'][0])
            with self.assertRaises(ValueError): validate_effective_learning(value, self.payload)


class ProfileTests(unittest.TestCase):
    setUp = unified_fixture.UnifiedDscMechanismTests.setUp
    record = unified_fixture.UnifiedDscMechanismTests.record
    batch = unified_fixture.UnifiedDscMechanismTests.batch
    inputs = unified_fixture.UnifiedDscMechanismTests.inputs
    edit = unified_fixture.UnifiedDscMechanismTests.edit
    round_fixture = unified_fixture.UnifiedDscMechanismTests.round_fixture

    def test_only_learning_format_paragraph_changes(self):
        fixture = self.round_fixture(profile=p1_input.PROFILE)
        for stage,key in [('diagnosis','current'),('fusion','update'),('editor','update'),('learn','payload')]:
            old = fixture[key]; new = deepcopy(old); new['update_profile'] = fix.PROFILE
            if 'binding_sha256' in new:
                new['binding_sha256'] = object_digest({k:v for k,v in new.items() if k!='binding_sha256'})
            before, after = grouped_messages(stage,old), grouped_messages(stage,new)
            expected = before[0]['content'].replace(p1_input.PROFILE,fix.PROFILE,1)
            if stage=='learn': expected = expected.replace(fix.OLD,fix.NEW)
            self.assertEqual(after[0]['content'],expected)
            restored=p1_input.decode(json.loads(after[1]['content']))
            prior=p1_input.decode(json.loads(before[1]['content']))
            restored['update_profile']=p1_input.PROFILE
            if 'binding_sha256' in restored:restored['binding_sha256']=prior['binding_sha256']
            self.assertEqual(restored,prior)
            if stage=='learn':
                for key in ['effect_id: string','index: integer','reason: nonempty string','findings: nonempty array','retire_limits=[]']:
                    self.assertIn(key,after[0]['content'])
                self.assertIn('"retire_limits": []',after[0]['content'])

    def test_classification_and_frozen_old_messages_unchanged(self):
        base=ROOT/'artifacts/methods/v22/17_p1_input/official_flash_validation'
        protocol=json.loads((base/'protocol.json').read_text())
        prompt=(ROOT/'experiments/methods/v22/08_grouped_continual/config/grouping_prompt.md').read_text()
        for case in protocol['cases']:
            d=base/'cases'/case['id'];payload=json.loads((d/'payload.json').read_text())
            actual=(grouping_messages(payload,prompt,profile=case['profile']) if case['stage']=='classification'
                    else grouped_messages(case['stage'],payload))
            self.assertEqual(actual,json.loads((d/'messages.json').read_text()))
            if case['stage']=='classification':self.assertEqual(grouping_messages(payload,prompt,profile=fix.PROFILE),actual)

    def test_original_algorithm_and_codec_and_validators_identical(self):
        import importlib
        old=ROOT/'experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22'
        expected = {
            'unified_dsc': ROOT/'src/skill_evolution/v22/unified_dsc.py',
            'p1_input': old/'p1_input.py',
            'contract_alignment': ROOT/'experiments/methods/v22/12_contract_alignment/revision/src/skill_evolution/v22/contract_alignment.py',
            'compact_learning': ROOT/'src/skill_evolution/v22/compact_learning.py',
        }
        for name, path in expected.items():
            module = importlib.import_module('src.skill_evolution.v22.' + name)
            self.assertEqual(Path(module.__file__).resolve(), path)
        memory = importlib.import_module('src.skill_evolution.v22.effective_memory')
        import ast
        def functions(path):
            return {n.name:ast.dump(n) for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        self.assertEqual(functions(old/'effective_memory.py'),functions(Path(memory.__file__)))
        self.assertEqual(fix.LEARNING_RULES.replace(fix.NEW,fix.OLD),unified_dsc.LEARNING_RULES)


if __name__=='__main__':unittest.main()
