import base64
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch, call

from PIL import Image
from skilladam.types import BenchmarkCase
from src.skill_evolution.v27.transport import RequestFailure
from src.skill_evolution.v29.storage import read, save
from src.skill_evolution.v29.benchmarks.docvqa import actor, protocol as p, scoring, facts
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter

DRAFT = p.ROOT / 'docs/methods/v29/actor_execution_scoring_draft_20261102'
FIVE = p.ROOT / 'docs/methods/v29/five_module_draft_20261102'
HIDDEN = 'PRIVATE_REASONING_NOT_OPTIMIZER_EVIDENCE'


def response(content='<answer>1,320</answer>', finish='stop', **extra):
    return {'choices': [{'message': {'role': 'assistant', 'content': content,
            'reasoning_content': HIDDEN, **extra}, 'finish_reason': finish}],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 10, 'total_tokens': 30,
                      'completion_tokens_details': {'reasoning_tokens': 5}}}


class Transport:
    def __init__(self, generate=None):
        self.generate = generate or (lambda messages, slot: response())
        self.seen = []

    def metadata(self):
        return p.actor_config()

    def __call__(self, messages, slot):
        self.seen.append(deepcopy(messages))
        return self.generate(messages, slot)


class Dataset:
    def __init__(self, root):
        self.root = root
        self.rows = {
            'synthetic:amount': ('What is the total amount due?', ['1,320'], 'train'),
            'synthetic:date': ('What is the invoice date?', ['12 May 2021'], 'train'),
            'synthetic:test': ('What is the total amount due?', ['1,320'], 'test'),
        }

    def case(self, task_id):
        question, answers, split = self.rows[task_id]
        return BenchmarkCase(task_id, {'question': question, 'image_path': 'images/amount.png'},
                             list(answers), {'split': split, 'source_split': split, 'image_root': str(self.root)})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'images').mkdir()
        Image.new('RGB', (2, 2), 'white').save(self.root / 'images/amount.png')
        self.dataset = Dataset(self.root)
        self.case = self.dataset.case('synthetic:amount')
        self.skill = p.initial_skill()
        self.skill_file = self.root / 'skill.md'
        self.skill_file.write_text(self.skill)
        self.sleep = self.enterContext(patch.object(actor.time, 'sleep'))


