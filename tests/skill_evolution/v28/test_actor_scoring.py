from copy import deepcopy
import json
from pathlib import Path
import unittest

from skilladam.benchmarks.searchqa import evaluation as native
from skilladam.benchmarks.searchqa.rollout import build_messages as native_messages, extract_answer
from skilladam.types import BenchmarkCase
from src.skill_evolution.v27.transport import RequestFailure
from src.skill_evolution.v28.benchmarks.searchqa import protocol as p, scoring as s

ROOT = Path(__file__).resolve().parents[3]


def response(content, finish='stop', **extra):
    return {'choices': [{'finish_reason': finish,
                         'message': {'role': 'assistant', 'content': content, **extra}}]}


def record(task_id, em, f1):
    return {'task_id': task_id, 'metrics': {'em': em, 'f1': f1}}


class ActorScoringTests(unittest.TestCase):
    def test_prompt_matches_review_draft(self):
        draft = ROOT / 'docs/methods/v28/actor_scoring_draft_20261101'
        for name in ('actor_system.md', 'actor_user.md'):
            self.assertEqual((p.CONTEXT / name).read_bytes(), (draft / name).read_bytes())

    def test_native_prompt_projection_and_literal_interpolation(self):
        case = BenchmarkCase(case_id='case', payload={
            'question': '  Who? {context}\n中文\n', 'context': '\n[DOC] {question} {skill_section}\n '},
            reference=['GOLD_SENTINEL'])
        for skill in (None, '', ' \n ', '  ## Strategy\n{context} {skill_section}\nUse café. \n'):
            with self.subTest(skill=skill):
                actual = p.build_messages(**case.payload, skill=skill)
                upstream = native_messages(case, method='skilladam', skill=skill)
                self.assertEqual(actual[1], upstream[1])
                self.assertEqual(actual[0]['content'].split('## Answer Format')[0],
                                 upstream[0]['content'].split('## Answer Format')[0])
                self.assertNotIn('GOLD_SENTINEL', json.dumps(actual))

    def test_gold_and_internal_fields_not_projected(self):
        row = {'id': 'ID_SENTINEL', 'question': 'Question', 'context': 'Context',
               'answers': ['GOLD_SENTINEL'], 'reasoning_content': 'HIDDEN_SENTINEL',
               'answer': 'OVERRIDE_SENTINEL', 'metadata': {'secret': 'META_SENTINEL'}}
        messages = p.messages_for_row(row, None)
        self.assertEqual(messages, p.build_messages(question='Question', context='Context', skill=None))
        for sentinel in ('ID_SENTINEL', 'GOLD_SENTINEL', 'HIDDEN_SENTINEL', 'OVERRIDE_SENTINEL', 'META_SENTINEL'):
            self.assertNotIn(sentinel, json.dumps(messages))

    def test_invalid_inputs_fail_before_execution(self):
        row = {'id': 'x', 'question': 'Q', 'context': 'C', 'answers': ['A']}
        for key, value in [('id', ''), ('question', ' '), ('context', None),
                           ('answers', []), ('answers', 'A'), ('answers', [' ']), ('answers', [2])]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                p.messages_for_row({**row, key: value}, None)
        with self.assertRaises(ValueError):
            p.messages_for_row(row, {'skill': 'not text'})

    def test_reviewed_scoring_examples(self):
        examples = json.loads((ROOT / 'docs/methods/v28/actor_scoring_draft_20261101/scoring_examples.json').read_text())
        for example in examples:
            with self.subTest(case=example['case']):
                answer, metrics = s.score(example['content'], example['gold_answers'])
                self.assertEqual(answer['extracted_answer'], example['extracted_answer'])
                self.assertEqual(metrics['em'], example['em'])
                self.assertAlmostEqual(metrics['f1'], example['f1'])

    def test_parser_edges(self):
        examples = [
            ('<ANSWER>\nParis\n</ANSWER>', 'Paris'),
            ('<answer>London</answer><answer>Paris</answer>', 'Paris'),
            ('<answer>Paris</answer>\n<answer>London', 'Paris'),
            ('<answer></answer>\nParis', ''),
            ('Reasoning\n\nParis\n ', 'Paris'),
            ('<answer>Paris', '<answer>Paris'),
            ('<answer class="x">Paris</answer>', '<answer class="x">Paris</answer>'),
            (' \n\t', ''),
        ]
        for content, expected in examples:
            with self.subTest(content=content):
                answer, _ = s.score(content, ['Paris'])
                self.assertEqual(answer['extracted_answer'], expected)
                self.assertEqual(answer['raw_content'], content)

    def test_native_differential_scoring(self):
        contents = ['', 'the', 'The Eiffel Tower.', 'foo_bar', 'Paris—France', "the's",
                    'red red blue', 'New York', 'Café 東京', '<answer>wrong</answer>\nPARIS']
        gold_sets = [['a'], ['Eiffel Tower'], ['foobar'], ['ParisFrance'], ['s'],
                     ['red blue blue'], ['New York City'], ['Café 東京'], ['London', 'Paris']]
        for content in contents:
            for answers in gold_sets:
                prediction, _ = extract_answer({'response': content})
                answer, metrics = s.score(content, answers)
                self.assertEqual(answer['extracted_answer'], prediction)
                self.assertEqual(metrics['em'], native.exact_match(prediction, answers))
                self.assertEqual(metrics['f1'], native.best_token_f1(prediction, answers))
        self.assertAlmostEqual(s.score('red red blue', ['red blue blue'])[1]['f1'], 2 / 3)
        self.assertEqual(s.score('New York', ['New York City'])[1], {'em': 0.0, 'f1': 0.8})

    def test_hidden_reasoning_and_answer_overrides_ignored(self):
        raw = response('<answer>Berlin</answer>', reasoning_content='<answer>Paris</answer>', answer='Paris')
        raw.update(answer='Paris', response='<answer>Paris</answer>')
        answer, metrics = s.score_response(raw, ['Paris'])
        self.assertEqual(answer['extracted_answer'], 'Berlin')
        self.assertEqual(metrics, {'em': 0, 'f1': 0})
        self.assertNotIn('Paris', json.dumps(answer))

    def test_normal_stop_empty_and_unformatted_scored_once(self):
        for content in ('', '<answer>Paris', 'No tags\nParis'):
            self.assertEqual(s.score_response(response(content), ['Paris']), s.score(content, ['Paris']))

    def test_length_never_scored_even_with_correct_answer(self):
        with self.assertRaises(RequestFailure) as caught:
            s.score_response(response('<answer>Paris</answer>', 'length'), ['Paris'])
        self.assertTrue(caught.exception.retryable)

    def test_malformed_and_terminal_response_classification(self):
        malformed = [{}, {'choices': []}, response(None), response('Paris')]
        malformed[-1]['choices'][0]['message']['role'] = 'user'
        for raw in malformed:
            with self.subTest(raw=raw), self.assertRaises(RequestFailure) as caught:
                s.score_response(raw, ['Paris'])
            self.assertTrue(caught.exception.retryable)
        for raw in (response('Paris', 'content_filter'), response('Paris', refusal='refused'),
                    response('Paris', tool_calls=[{'name': 'search'}]),
                    response('Paris', function_call={'name': 'search'})):
            with self.subTest(raw=raw), self.assertRaises(RequestFailure) as caught:
                s.score_response(raw, ['Paris'])
            self.assertFalse(caught.exception.retryable)

    def test_gate_accepts_em_gain_despite_f1_regression(self):
        # Real scoring examples: EM 0 -> 1/3 while mean F1 0.8 -> 1/3.
        gold = ['New York City']
        parent = [record(t, **s.score('New York', gold)[1]) for t in ['a', 'b', 'c']]
        candidate = [record(t, **s.score(content, gold)[1]) for t, content in
                     [('a', 'New York City'), ('b', 'Berlin'), ('c', 'Berlin')]]
        self.assertEqual(s.compare_scores(parent, candidate, ['a', 'b', 'c']),
                         {'decision': 'ACCEPT', 'parent_success': 0, 'candidate_success': 1, 'compared': 3})

    def test_gate_f1_alone_ties_and_em_loss_retain(self):
        examples = [
            ([record('a', 0, 0)], [record('a', 0, .8)]),
            ([record('a', 1, 1)], [record('a', 1, 1)]),
            ([record('a', 1, 1), record('b', 0, 0)],
             [record('a', 0, .8), record('b', 0, .8)]),
        ]
        for parent, candidate in examples:
            with self.subTest(parent=parent):
                self.assertEqual(s.compare_scores(parent, candidate, [r['task_id'] for r in parent])['decision'], 'RETAIN')

    def test_gate_rejects_incomplete_duplicate_wrong_tasks_and_invalid_scores(self):
        good = [record('a', 0, .2), record('b', 1, 1)]
        invalid = [good[:1], good + good[:1], [record('a', 0, .2), record('c', 1, 1)],
                   [record('a', 0, float('nan')), good[1]],
                   [record('a', True, 1), good[1]], [record('a', .5, .5), good[1]],
                   [record('a', 0, 1.01), good[1]], [record('a', 1, .5), good[1]],
                   [{'task_id': 'a', 'metrics': None}, good[1]]]
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                s.compare_scores(good, candidate, ['a', 'b'])
        for ids in ([], ['a', 'a'], ['a', 'unknown']):
            with self.assertRaises(ValueError):
                s.compare_scores(good, good, ids)

    def test_summary_requires_full_coverage_and_averages_task_f1(self):
        records = [record('a', 0, .8), record('b', 1, 1)]
        snapshot = deepcopy(records)
        self.assertEqual(s.summarize_scores(records, ['b', 'a']),
                         {'sample_count': 2, 'success_count': 1, 'em': .5, 'f1': .9})
        self.assertEqual(records, snapshot)
        with self.assertRaises(ValueError):
            s.summarize_scores(records, ['a', 'b', 'c'])


if __name__ == '__main__':
    unittest.main()
