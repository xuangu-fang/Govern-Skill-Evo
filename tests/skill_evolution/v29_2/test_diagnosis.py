"""Offline Diagnosis acceptance with synthetic, registered DocVQA archives.

Run from the repository with PYTHONPATH=.:external/SkillAdam and the DocVQA
Python environment. Network and subprocess calls are forbidden in every test.
"""
from copy import deepcopy
import json
import socket
import subprocess
from unittest.mock import patch

from src.skill_evolution.v29 import modules as old_modules
from src.skill_evolution.v29.benchmarks.docvqa import protocol, prompting
from src.skill_evolution.v29.storage import read, save
from src.skill_evolution.v29_1.campaign import CampaignAdapter, PROMPT_ROOT
from src.skill_evolution.v29_2 import diagnosis as d, execution_input_view as view
from tests.skill_evolution.v29.test_actor import HIDDEN
from tests.skill_evolution.v29.test_method import MethodBase, main_example


def proposal():
    return {
        'decision': 'revise',
        'reason': 'P1:1 returns a subtotal for a total question; preserve the matching date response.',
        'plan': {
            'goal': 'Improve requested amount selection while preserving complete date answers.',
            'updates': [{
                'id': 'u1',
                'text': '- When asked for a total, select the value whose role matches the requested total; '
                        'do not substitute a subtotal. Preserve the complete date when a date is requested.\n',
                'basis': ['G1', 'P1:0', 'P1:1', 'P1:outcome', 'P2:1', 'P2:outcome'],
            }],
        },
    }


