"""Small display projection: exact text, scoped sharing, strict single requests."""
from copy import deepcopy
import unittest

from src.skill_evolution.v27.benchmarks.lmb import replay_input_view as view
from src.skill_evolution.v27.benchmarks.lmb.protocol import FORMAL_CONTEXT


def example():
    result = {'parent': 'Parent', 'diff': 'Diff', 'plan': {}, 'pairs': [], 'runs': [],
              'memory': {'format': 'knowledge-only', 'entries': []}}
    for i in (1, 2):
        result['pairs'].append({'parent': f'P{i}', 'candidate': f'Q{i}', 'task_id': f't{i}'})
        for side in ('P', 'Q'):
            ref = f'{side}{i}'
            messages = [{'role': 'system', 'content': f'{side} full Skill\n'},
                        {'role': 'user', 'content': '  相同正文 {shared_message}\n\n', 'name': 'task'}]
            result['runs'].append({'ref': ref, 'task_id': f't{i}', 'run_id': f'run-{ref}',
                'initial': {'ref': ref + ':0', 'task': {'question': 'Q', 'context': 'C'},
                            'messages': messages},
                'attempts': [{'ref': ref + ':1', 'request_context': FORMAL_CONTEXT,
                              'request_messages': deepcopy(messages),
                              'assistant': {'role': 'assistant', 'content': ref + ' answer'}}],
                'outcome': {'ref': ref + ':outcome', 'answer': {'raw_content': ref + ' answer', 'predicted_label': 'A'}, 'score': {'em': 0.0}}})
    return result


