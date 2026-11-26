from copy import deepcopy
from unittest.mock import patch

from src.skill_evolution.v28.storage import read, save
from src.skill_evolution.v28.benchmarks.searchqa import actor, protocol as p, adapter as adapter_module
from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
from .runtime_support import Base, Dataset, Transport, SKILL, response, http_archive, snapshot


class ArchiveGateTests(Base):
    def batches(self, size=3):
        dataset, transport = Dataset(size), Transport(lambda m, d: response('New York'))
        adapter = SearchQAActorAdapter(dataset, transport)
        ids = list(dataset.rows)
        parent_dir, candidate_dir = self.root / 'parent', self.root / 'candidate'
        parent = adapter.actor_batch(ids, self.skill, parent_dir, {'split': 'train', 'role': 'parent'})
        candidate_skill = self.root / 'candidate.md'
        candidate_skill.write_text(SKILL + '\nBe precise.')
        transport.fn = lambda m, d: response('New York City' if d.parent.parent.name == p.digest(ids[0]) else 'Berlin')
        candidate = adapter.actor_batch(ids, candidate_skill, candidate_dir, {'split': 'train', 'role': 'candidate'})
        def gate(parents=parent, candidates=candidate, tasks=ids, **kwargs):
            args = {'parent_skill': SKILL, 'candidate_skill': candidate_skill.read_text(),
                    'parent_directory': parent_dir, 'candidate_directory': candidate_dir}
            args.update(kwargs)
            return adapter.build_gate(parents, candidates, tasks, **args)
        return dataset, transport, adapter, ids, parent, candidate, gate

    def test_gate_accepts_em_gain_despite_large_f1_drop_and_is_read_only(self):
        _, t, _, ids, parent, candidate, gate = self.batches()
        before, calls = snapshot(self.root), t.calls
        result = gate()
        self.assertEqual(result['result'], {'decision': 'ACCEPT', 'parent_success': 0, 'candidate_success': 1, 'compared': 3})
        self.assertEqual(len(result['input']['pairs']), len(ids))
        self.assertGreater(sum(r['execution']['metrics']['f1'] for r in parent), sum(r['execution']['metrics']['f1'] for r in candidate))
        self.assertEqual(t.calls, calls)
        self.assertEqual(snapshot(self.root), before)

    def test_gate_can_audit_without_a_transport(self):
        data, _, _, ids, parent, candidate, _ = self.batches(1)
        audit = SearchQAActorAdapter(data)
        result = audit.build_gate(parent, candidate, ids, parent_skill=SKILL,
            candidate_skill=SKILL + '\nBe precise.', parent_directory=self.root / 'parent',
            candidate_directory=self.root / 'candidate')
        self.assertEqual(result['result']['decision'], 'ACCEPT')

    def test_gate_rejects_task_run_role_skill_data_prompt_model_and_score_drift(self):
        _, t, _, ids, parent, candidate, gate = self.batches()
        mutations = [
            lambda r: r.update(task_id=ids[1]),
            lambda r: r.update(run_id=parent[0]['run_id']),
            lambda r: r['provenance'].update(role='parent'),
            lambda r: r['provenance'].update(batch_id='different'),
            lambda r: r['provenance'].update(case_sha256='0' * 64),
            lambda r: r['provenance'].update(dataset_sha256='0' * 64),
            lambda r: r['provenance'].update(protocol_sha256='0' * 64),
            lambda r: r['provenance'].update(scorer='other'),
            lambda r: r['provenance'].update(gate='other'),
            lambda r: r['task'].update(context='changed'),
            lambda r: r['execution'].update(skill='changed'),
            lambda r: r['execution']['actor'].update(model='other'),
            lambda r: r['execution']['initial_messages'][0].update(content='changed'),
            lambda r: r['execution'].update(content='Berlin'),
            lambda r: r['execution']['metrics'].update(em=0, f1=0),
            lambda r: r['execution'].update(termination='length'),
            lambda r: r['execution'].update(api_requests=7),
            lambda r: r['execution'].update(reasoning_content='PRIVATE'),
        ]
        before, calls = snapshot(self.root), t.calls
        for i, mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                altered = deepcopy(candidate)
                mutate(altered[0])
                altered[0]['provenance']['record_sha256'] = p.digest(altered[0]['execution'])
                self.reject(gate, candidates=altered)
        self.reject(gate, candidate_skill=SKILL)
        self.reject(gate, parent_directory=self.root / 'candidate')
        self.assertEqual(t.calls, calls)
        self.assertEqual(snapshot(self.root), before)

    def test_gate_rejects_incomplete_duplicate_and_uncommitted_batches(self):
        _, t, _, ids, parent, candidate, gate = self.batches()
        for altered in (candidate[:-1], candidate + candidate[:1], list(reversed(candidate)), candidate[1:] + candidate[1:2]):
            self.reject(gate, candidates=altered)
        self.reject(gate, tasks=ids + ids[:1])
        self.reject(gate, tasks=ids[:-1], parents=parent[:-1], candidates=candidate[:-1])
        (self.root / 'candidate/records.json').unlink()
        before, calls = snapshot(self.root), t.calls
        self.reject(gate)
        self.assertEqual(t.calls, calls)
        self.assertEqual(snapshot(self.root), before)

    def test_gate_rereads_original_response_and_rejects_forged_consistent_scores(self):
        _, t, _, _, _, candidate, gate = self.batches()
        root = self.root / 'candidate'
        folder = root / 'actor' / p.digest(candidate[0]['task_id'])
        # Forge all derived records coherently; the unchanged provider response
        # must still disprove them when Gate revalidates the original journal.
        altered = deepcopy(candidate)
        e = altered[0]['execution']
        e.update(content='Berlin', answer={'raw_content': 'Berlin', 'extracted_answer': 'Berlin'}, metrics={'em': 0, 'f1': 0})
        altered[0]['provenance']['record_sha256'] = p.digest(e)
        save(folder / 'result.json', e)
        save(folder / 'trajectory.json', altered[0])
        save(root / 'records.json', altered)
        before, calls = snapshot(self.root), t.calls
        self.reject(gate, candidates=altered)
        self.assertEqual(t.calls, calls)
        self.assertEqual(snapshot(self.root), before)

    def test_data_and_implementation_drift_stop_before_resume_or_gate(self):
        dataset, t, adapter, ids, _, _, gate = self.batches()
        calls = t.calls
        dataset.rows[ids[0]]['answers'] = ['Berlin']
        self.reject(gate)
        self.reject(adapter.actor_batch, ids, self.skill, self.root / 'parent', {'split': 'train', 'role': 'parent'})
        dataset.rows[ids[0]]['answers'] = ['New York City']
        changed = p.implementation_identity()
        changed['prompt']['profile'] = 'new-prompt'
        with patch.object(p, 'implementation_identity', return_value=changed):
            self.reject(gate)
            self.reject(adapter.actor_batch, ids, self.skill, self.root / 'parent', {'split': 'train', 'role': 'parent'})
        self.assertEqual(t.calls, calls)

    def test_test_tasks_cannot_enter_optimization_or_gate(self):
        dataset, t = Dataset(1, 'test'), Transport()
        a = SearchQAActorAdapter(dataset, t)
        ids = list(dataset.rows)
        self.reject(a.actor_batch, ids, self.skill, self.root / 'bad', {'split': 'train', 'role': 'parent'})
        self.reject(a.actor_batch, ids, self.skill, self.root / 'bad', {'split': 'test', 'role': 'parent'}, final=True)
        records = a.actor_batch(ids, self.skill, self.root / 'test', {'split': 'test', 'role': 'evaluation'}, final=True)
        self.reject(a.build_gate, records, records, ids, parent_skill=SKILL, candidate_skill=SKILL,
                    parent_directory=self.root / 'test', candidate_directory=self.root / 'test')
        self.assertEqual(t.calls, 1)

    def test_completed_batch_and_result_only_recovery_make_no_new_requests(self):
        data, t = Dataset(2), Transport()
        adapter = SearchQAActorAdapter(data, t)
        ids, root = list(data.rows), self.root / 'batch'
        records = adapter.actor_batch(ids, self.skill, root, {'split': 'train', 'role': 'parent'})
        calls = t.calls
        self.assertEqual(adapter.actor_batch(ids, self.skill, root, {'split': 'train', 'role': 'parent'}), records)
        (root / 'records.json').unlink()
        (root / 'actor' / p.digest(ids[0]) / 'trajectory.json').unlink()
        self.assertEqual(adapter.actor_batch(ids, self.skill, root, {'split': 'train', 'role': 'parent'}), records)
        self.assertEqual(t.calls, calls)

    def test_pending_first_corrupt_completed_last_stops_before_all_workers(self):
        for split, role in (('train', 'parent'), ('test', 'evaluation')):
            with self.subTest(split=split):
                data = Dataset(2, split)
                ids = list(data.rows)
                def interrupted(m, slot):
                    if slot.parent.parent.name == p.digest(ids[0]):
                        raise KeyboardInterrupt()
                    return http_archive(slot, response(None, 'length') if slot.name == '001' else response())
                t = Transport(interrupted)
                adapter = SearchQAActorAdapter(data, t)
                root, config = self.root / split, {'split': split, 'role': role}
                def run():
                    return adapter.actor_batch(ids, self.skill, root, config, final=split == 'test')
                with self.assertRaises(KeyboardInterrupt): run()
                t.fn = None
                folder = root / 'actor' / p.digest(ids[-1])
                self.assertTrue((folder / 'trajectory.json').exists())
                corruptions = [
                    ('result.json', None), ('attempts/002/http_response.txt', None),
                    ('attempts/001/request.json', None), ('attempts/002/request.json', None),
                    ('attempts/001/request.json', lambda v: v['body'].update(max_tokens=1)),
                    ('attempts/002/request.json', lambda v: v.update(endpoint='https://changed.invalid')),
                    ('attempts/001/response.json', None),
                    ('attempts/001/response.json', lambda v: v['choices'][0].update(finish_reason='stop')),
                    ('attempts/001/http_response.txt', None), ('attempts/001/http_status.json', None),
                    ('attempts/001/error.json', None),
                    ('attempts/001/error.json', lambda v: v.update(retryable=False)),
                    ('attempts/001/error.json', lambda v: v.pop('archive')),
                    ('attempts/002/request_started.json', None),
                    ('signature.json', lambda v: v.update(skill='changed')),
                ]
                for name, operation in corruptions:
                    with self.subTest(file=name):
                        path = folder / name
                        original = path.read_bytes()
                        if operation is None: path.unlink()
                        else:
                            value = read(path); operation(value); save(path, value)
                        damaged, calls = snapshot(root), t.calls
                        with patch.object(adapter_module, 'ThreadPoolExecutor', side_effect=AssertionError('Workers started before audit')):
                            self.reject(run)
                        self.assertEqual(t.calls, calls)
                        self.assertEqual(snapshot(root), damaged)
                        path.write_bytes(original)
                calls = t.calls
                completed = run()
                self.assertEqual(t.calls, calls + 1)
                self.assertEqual(completed[0]['execution']['api_requests'], 2)
                self.assertEqual(read(root / 'actor' / p.digest(ids[0]) / 'attempts/001/error.json')['status'], 'unknown')
                self.assertEqual(run(), completed)
                self.assertEqual(t.calls, calls + 1)

    def test_failed_pending_slot_corruption_blocks_other_workers(self):
        data, t = Dataset(2), Transport(lambda m, d: response(None, 'length'))
        a, ids, root = SearchQAActorAdapter(data, t), list(data.rows), self.root / 'pending'
        with patch.object(actor.time, 'sleep', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            a.actor_batch(ids, self.skill, root, {'split': 'train', 'role': 'parent'})
        slot = root / 'actor' / p.digest(ids[-1]) / 'attempts/001'
        (slot / 'http_response.txt').write_text('artifact added after receipt')
        calls, t.fn = t.calls, None
        with patch.object(adapter_module, 'ThreadPoolExecutor', side_effect=AssertionError('Workers started before audit')):
            self.reject(a.actor_batch, ids, self.skill, root, {'split': 'train', 'role': 'parent'})
        self.assertEqual(t.calls, calls)

    def test_completed_decoded_json_loss_uses_intact_http_without_requests(self):
        data, t = Dataset(1), Transport(lambda m, slot: http_archive(slot, response()))
        a = SearchQAActorAdapter(data, t)
        ids, root = list(data.rows), self.root / 'http_copy'
        config = {'split': 'train', 'role': 'parent'}
        original = a.actor_batch(ids, self.skill, root, config)
        (root / 'actor' / p.digest(ids[0]) / 'attempts/001/response.json').unlink()
        before = snapshot(root)
        self.assertEqual(a.actor_batch(ids, self.skill, root, config), original)
        self.assertEqual(t.calls, 1)
        self.assertEqual(snapshot(root), before)

    def test_full_gate_rejects_f1_only_gain(self):
        _, t, a, ids, parent, _, _ = self.batches()
        t.fn = lambda m, d: response('New York City metropolis')
        candidate = a.actor_batch(ids, self.skill, self.root / 'f1_candidate', {'split': 'train', 'role': 'candidate'})
        self.assertGreater(candidate[0]['execution']['metrics']['f1'], parent[0]['execution']['metrics']['f1'])
        decision = a.build_gate(parent, candidate, ids, parent_skill=SKILL, candidate_skill=SKILL,
            parent_directory=self.root / 'parent', candidate_directory=self.root / 'f1_candidate')
        self.assertEqual(decision['result']['decision'], 'RETAIN')

    def test_final_response_loss_without_http_cannot_resume(self):
        _, t, a, ids, _, candidate, gate = self.batches()
        folder = self.root / 'candidate/actor' / p.digest(ids[-1])
        (folder / 'attempts/001/response.json').unlink()
        before, calls = snapshot(self.root), t.calls
        self.reject(gate)
        self.reject(a.actor_batch, ids, self.root / 'candidate.md', self.root / 'candidate', {'split': 'train', 'role': 'candidate'})
        self.assertEqual(t.calls, calls)
        self.assertEqual(snapshot(self.root), before)

    def test_missing_batch_identity_cannot_create_new_runs_over_existing_journal(self):
        _, t, a, ids, _, _, gate = self.batches()
        (self.root / 'parent/batch.json').unlink()
        calls, before = t.calls, snapshot(self.root)
        self.reject(a.actor_batch, ids, self.skill, self.root / 'parent', {'split': 'train', 'role': 'parent'})
        self.reject(gate)
        self.assertEqual(t.calls, calls)
        self.assertEqual(snapshot(self.root), before)

    def test_frozen_dataset_loader_and_in_memory_drift_detection(self):
        dataset = SearchQADataset()
        self.assertEqual([len(dataset.splits[s]) for s in ('train', 'test')], [600, 1400])
        self.assertEqual(len(dataset.batches), 40)
        first_val = dataset.case(dataset.splits['train'][400])
        self.assertEqual(first_val.metadata['source_split'], 'val')
        self.assertEqual(first_val.metadata['split'], 'train')
        dataset.snapshot()
        dataset.rows[first_val.case_id]['context'] += 'changed'
        self.reject(dataset.snapshot)
        fake = self.root / 'wrong_data'
        fake.mkdir()
        save(fake / 'v28_dataset.lock.json', {})
        self.reject(SearchQADataset, fake)
