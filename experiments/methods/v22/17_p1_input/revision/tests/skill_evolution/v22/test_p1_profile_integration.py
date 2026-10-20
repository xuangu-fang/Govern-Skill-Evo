"""P1 preserves v3 contracts; synthetic callbacks never call a model or ALFWorld."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import object_digest, write_record
from src.skill_evolution.v22 import contract_alignment, p1_input
from src.skill_evolution.v22.continual_runner import run_campaign
from src.skill_evolution.v22.continual_runtime import _system_prompts, load_bundle
from src.skill_evolution.v22.continual_verify import verify_campaign
from src.skill_evolution.v22.effective_memory import effective_consumption_payload, memory_view_schema
from src.skill_evolution.v22.grouped_representation import build_grouping_input, grouping_messages
from src.skill_evolution.v22.grouped_update import (
    accept_diagnosis, compile_update, grouped_messages, learn_grouped_memory,
)
from tests.skill_evolution.v22 import test_unified_dsc_mechanism as fixtures
from tests.skill_evolution.v22 import test_stream_runtime as stream
from tests.skill_evolution.v22.test_continual_runner import PLAN, SyntheticCampaign


class P1ProfileInputTests(unittest.TestCase):
    setUp = fixtures.UnifiedDscMechanismTests.setUp
    record = fixtures.UnifiedDscMechanismTests.record
    batch = fixtures.UnifiedDscMechanismTests.batch
    inputs = fixtures.UnifiedDscMechanismTests.inputs
    edit = fixtures.UnifiedDscMechanismTests.edit
    response = fixtures.UnifiedDscMechanismTests.response
    round_fixture = fixtures.UnifiedDscMechanismTests.round_fixture

    def test_all_update_stages_preserve_v3_rule_text_and_entire_consumption_view(self):
        fixture = self.round_fixture(profile=contract_alignment.PROFILE)
        for stage, key in [('diagnosis', 'current'), ('fusion', 'update'),
                           ('editor', 'update'), ('learn', 'payload')]:
            with self.subTest(stage=stage):
                old = fixture[key]
                before = deepcopy(old)
                new = deepcopy(old)
                new['update_profile'] = p1_input.PROFILE
                if 'binding_sha256' in new:
                    new['binding_sha256'] = object_digest({k: v for k, v in new.items() if k != 'binding_sha256'})
                old_messages = grouped_messages(stage, old)
                messages = grouped_messages(stage, new)
                expected_system = old_messages[0]['content'].replace(
                    'Profile: ' + contract_alignment.PROFILE, 'Profile: ' + p1_input.PROFILE, 1)
                self.assertEqual(messages[0]['content'], expected_system + '\n' + p1_input.INSTRUCTIONS)
                decoded = p1_input.decode(json.loads(messages[1]['content']))
                expected = new if stage == 'diagnosis' else effective_consumption_payload(new)
                self.assertEqual(decoded, expected)
                normalized = deepcopy(decoded)
                normalized['update_profile'] = contract_alignment.PROFILE
                if 'binding_sha256' in normalized:
                    normalized['binding_sha256'] = old['binding_sha256']
                self.assertEqual(normalized, json.loads(old_messages[1]['content']))
                self.assertEqual(old, before)
                self.assertEqual(grouped_messages(stage, old), old_messages)

    def test_classification_decodes_to_same_opaque_tasks_and_every_step(self):
        fixture = self.round_fixture(profile=contract_alignment.PROFILE)
        payload = build_grouping_input(fixture['current'], self.context['round_id'])['model_input']
        old = grouping_messages(payload, self.prompt, profile=contract_alignment.PROFILE)
        new = grouping_messages(payload, self.prompt, profile=p1_input.PROFILE)
        self.assertEqual(p1_input.decode(json.loads(new[1]['content'])), payload)
        self.assertEqual(new[0]['content'], old[0]['content'] + '\n' + p1_input.INSTRUCTIONS)
        self.assertEqual(grouping_messages(payload, self.prompt), old)
        prompts = _system_prompts(self.prompt, profile=p1_input.PROFILE)
        self.assertEqual(prompts['classification']['text'], new[0]['content'])

    def test_v4_still_completes_evidence_groups_and_allows_keep(self):
        fixture = self.round_fixture(profile=p1_input.PROFILE)
        current, update = fixture['current'], fixture['update']
        raw = {'decision': 'revise', 'reason': 'Synthetic current evidence.', 'plan': deepcopy(update['plan'])}
        raw['plan']['requirements'][0]['basis'] = ['P1:1', 'P2:1']
        accepted = accept_diagnosis(raw, current)
        self.assertEqual(accepted['plan']['requirements'][0]['basis'], ['P1:1', 'P2:1',
            current['runs']['P1']['decision_group'], current['runs']['P2']['decision_group']])
        self.assertEqual(raw['plan']['requirements'][0]['basis'], ['P1:1', 'P2:1'])
        keep = {'decision': 'ready', 'reason': 'No new applicable relation.',
                'changes': [], 'watch_changes': [], 'open': []}
        self.assertEqual(compile_update(keep, update), update['plan'])

    def test_memory_storage_and_source_links_do_not_contain_consumption_pool_indices(self):
        fixture = self.round_fixture(profile=p1_input.PROFILE)
        payload = fixture['payload']
        memory, receipt = learn_grouped_memory(payload, self.response(payload))
        basis = memory[0]['basis'][0]
        self.assertIn('reference_contexts', basis['actual_update'])
        self.assertEqual(basis['sources']['requirement:u1'], payload['plan']['requirements'][0])
        self.assertEqual(basis['sources']['watch:w_joint'], payload['plan']['watch'][0])
        self.assertEqual(basis['actual_update']['update_context'], payload['update_context'])
        self.assertEqual(memory_view_schema(p1_input.PROFILE), contract_alignment.VIEW_SCHEMA)
        self.assertNotIn('@text', json.dumps(memory))
        self.assertEqual(receipt['memory_after_sha256'], object_digest(memory))


class P1RuntimeInputTests(unittest.TestCase):
    setUp = stream.StreamRuntimeTests.setUp
    bundle = stream.StreamRuntimeTests.bundle

    def test_streaming_profile_keeps_task_budget_and_original_profile(self):
        original = deepcopy(self.plan)
        new = deepcopy(original)
        new['update_profile'] = p1_input.PROFILE
        bundle = self.bundle(new)
        self.assertEqual(bundle['plan']['update_profile'], p1_input.PROFILE)
        self.assertEqual(bundle['plan']['budget'], original['budget'])
        self.assertEqual(self.plan, original)

    def test_synthetic_complete_flow_binds_all_five_encoded_stages_and_verifies_raw_facts(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = json.loads(PLAN.read_text())
            for row, key in ((plan['data'], 'task_manifest'), (plan['classification'], 'prompt_file')):
                row[key] = str((PLAN.parent / row[key]).resolve())
            plan['update_profile'] = p1_input.PROFILE
            plan_path = root / 'plan.json'
            write_record(plan_path, plan)
            bundle = load_bundle(plan_path)
            callbacks = SyntheticCampaign(root, bundle)

            def generated(stage, messages, path):
                # The test oracle reads exact decoded facts. Save synthetic call
                # accounting against the actual encoded messages sent by runner.
                decoded = deepcopy(messages)
                decoded[1]['content'] = json.dumps(p1_input.decode(json.loads(messages[1]['content'])))
                raw = callbacks.generate(stage, decoded, path)
                call = json.loads(Path(path).read_text())
                call['messages_sha256'] = object_digest(messages)
                step = call['steps'][0]
                step['messages'] = messages
                attempt = step['transport_attempts'][0]
                attempt['request_sha256'] = object_digest({**attempt['request_parameters'], 'messages': messages})
                write_record(path, call)
                return raw

            output = root / 'campaign'
            result = run_campaign(bundle, output, generated, callbacks.execute, offline=True)
            self.assertEqual(result['status'], 'completed', result)
            self.assertEqual(Counter(stage for _, stage, _ in callbacks.calls), {
                'classification': 2, 'diagnosis': 2, 'fusion': 1, 'main_editor': 2, 'post_gate_learning': 2})
            read = lambda name: json.loads((output / name).read_text())
            freeze = read('runtime_freeze.json')
            self.assertEqual(freeze['runtime']['contracts']['model_input_encoding'], p1_input.VIEW_SCHEMA)
            self.assertEqual(freeze['runtime']['contracts']['effective_memory_view'], contract_alignment.VIEW_SCHEMA)
            for number in (1, 2):
                prefix = f'rounds/r{number}/'
                grouping = read(prefix + 'grouping.json')
                self.assertEqual(grouping['prompt_sha256'], freeze['system_prompts']['classification']['sha256'])
                for stage in result['rounds'][number - 1]['stages']:
                    raw = read(prefix + 'inputs/' + stage + '.json')
                    consumed = p1_input.decode(json.loads(read(prefix + 'messages/' + stage + '.json')[1]['content']))
                    expected = raw if stage in ('classification', 'diagnosis') else effective_consumption_payload(raw)
                    self.assertEqual(consumed, expected)
                learning = read(prefix + 'learning_input.json')
                self.assertEqual(learning['plan'], read(prefix + 'execution_plan.json'))
                self.assertEqual(learning['update_context']['editor']['mappings'],
                                 read(prefix + 'outputs/main_editor.json')['mappings'])
            self.assertTrue(verify_campaign(output)['campaign_complete'])
            freeze['runtime']['contracts']['model_input_encoding'] = 'unregistered'
            freeze['sha256'] = object_digest({k: v for k, v in freeze.items() if k != 'sha256'})
            write_record(output / 'runtime_freeze.json', freeze)
            with self.assertRaisesRegex(ValueError, 'Frozen input encoding'):
                verify_campaign(output)


if __name__ == '__main__':
    unittest.main()