class ReplayInputViewTests(unittest.TestCase):
    def test_exact_sharing_and_request_omission_leave_source_untouched(self):
        original = example(); before = deepcopy(original)
        shared = view.model_input(original)
        table = shared['shared_initial']['messages']
        self.assertEqual(set(table), {'system_1', 'system_2', 'pair_1_user_1', 'pair_2_user_1'})
        self.assertEqual(original, before)
        restored = view.restore_initial(shared)
        for old, new in zip(original['runs'], restored['runs']):
            self.assertNotIn('request_messages', new['attempts'][0])
            new['attempts'][0]['request_messages'] = deepcopy(new['initial']['messages'])
            self.assertNotIn('raw_content', new['outcome']['answer'])
            new['outcome']['answer']['raw_content'] = new['attempts'][0]['assistant']['content']
            self.assertEqual(new, old)
        self.assertEqual(restored, original)
        shared['shared_initial']['messages']['system_1']['content'] = 'changed'
        shared['runs'][0]['initial']['task']['context'] = 'changed'
        self.assertEqual(original, before)

    def test_more_than_two_systems_and_unique_messages_stay_inline(self):
        original = example()
        original['runs'][0]['initial']['messages'][0]['content'] = 'Third system'
        original['runs'][0]['attempts'][0]['request_messages'] = deepcopy(original['runs'][0]['initial']['messages'])
        shared = view.model_input(original)
        self.assertEqual(shared['runs'][0]['initial']['messages'][0]['content'], 'Third system')
        self.assertEqual(shared['runs'][2]['initial']['messages'][0]['content'], 'P full Skill\n')
        self.assertEqual(shared['runs'][1]['initial']['messages'][0], {'shared_message': 'system_1'})
        self.assertEqual(shared['runs'][3]['initial']['messages'][0], {'shared_message': 'system_1'})

    def test_different_user_sequence_is_not_partially_shared(self):
        original = example()
        for run in original['runs'][:2]:
            run['initial']['messages'].append({'role': 'user', 'content': run['ref']})
            run['attempts'][0]['request_messages'] = deepcopy(run['initial']['messages'])
        shared = view.model_input(original)
        self.assertNotIn('pair_1_user_1', shared['shared_initial']['messages'])
        for run in shared['runs'][:2]:
            self.assertEqual(run['initial']['messages'][1:], original['runs'][0]['initial']['messages'][1:2]
                             + [{'role': 'user', 'content': run['ref']}])

    def test_message_metadata_and_whitespace_are_not_normalized(self):
        for key, value in (('content', '  相同正文 {shared_message}\n'), ('name', 'different')):
            original = example()
            original['runs'][1]['initial']['messages'][1][key] = value
            original['runs'][1]['attempts'][0]['request_messages'] = deepcopy(original['runs'][1]['initial']['messages'])
            shared = view.model_input(original)
            self.assertNotIn('pair_1_user_1', shared['shared_initial']['messages'])

    def test_reject_non_single_turn_or_different_request(self):
        for mutation in (
            lambda r: r.update(attempts=[]),
            lambda r: r['attempts'].append(deepcopy(r['attempts'][0])),
            lambda r: r['attempts'][0].update(request_context='multi-turn'),
            lambda r: r['attempts'][0].pop('request_messages'),
            lambda r: r['attempts'][0]['request_messages'][0].update(content='different'),
            lambda r: r['attempts'][0]['request_messages'].reverse(),
        ):
            original = example(); mutation(original['runs'][0])
            with self.assertRaises(ValueError): view.model_input(original)

    def test_restore_rejects_unknown_unused_and_cross_pair_pointers(self):
        for mutation in (
            lambda v: v['runs'][0]['initial']['messages'][0].update(shared_message='missing'),
            lambda v: v['shared_initial']['messages'].update(unused={'role': 'user', 'content': 'extra'}),
            lambda v: v['runs'][2]['initial']['messages'][1].update(shared_message='pair_1_user_1'),
            lambda v: v['shared_initial'].update(format='unknown'),
        ):
            shared = view.model_input(example()); mutation(shared)
            with self.assertRaises(ValueError): view.restore_initial(shared)

    def test_explicit_pairs_control_user_sharing_without_reordering_runs(self):
        original = example(); original['runs'].reverse(); original['pairs'].reverse()
        shared = view.model_input(original)
        self.assertEqual([r['ref'] for r in shared['runs']], ['Q2', 'P2', 'Q1', 'P1'])
        self.assertEqual(shared['pairs'], original['pairs'])
        self.assertEqual(shared['runs'][0]['initial']['messages'][1], {'shared_message': 'pair_1_user_1'})
        self.assertEqual(shared['runs'][2]['initial']['messages'][1], {'shared_message': 'pair_2_user_1'})

    def test_full_response_once_and_exact_roundtrip(self):
        import json
        for content in ('', '  数学\n\n<answer>A</answer>  ', 'unique-response-' + 'z' * 65536):
            original = example()
            for run in original['runs']:
                run['attempts'][0]['assistant']['content'] = content
                run['outcome']['answer']['raw_content'] = content
            before = deepcopy(original)
            compact = view.model_input(original)
            self.assertEqual(view.restore_model_input(compact), before)
            self.assertEqual(original, before)
            for run in compact['runs']:
                self.assertNotIn('raw_content', run['outcome']['answer'])
                self.assertEqual(run['attempts'][0]['assistant']['content'], content)
            if content.startswith('unique-response-'):
                self.assertEqual(json.dumps(compact).count('unique-response-'), 4)

    def test_response_mismatch_or_missing_rejected(self):
        for mutate in (lambda a: a.update(raw_content='different'), lambda a: a.pop('raw_content')):
            original = example()
            mutate(original['runs'][0]['outcome']['answer'])
            before = deepcopy(original)
            with self.assertRaises(ValueError): view.model_input(original)
            self.assertEqual(original, before)

    def test_restore_rejects_reintroduced_duplicates(self):
        for target in ('request_messages', 'raw_content'):
            compact = view.model_input(example())
            run = compact['runs'][0]
            if target == 'request_messages': run['attempts'][0][target] = []
            else: run['outcome']['answer'][target] = run['attempts'][0]['assistant']['content']
            with self.assertRaises(ValueError): view.restore_model_input(compact)
