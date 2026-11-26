"""Targeted offline recovery and exact-newline regressions for v29.2 only."""
import json
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v27.transport import RequestFailure
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29_2 import actor_io, evolution as ev
from src.skill_evolution.v29_2.campaign import CampaignAdapter
from tests.skill_evolution.v29.test_actor import Base
from tests.skill_evolution.v29.test_campaign import snapshot
from tests.skill_evolution.v29_2.test_editor import offline
from .campaign_support import bind, Generator


class ActorIOTests(Base):
    def setUp(self):
        super().setUp(); offline(self)
        self.data, self.transport, self.adapter, self.config = bind(self.root / 'fixture', sizes=(1,), mode='gain')
        self.campaign = self.root / 'run'
        self.generate = Generator(no_change='diagnosis')
        self.enterContext(self.adapter.using())

    def interrupt_body(self, failures=0):
        original = self.transport.generate
        def interrupted(messages, slot):
            if int(slot.name) <= failures: raise RequestFailure('Synthetic temporary failure')
            raw = original(messages, slot)
            (slot / 'http_response.txt').write_text(json.dumps(raw))
            raise KeyboardInterrupt('After body write, before status commit')
        self.transport.generate = interrupted
        try:
            with self.assertRaises(KeyboardInterrupt):
                ev.run_campaign(self.campaign, config=self.config, generate=self.generate)
        finally:
            self.transport.generate = original
        return self.campaign / 'rounds/R01/parent_runs/actor/0001/attempts' / f'{failures + 1:03}'

    def test_partial_http_body_preserved_and_unknown_request_consumes_budget(self):
        slot = self.interrupt_body()
        body = (slot / 'http_response.txt').read_bytes()
        # The original adapter retains its old behavior.
        with self.assertRaisesRegex(ValueError, 'Missing HTTP status'):
            self.adapter.actor_adapter.actor_batch(self.data.batches[0], self.campaign / 'rounds/R01/parent.md',
                self.campaign / 'rounds/R01/parent_runs', {'split': 'train', 'role': 'parent'})
        self.assertEqual(ev.run_campaign(self.campaign, generate=self.generate, resume=True)['status'], 'complete')
        self.assertEqual((slot / 'http_response.incomplete.txt').read_bytes(), body)
        self.assertFalse((slot / 'http_response.txt').exists())
        self.assertFalse((slot / 'http_status.json').exists())
        self.assertTrue(ev.read(slot / 'error.json')['retryable'])
        record = ev.read(self.campaign / 'rounds/R01/parent_runs/records.json')[0]
        self.assertEqual(record['execution']['api_requests'], 2)
        self.assertEqual(len(self.transport.seen), 2)
        before = snapshot(self.campaign)
        with CampaignAdapter(DocVQAActorAdapter(self.data)).using(): ev.final_parent(self.campaign)
        self.assertEqual(snapshot(self.campaign), before)

    def test_interruption_after_archiving_body_can_resume_again(self):
        slot = self.interrupt_body(); original = Path.replace
        def interrupted(path, destination):
            result = original(path, destination)
            if Path(destination).name == 'http_response.incomplete.txt': raise KeyboardInterrupt()
            return result
        with patch.object(Path, 'replace', interrupted), self.assertRaises(KeyboardInterrupt):
            ev.run_campaign(self.campaign, generate=self.generate, resume=True)
        self.assertFalse((slot / 'error.json').exists())
        self.assertEqual(ev.run_campaign(self.campaign, generate=self.generate, resume=True)['status'], 'complete')
        self.assertEqual(len(self.transport.seen), 2)

    def test_partial_body_in_sixth_slot_cannot_reset_budget(self):
        slot = self.interrupt_body(failures=5)
        for _ in range(2):
            with self.assertRaisesRegex(RequestFailure, 'budget exhausted'):
                ev.run_campaign(self.campaign, generate=self.generate, resume=True)
        self.assertTrue((slot / 'http_response.incomplete.txt').exists())
        self.assertEqual(len(self.transport.seen), 6)
        self.assertEqual(self.generate.calls, [])
        self.assertEqual(ev.read(self.campaign / 'state.json')['next_round'], 1)

    def test_partial_body_with_wrong_request_is_not_repaired(self):
        slot = self.interrupt_body()
        request = ev.read(slot / 'request.json'); request['body']['model'] = 'wrong'
        ev.save(slot / 'request.json', request)
        with self.assertRaisesRegex(ValueError, 'Existing record differs'):
            ev.run_campaign(self.campaign, generate=self.generate, resume=True)
        self.assertTrue((slot / 'http_response.txt').exists())
        self.assertFalse((slot / 'http_response.incomplete.txt').exists())
        self.assertEqual(len(self.transport.seen), 1)

    def test_completed_response_with_missing_http_status_is_not_hidden(self):
        slot = self.interrupt_body()
        ev.save(slot / 'response.json', json.loads((slot / 'http_response.txt').read_text()))
        with self.assertRaisesRegex(ValueError, 'conflicts with a completed'):
            ev.run_campaign(self.campaign, generate=self.generate, resume=True)
        self.assertTrue((slot / 'http_response.txt').exists())
        self.assertEqual(len(self.transport.seen), 1)

    def test_partial_batch_identity_reinitializes_before_any_request(self):
        original = actor_io.save
        def interrupted(path, value):
            if path.name == 'batch.json':
                path.with_suffix('.tmp').write_text('{partial')
                raise KeyboardInterrupt()
            return original(path, value)
        with patch.object(actor_io, 'save', interrupted), self.assertRaises(KeyboardInterrupt):
            ev.run_campaign(self.campaign, config=self.config, generate=self.generate)
        self.assertEqual(self.transport.seen, [])
        self.assertEqual(ev.run_campaign(self.campaign, generate=self.generate, resume=True)['status'], 'complete')
        self.assertFalse((self.campaign / 'rounds/R01/parent_runs/batch.tmp').exists())
        self.assertEqual(len(self.transport.seen), 1)

    def test_missing_batch_identity_with_task_artifacts_still_fails(self):
        folder = self.root / 'unsafe_batch'; folder.mkdir()
        (folder / 'batch.tmp').write_text('{partial')
        (folder / 'actor').mkdir()
        with self.assertRaisesRegex(ValueError, 'Missing identity'):
            self.adapter.actor_batch(self.data.batches[0], self.skill_file, folder, {'split': 'train', 'role': 'parent'})
        self.assertEqual(self.transport.seen, [])
        self.assertFalse((folder / 'batch.json').exists())

    def test_crlf_survives_candidate_next_parent_export_and_archive_only_recovery(self):
        from scripts.runs.run_v29_2_campaign import run_training
        data, transport, adapter, config = bind(self.root / 'crlf_fixture', sizes=(1, 1), mode='gain')
        root = self.root / 'crlf'; original = Generator(count=1)
        def generate(name, messages, directory, cfg):
            response = original(name, messages, directory, cfg)
            if name == 'editor':
                value = json.loads(response['content'])
                value['edits'][0]['patch'] = value['edits'][0]['patch'].replace(
                    'scoped amount guidance.\n', 'scoped amount guidance.\r\n')
                response['content'] = json.dumps(value)
            return response
        with adapter.using():
            summary = run_training(root, config, generate=generate)
            expected = (root / 'rounds/R01/editor/attempts/001/candidate.md').read_bytes()
            self.assertIn(b'\r\n', expected)
            self.assertEqual((root / 'rounds/R02/parent.md').read_bytes(), expected)
            self.assertEqual((root / 'final_skill.md').read_bytes(), expected)
            record = ev.read(root / 'rounds/R01/candidate_runs/records.json')[0]
            self.assertEqual(record['execution']['skill'].encode('utf-8'), expected)
        fresh = CampaignAdapter(DocVQAActorAdapter(data))
        with fresh.using():
            folder = root / 'rounds/R01/candidate_runs'
            records = ev.read(folder / 'records.json'); (folder / 'records.json').unlink()
            self.assertEqual(fresh.actor_batch(data.batches[0], root / 'rounds/R01/editor/attempts/001/candidate.md',
                                              folder, {'split': 'train', 'role': 'candidate'}), records)
            self.assertEqual(run_training(root, config, resume=True), summary)
        self.assertEqual(len(transport.seen), 4)
        self.assertEqual((root / 'final_skill.md').read_bytes(), expected)