class PromptAndScoringTests(Base):
    def test_installed_templates_equal_design_and_upstream(self):
        for name in ('actor_system.md', 'actor_user.md', 'initial_skill.md'):
            self.assertEqual((p.CONTEXT / name).read_bytes(), (DRAFT / name).read_bytes())
        self.assertEqual((p.CONTEXT / 'actor_system.md').read_bytes(),
                         (p.ROOT / 'external/SkillAdam/skilladam/benchmarks/docvqa/prompts/rollout_system.md').read_bytes())
        self.assertEqual(self.skill, (p.ROOT / 'external/SkillOpt/skillopt/envs/docvqa/skills/initial.md').read_text())

    def test_complete_text_original_image_and_auto_detail(self):
        messages = p.build_messages(question='  What {question}?\n', skill='  Rule {skill_section}\n',
                                    image_path='images/amount.png', image_root=self.root)
        self.assertIn('## Skill\nRule {skill_section}\n\n', messages[0]['content'])
        self.assertTrue(messages[0]['content'].endswith('\n'))
        self.assertEqual(messages[1]['content'][0]['text'],
                         '  What {question}?\n\n\nReturn the final answer inside <answer>...</answer>.')
        image_url = messages[1]['content'][1]['image_url']
        self.assertEqual(set(image_url), {'url'})
        self.assertEqual(base64.b64decode(image_url['url'].split(',', 1)[1]),
                         (self.root / 'images/amount.png').read_bytes())
        projected = p.text_projection(messages, 'images/amount.png')
        self.assertEqual(projected[0], messages[0])
        self.assertEqual(projected[1]['content'][0], messages[1]['content'][0])
        self.assertNotIn('image_url', json.dumps(projected))
        self.assertIn('not supplied', projected[1]['content'][1]['text'])

    def test_no_skill_and_reference_separation(self):
        messages = p.messages_for_case(self.case, None)
        self.assertNotIn('## Skill', messages[0]['content'])
        self.assertNotIn('1,320', json.dumps(messages))
        self.assertNotIn('reference', json.dumps(messages))

    def test_missing_image_or_invalid_references_fail_before_transport(self):
        for case in (BenchmarkCase('x', {'question': 'Q', 'image_path': 'missing.png'}, ['x'], self.case.metadata),
                     BenchmarkCase('x', self.case.payload, [], self.case.metadata)):
            transport = Transport()
            with self.assertRaises((ValueError, FileNotFoundError)):
                actor.execute(case, self.skill, self.root / 'invalid', transport)
            self.assertFalse(transport.seen)
            self.assertFalse((self.root / 'invalid').exists())

    def test_all_approved_scoring_examples(self):
        for row in read(DRAFT / 'examples/scoring_examples.json'):
            with self.subTest(case=row['case']):
                answer, metrics = scoring.score(row['ordinary_content'], row['reference_answers'])
                self.assertEqual(answer['extracted_answer'], row['expected_prediction'])
                self.assertEqual(answer['raw_content'], row['ordinary_content'])
                self.assertEqual(metrics, row['expected_score'])

    def test_invalid_references_metrics_and_incomplete_response(self):
        for answers in ([], [''], ['  '], 'answer', [None]):
            with self.assertRaises(ValueError): scoring.score('x', answers)
        for metrics in ({'hard': 1, 'anls': .9}, {'hard': 0, 'anls': float('nan')}, {'hard': True, 'anls': 1}):
            with self.assertRaises(ValueError): scoring.validate_metrics(metrics)
        with self.assertRaises(RequestFailure):
            scoring.score_response(response('<answer>1,320</answer>', 'length'), ['1,320'])

    def test_gate_examples_and_complete_coverage(self):
        for row in read(DRAFT / 'examples/gate_examples.json'):
            def records(side):
                return [{'task_id': r['task_id'], 'metrics': {k: r[k] for k in ('hard', 'anls')}} for r in row[side]]
            ids = [r['task_id'] for r in row['parent']]
            self.assertEqual(scoring.compare_scores(records('parent'), records('candidate'), ids)['decision'],
                             row['expected_gate'])
        good = [{'task_id': 'x', 'metrics': {'hard': 1, 'anls': 1}}]
        for records in ([], good * 2):
            with self.assertRaises(ValueError): scoring.summarize_scores(records, ['x'])
        self.assertEqual(scoring.summarize_scores(good, ['x']),
                         {'sample_count': 1, 'success_count': 1, 'hard': 1, 'anls': 1})


