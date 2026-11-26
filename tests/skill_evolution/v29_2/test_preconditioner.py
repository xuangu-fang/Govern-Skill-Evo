"""Offline acceptance using synthetic archives and hand-authored decisions.

These tests check contracts, compilation and prompt requirements, not live-model
semantic performance. No model transport, network or subprocess is permitted.
"""
from copy import deepcopy
import json
import socket
import subprocess
from unittest.mock import patch

from src.skill_evolution.v27.contracts import memory as old_memory
from src.skill_evolution.v29 import modules as old_modules
from src.skill_evolution.v29.benchmarks.docvqa import protocol, prompting
from src.skill_evolution.v29.storage import read, save
from src.skill_evolution.v29_1.campaign import CampaignAdapter, PROMPT_ROOT
from src.skill_evolution.v29_2 import diagnosis as d, preconditioner as p, execution_input_view as view
from tests.skill_evolution.v29.test_actor import HIDDEN
from tests.skill_evolution.v29.test_method import MethodBase, main_example
from tests.skill_evolution.v29_2.test_diagnosis import proposal


def memory_view():
    """Synthetic view only, deliberately no claimed historical archive backing."""
    return {'rounds': [{
        'round_id': 'R00',
        'source_updates': [
            {'id': 'u1', 'text': 'Use the explicitly labeled requested amount.', 'gate_decision': 'Retain'},
            {'id': 'u2', 'text': 'Prefer a label even when the question asks for a different role.',
             'gate_decision': 'Reject'},
            {'id': 'u3', 'text': 'Preserve requested date granularity.', 'gate_decision': 'Defer'},
            {'id': 'u4', 'text': 'Keep the existing answer element.', 'gate_decision': None},
        ],
        'entries': [
            {'id': 'M1', 'knowledge': {'task_id': 'old:gain', 'update_id': 'u1',
                                     'text': 'Selecting the requested labeled amount changed hard from 0 to 1.'}},
            {'id': 'M2', 'knowledge': {'task_id': 'old:loss', 'update_id': 'u2',
                                     'text': 'Preferring a conflicting label changed hard from 1 to 0.'}},
            {'id': 'M3', 'knowledge': {'task_id': 'old:unlinked', 'update_id': None,
                                     'text': 'Hard changed from 1 to 0 without a clear Update association.'}},
        ],
    }]}


def decisions(*actions):
    return {'adjustments': [
        {'target': f'u{i}', 'action': action,
         'text': '- Match the requested field role before using a label; preserve valid alternatives.\n'
                 if action == 'REPLACE' else None,
         'reason': 'The supplied evidence supports this scoped decision; execution effects remain unverified.'}
        for i, action in enumerate(actions or ('KEEP',), 1)
    ]}


