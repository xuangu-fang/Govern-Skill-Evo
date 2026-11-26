"""Offline joint-Replay acceptance with synthetic registered execution archives.

Authored Knowledge tests structure/reference routing, not model attribution quality.
No model/network/subprocess calls or real benchmark experiments are permitted.
"""
from copy import deepcopy
import json
from unittest.mock import patch

from src.skill_evolution.v29 import modules as old_modules
from src.skill_evolution.v29.benchmarks.docvqa import evidence, protocol, prompting
from src.skill_evolution.v29.storage import read, save
from src.skill_evolution.v29_1.campaign import CampaignAdapter
from src.skill_evolution.v29_2 import diagnosis as d, preconditioner as p, editor as e
from src.skill_evolution.v29_2 import replay as r, replay_input_view as display
from tests.skill_evolution.v29.test_actor import FIVE, HIDDEN
from tests.skill_evolution.v29.test_method import MethodBase, main_example
from tests.skill_evolution.v29_2.test_diagnosis import proposal
from tests.skill_evolution.v29_2.test_preconditioner import decisions, memory_view
from tests.skill_evolution.v29_2.test_editor import diff, output, offline


def knowledge():
    return {'entries': [{'knowledge': [
        {'task_id': 'synthetic:amount', 'update_id': 'u1',
         'text': 'P1:1 submitted a subtotal; Q1:1 returned the requested total and hard changed from 0 to 1. '
                 'The observable answer-role change matches the implemented total-selection rule.'},
        {'task_id': 'synthetic:date', 'update_id': None,
         'text': 'P2:1 was correct while Q2:1 returned a different year, changing hard from 1 to 0. '
                 'The text record does not clearly link this regression to one implemented Update.'},
    ]}]}