class RuntimeTests(Base):
    def test_length_retries_identical_request_and_keeps_hidden_private(self):
        for index, content in enumerate((None, '', '<answer>1,320</answer>', 'unfinished')):
            with self.subTest(content=content):
                transport = Transport(lambda m, s: response(content, 'length') if s.name == '001' else response())
                root = self.root / str(index)
                result = actor.execute(self.case, self.skill, root, transport)
                self.assertEqual(result['api_requests'], 2)
                self.assertEqual(result['metrics'], {'hard': 1, 'anls': 1})
                self.assertEqual(transport.seen, [result['initial_messages']] * 2)
                self.assertNotIn(HIDDEN, json.dumps(result))
                self.assertIn(HIDDEN, (root / 'attempts/001/response.json').read_text())
                self.assertEqual(actor.read_completed(self.case, self.skill, root), result)
                self.assertEqual(actor.execute(self.case, self.skill, root, transport), result)
                self.assertEqual(len(transport.seen), 2)

    def test_mixed_failures_share_six_attempts(self):
        def generate(messages, slot):
            if slot.name in ('001', '003'): raise RequestFailure('ConnectionError')
            return response('', 'length') if slot.name < '006' else response()
        transport = Transport(generate)
        root = self.root / 'mixed'
        result = actor.execute(self.case, self.skill, root, transport)
        self.assertEqual(result['api_requests'], 6)
        self.assertEqual(len(result['usage_records']), 6)
        self.assertEqual(self.sleep.call_args_list, [call(float(n)) for n in range(1, 6)])
        self.assertEqual(actor.read_completed(self.case, self.skill, root), result)

    def test_exhaustion_does_not_reset_or_assign_zero(self):
        transport = Transport(lambda m, s: response('x', 'length'))
        root = self.root / 'exhausted'
        for _ in range(2):
            with self.assertRaisesRegex(RequestFailure, 'budget exhausted'):
                actor.execute(self.case, self.skill, root, transport)
            self.assertEqual(len(transport.seen), 6)
            self.assertFalse((root / 'result.json').exists())

    def test_wrong_empty_and_unformatted_stop_do_not_retry(self):
        for index, content in enumerate(('', 'wrong', '<answer>1,320', 'Explanation\n1,320')):
            transport = Transport(lambda m, s: response(content))
            result = actor.execute(self.case, self.skill, self.root / str(index), transport)
            self.assertEqual(result['api_requests'], 1)
            self.assertEqual(len(transport.seen), 1)

    def test_terminal_errors_stay_terminal_on_resume(self):
        for index, raw in enumerate((response('x', refusal='no'), response('x', tool_calls=[{}]),
                                     response('x', 'content_filter'))):
            transport = Transport(lambda m, s: raw)
            for _ in range(2):
                with self.assertRaises(RequestFailure) as caught:
                    actor.execute(self.case, self.skill, self.root / str(index), transport)
                self.assertFalse(caught.exception.retryable)
                self.assertEqual(len(transport.seen), 1)

    def test_saved_response_and_raw_http_resume_without_resending(self):
        for kind in ('response', 'http'):
            def interrupt(messages, slot):
                if kind == 'response': save(slot / 'response.json', response())
                else:
                    (slot / 'http_response.txt').write_text(json.dumps(response()))
                    save(slot / 'http_status.json', {'status_code': 200})
                raise KeyboardInterrupt()
            root = self.root / kind
            transport = Transport(interrupt)
            with self.assertRaises(KeyboardInterrupt): actor.execute(self.case, self.skill, root, transport)
            result = actor.execute(self.case, self.skill, root, transport)
            self.assertEqual(result['api_requests'], 1)
            self.assertEqual(len(transport.seen), 1)
            self.assertEqual(actor.read_completed(self.case, self.skill, root), result)

    def test_unknown_request_consumes_slot_prepared_request_reuses_it(self):
        def interrupt(messages, slot): raise KeyboardInterrupt()
        for prepared in (False, True):
            root = self.root / str(prepared)
            with self.assertRaises(KeyboardInterrupt): actor.execute(self.case, self.skill, root, Transport(interrupt))
            if prepared: (root / 'attempts/001/request_started.json').unlink()
            transport = Transport()
            result = actor.execute(self.case, self.skill, root, transport)
            self.assertEqual(result['api_requests'], 1 if prepared else 2)
            self.assertEqual(len(transport.seen), 1)

    def test_completed_result_rechecks_response_and_identity(self):
        root = self.root / 'complete';transport = Transport()
        actor.execute(self.case, self.skill, root, transport)
        with self.assertRaises(ValueError): actor.execute(self.case, self.skill + 'changed', root, transport)
        saved = read(root / 'result.json');saved['metrics']['hard'] = 0;save(root / 'result.json', saved)
        with self.assertRaises(ValueError): actor.execute(self.case, self.skill, root, transport)
        self.assertEqual(len(transport.seen), 1)

    def test_missing_response_is_not_reissued_for_completed_task(self):
        root = self.root / 'missing';transport = Transport()
        actor.execute(self.case, self.skill, root, transport)
        (root / 'attempts/001/response.json').unlink()
        with self.assertRaises(ValueError): actor.execute(self.case, self.skill, root, transport)
        self.assertEqual(len(transport.seen), 1)

    def test_malformed_response_retries_and_unknown_usage_stays_unknown(self):
        transport = Transport(lambda m, s: {'choices': []} if s.name == '001' else
                              {'choices': [{'message': {'role': 'assistant', 'content': ''}, 'finish_reason': 'stop'}]})
        result = actor.execute(self.case, self.skill, self.root / 'malformed', transport)
        self.assertEqual(result['api_requests'], 2)
        self.assertEqual(result['metrics'], {'hard': 0, 'anls': 0})
        self.assertTrue(all(v is None for u in result['usage_records'] for v in u.values()))


