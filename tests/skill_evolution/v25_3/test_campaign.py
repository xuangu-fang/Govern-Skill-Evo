"""Offline execution of the public campaign path using the frozen Spreadsheet actor."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.skill_evolution.v25 import support
from src.skill_evolution.v25_3 import campaign, method
from src.skill_evolution.v25_3.stages import read, stage
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v25_3.baseline.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter


def replacement(old, new):
    return f'--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-{old}\n+{new}\n'


class Fixture:
    def __init__(self, mode='mixed'):
        self.mode = mode
        self.calls = []
        self.payloads = {}
        self.adapter = SpreadsheetBenchAdapter(generate=support.ActorResponses(candidate_correct=mode != 'steady'),
                                              execute=support.fast_execute)

    def generate(self, name, messages, directory, call):
        self.calls.append(name)
        payload = json.loads(messages[1]['content'])
        self.payloads[name] = payload
        if name == 'diagnosis':
            updates = [dict(id=f'u{i}', text='Implement change ' + str(i), basis=['P1:1']) for i in range(1, 4)]
            result = dict(decision='revise', reason='Based on the execution', plan=dict(goal='Repair', updates=updates))
            if self.mode == 'skip':
                result.update(decision='no_change', plan=None)
        elif name == 'preconditioner':
            result = {'adjustments': [dict(target=u['id'], action='WITHDRAW' if self.mode == 'withdraw' else 'KEEP',
                                           reason='Covered' if self.mode == 'withdraw' else 'Supported', text=None)
                                      for u in payload['plan']['updates']]}
        elif name == 'editor':
            patches = [replacement('Process rows from row 2 through the row before max_row.', support.NEW),
                       replacement('Preserve unrelated cells.', 'Preserve all unrelated cells.'), '']
            if self.mode == 'empty':
                patches = ['', '', '']
            if self.mode == 'blocked':
                patches[2] = None
            result = {'edits': [dict(update_id=u['id'], patch=p, reason='Implemented as requested.')
                                for u, p in zip(payload['plan']['updates'], patches)]}
        elif name == 'replay':
            result = {'entries': [{'knowledge': [dict(task_id=p['task_id'], text='Changed submitted program.',
                                update_id=None if self.mode == 'unknown' else 'u1') for p in payload['pairs']]}]}
        return support.response(json.dumps(result))


class CampaignTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'campaign'
        fixture = support.config(Path(temp.name) / 'data')
        self.config = campaign.configuration()
        for key in ('dataset', 'batches', 'task_items', 'test_tasks', 'initial_skill'):
            self.config[key] = fixture[key]
        self.config.update(actor_max_workers=1, retry_delay_seconds=0)
        campaign.prepare(self.root, self.config)

    def advance(self, fixture):
        return campaign.run(self.root, fixture.generate, adapter=fixture.adapter, expected_config=self.config)

    def test_joint_execution_selects_subset(self):
        fixture = Fixture()
        state = self.advance(fixture)
        self.assertEqual(fixture.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'])
        self.assertEqual(len(fixture.payloads['diagnosis']['runs']), 2)
        self.assertEqual(len(fixture.payloads['preconditioner']['runs']), 1)
        self.assertEqual(set(fixture.payloads['editor']), {'parent', 'plan'})
        self.assertEqual(set(fixture.payloads['replay']),
                         {'parent','plan','diff','edits','pairs','runs','shared_initial'})
        self.assertEqual(len(fixture.payloads['replay']['pairs']), 2)
        record = state['memory']['rounds'][0]
        self.assertEqual([u['gate_decision'] for u in record['source_updates']], ['Retain', 'Defer', None])
        self.assertEqual([e['id'] for e in record['entries']], ['M1', 'M2'])
        self.assertIn(support.NEW, state['selected'])
        self.assertNotIn('Preserve all unrelated', state['selected'])
        gate = read(self.root / 'rounds/R01/gate.json')
        self.assertIsNone(gate['selected_execution_source'])
        self.assertEqual((self.root / 'final_skill.md').read_text(), state['selected'])
        self.assertEqual(self.advance(fixture), state)
        self.assertEqual(len(fixture.calls), 4)

    def test_recover_completed_stages_before_commit(self):
        fixture = Fixture()
        with patch.object(campaign, '_publish', side_effect=InterruptedError):
            with self.assertRaises(InterruptedError):
                self.advance(fixture)
        self.assertEqual(campaign.current(self.root)[1]['next_round'], 1)
        state = self.advance(fixture)
        self.assertEqual(state['next_round'], 2)
        self.assertEqual(len(fixture.calls), 4)
        self.assertEqual(len(state['memory']['rounds']), 1)

    def test_all_withdrawn(self):
        fixture = Fixture('withdraw')
        state = self.advance(fixture)
        self.assertEqual(fixture.calls, ['diagnosis', 'preconditioner'])
        self.assertEqual(state['memory']['rounds'], [])

    def test_skip(self):
        fixture = Fixture('skip')
        self.assertEqual(self.advance(fixture)['memory']['rounds'], [])
        self.assertEqual(fixture.calls, ['diagnosis'])

    def test_editor_null_stops_without_partial_publication(self):
        fixture = Fixture('blocked')
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, 'blocked'):
                self.advance(fixture)
        self.assertEqual(fixture.calls, ['diagnosis', 'preconditioner', 'editor'])
        self.assertEqual(campaign.current(self.root)[1]['next_round'], 1)

    def test_empty_edits_record_without_candidate(self):
        fixture = Fixture('empty')
        record = self.advance(fixture)['memory']['rounds'][0]
        self.assertFalse((self.root / 'rounds/R01/candidate_runs').exists())
        self.assertEqual([u['gate_decision'] for u in record['source_updates']], [None] * 3)
        self.assertEqual(record['entries'], [])

    def test_no_flip_skips_replay(self):
        fixture = Fixture('steady')
        record = self.advance(fixture)['memory']['rounds'][0]
        self.assertNotIn('replay', fixture.calls)
        self.assertEqual([u['gate_decision'] for u in record['source_updates']], ['Defer','Defer',None])

    def test_null_events_stored_without_votes(self):
        fixture = Fixture('unknown')
        record = self.advance(fixture)['memory']['rounds'][0]
        self.assertEqual(len(record['entries']), 2)
        self.assertTrue(all(e['knowledge']['update_id'] is None for e in record['entries']))
        self.assertEqual(record['source_updates'][0]['gate_decision'], 'Defer')

    def test_replay_event_boundaries(self):
        fixture = Fixture()
        self.advance(fixture)
        payload = read(self.root / 'rounds/R01/replay/input.json')
        knowledge = read(self.root / 'rounds/R01/replay/result.json')['parsed']
        first, second = knowledge['entries'][0]['knowledge']
        for invalid in ([first], [first, first], [dict(first, update_id='u3'), second],
                        [dict(first, text='See `Evidence:Q2:1`'), second]):
            with self.assertRaises(ValueError):
                method.knowledge({'entries': [{'knowledge': invalid}]}, payload)

    def test_gate_loss_and_mixed_evidence(self):
        fixture = Fixture()
        self.advance(fixture)
        rd = self.root / 'rounds/R01'
        editor = read(rd / 'editor/input.json')
        edits = read(rd / 'editor/result.json')['parsed']
        pairs = read(rd / 'replay/input.json')['pairs']
        events = read(rd / 'replay/result.json')['result']
        pairs[1]['candidate_result']['hard'] = 0
        pairs[1]['parent_result']['hard'] = 1
        mixed, selected = method.gate(editor, edits, pairs, events)
        self.assertEqual((mixed[0]['G'], mixed[0]['L'], mixed[0]['gate_decision']), (1, 1, 'Defer'))
        self.assertEqual(selected['selected_text'], editor['parent'])
        events[1]['update_id'] = 'u2'
        separate, selected = method.gate(editor, edits, pairs, events)
        self.assertEqual([x['gate_decision'] for x in separate], ['Retain', 'Reject', None])
        self.assertEqual(selected['selected_update_ids'], ['u1'])

    def test_stage_retry_and_request_budget_persist(self):
        fixture = Fixture()
        def invalid(name, messages, slot, call):
            self.assertEqual(name, 'diagnosis')
            if slot.name != '001':
                self.assertEqual(messages[-2]['content'], '{}')
            fixture.calls.append(name)
            return support.response('{}')

        fixture.generate = invalid
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, 'budget exhausted'):
                self.advance(fixture)
        self.assertEqual(len(fixture.calls), self.config['max_attempts'])
        self.assertEqual(campaign.current(self.root)[1]['next_round'], 1)

    def test_output_corrections_at_each_stage(self):
        fixture = Fixture()
        generate = fixture.generate
        def correct(name, messages, slot, call):
            if slot.name == '001':
                if name == 'replay':
                    task = json.loads(messages[1]['content'])['pairs'][0]['task_id']
                    event = dict(task_id=task, update_id=[], text='Changed')
                    return support.response(json.dumps({'entries': [{'knowledge': [event]}]}))
                return support.response('not JSON' if name == 'diagnosis' else '{}')
            self.assertEqual(slot.name, '002')
            self.assertIn('Correct this output error', messages[-1]['content'])
            return generate(name, messages, slot, call)
        fixture.generate = correct
        self.advance(fixture)
        self.assertEqual(fixture.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'])

    def test_input_and_validator_defects_stop_without_correction_or_resampling(self):
        fixture = Fixture()
        def invalid_source(run):
            require(False, 'source record changed')
        for owner, name, failure in ((method.evidence, 'run_references', invalid_source),
                                     (method, 'citations', ValueError('internal defect')),
                                     (method, 'citations', TypeError('internal defect'))):
            with self.subTest(failure=failure), patch.object(owner, name, side_effect=failure):
                with self.assertRaisesRegex((TypeError, ValueError), 'source record changed|internal defect'):
                    self.advance(fixture)
            slots = self.root / 'rounds/R01/diagnosis/attempts'
            self.assertEqual([s.name for s in slots.iterdir()], ['001'])
            self.assertFalse((slots / '001/validation.json').exists())
        self.assertEqual(fixture.calls, ['diagnosis'])
        self.advance(fixture)
        self.assertEqual(fixture.calls.count('diagnosis'), 1)

    def test_editor_input_failure_is_fatal_even_inside_output_validator(self):
        fixture = Fixture()
        with self.assertRaisesRegex(ValueError, 'Editor requires effective Updates'):
            stage(self.root, 'editor', {'parent': '', 'plan': {'goal': 'test', 'updates': []}},
                  method.construct_candidate, self.config, fixture.generate)
        self.assertFalse((self.root / 'editor/attempts/002').exists())

    def test_corrupt_selected_response_does_not_request_a_correction(self):
        fixture = Fixture()
        rd = self.root / 'rounds/R01'
        self.advance(fixture)
        slot = rd / 'diagnosis/attempts/001'
        response = read(slot / 'response.json')
        (slot / 'response.json').write_text(json.dumps({**response, 'content': '{}'}))
        with self.assertRaisesRegex(ValueError, 'Selected response failed output verification'):
            stage(rd, 'diagnosis', read(rd / 'diagnosis/input.json'), method.diagnosis,
                  self.config, fixture.generate)
        self.assertFalse((slot / 'validation.json').exists())
        self.assertEqual(fixture.calls.count('diagnosis'), 1)

    def test_mismatched_http_archive_stops_before_retry_on_resume(self):
        fixture = Fixture()
        rd = self.root / 'rounds/R01'
        self.advance(fixture)
        root = rd / 'diagnosis'
        # Simulate interruption after the response was saved but before selection.
        (root / 'result.json').unlink()
        slot = root / 'attempts/001'
        (slot / 'http_status.json').write_text('{"status_code":200}')
        (slot / 'http_response.txt').write_text(json.dumps({'choices': [
            {'finish_reason': 'stop', 'message': {'content': '{}'}}]}))
        with self.assertRaisesRegex(ValueError, 'differs from HTTP archive'):
            stage(rd, 'diagnosis', read(root / 'input.json'), method.diagnosis, self.config, fixture.generate)
        self.assertEqual(fixture.calls.count('diagnosis'), 1)
        self.assertFalse((slot / 'validation.json').exists())

    def test_preconditioner_compiles_full_replacement_and_preserves_basis(self):
        payload = {'runs': [], 'memory': {'rounds': []}, 'plan': {'goal': 'repair', 'updates': [
            {'id': 'u1', 'text': 'original', 'basis': ['P1:1']},
            {'id': 'u2', 'text': 'redundant', 'basis': ['P1:1']}]}}
        decisions = {'adjustments': [
            dict(target='u2', action='WITHDRAW', text=None, reason='Already satisfied'),
            dict(target='u1', action='REPLACE', text='Complete revision', reason='Narrow the scope')]}
        plan = method.effective_plan(decisions, payload)
        self.assertEqual(plan['updates'], [dict(id='u1', text='Complete revision', basis=['P1:1'])])

    def test_next_round_uses_selected_subset_and_history(self):
        self.root = self.root.parent / 'two-rounds'
        tasks = self.config['batches'][0]
        self.config['batches'] = [[tasks[0]], [tasks[1]]]
        campaign.prepare(self.root, self.config)
        fixture = Fixture()
        first = campaign.run(self.root, fixture.generate, adapter=fixture.adapter, limit=1,
                             expected_config=self.config)
        self.assertEqual(first['next_round'], 2)
        fixture.mode = 'withdraw'
        final = self.advance(fixture)
        self.assertEqual(final['next_round'], 3)
        self.assertEqual(fixture.payloads['diagnosis']['parent'], first['selected'])
        self.assertEqual(fixture.payloads['preconditioner']['memory'], first['memory'])
        self.assertEqual(final['memory'], first['memory'])

    def test_domain_guidance_reaches_method_stages_only(self):
        fixture = Fixture()
        generate = fixture.generate

        def inspect(name, messages, directory, call):
            system = messages[0]['content']
            self.assertEqual('## SpreadsheetBench domain guidance' in system,
                             name in ('diagnosis', 'preconditioner'))
            self.assertEqual('## SpreadsheetBench event interpretation' in system, name == 'replay')
            return generate(name, messages, directory, call)

        fixture.generate = inspect
        self.advance(fixture)
        self.assertEqual(fixture.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'])
        for messages in fixture.adapter.generate.calls:
            self.assertNotIn('## SpreadsheetBench domain guidance', messages[0]['content'])


if __name__ == '__main__':
    unittest.main()