class ReplayTests(MethodBase):
    def test_slash_lists_preserve_replay_task_scope(self):
        value = knowledge()
        value['entries'][0]['knowledge'][0]['text'] = 'Compare P1/Q1 and P1:1/Q1:outcome.'
        r.replay_call(self.bundle).complete(value)
        for token in ('P1/P2', 'P1/Q2', 'P1/Q99', 'R03/P1/Q1', 'R03/diff'):
            bad = deepcopy(value); bad['entries'][0]['knowledge'][0]['text'] += ' ' + token
            with self.subTest(token=token), self.assertRaises(ValueError):
                r.replay_call(self.bundle).complete(bad)

    def setUp(self):
        super().setUp()
        offline(self)
        self.method = CampaignAdapter(self.adapter)
        self.enterContext(self.method.using())
        self.dataset.rows['synthetic:stable_fail'] = ('What is the code?', ['CODE'], 'train')
        self.dataset.rows['synthetic:stable_success'] = ('What is the name?', ['ALPHA'], 'train')
        self.tasks += ['synthetic:stable_fail', 'synthetic:stable_success']
        self.parent_contents = ['I will use the subtotal as the total.\n<answer>1,200</answer>',
                                '<answer>12 May 2021</answer>', 'UNCHANGED_FAIL_PRIVATE\n<answer>X</answer>',
                                'UNCHANGED_SUCCESS_PRIVATE\n<answer>ALPHA</answer>']
        self.candidate_contents = ['<answer>1,320</answer>', '<answer>12 May 2022</answer>',
                                   '<answer>COD</answer>', '<answer>alpha</answer>']
        self.parents, self.parent_dir = self.batch(self.skill, self.parent_contents, 'parent')
        grouped = old_modules.grouping_call(self.parents, 'R01').complete({'groups': [{
            'group_id': 'G1', 'members': ['P1', 'P2', 'P3', 'P4'],
            'decision_problem': 'Preserve the requested answer role and scope.',
            'shared_basis': 'P1:1 selected a subtotal; P2:1 returned a date; P3:1 returned a code; P4:1 a name.',
            'important_differences': [],
        }]})
        value = proposal()
        value['plan']['updates'].append({'id': 'u2', 'text': '- Keep the required final answer element.\n',
                                        'basis': ['P2:1']})
        diagnosed = d.diagnosis_call(grouped).complete(value)
        self.preconditioned = p.preconditioner_call(diagnosed, memory_view()).complete(decisions('KEEP', 'KEEP'))
        self.change = diff(''.join(' ' + line for line in self.skill.splitlines(keepends=True)) +
                           '+- For a total question, select the requested total rather than a subtotal.\n')
        self.edited = e.editor_call(self.preconditioned).complete(output(self.change, ''))
        self.children, self.child_dir = self.batch(self.edited['candidate_text'], self.candidate_contents, 'candidate')
        self.bundle = r.build_replay_from_editor(self.edited, self.parents, self.children)

    def bundle_with(self, contents, *, tasks=None, skill=None):
        children, directory = self.batch(self.edited['candidate_text'] if skill is None else skill,
                                         contents, 'candidate', tasks)
        return r.build_replay_from_editor(self.edited, self.parents, children), directory

    def test_versioned_call_and_three_field_knowledge_completion(self):
        call = r.replay_call(self.bundle)
        self.assertEqual((call.name, call.prompt_version, call.contract_version),
                         ('replay', r.PROMPT_VERSION, r.CONTRACT_VERSION))
        self.assertEqual(json.loads(call.messages[1]['content']), r.model_input(self.bundle))
        result = call.complete_text(json.dumps(knowledge()))
        self.assertEqual(result['replay'], knowledge())
        self.assertEqual(result['knowledge'], knowledge()['entries'][0]['knowledge'])
        self.assertTrue(result['replay_called'])
        self.assertIsNone(result['replay_skip_reason'])
        self.assertEqual(len(self.transport.seen), 8)  # Only authored synthetic fixture runs.

    def test_full_batch_is_verified_before_hard_transition_filtering(self):
        with patch.object(evidence, 'verify_pair', wraps=evidence.verify_pair) as verify:
            view = r.replay_input(self.bundle)
        self.assertEqual(verify.call_count, 4)
        full = self.bundle['payload']
        self.assertEqual([(x['parent_result']['hard'], x['candidate_result']['hard'])
                          for x in full['pairs']], [(0, 1), (1, 0), (0, 0), (1, 1)])
        self.assertNotEqual(full['pairs'][2]['parent_result']['anls'], full['pairs'][2]['candidate_result']['anls'])
        self.assertEqual([x['task_id'] for x in view['pairs']], self.tasks[:2])
        self.assertEqual([x['ref'] for x in view['runs']], ['P1', 'Q1', 'P2', 'Q2'])
        self.assertEqual(len(full['runs']), 8)

    def test_filtering_preserves_original_reference_numbers(self):
        bundle, _ = self.bundle_with(['<answer>1,200</answer>', '<answer>12 May 2022</answer>',
                                     '<answer>COD</answer>', '<answer>ALPHA</answer>'])
        view = r.replay_input(bundle)
        self.assertEqual([run['ref'] for run in view['runs']], ['P2', 'Q2'])
        self.assertEqual(view['pairs'][0]['task_id'], 'synthetic:date')
        self.assertEqual(display.restore_model_input(r.model_input(bundle)), view)

    def test_independently_ordered_candidate_batch_pairs_by_task(self):
        bundle, _ = self.bundle_with(list(reversed(self.candidate_contents)), tasks=list(reversed(self.tasks)))
        view = r.replay_input(bundle)
        self.assertEqual([pair['task_id'] for pair in view['pairs']], self.tasks[:2])
        q1 = next(run for run in view['runs'] if run['ref'] == 'Q1')
        self.assertEqual(q1['task_id'], 'synthetic:amount')
        self.assertTrue(q1['run_id'].endswith(':0004'))

    def test_projection_excludes_memory_reasons_basis_and_unchanged_runs(self):
        bundle = deepcopy(self.bundle)
        saved = bundle['audit']['editor']
        saved['memory']['rounds'][0]['entries'][0]['knowledge']['text'] += ' PRIVATE_MEMORY'
        saved['preconditioner']['adjustments'][0]['reason'] += ' PRIVATE_PRECONDITIONER'
        saved['editor']['edits'][0]['reason'] += ' PRIVATE_EDITOR'
        bundle = r.build_replay_from_editor(saved, self.parents, self.children)
        body = r.replay_call(bundle).messages[1]['content']
        self.assertEqual(set(json.loads(body)), {'parent', 'diff', 'plan', 'edits', 'pairs', 'runs', 'shared_initial'})
        for forbidden in ('PRIVATE_MEMORY', 'PRIVATE_PRECONDITIONER', 'PRIVATE_EDITOR',
                          'UNCHANGED_FAIL_PRIVATE', 'UNCHANGED_SUCCESS_PRIVATE',
                          HIDDEN, 'reasoning_content', 'image_url', 'data:image', '"basis"',
                          '"memory"', '"reason"', '"checks"', '"revises"'):
            self.assertNotIn(forbidden, body)
        self.assertEqual(json.loads(body)['edits'], [{'update_id': 'u1', 'patch': self.change},
                                                     {'update_id': 'u2', 'patch': ''}])

    def test_shared_projection_restores_exact_runs_and_candidate_skill(self):
        raw = r.replay_input(self.bundle)
        compact = r.model_input(self.bundle)
        self.assertEqual(display.restore_model_input(compact), raw)
        self.assertLess(len(json.dumps(compact)), len(json.dumps(raw)))
        for run in compact['runs']:
            self.assertNotIn('request_messages', run['attempts'][0])
            self.assertNotIn('raw_content', run['outcome']['answer'])
        restored = display.restore_model_input(compact)
        for run in restored['runs']:
            expected = self.skill if run['ref'].startswith('P') else self.edited['candidate_text']
            self.assertIn(expected.strip(), run['initial']['messages'][0]['content'])
        raw['runs'][0]['attempts'][0]['assistant']['content'] = 'changed copy'
        self.assertNotEqual(raw, r.replay_input(self.bundle))

    def test_missing_extra_duplicate_and_incomplete_batches_are_rejected(self):
        for records in (self.children[:-1], self.children + [self.children[0]],
                        [self.children[0]] * 4, list(reversed(self.children)), []):
            with self.subTest(size=len(records)), self.assertRaises(ValueError):
                r.build_replay_from_editor(self.edited, self.parents, records)
        # A valid but smaller complete Candidate batch is still not a paired batch.
        children, _ = self.batch(self.edited['candidate_text'], self.candidate_contents[:3], 'candidate', self.tasks[:3])
        with self.assertRaises(ValueError):
            r.build_replay_from_editor(self.edited, self.parents, children)
        self.dataset.rows['synthetic:extra'] = ('What is the extra value?', ['EXTRA'], 'train')
        children, _ = self.batch(self.edited['candidate_text'], self.candidate_contents + ['<answer>EXTRA</answer>'],
                                  'candidate', self.tasks + ['synthetic:extra'])
        with self.assertRaises(ValueError):
            r.build_replay_from_editor(self.edited, self.parents, children)

    def test_resampled_parent_is_not_the_original_diagnosis_execution(self):
        replacement, _ = self.batch(self.skill, self.parent_contents, 'parent')
        with self.assertRaisesRegex(ValueError, 'Parent lineage'):
            r.build_replay_from_editor(self.edited, replacement, self.children)

    def test_wrong_executed_skill_and_wrong_roles_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Executed Candidate'):
            self.bundle_with(self.candidate_contents, skill=self.skill + '\nUnrelated rule.\n')
        with self.assertRaises(ValueError):
            r.build_replay_from_editor(self.edited, self.parents, self.parents)

    def test_editor_handoff_is_rebuilt_not_trusted(self):
        for change in ('candidate_text', 'actual_diff', 'editor_status', 'patch', 'effective_plan'):
            saved = deepcopy(self.edited)
            if change in ('candidate_text', 'actual_diff', 'editor_status'): saved[change] = 'forged'
            elif change == 'patch': saved['editor']['edits'][0]['patch'] = ''
            else: saved['effective_plan']['updates'][0]['text'] = 'forged'
            with self.subTest(change=change), self.assertRaises(ValueError):
                r.build_replay_from_editor(saved, self.parents, self.children)
        for patch_value in ('', None):
            saved = e.editor_call(self.preconditioned).complete(output(patch_value, ''))
            with self.subTest(patch_value=patch_value), self.assertRaises(ValueError):
                r.build_replay_from_editor(saved, self.parents, self.children)

    def test_record_task_image_config_score_and_completion_tampering_rejected(self):
        for change in ('task', 'image', 'actor', 'content', 'score', 'termination'):
            children = deepcopy(self.children)
            execution = children[0]['execution']
            if change == 'task': children[0]['task_id'] = 'synthetic:date'
            elif change == 'image': children[0]['task']['image_path'] = 'images/other.png'
            elif change == 'actor': execution['actor']['temperature'] = 0
            elif change == 'content': execution['content'] = 'forged'
            elif change == 'score': execution['metrics']['hard'] = 0
            else: execution['termination'] = 'length'
            with self.subTest(change=change), self.assertRaises(ValueError):
                r.build_replay_from_editor(self.edited, self.parents, children)

    def test_full_bundle_and_compact_input_cannot_be_forged(self):
        for change in ('drop_unchanged', 'hard_boolean', 'patch', 'pair', 'run', 'extra'):
            bad = deepcopy(self.bundle)
            if change == 'drop_unchanged':
                bad['payload']['pairs'].pop()
                bad['payload']['runs'] = bad['payload']['runs'][:-2]
            elif change == 'hard_boolean': bad['payload']['pairs'][0]['candidate_result']['hard'] = True
            elif change == 'patch': bad['payload']['edits'][0]['patch'] = ''
            elif change == 'pair': bad['payload']['pairs'][0]['candidate'] = 'Q2'
            elif change == 'run': bad['payload']['runs'][0]['attempts'][0]['assistant']['content'] = 'changed'
            else: bad['memory'] = {}
            with self.subTest(change=change), self.assertRaises(ValueError):
                r.replay_call(bad)
        good = r.model_input(self.bundle)
        r.validate_input(good, bundle=self.bundle)
        for field in ('pairs', 'runs', 'edits', 'shared_initial', 'plan'):
            bad = deepcopy(good)
            bad[field] = []
            with self.subTest(field=field), self.assertRaises(ValueError):
                r.validate_input(bad, bundle=self.bundle)

    def test_unchanged_archive_mutation_is_caught_even_after_call_preparation(self):
        call = r.replay_call(self.bundle)
        path = self.child_dir / 'actor/0003/trajectory.json'
        record = read(path)
        record['execution']['content'] = 'forged unchanged-hard task'
        save(path, record)
        with self.assertRaises(ValueError):
            call.complete(knowledge())
        with self.assertRaises(ValueError):
            r.replay_input(self.bundle)

    def test_no_hard_transitions_skip_model_and_preserve_all_effective_updates(self):
        bundle, _ = self.bundle_with(['<answer>1,200</answer>', '<answer>12 May 2021</answer>',
                                     '<answer>COD</answer>', '<answer>ALPHA</answer>'])
        with patch.object(r, 'render_prompt', side_effect=AssertionError('No prompt for skipped Replay')):
            self.assertIsNone(r.replay_call(bundle))
        result = r.skip_replay(bundle)
        self.assertFalse(result['replay_called'])
        self.assertEqual(result['replay_skip_reason'], 'no_hard_transitions')
        self.assertEqual(result['replay'], {'entries': []})
        self.assertEqual(result['knowledge'], [])
        self.assertEqual(result['payload']['plan'], bundle['payload']['plan'])
        self.assertEqual([u['id'] for u in result['payload']['plan']['updates']], ['u1', 'u2'])
        self.assertEqual(result['audit']['editor']['memory'], self.edited['memory'])
        self.assertEqual(display.restore_model_input(r.model_input(bundle)), r.replay_input(bundle))
        r.validate_replay({'entries': []}, bundle=bundle)
        for invalid in ({'entries': [{'knowledge': []}]}, knowledge()):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'requires entries='):
                r.validate_replay(invalid, bundle=bundle)
        with self.assertRaises(ValueError):
            r.skip_replay(self.bundle)

    def test_output_requires_exact_coverage_within_single_entry(self):
        valid = knowledge()
        cases = [{'entries': []}]
        missing = knowledge(); missing['entries'][0]['knowledge'].pop(); cases.append(missing)
        duplicate = knowledge()
        duplicate['entries'][0]['knowledge'].append(deepcopy(duplicate['entries'][0]['knowledge'][0]))
        cases.append(duplicate)
        for tid in ('synthetic:stable_fail', 'synthetic:stable_success', 'old:gain', 'unknown', '', None, []):
            bad = knowledge(); bad['entries'][0]['knowledge'][0]['task_id'] = tid; cases.append(bad)
        for bad in cases:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                r.validate_replay(bad, bundle=self.bundle)
        # Model item order does not affect the canonical batch order or Memory IDs.
        reordered = knowledge()
        reordered['entries'][0]['knowledge'].reverse()
        self.assertEqual(r.replay_call(self.bundle).complete(reordered)['knowledge'], valid['entries'][0]['knowledge'])

    def test_multiple_entries_rejected_even_with_complete_unique_coverage(self):
        items = knowledge()['entries'][0]['knowledge']
        split = {'entries': [{'knowledge': [items[0]]}, {'knowledge': [items[1]]}]}
        extra_empty = knowledge()
        extra_empty['entries'].append({'knowledge': []})
        call = r.replay_call(self.bundle)
        for invalid in (split, extra_empty):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'exactly one entry'):
                call.complete(invalid)
        # Reject rather than silently merging the old multi-entry shape.
        self.assertEqual(call.complete(knowledge())['replay'], knowledge())

    def test_only_current_nonempty_patch_ids_are_eligible(self):
        for uid in ('u2', 'u99', 'R00/u1', '', [], True):
            bad = knowledge(); bad['entries'][0]['knowledge'][0]['update_id'] = uid
            with self.subTest(uid=uid), self.assertRaises(ValueError):
                r.validate_replay(bad, bundle=self.bundle)
        value = knowledge()
        for item in value['entries'][0]['knowledge']:
            item['update_id'] = None
        result = r.replay_call(self.bundle).complete(value)
        self.assertEqual(len(result['knowledge']), 2)
        self.assertTrue(all(x['update_id'] is None for x in result['knowledge']))

    def test_output_schema_has_only_three_knowledge_fields(self):
        cases = [None, [], {}, {'entries': None}, {'entries': [{'knowledge': []}]},
                 {'entries': [{'knowledge': {}}]}]
        for key in ('attributions', 'revises', 'G', 'L', 'gate_decision'):
            cases.append({**knowledge(), key: []})
        for key in ('revises', 'id', 'evidence'):
            bad = knowledge(); bad['entries'][0][key] = []; cases.append(bad)
        for key in ('evidence', 'attribution_reason', 'round_id', 'confidence', 'hard'):
            bad = knowledge(); bad['entries'][0]['knowledge'][0][key] = []; cases.append(bad)
        for key in ('task_id', 'update_id', 'text'):
            bad = knowledge(); del bad['entries'][0]['knowledge'][0][key]; cases.append(bad)
        for value in ('', ' ', None, [], '\0', '\ud800'):
            bad = knowledge(); bad['entries'][0]['knowledge'][0]['text'] = value; cases.append(bad)
        for bad in cases:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                r.validate_replay(bad, bundle=self.bundle)

    def test_text_references_are_limited_to_own_event_and_actual_diff(self):
        good = knowledge()
        good['entries'][0]['knowledge'][0]['text'] += ' See `Evidence:diff`, `Evidence:P1:1` and `Update:u1`.'
        r.validate_replay(good, bundle=self.bundle)
        for ref in ('P2:1', 'Q2:outcome', 'P3:1', 'Q99:1', 'P1:2', 'R00/P1:1',
                    'R00/diff', '`Memory:M1`', '`Group:G1`', '`Check:c1`', '`Update:u99`',
                    'Evidence:P1:1', '`Evidence:pair_1_user_1`'):
            bad = knowledge(); bad['entries'][0]['knowledge'][0]['text'] = f'Unsupported {ref}.'
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                r.validate_replay(bad, bundle=self.bundle)

    def test_counts_and_direction_are_not_parsed_from_free_text(self):
        # Structural validation is not a semantic judge. Numeric truth stays in pairs.
        value = knowledge()
        value['entries'][0]['knowledge'][0]['text'] = 'An authored explanation without a score-parsing template.'
        result = r.replay_call(self.bundle).complete(value)
        self.assertEqual(result['payload']['pairs'][0]['parent_result']['hard'], 0)
        self.assertEqual(result['payload']['pairs'][0]['candidate_result']['hard'], 1)
        self.assertNotIn('G', result)
        self.assertNotIn('gate_decision', result)

    def test_no_files_written_and_snapshots_are_detached(self):
        before = {str(path): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        bundle, value = deepcopy(self.bundle), knowledge()
        call = r.replay_call(bundle)
        bundle['payload']['pairs'].clear()
        call.input['audit']['editor']['candidate_text'] = 'changed public snapshot'
        call.messages[1]['content'] = '{}'
        result = call.complete(value)
        value['entries'].clear()
        self.assertEqual(result['replay'], knowledge())
        result['knowledge'][0]['text'] = 'changed result'
        result['audit']['editor']['memory']['rounds'].clear()
        again = call.complete(knowledge())
        self.assertEqual(again['knowledge'], knowledge()['entries'][0]['knowledge'])
        self.assertEqual(again['audit']['editor']['memory'], self.edited['memory'])
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.root.rglob('*') if path.is_file()})

    def test_invalid_json_does_not_fill_null_or_empty_events(self):
        call = r.replay_call(self.bundle)
        for raw in ('', '[]', '{} trailing', '{"entries":[],"entries":[]}', '{"entries":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                call.complete_text(raw)

    def test_compact_view_rejects_missing_unused_or_cross_pair_shared_references(self):
        original = r.model_input(self.bundle)
        for change in ('missing', 'unused', 'cross_pair', 'role', 'duplicate_field', 'extra'):
            bad = deepcopy(original)
            table = bad['shared_initial']['messages']
            if change == 'missing': del table['pair_1_user_1']
            elif change == 'unused': table['unused'] = deepcopy(table['pair_1_user_1'])
            elif change == 'cross_pair': bad['runs'][0]['initial']['messages'][1] = {'shared_message': 'pair_2_user_1'}
            elif change == 'role': table['pair_1_user_1']['role'] = 'assistant'
            elif change == 'duplicate_field': bad['runs'][0]['attempts'][0]['request_messages'] = []
            else: bad['memory'] = {}
            with self.subTest(change=change), self.assertRaises(ValueError):
                display.restore_model_input(bad)

    def test_prompt_keeps_v29_1_runtime_and_enforces_new_evidence_boundaries(self):
        old = (FIVE / 'prompts/replay.md').read_text()
        prompt = r.render_prompt(protocol.actor_config())
        start = '## Agreed Actor protocol and runtime'
        self.assertEqual(old.split(start)[1].split('## Knowledge Only historical view')[0],
                         prompt.split(start)[1].split('## Verified current input')[0])
        for requirement in ('BEFORE selecting', 'exactly one event Knowledge per task',
                            'related out-of-scope regressions', 'empty patch has no new intervention',
                            'multiple Updates cannot be distinguished', 'does not prove that all Updates are unrelated',
                            'Historical Memory, basis, Preconditioner reasons, Editor reasons, Checks',
                            'never from score claims in your text',
                            'entries must contain exactly one entry', 'Do not group events into multiple entries',
                            'An entry with an empty knowledge array is never valid'):
            self.assertIn(requirement, prompt)
        for obsolete in ('Gate accepts strictly more hard successes', '## Revise whole entries',
                         '## Survey the full batch', '"revises":', '"evidence":'):
            self.assertNotIn(obsolete, prompt)
        sample = json.loads(prompt.split('```json\n')[1].split('\n```')[0])
        for item, tid in zip(sample['entries'][0]['knowledge'], self.tasks): item['task_id'] = tid
        r.validate_replay(sample, bundle=self.bundle)

    def test_prompt_version_and_runtime_are_checked(self):
        self.assertEqual(r.PROMPT_VERSION, 'v29_2_docvqa_replay_v4')
        self.assertEqual(r.CONTRACT_VERSION, 'v29_2_replay_transition_knowledge_v4')
        for version in ('v29_docvqa_replay_v1', 'v29_2_docvqa_replay_v1', 'v29_2_docvqa_replay_v2'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                r.render_prompt(protocol.actor_config(), prompt_version=version)
        changed = protocol.actor_config(); changed['temperature'] = 0
        with self.assertRaises(ValueError):
            r.render_prompt(changed)

    def test_v29_1_prompt_and_output_contract_remain_separate(self):
        self.assertEqual(prompting.render('replay', protocol.actor_config()), (FIVE / 'prompts/replay.md').read_text())
        self.tasks = self.tasks[:2]  # The unchanged legacy fixture has two tasks.
        legacy_bundle = self.chain()
        old_call = old_modules.replay_call(legacy_bundle)
        old_call.complete(main_example('replay'))
        with self.assertRaises(ValueError):
            old_call.complete(knowledge())
        with self.assertRaises(ValueError):
            r.replay_call(self.bundle).complete(main_example('replay'))


if __name__ == '__main__':
    import unittest
    unittest.main()