class AdapterAndFactsTests(Base):
    def test_long_ordinary_response_and_all_references_survive_projection(self):
        case = BenchmarkCase(self.case.case_id, self.case.payload,
                             ['1,320', '1320', 'one thousand three hundred twenty'], self.case.metadata)
        content = ('Actor-reported transcription; not independently verified.\n' * 2000) + '<answer>1,320</answer>'
        result = actor.execute(case, self.skill, self.root / 'long', Transport(lambda m, s: response(content)))
        projected = facts.project_execution(case, result, ref='P1', run_id='synthetic:long')
        self.assertEqual(projected['attempts'][0]['assistant']['content'], content)
        self.assertEqual(projected['outcome']['answer']['raw_content'], content)
        self.assertEqual(projected['outcome']['reference_answers'], case.reference)
        self.assertEqual(projected['initial']['messages'][0], result['initial_messages'][0])
        self.assertNotIn(HIDDEN, json.dumps(projected))

    def test_parent_candidate_gate_and_full_text_evidence(self):
        candidate = (FIVE / 'examples/01_full_chain/candidate_skill.md').read_text()
        candidate_file = self.root / 'candidate.md';candidate_file.write_text(candidate)
        def generate(messages, slot):
            is_candidate = candidate.strip() in messages[0]['content']
            if 'invoice date' in messages[1]['content'][0]['text']:
                return response('<answer>12 May 2022</answer>' if is_candidate else '<answer>12 May 2021</answer>')
            return response('<answer>1,320</answer>' if is_candidate else
                            'I will use the subtotal as the total.\n<answer>1,200</answer>')
        transport = Transport(generate);adapter = DocVQAActorAdapter(self.dataset, transport)
        tasks = ['synthetic:amount', 'synthetic:date']
        left = adapter.actor_batch(tasks, self.skill_file, self.root / 'p', {'split': 'train', 'role': 'parent'})
        right = adapter.actor_batch(tasks, candidate_file, self.root / 'q', {'split': 'train', 'role': 'candidate'})
        self.assertEqual(adapter.build_gate(self.root / 'p', self.root / 'q')['result']['decision'], 'RETAIN')
        parent = facts.build_facts(left, adapter=adapter, directory=self.root / 'p')['facts']['runs']
        child = facts.build_facts(right, adapter=adapter, directory=self.root / 'q')['facts']['runs']
        expected = read(DRAFT / 'examples/optimization_run.json');actual = deepcopy(parent[0])
        actual['run_id'] = expected['run_id'];self.assertEqual(actual, expected)
        self.assertEqual(child[0]['ref'], 'Q1')
        self.assertIn(candidate.strip(), child[0]['initial']['messages'][0]['content'])
        text = json.dumps(parent + child)
        for forbidden in (HIDDEN, 'image_url', 'data:image', 'usage_records', 'reasoning_content'):
            self.assertNotIn(forbidden, text)
        self.assertEqual(facts.run_references(parent[0]), {'P1', 'P1:0', 'P1:1', 'P1:outcome'})
        self.assertEqual([r['task_id'] for r in left], tasks)
        self.assertEqual(len(transport.seen), 4)

    def test_test_role_isolated_from_training_evidence(self):
        adapter = DocVQAActorAdapter(self.dataset, Transport())
        root = self.root / 'test'
        records = adapter.actor_batch(['synthetic:test'], self.skill_file, root,
                                      {'split': 'test', 'role': 'evaluation'}, final=True)
        with self.assertRaises(ValueError): facts.build_facts(records, adapter=adapter, directory=root)
        with self.assertRaises(ValueError):
            adapter.actor_batch(['synthetic:test'], self.skill_file, self.root / 'bad', {'split': 'train', 'role': 'parent'})
        self.assertFalse((self.root / 'bad').exists())

    def test_batch_summary_and_trajectory_recover_without_new_calls(self):
        transport = Transport();adapter = DocVQAActorAdapter(self.dataset, transport);root = self.root / 'batch'
        args = (['synthetic:amount'], self.skill_file, root, {'split': 'train', 'role': 'parent'})
        records = adapter.actor_batch(*args)
        (root / 'records.json').unlink();(root / 'actor/0001/trajectory.json').unlink()
        self.assertEqual(adapter.actor_batch(*args), records)
        self.assertEqual(len(transport.seen), 1)

    def test_preflight_all_siblings_before_new_calls(self):
        transport = Transport();adapter = DocVQAActorAdapter(self.dataset, transport);root = self.root / 'batch'
        args = (['synthetic:amount', 'synthetic:date'], self.skill_file, root, {'split': 'train', 'role': 'parent'})
        adapter.actor_batch(*args);(root / 'records.json').unlink()
        shutil.rmtree(root / 'actor/0001')
        result = read(root / 'actor/0002/result.json');result['content'] = 'changed';save(root / 'actor/0002/result.json', result)
        with self.assertRaises(ValueError): adapter.actor_batch(*args)
        self.assertEqual(len(transport.seen), 2)

    def test_record_cannot_relabel_skill_or_response(self):
        transport = Transport();adapter = DocVQAActorAdapter(self.dataset, transport);root = self.root / 'batch'
        records = adapter.actor_batch(['synthetic:amount'], self.skill_file, root, {'split': 'train', 'role': 'parent'})
        changed = deepcopy(records);changed[0]['execution']['skill'] += 'changed'
        with self.assertRaises(ValueError): facts.build_facts(changed, adapter=adapter, directory=root)


