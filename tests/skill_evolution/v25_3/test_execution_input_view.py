"""Losslessness, sharing boundaries and real stage/retry wiring, without model calls."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from src.skill_evolution.v25_3 import BASELINE, execution_input_view as view, method
from src.skill_evolution.v25_3.baseline.benchmarks.spreadsheetbench import protocol, timeline
from src.skill_evolution.v25_3.stages import stage
from tests.skill_evolution.v25_3 import test_campaign as fixtures


def run(ref, task, system='完整 Skill\n' * 50, user='题目与工作簿预览\n' * 50, adapted=False):
    messages = [{'role': 'system', 'content': system, 'name': 'actor'},
                {'role': 'user', 'content': user}]
    result = dict(ref=ref, task_id=task, run_id='execution-' + ref,
                  initial={'ref': ref + ':0', 'messages': deepcopy(messages)},
                  attempts=[], outcome={'ref': ref + ':outcome', 'score': {'hard': 0}})
    for number in (1, 3):  # Gaps are legal in execution-only evidence.
        body = ('INPUT_PATH = "local.xlsx"\n' if adapted else '') + 'print("中文🧪")\n'
        response = '```python\n' + body + '```'
        _, code = protocol.extract_code(response)
        feedback = {'role': 'user', 'content': 'Runtime error\n'} if number == 1 else None
        result['attempts'].append(dict(ref=f'{ref}:{number}', request_messages=deepcopy(messages),
            request_context=protocol.EXECUTION_HISTORY, response=response, executed_code=code,
            executed=True, response_in_history=True, feedback_to_actor=feedback,
            execution={'stderr': 'Runtime error\n' if feedback else '', 'stdout': ''}))
        messages.append({'role': 'assistant', 'content': response})
        if feedback:
            messages.append(feedback)
    return result


def replay():
    return dict(parent='完整 Skill', plan={'goal': 'Fix', 'updates': []}, diff='', edits=[],
        pairs=[dict(task_id=str(i), parent=f'P{i}', candidate=f'Q{i}') for i in (1, 2)],
        runs=[run(ref, str(i), system=('Parent\n' if ref.startswith('P') else 'Candidate\n') * 100)
              for i in (1, 2) for ref in (f'P{i}', f'Q{i}')])


class InputViewTests(unittest.TestCase):
    def test_multiturn_roundtrip_and_pair_scoped_sharing(self):
        raw = replay()
        before = deepcopy(raw)
        compact = view.project(raw)
        self.assertEqual(view.restore(compact), raw)
        self.assertEqual(raw, before)
        table = compact['shared_initial']['messages']
        self.assertEqual(len(table), 4)  # Two systems and one user per pair, not cross-task.
        self.assertEqual(sum(m['role'] == 'system' for m in table.values()), 2)
        for r in compact['runs']:
            for a in r['attempts']:
                self.assertNotIn('request_messages', a)
                self.assertEqual(a['executed_code'], view.replay_code_view.MARKER)
        self.assertLess(len(view.exact(compact).encode()), len(view.exact(timeline.project(raw)).encode()))

    def test_diagnosis_and_preconditioner_keep_user_inline(self):
        for module in ('diagnosis', 'preconditioner'):
            raw = dict(parent='Parent', runs=[run('P1', '1'), run('P2', '2')])
            if module == 'preconditioner':
                raw.update(plan={'updates': []}, memory={'rounds': [{'entries': ['history']}]})
            compact = view.project(raw)
            self.assertEqual(view.restore(compact), raw)
            self.assertEqual(len(compact['shared_initial']['messages']), 1)
            for r in compact['runs']:
                self.assertEqual(r['initial']['messages'][1]['role'], 'user')

    def test_adapted_code_stays_complete(self):
        raw = dict(parent='Parent', runs=[run('P1', '1', adapted=True)])
        compact = view.project(raw)
        for a in compact['runs'][0]['attempts']:
            self.assertIsInstance(a['executed_code'], str)
            self.assertIn('pass', a['executed_code'])
            self.assertIn('INPUT_PATH =', a['response'])
        self.assertEqual(view.restore(compact), raw)
        compact['runs'][0]['attempts'][0]['executed_code'] = view.replay_code_view.MARKER
        with self.assertRaises(ValueError):
            view.restore(compact)

    def test_exact_message_equality_required(self):
        raw = replay()
        # Tiny text or metadata changes must stay visible, including user whitespace.
        raw['runs'][0]['initial']['messages'][0]['name'] = 'different'
        raw['runs'][1]['initial']['messages'][1]['content'] += ' '
        for r in raw['runs']:
            for a, messages in zip(r['attempts'], timeline.requests_for(r)):
                a['request_messages'] = messages
        compact = view.project(raw)
        self.assertEqual(view.restore(compact), raw)
        self.assertEqual(compact['runs'][0]['initial']['messages'][0]['name'], 'different')
        self.assertIn('content', compact['runs'][1]['initial']['messages'][1])

    def test_invalid_history_pair_and_pointer_rejected(self):
        raw = replay()
        raw['runs'][0]['attempts'][1]['request_messages'].pop()
        with self.assertRaises(ValueError):
            view.project(raw)
        raw = replay()
        raw['pairs'][0]['task_id'] = 'wrong-task'
        with self.assertRaises(ValueError):
            view.project(raw)
        compact = view.project(replay())
        compact['runs'][0]['initial']['messages'][0] = {'shared_message': 'missing'}
        with self.assertRaises(ValueError):
            view.restore(compact)
        compact = view.project(replay())
        compact['shared_initial']['messages']['unused'] = {'role': 'system', 'content': 'unused'}
        with self.assertRaises(ValueError):
            view.restore(compact)

    def test_empty_runs_and_editor_unchanged(self):
        for raw in ({'parent': 'P', 'plan': {}}, {'parent': 'P', 'runs': []}):
            self.assertEqual(view.restore(view.project(raw)), raw)

    def test_campaign_sends_compact_views_but_archives_full_inputs(self):
        case = fixtures.CampaignTests('test_joint_execution_selects_subset')
        try:
            case.setUp()
            fixture = fixtures.Fixture()
            case.advance(fixture)
            for name in ('diagnosis', 'preconditioner', 'replay'):
                raw = json.loads((case.root / 'rounds/R01' / name / 'input.json').read_text())
                self.assertEqual(view.restore(fixture.payloads[name]), raw)
                self.assertNotIn('shared_initial', raw)
                self.assertIn('request_messages', raw['runs'][0]['attempts'][0])
        finally:
            case.doCleanups()

    def test_retry_keeps_compact_base_and_validates_full_payload(self):
        raw = {'parent': 'P', 'runs': [run('P1', '1'), run('P2', '2')]}
        config = {'actor_profile': json.loads((BASELINE / 'config.json').read_text())['actor_profile'],
                  'call_config': {'max_tokens': 100}, 'module_max_tokens': {},
                  'max_input_chars': 1000000, 'max_message_utf8_bytes': 2000000,
                  'max_attempts': 2, 'retry_delay_seconds': 0}
        calls = []
        def generate(name, messages, slot, call):
            calls.append(deepcopy(messages))
            output = {} if len(calls) == 1 else dict(decision='no_change', reason='Sufficient', plan=None)
            return {'content': json.dumps(output), 'finish_reason': 'stop'}
        def validate(parsed, payload):
            self.assertEqual(payload, raw)
            return method.diagnosis(parsed, payload)
        with tempfile.TemporaryDirectory() as directory:
            stage(Path(directory), 'diagnosis', raw, validate, config, generate)
        self.assertEqual(calls[0], calls[1][:2])
        self.assertEqual(len(calls[1]), 4)
        self.assertEqual(view.restore(json.loads(calls[1][1]['content'])), raw)
        self.assertIn('Shared execution evidence', calls[0][0]['content'])


if __name__ == '__main__':
    unittest.main()
