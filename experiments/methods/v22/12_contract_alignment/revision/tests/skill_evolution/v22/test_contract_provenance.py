"""Generic provenance handoffs; authored fixtures do not establish model semantics."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.contract_alignment import PROFILE, VIEW_SCHEMA
from src.skill_evolution.v22.continual_runner import run_campaign
from src.skill_evolution.v22.continual_runtime import load_bundle
from src.skill_evolution.v22.continual_verify import verify_campaign
from src.skill_evolution.v22.grouped_representation import validate_grouped_plan
from src.skill_evolution.v22.grouped_update import accept_diagnosis, compile_update, update_payload
from src.skill_evolution.v22.unified_dsc import PROFILE as V1
from src.skill_evolution.v22.memory_identity import PROFILE as V2
from tests.skill_evolution.v22 import test_unified_dsc_mechanism as fixtures
from tests.skill_evolution.v22 import test_dsc_refinement_flow as flows
from tests.skill_evolution.v22 import test_stream_runtime as stream
from tests.skill_evolution.v22.test_continual_runner import PLAN, SyntheticCampaign


class ContractProvenanceTests(unittest.TestCase):
    setUp = fixtures.UnifiedDscMechanismTests.setUp
    record = fixtures.UnifiedDscMechanismTests.record
    batch = fixtures.UnifiedDscMechanismTests.batch
    edit = fixtures.UnifiedDscMechanismTests.edit
    response = fixtures.UnifiedDscMechanismTests.response
    next_context = fixtures.UnifiedDscMechanismTests.next_context

    def inputs(self, context, parents, profile=PROFILE):
        return fixtures.UnifiedDscMechanismTests.inputs(self, context, parents, profile)

    def round_fixture(self, context=None, *, profile=PROFILE, extra_watch=False):
        return fixtures.UnifiedDscMechanismTests.round_fixture(self, context, profile=profile, extra_watch=extra_watch)

    def draft(self):
        parents = self.batch(self.context, self.context['parent'], [False, True, False])
        _, current, update = self.inputs(self.context, parents)
        return current, {'decision': 'revise', 'reason': 'Authored fixture.', 'plan': deepcopy(update['plan'])}

    def test_single_and_joint_sources_are_completed_without_changing_update_scope(self):
        current, raw = self.draft()
        raw['plan']['requirements'][0]['basis'] = ['P1:1', 'P2:1']
        raw['plan']['requirements'][1]['basis'] = ['P2:1']
        before = deepcopy(raw)
        accepted = accept_diagnosis(raw, current)
        first = accepted['plan']['requirements'][0]
        self.assertEqual(first['basis'], ['P1:1', 'P2:1',
            current['runs']['P1']['decision_group'], current['runs']['P2']['decision_group']])
        self.assertEqual(accepted['plan']['requirements'][1]['basis'],
                         ['P2:1', current['runs']['P2']['decision_group']])
        self.assertEqual(first['text'], before['plan']['requirements'][0]['text'])
        self.assertEqual(raw, before)
        self.assertEqual(accept_diagnosis(accepted, current), accepted)
        validate_grouped_plan(accepted['plan'], current)

    def test_unbacked_or_unknown_sources_and_missing_parent_evidence_still_fail(self):
        current, raw = self.draft()
        other_group = current['runs']['P2']['decision_group']
        for basis in ([other_group, 'P1:1'], ['P1:999'], [other_group], ['not-a-source']):
            with self.subTest(basis=basis), self.assertRaises(ValueError):
                value = deepcopy(raw)
                value['plan']['requirements'][0]['basis'] = basis
                accept_diagnosis(value, current)
        # A forged source-directory entry cannot make a nonexistent step valid.
        altered = deepcopy(current)
        altered['sources']['P1:999'] = {'kind': 'event', 'run': 'P1', 'step': 999}
        raw['plan']['requirements'][0]['basis'] = ['P1:999']
        with self.assertRaisesRegex(ValueError, 'nonexistent Parent event'):
            accept_diagnosis(raw, altered)

    def test_legacy_profiles_keep_strict_original_contract(self):
        current, raw = self.draft()
        raw['plan']['requirements'][0]['basis'] = ['P1:1']
        for profile in (V1, V2):
            with self.subTest(profile=profile), self.assertRaisesRegex(ValueError, 'matching Parent event'):
                accept_diagnosis(raw, {**current, 'update_profile': profile})
        self.assertEqual(accept_diagnosis(raw, current)['decision'], 'revise')

    def test_fusion_completes_new_cross_group_evidence_and_preserves_raw_increment(self):
        current, raw = self.draft()
        update = update_payload(self.context, current, raw['plan'])
        transform = {'decision': 'ready', 'reason': 'Current evidence supplies an additional condition.',
            'changes': [{'from': ['u1'], 'to': [{'id': 'u1', 'text': raw['plan']['requirements'][0]['text']}],
                         'basis': ['P2:1'], 'reason': 'A related observed prerequisite.', 'disposition': 'replace'}],
            'watch_changes': [{'from': ['w_joint'], 'to': [raw['plan']['watch'][0]]}], 'open': []}
        before = deepcopy(transform)
        effective = compile_update(transform, update)
        self.assertIn(current['runs']['P2']['decision_group'], effective['requirements'][-1]['basis'])
        self.assertEqual(transform, before)
        validate_grouped_plan(effective, update)
        with self.assertRaisesRegex(ValueError, 'matching Parent event'):
            compile_update(transform, {**update, 'update_profile': V2})

    # These authored flows check that the new routing preserves the existing
    # expressive routes and response linkage, not whether an LLM chooses well.
    test_keep_and_exploration = flows.DscRefinementFlowTests.test_keep_and_bounded_exploration_still_realize_candidates
    test_direction_bidirectional_scale_and_coupling = flows.DscRefinementFlowTests.test_authored_direction_bidirectional_scale_and_coupling_are_realizable
    test_watch_diff_editor_memory_closure = fixtures.UnifiedDscMechanismTests.test_watch_closure_persists_effective_joint_update_and_actual_realization
    test_unassessed_response_can_remain_unknown = flows.DscRefinementFlowTests.test_missing_opportunity_and_nonexecution_do_not_require_negative_effects
    test_partial_knowledge_revision_can_expand_supported_scope = flows.DscRefinementFlowTests.test_authored_partial_revision_expands_knowledge_without_erasing_remainder


class ContractStreamingProfileTests(unittest.TestCase):
    setUp = stream.StreamRuntimeTests.setUp
    bundle = stream.StreamRuntimeTests.bundle

    def test_v3_is_explicit_opt_in_without_changing_frozen_v2_configuration(self):
        before = deepcopy(self.plan)
        updated = deepcopy(self.plan)
        updated['update_profile'] = PROFILE
        bundle = self.bundle(updated)
        self.assertEqual(bundle['plan']['update_profile'], PROFILE)
        self.assertEqual(bundle['plan']['budget'], before['budget'])
        self.assertEqual(self.plan, before)
        self.assertEqual(self.bundle()['plan']['update_profile'], V2)

    def test_synthetic_campaign_preserves_raw_response_and_verifies_completed_provenance(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = json.loads(PLAN.read_text())
            for row, key in ((plan['data'], 'task_manifest'), (plan['classification'], 'prompt_file')):
                row[key] = str((PLAN.parent / row[key]).resolve())
            plan['update_profile'] = PROFILE
            path = root / 'plan.json'
            write_record(path, plan)
            bundle = load_bundle(path)
            callbacks = SyntheticCampaign(root, bundle)

            def events_only(value, _):
                value['plan']['requirements'][0]['basis'] = ['P1:1']
                return value

            for round_id in ('r1', 'r2'):
                callbacks.override[(round_id, 'diagnosis')] = events_only
            output = root / 'campaign'
            result = run_campaign(bundle, output, callbacks.generate, callbacks.execute, offline=True)
            self.assertEqual(result['status'], 'completed', result)
            self.assertEqual(len(callbacks.calls), 9)
            read = lambda name: json.loads((output / name).read_text())
            frozen = read('runtime_freeze.json')
            self.assertEqual(frozen['runtime']['contracts']['effective_memory_view'], VIEW_SCHEMA)
            for round_id in ('r1', 'r2'):
                prefix = 'rounds/' + round_id
                raw = read(prefix + '/raw_outputs/diagnosis.json')
                accepted = read(prefix + '/outputs/diagnosis.json')
                self.assertEqual(raw['plan']['requirements'][0]['basis'], ['P1:1'])
                self.assertEqual(len(accepted['plan']['requirements'][0]['basis']), 2)
                self.assertEqual(read(prefix + '/initial_plan.json'), accepted['plan'])
                effective = read(prefix + '/execution_plan.json')
                learning = read(prefix + '/learning_input.json')
                self.assertEqual(learning['plan'], effective)
                basis = read(prefix + '/memory_after.json')[-1]['basis'][-1]
                self.assertEqual(basis['actual_update']['update_context'], learning['update_context'])
                for requirement in effective['requirements']:
                    self.assertEqual(basis['sources']['requirement:' + requirement['id']], requirement)
            self.assertTrue(verify_campaign(output)['campaign_complete'])


if __name__ == '__main__':
    unittest.main()