class HTTPTests(Base):
    def test_real_transport_with_mock_http_has_no_sdk_retry_or_saved_key(self):
        calls = [];mounts = []
        class Reply:
            status_code = 200
            content = json.dumps(response()).encode()
            text = content.decode()
            def json(self): return json.loads(self.text)
        class Session:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def mount(self, prefix, adapter): mounts.append(adapter.max_retries.total)
            def post(self, url, **kwargs): calls.append((url, kwargs));return Reply()
        root = self.root / 'http'
        result = actor.execute(self.case, self.skill, root, actor.ChatTransport('TEST_KEY', session_factory=Session))
        self.assertEqual(mounts, [0, 0])
        self.assertEqual(calls[0][1]['timeout'], (10, 300))
        self.assertFalse(calls[0][1]['allow_redirects'])
        self.assertEqual(calls[0][1]['json'], read(root / 'attempts/001/request.json')['body'])
        self.assertEqual(actor.read_completed(self.case, self.skill, root), result)
        self.assertTrue(all('TEST_KEY' not in f.read_text() for f in root.rglob('*') if f.is_file()))

    def test_http_retry_and_terminal_classification(self):
        for status, retryable in ((429, True), (500, True), (403, False)):
            with self.subTest(status=status):
                class Reply:
                    status_code = status
                    content = b'{"error":"example"}'
                    text = content.decode()
                class Session:
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                    def mount(self, *args): pass
                    def post(self, *args, **kwargs): return Reply()
                root = self.root / str(status)
                transport = actor.ChatTransport('TEST_KEY', session_factory=Session)
                with self.assertRaises(RequestFailure): actor.execute(self.case, self.skill, root, transport)
                self.assertEqual(len(list((root / 'attempts').iterdir())), 6 if retryable else 1)
                self.assertFalse((root / 'result.json').exists())