class DiagnosisTests(MethodBase):
    def test_slash_lists_preserve_diagnosis_scope_and_handoff(self):
        value = proposal()
        value['reason'] = 'Compare P1/P2 and P1:1/P2:outcome.'
        value['plan']['goal'] = 'Preserve P1/P2 behavior.'
        value['plan']['updates'][0]['text'] += ' Compare P1:1/P2:1.'
        self.assertEqual(d.diagnosis_call(self.grouped).complete(value)['diagnosis'], value)
        self.assertEqual([r['ref'] for r in d.referenced_runs(value, self.payload)], ['P1', 'P2'])
        for token in ('P1/P99', 'P1/Q1', 'R03/P1/P2', 'R03/P1:1', 'R03/diff'):
            bad = deepcopy(value); bad['reason'] = 'Compare ' + token
            with self.subTest(token=token), self.assertRaises(ValueError):
                d.diagnosis_call(self.grouped).complete(bad)

    def test_grouping_slash_list_survives_diagnosis_input_validation(self):
        from src.skill_evolution.v29_2 import grouping
        grouped = deepcopy(self.grouped)
        grouped['grouping']['groups'][0]['shared_basis'] = 'Compare P1:1/P2:1.'
        grouping.validate_grouping(grouped['grouping'], grouped['facts'])
        d.diagnosis_call(grouped).complete(proposal())
        for token in ('P1:1/P99:1', 'R03/P1:1', 'P1:1/Q1:1'):
            bad = deepcopy(grouped['grouping'])
            bad['groups'][0]['shared_basis'] += ' ' + token
            with self.subTest(token=token), self.assertRaises(ValueError):
                grouping.validate_grouping(bad, grouped['facts'])

    def setUp(self):
        super().setUp()
        self.blocked = []

        def deny(*args, **kwargs):
            self.blocked.append('network_or_process')
            raise AssertionError('Offline Diagnosis test attempted network/process access')

        self.enterContext(patch.object(socket.socket, 'connect', deny))
        self.enterContext(patch.object(socket.socket, 'connect_ex', deny))
        self.enterContext(patch.object(socket, 'create_connection', deny))
        self.enterContext(patch.object(subprocess, 'Popen', deny))
        self.addCleanup(lambda: self.assertEqual(self.blocked, []))
        # Use the actual v29.1 binding and its unchanged synthetic execution path.
        self.method = CampaignAdapter(self.adapter)
        self.enterContext(self.method.using())
        self.grouped = old_modules.grouping_call(self.parent(), 'R01').complete(main_example('grouping'))
        self.payload = d.diagnosis_input(self.grouped)

    def test_new_contract_and_complete_parent_inputs(self):
        call = d.diagnosis_call(self.grouped)
        self.assertEqual(call.name, 'diagnosis')
        self.assertEqual(call.prompt_version, d.PROMPT_VERSION)
        self.assertEqual(call.contract_version, d.CONTRACT_VERSION)
        self.assertEqual(view.restore_model_input(json.loads(call.messages[1]['content']), module='diagnosis'), self.payload)
        self.assertEqual(set(self.payload), {'parent', 'runs', 'grouping'})
        self.assertEqual(self.payload['parent'], self.skill)
        self.assertEqual([r['outcome']['score']['hard'] for r in self.payload['runs']], [0, 1])
        result = call.complete_text(json.dumps(proposal()))
        self.assertEqual(result['diagnosis'], proposal())
        self.assertEqual(set(result['diagnosis']['plan']), {'goal', 'updates'})
        self.assertEqual(len(self.transport.seen), 2)  # Only the two synthetic Parent calls.

    def test_projection_does_not_expose_hidden_fields_or_unrelated_saved_data(self):
        saved = deepcopy(self.grouped)
        saved['memory'] = {'private': 'DO_NOT_PROJECT_MEMORY'}
        saved['candidate'] = 'DO_NOT_PROJECT_CANDIDATE'
        messages = d.diagnosis_call(saved).messages
        body = messages[1]['content']
        for forbidden in (HIDDEN, 'reasoning_content', 'image_url', 'data:image',
                          'DO_NOT_PROJECT_MEMORY', 'DO_NOT_PROJECT_CANDIDATE'):
            self.assertNotIn(forbidden, body)
        self.assertEqual(view.restore_model_input(json.loads(body), module='diagnosis'), self.payload)

    def test_v29_1_prompt_reasoning_sections_preserved(self):
        original = (PROMPT_ROOT / 'diagnosis.md').read_text()
        prompt = d.render_prompt(protocol.actor_config())
        for start, end in [
            ('## Agreed Actor protocol and runtime', '## Examine current evidence'),
            ('## Examine current evidence', '## Evidence'),
        ]:
            self.assertEqual(prompt.split(start)[1].split(end)[0],
                             original.split(start)[1].split(end)[0].replace(
                                 'Input contains exactly parent, runs and grouping.',
                                 'Input contains exactly parent, runs, grouping and shared_initial.'))
        self.assertNotIn('Gate accepts strictly more hard successes', prompt)
        self.assertNotIn('"checks"', prompt)
        self.assertNotIn('Each Check has', prompt)
        self.assertIn('hard success/failure transitions', prompt)
        self.assertIn('not only in reason', prompt)
        self.assertIn('including successes', prompt)
        example = json.loads(prompt.split('```json\n')[1].split('\n```')[0])
        d.validate_diagnosis(example, self.payload)

    def test_prompt_version_and_runtime_are_checked(self):
        for version in ('v29_docvqa_diagnosis_v1', 'v29_1_docvqa_diagnosis_v1'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                d.render_prompt(protocol.actor_config(), prompt_version=version)
        changed = protocol.actor_config()
        changed['temperature'] = 0
        with self.assertRaises(ValueError):
            d.render_prompt(changed)

    def test_v29_1_prompt_and_output_contract_are_not_switched(self):
        old = old_modules.diagnosis_call(self.grouped)
        self.assertEqual(old.messages[0]['content'], (PROMPT_ROOT / 'diagnosis.md').read_text())
        old.complete(main_example('diagnosis'))
        with self.assertRaises(ValueError):
            old.complete(proposal())
        new = d.diagnosis_call(self.grouped)
        new.complete(proposal())
        with self.assertRaises(ValueError):
            new.complete(main_example('diagnosis'))
        self.assertEqual(prompting.render('diagnosis', protocol.actor_config()), old.messages[0]['content'])

    def test_no_change_is_explicit_and_has_no_plan_handoff(self):
        result = {'decision': 'no_change', 'reason': 'No justified behavioral increment.', 'plan': None}
        self.assertEqual(d.diagnosis_call(self.grouped).complete(result)['diagnosis'], result)
        self.assertEqual(d.referenced_runs(result, self.payload), [])
        for plan in ({}, proposal()['plan']):
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                d.validate_diagnosis({**result, 'plan': plan}, self.payload)

    def test_top_level_fields_and_decisions_are_exact(self):
        for key in ('decision', 'reason', 'plan'):
            bad = proposal()
            del bad[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                d.validate_diagnosis(bad, self.payload)
        for key in ('checks', 'focus', 'confidence', 'gate_decision'):
            with self.subTest(extra=key), self.assertRaises(ValueError):
                d.validate_diagnosis({**proposal(), key: []}, self.payload)
        for decision in ('KEEP', 'need_evidence', '', None, []):
            bad = proposal()
            bad['decision'] = decision
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                d.validate_diagnosis(bad, self.payload)

    def test_plan_schema_rejects_checks_missing_and_empty_updates(self):
        plans = [None, {}, {'goal': 'Goal', 'updates': []},
                 {'goal': ' ', 'updates': proposal()['plan']['updates']},
                 {**proposal()['plan'], 'checks': []}]
        for plan in plans:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                d.validate_diagnosis({**proposal(), 'plan': plan}, self.payload)

    def test_update_fields_ids_text_and_basis_are_validated(self):
        valid = proposal()['plan']['updates'][0]
        variants = [{k: v for k, v in valid.items() if k != missing} for missing in valid]
        variants += [{**valid, 'patch': ''}, {**valid, 'text': ' '}, {**valid, 'id': ''}]
        variants += [{**valid, 'id': uid} for uid in ('P1', 'P1:outcome', 'G1')]
        variants += [{**valid, 'basis': basis} for basis in
                     ([], ['P1:1', 'P1:1'], ['G1'], ['G2', 'P1:1'], ['P99:1'], ['Q1:1'],
                      ['R00/P1:outcome'], ['synthetic:test'], ['Memory:M1'], 'P1:1')]
        for update in variants:
            bad = proposal()
            bad['plan']['updates'] = [update]
            with self.subTest(update=update), self.assertRaises(ValueError):
                d.validate_diagnosis(bad, self.payload)
        bad = proposal()
        bad['plan']['updates'] *= 2
        with self.assertRaises(ValueError):
            d.validate_diagnosis(bad, self.payload)

    def test_unavailable_prose_references_are_rejected_everywhere(self):
        for ref in ('Q1:1', 'R00/P1:1', 'R00/diff', 'P99:outcome', 'P1:2', 'G99', 'Memory:M1'):
            for field in ('reason', 'goal', 'text'):
                bad = proposal()
                obj = bad if field == 'reason' else bad['plan'] if field == 'goal' else bad['plan']['updates'][0]
                obj[field] = f'Unsupported source {ref}.'
                with self.subTest(ref=ref, field=field), self.assertRaises(ValueError):
                    d.validate_diagnosis(bad, self.payload)

    def test_ordinary_namespace_labels_keep_existing_diagnosis_rules(self):
        value = proposal()
        value['reason'] = 'Update: the current evidence supports a scoped proposal.'
        value['plan']['goal'] = 'Evidence: select the requested amount while preserving dates.'
        value['plan']['updates'][0]['text'] = 'Update: u1 should preserve the requested field role.'
        self.assertEqual(d.diagnosis_call(self.grouped).complete(value)['diagnosis'], value)
        no_change = {'decision': 'no_change', 'reason': 'Update: no justified increment.', 'plan': None}
        self.assertEqual(d.diagnosis_call(self.grouped).complete(no_change)['diagnosis'], no_change)
        # Diagnosis still permits its unprefixed current execution references.
        value['reason'] = 'Evidence: P1:1 supports the proposal.'
        self.assertEqual(d.diagnosis_call(self.grouped).complete(value)['diagnosis'], value)

    def test_prose_label_does_not_authorize_forbidden_diagnosis_sources(self):
        for field in ('reason', 'goal', 'text'):
            for ref in ('Memory:M1', 'Q1:1', 'P99:1', 'G99', 'R00/P1:1'):
                value = proposal()
                target = value if field == 'reason' else value['plan'] if field == 'goal' else value['plan']['updates'][0]
                target[field] = 'Update: the explanation relies on ' + ref
                with self.subTest(field=field, ref=ref), self.assertRaises(ValueError):
                    d._validate_output(value, self.payload)

    def test_multiple_updates_are_allowed_and_preserved_in_order(self):
        value = proposal()
        # A structural test, not a recommendation to propose this many changes.
        value['plan']['updates'] = [{**deepcopy(value['plan']['updates'][0]), 'id': f'u{i}'}
                                   for i in range(1, 13)]
        actual = d.diagnosis_call(self.grouped).complete(value)['diagnosis']
        self.assertEqual(actual, value)

    def test_basis_success_and_counterexample_handoff_contains_whole_runs(self):
        runs = d.referenced_runs(proposal(), self.payload)
        self.assertEqual(runs, self.payload['runs'])
        self.assertEqual(runs[1]['attempts'][0]['assistant']['content'], '<answer>12 May 2021</answer>')
        runs[0]['attempts'][0]['assistant']['content'] = 'changed copy'
        self.assertNotEqual(runs, self.payload['runs'])

    def test_group_reference_does_not_expand_other_members(self):
        payload = deepcopy(self.payload)
        payload['grouping'] = {'groups': [{
            'group_id': 'G1', 'members': ['P1', 'P2'], 'decision_problem': 'Answer selection.',
            'shared_basis': 'P1:1 is an amount; P2:1 is a date.', 'important_differences': [],
        }]}
        result = proposal()
        result['plan']['updates'][0]['basis'] = ['G1', 'P1:1']
        self.assertEqual([r['ref'] for r in d.referenced_runs(result, payload)], ['P1'])

    def test_plan_prose_references_select_runs_but_reason_does_not(self):
        result = proposal()
        result['plan']['updates'][0]['basis'] = ['P1:1']
        result['reason'] = 'P2:1 is also available.'
        self.assertEqual([r['ref'] for r in d.referenced_runs(result, self.payload)], ['P1'])
        result['plan']['goal'] += ' Preserve the behavior in P2:1.'
        self.assertEqual([r['ref'] for r in d.referenced_runs(result, self.payload)], ['P1', 'P2'])

    def test_input_rejects_extra_fields_missing_and_changed_parent(self):
        variants = [{**self.payload, 'memory': {}}, {**self.payload, 'candidate': ''},
                    {**self.payload, 'parent': 'Forged Parent'}, {**self.payload, 'runs': []}]
        variants += [{k: v for k, v in self.payload.items() if k != missing} for missing in self.payload]
        for payload in variants:
            with self.subTest(keys=list(payload)), self.assertRaises(ValueError):
                d.validate_input(payload)

    def test_input_requires_complete_untampered_parent_batch(self):
        variants = []
        for change in ('drop', 'duplicate', 'reorder', 'role', 'content', 'score', 'hidden'):
            payload = deepcopy(self.payload)
            if change == 'drop': payload['runs'].pop()
            elif change == 'duplicate': payload['runs'].append(deepcopy(payload['runs'][0]))
            elif change == 'reorder': payload['runs'].reverse()
            elif change == 'role': payload['runs'][0]['ref'] = 'Q1'
            elif change == 'content': payload['runs'][0]['attempts'][0]['assistant']['content'] = 'forged'
            elif change == 'score': payload['runs'][0]['outcome']['score']['hard'] = 1
            else: payload['runs'][0]['attempts'][0]['assistant']['reasoning_content'] = HIDDEN
            variants.append((change, payload))
        for change, payload in variants:
            with self.subTest(change=change), self.assertRaises(ValueError):
                d.validate_input(payload)

    def test_grouping_coverage_and_sources_are_checked(self):
        for change in ('missing', 'duplicate', 'unknown', 'unsupported'):
            payload = deepcopy(self.payload)
            groups = payload['grouping']['groups']
            if change == 'missing': groups.pop()
            elif change == 'duplicate': groups[1]['members'] = ['P1']
            elif change == 'unknown': groups[0]['members'] = ['P99']
            else: groups[0]['shared_basis'] = 'P99:1 explains the problem.'
            with self.subTest(change=change), self.assertRaises(ValueError):
                d.validate_input(payload)

    def test_candidate_archive_is_not_diagnosis_input(self):
        children, _ = self.batch(self.skill, ['<answer>1,320</answer>', '<answer>12 May 2021</answer>'], 'candidate')
        payload = deepcopy(self.payload)
        payload['runs'] = self.method.build_facts(children, role='candidate')['facts']['runs']
        with self.assertRaises(ValueError):
            d.validate_input(payload)

    def test_test_archive_cannot_be_registered_for_diagnosis(self):
        directory = self.root / 'held-out'
        self.adapter.actor_batch(['synthetic:test'], self.skill_file, directory,
                                 {'split': 'test', 'role': 'evaluation'}, final=True)
        with self.assertRaises(ValueError):
            self.method.register_archive(directory)

    def test_call_snapshots_inputs_and_detaches_results(self):
        saved, parsed = deepcopy(self.grouped), proposal()
        call = d.diagnosis_call(saved)
        saved['facts']['parent'] = 'mutated caller'
        call.input['facts']['parent'] = 'mutated public snapshot'
        result = call.complete(parsed)
        parsed['plan']['updates'][0]['text'] = 'mutated caller output'
        self.assertEqual(result['facts']['parent'], self.skill)
        self.assertEqual(result['diagnosis'], proposal())
        result['diagnosis']['plan']['updates'][0]['text'] = 'mutated result'
        self.assertEqual(call.complete(proposal())['diagnosis'], proposal())

    def test_changed_archive_is_rechecked_at_completion(self):
        call = d.diagnosis_call(self.grouped)
        path = self.parent_dir / 'actor/0001/trajectory.json'
        record = read(path)
        record['execution']['content'] = 'forged after call preparation'
        save(path, record)
        with self.assertRaises(ValueError):
            call.complete(proposal())

    def test_invalid_json_is_not_converted_to_no_change(self):
        call = d.diagnosis_call(self.grouped)
        for raw in ('{} trailing', '[]', '{"decision":"no_change","decision":"revise"}',
                    '{"decision":"no_change","reason":NaN,"plan":null}', ''):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                call.complete_text(raw)


if __name__ == '__main__':
    import unittest
    unittest.main()
