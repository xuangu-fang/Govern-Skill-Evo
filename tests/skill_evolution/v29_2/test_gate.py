"""Offline selective Gate acceptance with authored, registered execution archives.

These tests validate counting/contracts/composition, not causal attribution or
live-model editing quality. Network and subprocess access are forbidden.
"""
from copy import deepcopy
from contextlib import ExitStack
import unittest
from unittest.mock import patch

from src.skill_evolution.v27.contracts.editor import NO_NEWLINE
from src.skill_evolution.v29 import modules as old_modules
from src.skill_evolution.v29.storage import read, save
from src.skill_evolution.v29_1.campaign import CampaignAdapter
from src.skill_evolution.v29_2 import diagnosis as d, preconditioner as p, editor as e
from src.skill_evolution.v29_2 import replay as r, gate as g
from tests.skill_evolution.v29.test_method import MethodBase
from tests.skill_evolution.v29.test_actor import response
from tests.skill_evolution.v29_2.test_diagnosis import proposal
from tests.skill_evolution.v29_2.test_preconditioner import decisions, memory_view
from tests.skill_evolution.v29_2.test_editor import diff, output, replace_line, offline


class GateTests(MethodBase):
    def setUp(self):
        super().setUp()
        offline(self)
        self.method = CampaignAdapter(self.adapter)
        self.enterContext(self.method.using())
        for name in ('gain2', 'gain3', 'loss2', 'stable_fail', 'stable_success'):
            tid = 'synthetic:' + name
            self.dataset.rows[tid] = (f'What is the {name} value?', ['YES'], 'train')
            self.tasks.append(tid)
        self.parent_contents = ['<answer>1,200</answer>', '<answer>12 May 2021</answer>',
                                '<answer>NO</answer>', '<answer>NO</answer>', '<answer>YES</answer>',
                                '<answer>X</answer>', '<answer>YES</answer>']
        self.candidate_contents = ['<answer>1,320</answer>', '<answer>12 May 2022</answer>',
                                   '<answer>YES</answer>', '<answer>YES</answer>', '<answer>NO</answer>',
                                   '<answer>YE</answer>', '<answer>yes</answer>']
        self.parents, self.parent_dir = self.batch(self.skill, self.parent_contents, 'parent')
        self.grouped = self.group(self.parents)
        context = ''.join(' ' + line for line in self.skill.splitlines(keepends=True))
        self.patches = [diff(context + f'+- Scoped requirement {index}.\n') for index in range(1, 5)] + ['']
        self.edited = self.make_editor(self.patches)
        self.children, self.child_dir = self.batch(self.edited['candidate_text'], self.candidate_contents, 'candidate')
        self.bundle = r.build_replay_from_editor(self.edited, self.parents, self.children)
        self.links = ['u1', 'u2', 'u3', None, 'u3']
        self.replayed = self.finish(self.bundle, self.links)

    def group(self, parents):
        return old_modules.grouping_call(parents, 'R01').complete({'groups': [{
            'group_id': 'G1', 'members': [f'P{i}' for i in range(1, len(parents) + 1)],
            'decision_problem': 'Preserve requested answer roles and scope.',
            'shared_basis': ' '.join(f'P{i}:1 returned an authored answer.' for i in range(1, len(parents) + 1)),
            'important_differences': [],
        }]})

    def make_editor(self, patches, *, actions=None, reverse=False):
        plan = proposal()
        plan['plan']['updates'] = [{**deepcopy(plan['plan']['updates'][0]), 'id': f'u{i}'}
                                    for i in range(1, len(actions or patches) + 1)]
        diagnosed = d.diagnosis_call(self.grouped).complete(plan)
        prepared = p.preconditioner_call(diagnosed, memory_view()).complete(
            decisions(*(actions or ['KEEP'] * len(patches))))
        parsed = output(*patches)
        if reverse: parsed['edits'].reverse()
        return e.editor_call(prepared).complete(parsed)

    def finish(self, bundle, links):
        pairs = [pair for pair in bundle['payload']['pairs']
                 if pair['parent_result']['hard'] != pair['candidate_result']['hard']]
        self.assertEqual(len(links), len(pairs))
        if not pairs: return r.skip_replay(bundle)
        items = [{'task_id': pair['task_id'], 'update_id': uid,
                  'text': 'The authored comparison records a changed answer and a scoped behavioral association.'}
                 for pair, uid in zip(pairs, links)]
        return r.replay_call(bundle).complete({'entries': [{'knowledge': items}]})

    def replay_for(self, *, edited=None, contents=None, links=None):
        edited = self.edited if edited is None else edited
        contents = self.candidate_contents if contents is None else contents
        children, _ = self.batch(edited['candidate_text'], contents, 'candidate')
        bundle = r.build_replay_from_editor(edited, self.parents, children)
        return self.finish(bundle, self.links if links is None else links)

    def assert_decision(self, result, uid, gains, losses, decision):
        self.assertEqual(next(item for item in result['decisions'] if item['update_id'] == uid),
                         {'update_id': uid, 'G': gains, 'L': losses, 'gate_decision': decision})

    def test_complete_result_all_decision_states_and_unexecuted_subset(self):
        result = g.evaluate_gate(self.replayed)
        self.assertEqual(set(result), {'decisions', 'selection', 'selected_execution_source'})
        for row in (('u1', 1, 0, 'Retain'), ('u2', 0, 1, 'Reject'), ('u3', 1, 1, 'Defer'),
                    ('u4', 0, 0, 'Defer'), ('u5', 0, 0, None)):
            self.assert_decision(result, *row)
        self.assertEqual(result['selection'], e.select_skill(self.edited, ['u1']))
        self.assertIsNone(result['selected_execution_source'])
        self.assertEqual(sum(item['G'] + item['L'] for item in result['decisions']), 4)
        self.assertEqual(g.validate_gate(result, replayed=self.replayed), result)
        self.assertEqual(g.CONTRACT_VERSION, 'v29_2_gate_selective_hard_v1')

    def test_positive_net_gain_with_regression_is_defer(self):
        replayed = self.finish(self.bundle, ['u1', 'u1', 'u1', 'u1', None])
        result = g.evaluate_gate(replayed)
        self.assert_decision(result, 'u1', 3, 1, 'Defer')
        self.assertEqual(result['selection']['selected_update_ids'], [])
        self.assertEqual(result['selection']['selected_text'], self.skill)
        self.assertEqual(result['selected_execution_source'], 'parent')

    def test_multiple_gains_and_multiple_losses_count_each_task_once(self):
        replayed = self.finish(self.bundle, ['u1', 'u2', 'u1', 'u1', 'u2'])
        result = g.evaluate_gate(replayed)
        self.assert_decision(result, 'u1', 3, 0, 'Retain')
        self.assert_decision(result, 'u2', 0, 2, 'Reject')
        self.assertEqual(sum(item['G'] + item['L'] for item in result['decisions']), 5)

    def test_prose_does_not_override_recorded_hard_direction(self):
        replayed = deepcopy(self.replayed)
        raw = replayed['replay']['entries'][0]['knowledge']
        raw[0]['text'] = 'This task regressed from success to failure.'
        raw[1]['text'] = 'This task improved from failure to success.'
        replayed['knowledge'] = deepcopy(raw)
        self.assertEqual(g.evaluate_gate(replayed), g.evaluate_gate(self.replayed))

    def test_all_unlinked_events_are_preserved_but_cast_no_votes(self):
        replayed = self.finish(self.bundle, [None] * 5)
        before = deepcopy(replayed)
        result = g.evaluate_gate(replayed)
        self.assertEqual(len(replayed['knowledge']), 5)
        self.assertEqual(replayed, before)
        for index in range(1, 5): self.assert_decision(result, f'u{index}', 0, 0, 'Defer')
        self.assertEqual(result['selection'], e.select_skill(self.edited, []))
        self.assertEqual(result['selected_execution_source'], 'parent')

    def test_reject_and_defer_omit_new_patches_without_removing_parent_rules(self):
        replayed = self.finish(self.bundle, [None, 'u1', None, None, 'u2'])
        result = g.evaluate_gate(replayed)
        self.assert_decision(result, 'u1', 0, 1, 'Reject')
        self.assert_decision(result, 'u2', 0, 1, 'Reject')
        self.assert_decision(result, 'u3', 0, 0, 'Defer')
        self.assertEqual(result['selection'], {
            'selected_update_ids': [], 'selected_text': self.skill, 'actual_diff': ''})
        self.assertEqual(result['selected_execution_source'], 'parent')

    def test_historical_memory_does_not_vote_even_with_same_update_ids(self):
        saved = deepcopy(self.edited)
        memory = saved['memory']['rounds'][0]
        for index in range(50):
            memory['entries'].append({'id': f'EXTRA{index}', 'knowledge': {
                'task_id': f'old:{index}', 'update_id': 'u2', 'text': 'A historical hard improvement.'}})
        rebuilt = r.build_replay_from_editor(saved, self.parents, self.children)
        result = g.evaluate_gate(self.finish(rebuilt, self.links))
        self.assertEqual(result, g.evaluate_gate(self.replayed))

    def test_total_candidate_regression_does_not_veto_linked_gain(self):
        contents = list(self.candidate_contents)
        contents[2] = contents[3] = '<answer>NO</answer>'
        replayed = self.replay_for(contents=contents, links=['u1', None, None])
        pairs = replayed['payload']['pairs']
        self.assertLess(sum(x['candidate_result']['hard'] for x in pairs),
                        sum(x['parent_result']['hard'] for x in pairs))
        self.assert_decision(g.evaluate_gate(replayed), 'u1', 1, 0, 'Retain')

    def test_unchanged_hard_soft_score_changes_do_not_vote(self):
        contents = list(self.parent_contents)
        contents[5], contents[6] = '<answer>YE</answer>', '<answer>yes</answer>'
        replayed = self.replay_for(contents=contents, links=[])
        self.assertNotEqual(replayed['payload']['pairs'][5]['parent_result']['anls'],
                            replayed['payload']['pairs'][5]['candidate_result']['anls'])
        result = g.evaluate_gate(replayed)
        for index in range(1, 5): self.assert_decision(result, f'u{index}', 0, 0, 'Defer')
        self.assert_decision(result, 'u5', 0, 0, None)
        self.assertFalse(replayed['replay_called'])
        self.assertEqual(result['selection']['actual_diff'], '')
        self.assertEqual(result['selected_execution_source'], 'parent')

    def test_all_actual_patches_retained_matches_executed_candidate(self):
        edited = self.make_editor(self.patches[:2] + [''])
        replayed = self.replay_for(edited=edited, links=['u1', None, 'u2', None, None])
        result = g.evaluate_gate(replayed)
        self.assertEqual(result['selection']['selected_update_ids'], ['u1', 'u2'])
        self.assertEqual(result['selection']['selected_text'], edited['candidate_text'])
        self.assertEqual(result['selected_execution_source'], 'candidate')
        self.assertEqual(set(result['selection']), {'selected_update_ids', 'selected_text', 'actual_diff'})

    def test_empty_patch_is_neither_retain_nor_defer_and_cannot_be_attributed(self):
        result = g.evaluate_gate(self.replayed)
        self.assert_decision(result, 'u5', 0, 0, None)
        for uid in ('u5', 'u99', 'R00/u1', [], True):
            bad = deepcopy(self.replayed)
            bad['replay']['entries'][0]['knowledge'][0]['update_id'] = uid
            bad['knowledge'] = deepcopy(bad['replay']['entries'][0]['knowledge'])
            with self.subTest(uid=uid), self.assertRaises(ValueError): g.evaluate_gate(bad)

    def test_withdrawn_update_cannot_be_attributed(self):
        edited = self.make_editor(self.patches[:2], actions=['KEEP', 'KEEP', 'WITHDRAW'])
        replayed = self.replay_for(edited=edited, links=['u1', None, None, None, None])
        replayed['replay']['entries'][0]['knowledge'][0]['update_id'] = 'u3'
        replayed['knowledge'][0]['update_id'] = 'u3'
        with self.assertRaises(ValueError): g.evaluate_gate(replayed)

    def test_missing_duplicate_unknown_unchanged_task_events_rejected(self):
        for kind in ('missing', 'duplicate', 'unknown', 'unchanged', 'old'):
            bad = deepcopy(self.replayed)
            items = bad['replay']['entries'][0]['knowledge']
            if kind == 'missing': items.pop()
            elif kind == 'duplicate': items.append(deepcopy(items[0]))
            else: items[0]['task_id'] = {'unknown': 'unknown', 'unchanged': self.tasks[5], 'old': 'old:gain'}[kind]
            bad['knowledge'] = deepcopy(items)
            with self.subTest(kind=kind), self.assertRaises(ValueError): g.evaluate_gate(bad)

    def test_single_entry_and_three_field_contract_are_enforced(self):
        for kind in ('zero', 'multiple', 'empty', 'extra_knowledge', 'extra_replay'):
            bad = deepcopy(self.replayed)
            items = bad['replay']['entries'][0]['knowledge']
            if kind == 'zero': bad['replay']['entries'] = []
            elif kind == 'multiple': bad['replay']['entries'] = [{'knowledge': items[:1]}, {'knowledge': items[1:]}]
            elif kind == 'empty': bad['replay']['entries'][0]['knowledge'] = []
            elif kind == 'extra_knowledge': items[0]['G'] = 99
            else: bad['replay']['attributions'] = []
            with self.subTest(kind=kind), self.assertRaises(ValueError): g.evaluate_gate(bad)

    def test_replay_reference_permissions_are_rechecked(self):
        for text in ('P2:1 supports the first task.', 'Q99:1 supports the first task.',
                     '`Memory:M1` establishes the current effect.'):
            bad = deepcopy(self.replayed)
            bad['replay']['entries'][0]['knowledge'][0]['text'] = text
            bad['knowledge'][0]['text'] = text
            with self.subTest(text=text), self.assertRaises(ValueError): g.evaluate_gate(bad)

    def test_receipt_schema_and_cached_knowledge_are_not_trusted(self):
        for kind in ('missing', 'extra', 'raw_only', 'changed', 'reordered', 'tuple', 'not_object'):
            bad = deepcopy(self.replayed)
            if kind == 'missing': del bad['knowledge']
            elif kind == 'extra': bad['gate'] = {}
            elif kind == 'raw_only': bad = bad['replay']
            elif kind == 'changed': bad['knowledge'][0]['update_id'] = 'u2'
            elif kind == 'reordered': bad['knowledge'].reverse()
            elif kind == 'tuple': bad['knowledge'] = tuple(bad['knowledge'])
            else: bad = []
            with self.subTest(kind=kind), self.assertRaises(ValueError): g.evaluate_gate(bad)

    def test_call_skip_flags_must_match_verified_transitions_with_strict_types(self):
        skipped = self.replay_for(contents=self.parent_contents, links=[])
        for receipt in (self.replayed, skipped):
            for flag in (None, 0, 1, 'true', not receipt['replay_called']):
                bad = deepcopy(receipt); bad['replay_called'] = flag
                with self.subTest(flag=flag), self.assertRaises(ValueError): g.evaluate_gate(bad)
            bad = deepcopy(receipt)
            bad['replay_skip_reason'] = 'no_hard_transitions' if receipt['replay_called'] else None
            with self.assertRaises(ValueError): g.evaluate_gate(bad)
        bad = deepcopy(skipped); bad['replay'] = {'entries': [{'knowledge': []}]}
        with self.assertRaises(ValueError): g.evaluate_gate(bad)

    def test_complete_batch_payload_and_hard_scores_are_reverified(self):
        for kind in ('drop_unchanged', 'pair', 'hard', 'bool', 'float', 'nan', 'patch', 'run'):
            bad = deepcopy(self.replayed)
            if kind == 'drop_unchanged': bad['payload']['pairs'].pop()
            elif kind == 'pair': bad['payload']['pairs'][0]['candidate'] = 'Q2'
            elif kind in ('hard', 'bool', 'float', 'nan'):
                bad['payload']['pairs'][0]['candidate_result']['hard'] = {
                    'hard': 0, 'bool': True, 'float': 1.0, 'nan': float('nan')}[kind]
            elif kind == 'patch': bad['payload']['edits'][0]['patch'] = ''
            else: bad['payload']['runs'][0]['attempts'][0]['assistant']['content'] = 'forged'
            with self.subTest(kind=kind), self.assertRaises(ValueError): g.evaluate_gate(bad)

    def test_editor_handoff_and_execution_records_are_reverified(self):
        for kind in ('candidate', 'parent', 'status', 'patch', 'effective', 'record', 'coverage'):
            bad = deepcopy(self.replayed)
            saved = bad['audit']['editor']
            if kind == 'candidate': saved['candidate_text'] += 'forged'
            elif kind == 'parent': saved['facts']['parent'] += 'forged'
            elif kind == 'status': saved['editor_status'] = 'no_change'
            elif kind == 'patch': saved['editor']['edits'][0]['patch'] = None
            elif kind == 'effective': saved['effective_plan']['updates'][0]['text'] = 'forged'
            elif kind == 'record': bad['audit']['candidate_records'][0]['execution']['metrics']['hard'] = 0
            else: bad['audit']['candidate_records'].pop()
            with self.subTest(kind=kind), self.assertRaises(ValueError): g.evaluate_gate(bad)

    def test_changed_unchanged_task_archive_is_caught_after_replay_completion(self):
        path = self.child_dir / 'actor/0006/trajectory.json'
        record = read(path); record['execution']['content'] = 'forged after Replay'
        save(path, record)
        with self.assertRaises(ValueError): g.evaluate_gate(self.replayed)

    def test_no_change_and_null_editor_cannot_enter_gate_via_forged_receipt(self):
        for value in ('', None):
            bad = deepcopy(self.replayed)
            bad['audit']['editor'] = self.make_editor([value] * 5)
            with self.subTest(value=value), self.assertRaises(ValueError): g.evaluate_gate(bad)

    def test_valid_output_recomputed_and_forged_results_rejected(self):
        original = g.evaluate_gate(self.replayed)
        for kind in ('count', 'decision', 'empty_patch', 'id', 'duplicate', 'order', 'missing',
                     'selected_ids', 'selected_text', 'diff', 'source', 'score', 'reason'):
            bad = deepcopy(original)
            if kind == 'count': bad['decisions'][0]['G'] = 99
            elif kind == 'decision': bad['decisions'][0]['gate_decision'] = 'Reject'
            elif kind == 'empty_patch': bad['decisions'][-1]['gate_decision'] = 'Defer'
            elif kind == 'id': bad['decisions'][0]['update_id'] = 'u99'
            elif kind == 'duplicate': bad['decisions'].append(deepcopy(bad['decisions'][0]))
            elif kind == 'order': bad['decisions'].reverse()
            elif kind == 'missing': bad['decisions'].pop()
            elif kind == 'selected_ids': bad['selection']['selected_update_ids'] = ['u2']
            elif kind == 'selected_text': bad['selection']['selected_text'] = self.edited['candidate_text']
            elif kind == 'diff': bad['selection']['actual_diff'] = ''
            elif kind == 'source': bad['selected_execution_source'] = 'candidate'
            elif kind == 'score': bad['selection']['hard'] = 100
            else: bad['decisions'][0]['reason'] = 'invented'
            with self.subTest(kind=kind), self.assertRaises(ValueError): g.validate_gate(bad, replayed=self.replayed)

    def test_output_counts_and_arrays_have_strict_types(self):
        original = g.evaluate_gate(self.replayed)
        for value in (True, False, 1.0, -1, float('nan'), '1', None):
            bad = deepcopy(original); bad['decisions'][0]['G'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): g.validate_gate(bad, replayed=self.replayed)
        for kind in ('decisions_tuple', 'ids_tuple', 'unknown_state', 'extra', 'missing', 'not_object'):
            bad = deepcopy(original)
            if kind == 'decisions_tuple': bad['decisions'] = tuple(bad['decisions'])
            elif kind == 'ids_tuple': bad['selection']['selected_update_ids'] = tuple(bad['selection']['selected_update_ids'])
            elif kind == 'unknown_state': bad['decisions'][0]['gate_decision'] = 'RETAIN'
            elif kind == 'extra': bad['reason'] = 'extra'
            elif kind == 'missing': del bad['selection']
            else: bad = []
            with self.subTest(kind=kind), self.assertRaises(ValueError): g.validate_gate(bad, replayed=self.replayed)

    def test_gate_validation_rechecks_archives_instead_of_trusting_valid_output(self):
        result = g.evaluate_gate(self.replayed)
        path = self.parent_dir / 'actor/0001/trajectory.json'
        record = read(path); record['execution']['content'] = 'forged after Gate'
        save(path, record)
        with self.assertRaises(ValueError): g.validate_gate(result, replayed=self.replayed)

    def test_model_knowledge_and_edit_array_order_do_not_change_gate(self):
        edited = self.make_editor(self.patches, reverse=True)
        bundle = r.build_replay_from_editor(edited, self.parents, self.children)
        raw = deepcopy(self.replayed['replay'])
        raw['entries'][0]['knowledge'].reverse()
        replayed = r.replay_call(bundle).complete(raw)
        self.assertEqual(g.evaluate_gate(replayed), g.evaluate_gate(self.replayed))

    def test_same_line_subsets_and_same_gap_order_use_existing_composer(self):
        # Rebuild a synthetic Parent with simple literal anchors; all subsequent
        # handoffs still pass the real upstream/archive validators.
        self.skill = 'Preserve dates and author names.\nTail\n'
        self.parents, self.parent_dir = self.batch(self.skill, self.parent_contents, 'parent')
        self.grouped = self.group(self.parents)
        line = 'Preserve dates and author names.\n'
        patches = [replace_line(line, line.replace('dates', 'numbers')),
                   replace_line(line, line.replace('author', 'publisher')),
                   diff(' ' + line + '+Date rule.\n Tail\n'),
                   diff(' ' + line + '+Author rule.\n Tail\n')]
        edited = self.make_editor(patches, reverse=True)
        # Two improvements can select any pair of independent Updates.
        for ids in (['u1', 'u2'], ['u1', 'u3'], ['u3', 'u4']):
            replayed = self.replay_for(edited=edited, links=[ids[0], None, ids[1], None, None])
            result = g.evaluate_gate(replayed)
            self.assertEqual(result['selection'], e.select_skill(edited, ids))
            self.assertIsNone(result['selected_execution_source'])
        self.assertEqual(result['selection']['selected_text'],
                         line + 'Date rule.\nAuthor rule.\nTail\n')

    def test_invalid_selected_empty_text_raises_without_fallback_or_extra_selection(self):
        self.skill = 'Rule\n'
        self.parents, self.parent_dir = self.batch(self.skill, self.parent_contents, 'parent')
        self.grouped = self.group(self.parents)
        edited = self.make_editor([diff('-Rule\n'), diff('+Replacement\n Rule\n')])
        replayed = self.replay_for(edited=edited, links=['u1', None, None, None, None])
        before = deepcopy(replayed)
        with patch.object(e, 'select_skill', wraps=e.select_skill) as select:
            with self.assertRaisesRegex(ValueError, 'empty Skill'): g.evaluate_gate(replayed)
        self.assertEqual(select.call_count, 1)
        self.assertEqual(select.call_args.args[1], ['u1'])
        self.assertEqual(replayed, before)

    def test_invalid_subset_eof_raises_even_when_complete_candidate_was_executed(self):
        self.skill = 'A\nB\n'
        self.parents, self.parent_dir = self.batch(self.skill, self.parent_contents, 'parent')
        self.grouped = self.group(self.parents)
        edited = self.make_editor([diff('-A\n+X\n' + NO_NEWLINE + '\n'), diff('-B\n')])
        self.assertEqual(edited['candidate_text'], 'X')
        replayed = self.replay_for(edited=edited, links=['u1', None, None, None, None])
        with self.assertRaisesRegex(ValueError, 'Selected Skill EOF'): g.evaluate_gate(replayed)

    def test_selected_patches_can_cancel_exactly_to_parent(self):
        self.skill = 'A\n'
        self.parents, self.parent_dir = self.batch(self.skill, self.parent_contents, 'parent')
        self.grouped = self.group(self.parents)
        edited = self.make_editor([diff('-A\n'), diff('+A\n A\n'), diff('+B\n A\n')])
        replayed = self.replay_for(edited=edited, links=['u1', None, 'u2', None, None])
        result = g.evaluate_gate(replayed)
        self.assertEqual(result['selection']['selected_update_ids'], ['u1', 'u2'])
        self.assertEqual(result['selection']['selected_text'], self.skill)
        self.assertEqual(result['selection']['actual_diff'], '')
        self.assertEqual(result['selected_execution_source'], 'parent')

    def test_exact_text_identity_does_not_normalize_trailing_whitespace(self):
        self.skill = 'Rule\n'
        self.parents, self.parent_dir = self.batch(self.skill, self.parent_contents, 'parent')
        self.grouped = self.group(self.parents)
        edited = self.make_editor([replace_line('Rule\n', 'Rule \n'), diff(' Rule\n+Extra\n')])
        result = g.evaluate_gate(self.replay_for(edited=edited, links=['u1', None, None, None, None]))
        self.assertEqual(result['selection']['selected_text'], 'Rule \n')
        self.assertIsNone(result['selected_execution_source'])

    def test_empty_and_absent_parent_are_preserved_as_distinct_values(self):
        for parent in ('', None):
            with self.subTest(parent=parent):
                self.skill = parent
                if parent is None:
                    directory = self.root / 'no-initial-skill'
                    by_question = {self.dataset.case(t).payload['question']: c
                                   for t, c in zip(self.tasks, self.parent_contents)}
                    self.transport.generate = lambda messages, slot: response(
                        by_question[messages[1]['content'][0]['text'].split('\n\n')[0]])
                    self.parents = self.adapter.actor_batch(self.tasks, None, directory,
                                                           {'split': 'train', 'role': 'parent'})
                    self.method.register_archive(directory)
                else:
                    self.parents, _ = self.batch(parent, self.parent_contents, 'parent')
                self.grouped = self.group(self.parents)
                edited = self.make_editor([diff('+Rule\n', create=parent is None)])
                replayed = self.replay_for(edited=edited, links=[None] * 5)
                result = g.evaluate_gate(replayed)
                self.assertEqual(result['selection'], {
                    'selected_update_ids': [], 'selected_text': parent, 'actual_diff': ''})
                self.assertEqual(result['selected_execution_source'], 'parent')
                self.assertEqual(g.validate_gate(result, replayed=replayed), result)
                forged = deepcopy(result)
                forged['selection']['selected_text'] = '' if parent is None else None
                with self.assertRaises(ValueError): g.validate_gate(forged, replayed=replayed)

    def test_no_model_actor_process_or_archive_writes_and_detached_results(self):
        before = deepcopy(self.replayed)
        files = {str(path): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        seen = len(self.transport.seen)
        with ExitStack() as stack:
            for module, name in ((r, 'replay_call'), (r, 'render_prompt'), (e, 'editor_call'),
                                  (e, 'render_prompt'), (self.adapter, 'actor_batch'),
                                  (self.adapter, 'build_gate'), (self.method, 'commit_memory')):
                stack.enter_context(patch.object(module, name, side_effect=AssertionError('Gate must not execute models')))
            first = g.evaluate_gate(self.replayed)
            checked = g.validate_gate(first, replayed=self.replayed)
            checked['decisions'].clear()
            self.assertTrue(first['decisions'])
            first['selection']['selected_update_ids'].clear()
            self.assertEqual(g.evaluate_gate(self.replayed)['selection']['selected_update_ids'], ['u1'])
        self.assertEqual(len(self.transport.seen), seen)
        self.assertEqual(self.replayed, before)
        self.assertEqual(files, {str(path): path.read_bytes() for path in self.root.rglob('*') if path.is_file()})


if __name__ == '__main__':
    unittest.main()
