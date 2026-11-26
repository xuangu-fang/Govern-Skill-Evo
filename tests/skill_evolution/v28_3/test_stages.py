"""Shared six-attempt budget, feedback provenance and durable recovery."""
from copy import deepcopy
import json
from unittest.mock import patch
from src.skill_evolution.v27.transport import RequestFailure
from src.skill_evolution.v28_3 import diagnosis as modules, facts
from src.skill_evolution.v28_3 import stages, preconditioner, diagnosis
from tests.skill_evolution.v28.runtime_support import Base, HIDDEN
from .support import bind, Generator, no_hashes
from .test_editor import offline

class StageTests(Base):
    def setUp(self):
        super().setUp(); self.enterContext(no_hashes())
        offline(self)
        self.data, self.transport, self.adapter, self.config = bind(self.root / 'fixture', rounds=1, size=1)
        scope = self.adapter.using(); scope.__enter__(); self.addCleanup(scope.__exit__, None, None, None)
        directory = self.root / 'parents'
        records = self.adapter.actor_batch(self.data.batches[0], self.skill, directory, {'split': 'train', 'role': 'parent'})
        self.adapter.register_archive(directory)
        self.call = modules.diagnosis_call(facts.build_parent_bundle(records, 'synthetic_stage'))
        self.generator = Generator()
        self.kw = {'call_config': self.config['module_calls']['diagnosis'], 'max_attempts': 6,
                   'max_input_chars': 1000000, 'max_message_utf8_bytes': 2000000,
                   'retry_delay_seconds': 2.0}

    def run_stage(self, directory, generate=None, **kwargs):
        return stages.run_stage(directory, self.call, generate=generate, **(self.kw | kwargs))

    def reject(self, fn, *args, **kwargs):
        with self.assertRaises((ValueError, KeyError, FileNotFoundError, stages.Stopped)):
            fn(*args, **kwargs)

    def test_validation_then_technical_retries_keep_only_latest_feedback(self):
        seen = []
        def generate(name, messages, directory, config):
            seen.append(deepcopy(messages))
            if len(seen) == 1:
                return {'content': '{"decision":"revise","reason":"Incomplete plan.","plan":null}', 'finish_reason': 'stop', 'reasoning_content': HIDDEN}
            if len(seen) == 2:
                raise RequestFailure('temporary')
            if len(seen) == 3:
                return {'content': 'not json', 'finish_reason': 'stop'}
            return self.generator(name, messages, directory, config)
        root = self.root / 'feedback'; path, _ = self.run_stage(root, generate)
        self.assertEqual(path.name, '004')
        self.assertEqual([len(m) for m in seen], [2, 4, 4, 4])
        self.assertEqual(seen[1], seen[2])
        self.assertEqual(seen[3][-2]['content'], 'not json')
        self.assertNotIn(HIDDEN, json.dumps(seen))
        self.assertEqual(self.sleep.call_args_list[-3:], [((2.0,),), ((4.0,),), ((6.0,),)])
        before = len(seen); self.run_stage(root, resume=True, read_only=True)
        self.assertEqual(len(seen), before)

    def test_shared_six_attempt_budget_never_resets(self):
        calls = []
        def fail(name, messages, directory, config):
            calls.append(directory.name)
            if len(calls) % 2:
                return {'content': '{}', 'finish_reason': 'length'}
            return {'content': '{}', 'finish_reason': 'stop'}
        root = self.root / 'exhaust'
        self.reject(self.run_stage, root, fail)
        self.assertEqual(calls, ['001', '002', '003', '004', '005', '006'])
        self.reject(self.run_stage, root, fail, resume=True)
        self.assertEqual(len(calls), 6)

    def test_non_retryable_provider_and_programming_errors_stop(self):
        for kind in ('quota', 'bug'):
            calls = []
            def fail(*args):
                calls.append(1)
                if kind == 'quota':
                    raise RequestFailure('HTTP 429 quota', retryable=False)
                raise ValueError('unrecognized implementation error')
            root = self.root / kind
            self.reject(self.run_stage, root, fail)
            self.reject(self.run_stage, root, fail, resume=True)
            self.assertEqual(len(calls), 1)
            self.assertEqual(stages.read(root / 'attempts/001/error.json')['kind'], 'technical')

    def test_saved_response_recovery_sends_no_new_request(self):
        root = self.root / 'response_recovery'
        with patch('src.skill_evolution.v28_3.stages._parse', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_stage(root, self.generator)
        self.run_stage(root, resume=True)
        self.assertEqual(self.generator.calls, ['diagnosis'])
        self.assertEqual(stages.read(root / 'attempts/001/recovery.json'), {'additional_requests': 0})

    def test_raw_http_recovery_without_decoded_response(self):
        root = self.root / 'http_recovery'
        def generate(name, messages, directory, config):
            answer = self.generator(name, messages, directory, config)
            raw = {'choices': [{'finish_reason': 'stop', 'message': {'content': answer['content'], 'reasoning_content': HIDDEN}}]}
            (directory / 'http_response.txt').write_text(json.dumps(raw))
            stages.save(directory / 'http_status.json', {'status_code': 200})
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_stage(root, generate)
        _, result = self.run_stage(root, resume=True)
        self.assertEqual(self.generator.calls, ['diagnosis'])
        self.assertNotIn(HIDDEN, json.dumps(result))

    def test_unknown_started_request_consumes_slot(self):
        root = self.root / 'unknown'
        def interrupted(*args):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_stage(root, interrupted)
        path, _ = self.run_stage(root, self.generator, resume=True)
        self.assertEqual(path.name, '002')
        self.assertEqual(stages.read(root / 'attempts/001/error.json')['kind'], 'technical')

    def test_unstarted_preparation_reuses_same_slot(self):
        root = self.root / 'prepared'; original = stages.save
        def interrupt(path, value):
            if path.name == 'request_started.json':
                raise KeyboardInterrupt()
            return original(path, value)
        with patch('src.skill_evolution.v28_3.stages.save', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_stage(root, self.generator)
        self.assertEqual(self.generator.calls, [])
        path, _ = self.run_stage(root, self.generator, resume=True)
        self.assertEqual(path.name, '001')

    def test_completed_unselected_response_restores_marker(self):
        root = self.root / 'completed'; original = stages.freeze
        def interrupt(path, value, **kwargs):
            if path == root / 'result.json':
                raise KeyboardInterrupt()
            return original(path, value, **kwargs)
        with patch('src.skill_evolution.v28_3.stages.freeze', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_stage(root, self.generator)
        self.run_stage(root, resume=True)
        self.assertEqual(self.generator.calls, ['diagnosis'])

    def test_capacity_rejects_before_requests_and_cannot_expand_on_resume(self):
        root = self.root / 'capacity'
        self.reject(self.run_stage, root, self.generator, max_input_chars=1)
        self.assertEqual(self.generator.calls, [])
        self.reject(self.run_stage, root, self.generator, resume=True)
        config = deepcopy(self.kw['call_config']); config['context_window_tokens'] = config['max_tokens'] + 1
        self.reject(self.run_stage, self.root / 'tokens', self.generator, call_config=config)
        self.assertEqual(self.generator.calls, [])

    def test_archive_corruption_is_not_output_feedback(self):
        root = self.root / 'corrupt'
        def generate(name, messages, directory, config):
            record_dir = self.root / 'parents/actor' / self.adapter.actor_adapter.task_key(self.data.batches[0][0])
            stages.save(record_dir / 'trajectory.json', {'forged': True})
            return self.generator(name, messages, directory, config)
        self.reject(self.run_stage, root, generate)
        self.assertEqual(self.generator.calls, ['diagnosis'])
        error = stages.read(root / 'attempts/001/error.json')
        self.assertEqual(error['kind'], 'technical')
        self.assertFalse(error['retryable'])
        self.assertNotIn('diagnostic', error)

    def test_selected_artifacts_and_request_identity_tampering_rejected(self):
        for filename in ('messages.json', 'request_context.json', 'capacity.json', 'result.json', 'parsed.json'):
            root = self.root / filename.replace('.', '_')
            path, _ = self.run_stage(root, self.generator)
            stages.save(path / filename, {'forged': True})
            before = len(self.generator.calls)
            self.reject(self.run_stage, root, self.generator, resume=True)
            self.assertEqual(len(self.generator.calls), before)

    def test_preconditioner_schema_errors_are_retryable_outputs(self):
        value = {'decision': 'revise', 'reason': 'P1:1 supports a scoped change.', 'plan': {'goal': 'Entity boundary', 'updates': [{'id': 'u1', 'text': 'Use the exact entity.', 'basis': ['P1:1']}]}}
        saved = self.call.complete(value)
        self.call = preconditioner.preconditioner_call(saved, {'rounds': []})
        self.kw['call_config'] = self.config['module_calls']['preconditioner']
        calls = []
        def generate(*args):
            calls.append(1)
            result = {'adjustments': [{'target': 'u1', 'action': 'KEEP', 'text': None, 'reason': 'Keep the scoped requirement.'}]}
            return {'content': json.dumps({'decision': 'ready'} if len(calls) == 1 else result), 'finish_reason': 'stop'}
        path, _ = self.run_stage(self.root / 'preconditioner', generate)
        self.assertEqual(path.name, '002')

    def test_prior_failure_receipts_and_requests_revalidated(self):
        for artifact in ('messages.json', 'error.json'):
            root = self.root / artifact.replace('.', '_')
            def generate(name, messages, directory, config):
                if directory.name == '001':
                    return {'content': '{"decision":"revise","reason":"Incomplete plan.","plan":null}', 'finish_reason': 'stop'}
                return self.generator(name, messages, directory, config)
            self.run_stage(root, generate)
            target = root / 'attempts/001' / artifact
            if artifact == 'error.json':
                value = stages.read(target); value['diagnostic']['error'] = 'invented feedback'
            else:
                value = [{'role': 'user', 'content': 'forged request'}]
            stages.save(target, value)
            before = len(self.generator.calls)
            self.reject(self.run_stage, root, generate, resume=True)
            self.assertEqual(len(self.generator.calls), before)

    def test_completed_http_content_conflict_is_fatal(self):
        root = self.root / 'http_conflict'
        def generate(name, messages, directory, config):
            from src.skill_evolution.v27.transport import response_value
            answer = self.generator(name, messages, directory, config)
            raw = {'choices': [{'finish_reason': 'stop', 'message': {'content': answer['content']}}]}
            (directory / 'http_response.txt').write_text(json.dumps(raw))
            stages.save(directory / 'http_status.json', {'status_code': 200})
            return response_value(raw)
        path, _ = self.run_stage(root, generate)
        raw = json.loads((path / 'http_response.txt').read_text())
        raw['choices'][0]['message']['content'] = '{}'
        (path / 'http_response.txt').write_text(json.dumps(raw))
        self.reject(self.run_stage, root, generate, resume=True)
        self.assertEqual(self.generator.calls, ['diagnosis'])

    def test_local_persistence_failure_recovers_saved_response_without_resampling(self):
        root = self.root / 'disk'; real = stages.freeze
        def fail(path, value, **kwargs):
            if path.name == 'parsed.json': raise OSError('injected local I/O failure')
            return real(path, value, **kwargs)
        with patch.object(stages, 'freeze', side_effect=fail):
            with self.assertRaises(OSError): self.run_stage(root, self.generator)
        self.assertFalse((root / 'attempts/001/error.json').exists())
        self.run_stage(root, resume=True)
        self.assertEqual(self.generator.calls, ['diagnosis'])

    def test_budget_prompt_and_implementation_identity_cannot_change_on_resume(self):
        root = self.root / 'identity'
        self.run_stage(root, self.generator)
        for kwargs in ({'max_attempts': 5}, {'retry_delay_seconds': 0},
                       {'call_config': {**self.kw['call_config'], 'max_tokens': 2000}}):
            self.reject(self.run_stage, root, self.generator, resume=True, **kwargs)
        with patch.object(modules, 'render_prompt', return_value='changed prompt'):
            self.reject(self.run_stage, root, self.generator, resume=True)
        self.assertEqual(self.generator.calls, ['diagnosis'])

    def test_read_only_audit_writes_nothing_and_missing_artifacts_are_not_rebuilt(self):
        root = self.root / 'read-only'
        path, _ = self.run_stage(root, self.generator)
        files = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.run_stage(root, read_only=True)
        self.assertEqual(files, {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()})
        (path / 'parsed.json').unlink()
        self.reject(self.run_stage, root, self.generator, read_only=True)
        self.assertFalse((path / 'parsed.json').exists())
        self.assertEqual(self.generator.calls, ['diagnosis'])