class PreconditionerTests(MethodBase):
    def test_slash_lists_preserve_preconditioner_scope(self):
        value = decisions('REPLACE')
        value['adjustments'][0]['reason'] = 'Compare P1/P2 and P1:1/P2:1.'
        value['adjustments'][0]['text'] = '- Preserve the supported behavior in P1/P2.\n'
        p._compile(value, self.payload)
        for field in ('reason', 'text'):
            for token in ('P1/P99', 'P1/Q1', 'R03/P1/P2', 'R03/diff'):
                bad = deepcopy(value); bad['adjustments'][0][field] += ' ' + token
                with self.subTest(field=field, token=token), self.assertRaises(ValueError):
                    p._compile(bad, self.payload)

    def setUp(self):
        super().setUp()
        self.blocked = []

        def deny(*args, **kwargs):
            self.blocked.append('network_or_process')
            raise AssertionError('Offline Preconditioner test attempted network/process access')

        self.enterContext(patch.object(socket.socket, 'connect', deny))
        self.enterContext(patch.object(socket.socket, 'connect_ex', deny))
        self.enterContext(patch.object(socket, 'create_connection', deny))
        self.enterContext(patch.object(subprocess, 'Popen', deny))
        self.addCleanup(lambda: self.assertEqual(self.blocked, []))
        self.method = CampaignAdapter(self.adapter)
        self.enterContext(self.method.using())
        self.grouped = old_modules.grouping_call(self.parent(), 'R01').complete(main_example('grouping'))
        self.saved = d.diagnosis_call(self.grouped).complete(proposal())
        self.memory = memory_view()
        self.payload = p.preconditioner_input(self.saved, self.memory)

    def multi_saved(self):
        result = proposal()
        result['plan']['updates'] = [
            {**deepcopy(result['plan']['updates'][0]), 'id': f'u{i}',
             'text': f'- Original behavioral requirement {i}.\n'} for i in range(1, 4)]
        return d.diagnosis_call(self.grouped).complete(result)

    def test_versioned_call_preserves_complete_four_field_input(self):
        call = p.preconditioner_call(self.saved, self.memory)
        self.assertEqual((call.name, call.prompt_version, call.contract_version),
                         ('preconditioner', p.PROMPT_VERSION, p.CONTRACT_VERSION))
        self.assertEqual(view.restore_model_input(json.loads(call.messages[1]['content']), module='preconditioner'), self.payload)
        self.assertEqual(set(self.payload), {'parent', 'plan', 'runs', 'memory'})
        self.assertEqual(set(self.payload['plan']), {'goal', 'updates'})
        result = call.complete_text(json.dumps(decisions()))
        self.assertEqual(result['effective_plan'], proposal()['plan'])
        self.assertEqual(result['preconditioner'], decisions())
        self.assertEqual(len(self.transport.seen), 2)  # Synthetic Parent fixture only.

    def test_no_change_and_legacy_diagnosis_are_not_accepted(self):
        no_change = d.diagnosis_call(self.grouped).complete({
            'decision': 'no_change', 'reason': 'No justified proposal.', 'plan': None})
        legacy = old_modules.diagnosis_call(self.grouped).complete(main_example('diagnosis'))
        for saved in (no_change, legacy):
            with self.subTest(saved=saved['diagnosis']['decision']), self.assertRaises(ValueError):
                p.preconditioner_call(saved, self.memory)

    def test_parent_without_initial_skill_is_supported(self):
        directory = self.root / 'no-initial-skill'
        records = self.adapter.actor_batch(self.tasks, None, directory,
                                           {'split': 'train', 'role': 'parent'})
        self.method.register_archive(directory)
        grouped = old_modules.grouping_call(records, 'R01').complete(main_example('grouping'))
        saved = d.diagnosis_call(grouped).complete(proposal())
        call = p.preconditioner_call(saved, {'rounds': []})
        self.assertIsNone(json.loads(call.messages[1]['content'])['parent'])
        self.assertEqual(call.complete(decisions())['effective_plan'], proposal()['plan'])

    def test_projection_includes_success_and_full_runs_without_hidden_data(self):
        saved = deepcopy(self.saved)
        saved['candidate'] = 'DO_NOT_PROJECT_CANDIDATE'
        saved['diagnosis']['reason'] += ' DO_NOT_PROJECT_DIAGNOSIS_REASON'
        body = p.preconditioner_call(saved, self.memory).messages[1]['content']
        for forbidden in (HIDDEN, 'reasoning_content', 'image_url', 'data:image',
                          'DO_NOT_PROJECT_CANDIDATE', 'DO_NOT_PROJECT_DIAGNOSIS_REASON', '"grouping"'):
            self.assertNotIn(forbidden, body)
        runs = view.restore_model_input(json.loads(body), module='preconditioner')['runs']
        self.assertEqual(runs, self.saved['facts']['runs'])
        self.assertEqual([r['outcome']['score']['hard'] for r in runs], [0, 1])
        self.assertEqual(runs[1]['attempts'][0]['assistant']['content'], '<answer>12 May 2021</answer>')

    def test_plan_references_select_whole_runs_without_group_expansion(self):
        grouped = deepcopy(self.grouped)
        grouped['grouping'] = {'groups': [{
            'group_id': 'G1', 'members': ['P1', 'P2'], 'decision_problem': 'Answer selection.',
            'shared_basis': 'P1:1 is an amount; P2:1 is a date.', 'important_differences': [],
        }]}
        value = proposal()
        value['plan']['updates'][0]['basis'] = ['G1', 'P1:1']
        value['reason'] = 'P2:1 occurs only in Diagnosis reason.'
        saved = d.diagnosis_call(grouped).complete(value)
        self.assertEqual([r['ref'] for r in p.preconditioner_input(saved, self.memory)['runs']], ['P1'])
        value['plan']['goal'] += ' Preserve P2:1.'
        saved = d.diagnosis_call(grouped).complete(value)
        self.assertEqual(p.preconditioner_input(saved, self.memory)['runs'], grouped['facts']['runs'])

    def test_input_must_match_verified_diagnosis_projection(self):
        variants = [{**self.payload, 'grouping': {}}, {**self.payload, 'parent': 'forged'}]
        variants += [{k: v for k, v in self.payload.items() if k != key} for key in self.payload]
        for change in ('drop', 'reorder', 'duplicate', 'content', 'score', 'boolean_score', 'goal', 'basis'):
            value = deepcopy(self.payload)
            if change == 'drop': value['runs'].pop()
            elif change == 'reorder': value['runs'].reverse()
            elif change == 'duplicate': value['runs'].append(deepcopy(value['runs'][0]))
            elif change == 'content': value['runs'][0]['attempts'][0]['assistant']['content'] = 'forged'
            elif change == 'score': value['runs'][0]['outcome']['score']['hard'] = 1
            elif change == 'boolean_score': value['runs'][0]['outcome']['score']['hard'] = False
            elif change == 'goal': value['plan']['goal'] = 'changed'
            else: value['plan']['updates'][0]['basis'] = ['P1:1']
            variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                p.validate_input(value, saved=self.saved)

    def test_memory_empty_rounds_and_reused_local_ids_are_preserved(self):
        history = memory_view()
        next_round = deepcopy(history['rounds'][0])
        next_round['round_id'] = 'R-before'
        next_round['entries'] = []
        history['rounds'].append(next_round)
        for memory in ({'rounds': []}, history):
            call = p.preconditioner_call(self.saved, memory)
            self.assertEqual(json.loads(call.messages[1]['content'])['memory'], memory)
            self.assertEqual(call.complete(decisions())['memory'], memory)

    def test_memory_schema_types_and_all_fields_are_strict(self):
        for path in ((), ('rounds', 0), ('rounds', 0, 'source_updates', 0),
                     ('rounds', 0, 'entries', 0), ('rounds', 0, 'entries', 0, 'knowledge')):
            original = memory_view()
            obj = original
            for key in path: obj = obj[key]
            for change in ['extra', *obj]:
                bad = memory_view()
                target = bad
                for key in path: target = target[key]
                if change == 'extra': target['revises'] = []
                else: del target[change]
                with self.subTest(path=path, change=change), self.assertRaises(ValueError):
                    p.validate_memory_view(bad)
        for value in (None, [], {'rounds': None}, {'rounds': {}}, {'entries': []}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                p.validate_memory_view(value)

    def test_memory_identifiers_events_and_links_are_validated(self):
        for change in ('round', 'update', 'memory', 'task', 'dangling', 'no_modification',
                       'gate', 'knowledge_array', 'blank_text', 'bad_id', 'bad_task', 'bad_update'):
            bad = memory_view()
            r = bad['rounds'][0]
            if change == 'round': bad['rounds'].append(deepcopy(r))
            elif change == 'update': r['source_updates'].append(deepcopy(r['source_updates'][0]))
            elif change == 'memory': r['entries'][1]['id'] = 'M1'
            elif change == 'task': r['entries'][1]['knowledge']['task_id'] = 'old:gain'
            elif change == 'dangling': r['entries'][0]['knowledge']['update_id'] = 'u99'
            elif change == 'no_modification': r['entries'][0]['knowledge']['update_id'] = 'u4'
            elif change == 'gate': r['source_updates'][0]['gate_decision'] = 'KEEP'
            elif change == 'knowledge_array': r['entries'][0]['knowledge'] = [r['entries'][0]['knowledge']]
            elif change == 'blank_text': r['source_updates'][0]['text'] = ' '
            elif change == 'bad_id': r['entries'][0]['id'] = []
            elif change == 'bad_task': r['entries'][0]['knowledge']['task_id'] = None
            else: r['entries'][0]['knowledge']['update_id'] = []
            with self.subTest(change=change), self.assertRaises(ValueError):
                p.validate_memory_view(bad)
        bad = memory_view()
        other = deepcopy(bad['rounds'][0])
        other['round_id'] = 'R-other'
        bad['rounds'].append(other)
        with self.assertRaisesRegex(ValueError, 'Duplicate Memory ID'):
            p.validate_memory_view(bad)

    def test_historical_links_are_round_local_and_current_round_is_excluded(self):
        bad = memory_view()
        other = deepcopy(bad['rounds'][0])
        other['round_id'] = 'R-other'
        other['source_updates'] = []
        for i, e in enumerate(other['entries']): e['id'] = f'M-new-{i}'
        bad['rounds'].append(other)
        with self.assertRaises(ValueError):
            p.preconditioner_call(self.saved, bad)
        bad = memory_view()
        bad['rounds'][0]['round_id'] = self.saved['round_id']
        with self.assertRaisesRegex(ValueError, 'Current round'):
            p.preconditioner_call(self.saved, bad)

    def test_mixed_decisions_compile_in_original_order_and_preserve_provenance(self):
        saved = self.multi_saved()
        output = decisions('KEEP', 'REPLACE', 'WITHDRAW')
        output['adjustments'].reverse()
        before = deepcopy(saved)
        result = p.preconditioner_call(saved, self.memory).complete(output)
        original = saved['diagnosis']['plan']
        expected = deepcopy(original)
        expected['updates'].pop()
        expected['updates'][1]['text'] = output['adjustments'][1]['text']
        self.assertEqual(result['effective_plan'], expected)
        self.assertEqual(result['diagnosis']['plan'], original)
        self.assertEqual(saved, before)
        self.assertEqual(result['effective_plan']['updates'][1]['basis'], original['updates'][1]['basis'])
        self.assertEqual(set(result['update_diffs']), {'u2'})
        self.assertIn('-' + original['updates'][1]['text'], result['update_diffs']['u2'])
        self.assertEqual(result['preconditioner'], output)

    def test_all_keep_and_all_withdraw_need_no_checks(self):
        saved = self.multi_saved()
        call = p.preconditioner_call(saved, {'rounds': []})
        self.assertEqual(call.complete(decisions('KEEP', 'KEEP', 'KEEP'))['effective_plan'],
                         saved['diagnosis']['plan'])
        result = call.complete(decisions('WITHDRAW', 'WITHDRAW', 'WITHDRAW'))
        self.assertIsNone(result['effective_plan'])
        self.assertEqual(result['update_diffs'], {})
        self.assertEqual(result['memory'], {'rounds': []})

    def test_contract_rejects_legacy_fields_and_partial_output(self):
        valid = decisions()
        variants = [None, [], {}, {'adjustments': None}, {'adjustments': []}]
        variants += [{**valid, key: []} for key in ('checks', 'focus', 'decision', 'effective_plan')]
        for key in ('focus', 'change', 'to', 'patch', 'basis', 'update_ids'):
            value = decisions()
            value['adjustments'][0][key] = None
            variants.append(value)
        for key in valid['adjustments'][0]:
            value = decisions()
            del value['adjustments'][0][key]
            variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                p.validate_preconditioner(value, self.payload, saved=self.saved)

    def test_targets_require_exact_complete_coverage(self):
        call = p.preconditioner_call(self.multi_saved(), self.memory)
        for change in ('missing', 'duplicate', 'unknown', 'wrong_type', 'empty'):
            value = decisions('KEEP', 'KEEP', 'KEEP')
            if change == 'missing': value['adjustments'].pop()
            elif change == 'duplicate': value['adjustments'][1]['target'] = 'u1'
            elif change == 'unknown': value['adjustments'][1]['target'] = 'u99'
            elif change == 'wrong_type': value['adjustments'][1]['target'] = []
            else: value['adjustments'][1]['target'] = ' '
            with self.subTest(change=change), self.assertRaises(ValueError):
                call.complete(value)

    def test_action_text_pairs_and_reason_types_are_strict(self):
        cases = []
        for action in ('keep', 'Retain', 'DEFER', '', None, [], True):
            cases.append({'action': action})
        for action in ('KEEP', 'WITHDRAW'):
            for value in ('', 'replacement', [], False):
                cases.append({'action': action, 'text': value})
        for value in (None, '', ' \n', [], False, proposal()['plan']['updates'][0]['text']):
            cases.append({'action': 'REPLACE', 'text': value})
        for reason in ('', ' ', [], None): cases.append({'reason': reason})
        call = p.preconditioner_call(self.saved, self.memory)
        for changes in cases:
            value = decisions()
            value['adjustments'][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                call.complete(value)

    def test_replacement_preserves_literal_whitespace_and_final_newline(self):
        call = p.preconditioner_call(self.saved, self.memory)
        for new_text in ('  Conditional requirement.\n\n', '- First requirement.\n- Preserve exception.'):
            output = decisions('REPLACE')
            output['adjustments'][0]['text'] = new_text
            result = call.complete(output)
            self.assertEqual(result['effective_plan']['updates'][0]['text'], new_text)

    def test_reference_permissions_cover_only_supplied_current_and_memory_ids(self):
        call = p.preconditioner_call(self.saved, self.memory)
        output = decisions('REPLACE')
        output['adjustments'][0]['reason'] = (
            'Current `Evidence:P1:1` and `Evidence:P2:outcome`, with inherited `Group:G1`, '
            'support adjusting `Update:u1`; historical R00 u2 and `Memory:M2` qualify the scope.')
        call.complete(output)
        for ref in ('Memory:M99', 'Evidence:Q1:1', 'Evidence:P1:2', 'Evidence:R00/P1:1',
                    'Evidence:R00/diff', 'Group:G99', 'Update:u99', 'Check:c1'):
            for field in ('reason', 'text'):
                bad = deepcopy(output)
                bad['adjustments'][0][field] = f'Unavailable `{ref}`.'
                with self.subTest(ref=ref, field=field), self.assertRaises(ValueError):
                    call.complete(bad)
        for ref in ('Q1:1', 'R00/P1:1', 'R00/diff', 'P99:1', 'G99',
                    'Memory:M1', '`Memory:M1, Memory:M2`', '``Memory:M1``'):
            bad = decisions()
            bad['adjustments'][0]['reason'] = f'Unsupported or malformed {ref}.'
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                call.complete(bad)

    def test_prose_labels_pass_in_all_reasons_and_replacement_text(self):
        call = p.preconditioner_call(self.saved, self.memory)
        for action in ('KEEP', 'REPLACE', 'WITHDRAW'):
            value = decisions(action)
            value['adjustments'][0]['reason'] = (
                'Either implemented Update: u1 concerns amounts. Memory: the supplied history '
                'qualifies the scope. See `Memory:M1`, `Group:G1`, `Evidence:P1:1` and `Update:u1`.')
            if action == 'REPLACE':
                value['adjustments'][0]['text'] = (
                    'Update: select the requested amount role; preserve the complete date.\n')
            with self.subTest(action=action):
                result = call.complete(value)
                self.assertEqual(result['preconditioner'], value)
                if action == 'WITHDRAW':
                    self.assertIsNone(result['effective_plan'])
                elif action == 'REPLACE':
                    self.assertEqual(result['effective_plan']['updates'][0]['text'],
                                     value['adjustments'][0]['text'])

    def test_both_prose_fields_preserve_syntax_and_scope_errors(self):
        bad_refs = ('Memory:M1', '`Memory:M1', '``Memory:M1``', '`Memory: M1`',
                    '`Memory:M99`', '`Evidence:P99:1`', '`Evidence:R00/P1:1`',
                    '`Evidence:Q1:1`', '`Group:G99`', '`Update:u99`', '`Check:c1`',
                    'Q99:1', 'G99', '`Update:u1`Evidence:Q1:1')
        for field in ('reason', 'text'):
            for ref in bad_refs:
                value = decisions('REPLACE')
                value['adjustments'][0][field] = 'Update: ordinary prose. ' + ref
                with self.subTest(field=field, ref=ref), self.assertRaises(ValueError):
                    p._compile(value, self.payload)

    def test_shared_parser_keeps_module_specific_memory_permissions(self):
        from src.skill_evolution.v29_2 import replay
        self.assertIs(p.parse_references, replay.parse_references)
        value = decisions()
        value['adjustments'][0]['reason'] = 'History supports scope: `Memory:M1`.'
        p._compile(value, self.payload)
        without_memory = deepcopy(self.payload)
        without_memory['memory'] = {'rounds': []}
        with self.assertRaises(ValueError):
            p._compile(value, without_memory)
        with self.assertRaises(ValueError):
            replay.parse_references(value['adjustments'][0]['reason'],
                                    {'Memory': set()}, location='replay task')

    def test_citation_prompt_and_contract_versions_are_explicit(self):
        self.assertEqual(p.PROMPT_VERSION, 'v29_2_docvqa_preconditioner_v4')
        self.assertEqual(p.CONTRACT_VERSION, 'v29_2_preconditioner_actions_v3')
        prompt = p.render_prompt(protocol.actor_config())
        for detail in ('single pair of backticks', 'Ordinary prose need not', 'historical raw executions and Checks are unavailable'):
            self.assertIn(detail, prompt)
        with self.assertRaises(ValueError):
            p.render_prompt(protocol.actor_config(), prompt_version='v29_2_docvqa_preconditioner_v2')

    def test_unselected_runs_and_uninherited_groups_are_not_new_evidence(self):
        value = proposal()
        value['plan']['updates'][0]['basis'] = ['P1:1']
        saved = d.diagnosis_call(self.grouped).complete(value)
        call = p.preconditioner_call(saved, self.memory)
        for ref in ('Evidence:P2:1', 'Group:G1'):
            bad = decisions()
            bad['adjustments'][0]['reason'] = f'Claim about `{ref}`.'
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                call.complete(bad)

    def test_output_failure_is_atomic_and_inputs_and_results_are_detached(self):
        saved, memory = self.multi_saved(), memory_view()
        before = deepcopy(saved)
        call = p.preconditioner_call(saved, memory)
        saved['diagnosis']['plan']['goal'] = 'caller changed'
        memory['rounds'].clear()
        call.input['facts']['parent'] = 'public snapshot changed'
        call.input['memory']['rounds'].clear()
        invalid = decisions('REPLACE', 'REPLACE', 'KEEP')
        invalid['adjustments'][2]['text'] = 'invalid'
        with self.assertRaises(ValueError):
            call.complete(invalid)
        valid = decisions('KEEP', 'KEEP', 'KEEP')
        result = call.complete(valid)
        self.assertEqual(result['effective_plan'], before['diagnosis']['plan'])
        self.assertEqual(result['memory'], memory_view())
        valid['adjustments'][0]['reason'] = 'caller output changed'
        self.assertNotEqual(result['preconditioner'], valid)
        result['effective_plan']['updates'][0]['basis'].clear()
        result['memory']['rounds'].clear()
        again = call.complete(decisions('KEEP', 'KEEP', 'KEEP'))
        self.assertEqual(again['effective_plan'], before['diagnosis']['plan'])
        self.assertEqual(again['memory'], memory_view())

    def test_archive_mutation_is_rechecked_at_completion(self):
        call = p.preconditioner_call(self.saved, self.memory)
        path = self.parent_dir / 'actor/0001/trajectory.json'
        record = read(path)
        record['execution']['content'] = 'tampered after preparation'
        save(path, record)
        with self.assertRaises(ValueError):
            call.complete(decisions())

    def test_invalid_json_is_not_a_semantic_keep_or_withdrawal(self):
        call = p.preconditioner_call(self.saved, self.memory)
        for raw in ('', '[]', '{} trailing', '{"adjustments":[],"adjustments":[]}',
                    '{"adjustments":NaN}', '{"adjustments":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                call.complete_text(raw)

    def test_prompt_preserves_v29_1_analysis_and_runtime(self):
        old = (PROMPT_ROOT / 'preconditioner.md').read_text()
        prompt = p.render_prompt(protocol.actor_config())
        for start, end in (
            ('## Agreed Actor protocol and runtime', '## Knowledge Only historical view'),
            ('## Relate historical edits and observable responses', '## Decide Direction Scope and Coordination'),
        ):
            new_end = '## Historical Memory by round' if end.startswith('## Knowledge') else end
            self.assertEqual(old.split(start)[1].split(end)[0], prompt.split(start)[1].split(new_end)[0])
        for obsolete in ('Gate accepts strictly more hard successes', '## Exact Update patches',
                         'checks=null', 'focus=[]', 'change=KEEP', 'to=[]', 'all active entries'):
            self.assertNotIn(obsolete, prompt)
        illustration = json.loads(prompt.split('```json\n')[1].split('\n```')[0])
        p.validate_preconditioner(illustration, self.payload, saved=self.saved)

    def test_prompt_semantic_boundaries_and_hand_authored_examples(self):
        prompt = p.render_prompt(protocol.actor_config())
        # Prompt requirements plus authored fixtures, not assertions about model quality.
        cases = [
            ('Empty or irrelevant Memory neither requires KEEP nor prevents it', 'KEEP'),
            ('preserve both the local gain and the local regression', 'REPLACE'),
            ('Defer does not by itself establish harm or ineffectiveness', 'KEEP'),
            ('If only part needs correction, choose REPLACE', 'REPLACE'),
            ('If withdrawing one removes an essential prerequisite', 'WITHDRAW'),
            ('A null update_id supplies no specific Update attribution', 'KEEP'),
        ]
        for requirement, action in cases:
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, prompt)
                result = p.preconditioner_call(self.saved, self.memory).complete(decisions(action))
                self.assertEqual(result['effective_plan'] is None, action == 'WITHDRAW')

    def test_authored_counterexample_replacement_contains_preservation_conditions(self):
        value = proposal()
        value['plan']['updates'][0]['text'] = '- Always prefer the explicitly labeled amount.\n'
        saved = d.diagnosis_call(self.grouped).complete(value)
        output = {'adjustments': [{
            'target': 'u1', 'action': 'REPLACE',
            'text': '- For an amount question, use an explicitly labeled value when its role matches '
                    'the requested role. Do not prefer a conflicting label over the requested role; '
                    'preserve the complete requested date when answering a date question.\n',
            'reason': 'Historical R00 u1 and `Memory:M1` support the matched-label case; '
                      'R00 u2 and `Memory:M2` motivate the conflicting-role exception. '
                      'The successful current `Evidence:P2:1` supplies a date preservation boundary. '
                      'The joint historical comparison does not independently prove either strategy.',
        }]}
        result = p.preconditioner_call(saved, self.memory).complete(output)
        self.assertEqual(result['effective_plan']['updates'][0]['text'], output['adjustments'][0]['text'])
        self.assertEqual(result['effective_plan']['updates'][0]['basis'], value['plan']['updates'][0]['basis'])
        self.assertEqual(result['memory'], self.memory)

    def test_authored_dependency_withdrawal_revises_the_dependent_update(self):
        value = proposal()
        source = value['plan']['updates'][0]
        value['plan']['updates'] = [
            {**deepcopy(source), 'text': '- Resolve a numeric date using a fixed month-first convention.\n'},
            {**deepcopy(source), 'id': 'u2',
             'text': '- After resolving the numeric date, expand it into a written month date.\n'},
        ]
        saved = d.diagnosis_call(self.grouped).complete(value)
        output = {'adjustments': [
            {'target': 'u1', 'action': 'WITHDRAW', 'text': None,
             'reason': 'The supplied evidence does not justify the fixed date convention.'},
            {'target': 'u2', 'action': 'REPLACE',
             'text': '- Preserve the complete date as written when the question requests that date; '
                     'do not expand an ambiguous numeric date using an assumed convention.\n',
             'reason': 'Removing `Update:u1` removes the prerequisite for expansion; '
                       'the replacement preserves the requested date without that prerequisite.'},
        ]}
        effective = p.preconditioner_call(saved, self.memory).complete(output)['effective_plan']
        self.assertEqual(effective['updates'], [{**deepcopy(value['plan']['updates'][1]),
                                               'text': output['adjustments'][1]['text']}])

    def test_prompt_version_and_runtime_are_checked(self):
        for version in ('v29_docvqa_preconditioner_v1', 'v29_1_docvqa_preconditioner_v1'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                p.render_prompt(protocol.actor_config(), prompt_version=version)
        changed = protocol.actor_config()
        changed['temperature'] = 0
        with self.assertRaises(ValueError):
            p.render_prompt(changed)

    def test_v29_1_prompt_and_contract_remain_independent(self):
        saved = old_modules.diagnosis_call(self.grouped).complete(main_example('diagnosis'))
        old = old_modules.preconditioner_call(saved, old_memory.empty_memory())
        self.assertEqual(old.messages[0]['content'], (PROMPT_ROOT / 'preconditioner.md').read_text())
        old.complete(main_example('preconditioner'))
        with self.assertRaises(ValueError):
            old.complete(decisions())
        with self.assertRaises(ValueError):
            p.preconditioner_call(self.saved, self.memory).complete(main_example('preconditioner'))
        self.assertEqual(prompting.render('preconditioner', protocol.actor_config()), old.messages[0]['content'])


if __name__ == '__main__':
    import unittest
    unittest.main()
