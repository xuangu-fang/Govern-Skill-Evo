"""Bounded method requests, feedback provenance and archive-only recovery."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
from unittest.mock import patch

from src.skill_evolution.v27.transport import RequestFailure
from src.skill_evolution.v29_8.facts import build_parent_bundle
from src.skill_evolution.v29_8 import stages, config, preconditioner, diagnosis, editor, replay
from src.skill_evolution.v29.benchmarks.docvqa import protocol as p
from tests.skill_evolution.v29.test_actor import Base, HIDDEN
from .campaign_support import bind, Generator
from .helpers import offline, diff, output
from tests.skill_evolution.v29.test_method import MethodBase, main_example
from .helpers import proposal
from .helpers import decisions


class StageTests(Base):
    def setUp(self):
        super().setUp()
        offline(self)
        self.data, self.transport, self.adapter, self.config = bind(self.root / 'fixture', sizes=(1,))
        scope = self.adapter.using(); scope.__enter__(); self.addCleanup(scope.__exit__, None, None, None)
        directory = self.root / 'parents'
        records = self.adapter.actor_batch(self.data.batches[0], self.skill_file, directory, {'split': 'train', 'role': 'parent'})
        self.adapter.register_archive(directory)
        self.call = diagnosis.diagnosis_call(build_parent_bundle(records, 'synthetic_stage'))
        self.generator = Generator(count=1)
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
                return {'content': '{"groups":[]}', 'finish_reason': 'stop', 'reasoning_content': HIDDEN}
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
        with patch('src.skill_evolution.v29_8.stages._parse', side_effect=KeyboardInterrupt):
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
        with patch('src.skill_evolution.v29_8.stages.save', side_effect=interrupt):
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
        with patch('src.skill_evolution.v29_8.stages.freeze', side_effect=interrupt):
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
            record_dir = self.root / 'parents/actor' / '0001'
            (record_dir / 'trajectory.json').unlink()
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
        saved = self.call.complete(json.loads(self.generator('diagnosis', self.call.messages, self.root, self.kw['call_config'])['content']))
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
                    return {'content': '{"groups":[]}', 'finish_reason': 'stop'}
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
        with patch.object(stages, '_source_hashes', return_value={'forged': 'hash'}):
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


class ModuleStageTests(MethodBase):
    def setUp(self):
        super().setUp()
        offline(self)
        self.parents = self.parent()
        self.grouped = build_parent_bundle(self.parents, 'R01')
        plan = proposal()
        plan['plan']['updates'].append({'id': 'u2', 'text': 'Preserve complete date answers.', 'basis': ['P2:1']})
        self.diagnosed = diagnosis.diagnosis_call(self.grouped).complete(plan)
        self.prepared = preconditioner.preconditioner_call(self.diagnosed, {'rounds': []}).complete(decisions('KEEP', 'KEEP'))
        context = ''.join(' ' + line for line in self.skill.splitlines(keepends=True))
        self.edits = output(diff(context + '+- Select the requested amount role.\n'),
                            diff(context + '+- Preserve the requested date granularity.\n'))
        self.edited = editor.editor_call(self.prepared).complete(self.edits)
        self.children, _ = self.batch(self.edited['candidate_text'],
                                     ['<answer>1,320</answer>', '<answer>12 May 2022</answer>'], 'candidate')
        self.bundle = replay.build_replay_from_editor(self.edited, self.parents, self.children)
        self.knowledge = {'entries': [{'knowledge': [
            {'task_id': pair['task_id'], 'update_id': f'u{i}', 'text': 'Observed answer change and scoped association.'}
            for i, pair in enumerate(self.bundle['payload']['pairs'], 1)]}]}
        self.called, self.messages = [], []
        calls = config.pending_calls()
        for value in calls.values(): value.update(max_tokens=1000, timeout_seconds=1)
        self.calls = calls
        self.options = {'max_attempts': 6, 'max_input_chars': 1000000,
                        'max_message_utf8_bytes': 2000000, 'retry_delay_seconds': 0}

    def generate(self, *outputs):
        values = iter(outputs)
        def call(name, messages, directory, cfg):
            self.called.append(name); self.messages.append(deepcopy(messages))
            return {'content': json.dumps(next(values)), 'finish_reason': 'stop'}
        return call

    def run_call(self, name, call, generate=None, **kwargs):
        return stages.run_stage(self.root / name, call, call_config=self.calls[call.name],
                                generate=generate, **(self.options | kwargs))

    def run_replay(self, name, bundle=None, generate=None, **kwargs):
        return stages.run_replay_stage(self.root / name, self.bundle if bundle is None else bundle,
                                       call_config=self.calls['replay'], generate=generate, **(self.options | kwargs))

    def no_flips(self):
        children, _ = self.batch(self.edited['candidate_text'],
                                 ['<answer>1,200</answer>', '<answer>12 May 2021</answer>'], 'candidate')
        return replay.build_replay_from_editor(self.edited, self.parents, children)

    def test_editor_archives_every_patch_and_complete_candidate(self):
        path, result = self.run_call('editor', editor.editor_call(self.prepared), self.generate(self.edits))
        self.assertEqual(stages.read(path / 'edits.json'), self.edits['edits'])
        self.assertEqual((path / 'candidate.md').read_text(), self.edited['candidate_text'])
        self.assertEqual((path / 'actual.diff').read_text(), self.edited['actual_diff'])
        self.assertFalse((path / 'patch.diff').exists())
        identity = stages.read(self.root / 'editor/identity.json')
        self.assertEqual(identity['contract'], editor.CONTRACT_VERSION)
        self.assertEqual(identity['prompt'], editor.PROMPT_VERSION)
        self.assertEqual(result, self.edited)
        self.run_call('editor', editor.editor_call(self.prepared), read_only=True)
        self.assertEqual(self.called, ['editor'])

    def test_editor_no_change_and_null_are_valid_results_not_semantic_resampling(self):
        for value, status in (('', 'no_change'), (None, 'needs_revision')):
            edits = output(value, '')
            path, result = self.run_call(status, editor.editor_call(self.prepared), self.generate(edits))
            self.assertEqual(result['editor_status'], status)
            self.assertEqual(stages.read(path / 'edits.json'), edits['edits'])
            self.assertFalse((path / 'candidate.md').exists())
            self.assertFalse((path / 'actual.diff').exists())
            self.run_call(status, editor.editor_call(self.prepared), resume=True)
        self.assertEqual(self.called, ['editor', 'editor'])

    def test_editor_mapping_patch_and_character_conflicts_are_output_errors(self):
        variants = [output('bad patch', ''), output(self.edits['edits'][0]['patch']),
                    output(diff('-missing original line\n+new\n'), '')]
        for index, invalid in enumerate(variants):
            path, result = self.run_call(f'invalid-{index}', editor.editor_call(self.prepared),
                                         self.generate(invalid, self.edits))
            self.assertEqual(path.name, '002')
            self.assertEqual(result, self.edited)
            self.assertEqual(stages.read(path.parent / '001/error.json')['kind'], 'output_validation')

    def test_diagnosis_no_change_and_preconditioner_withdraw_do_not_retry(self):
        call = diagnosis.diagnosis_call(self.grouped)
        _, result = self.run_call('diagnosis', call, self.generate({'decision': 'no_change', 'reason': 'No proposal.', 'plan': None}))
        self.assertEqual(result['diagnosis']['decision'], 'no_change')
        call = preconditioner.preconditioner_call(self.diagnosed, {'rounds': []})
        _, result = self.run_call('preconditioner', call, self.generate(decisions('WITHDRAW', 'WITHDRAW')))
        self.assertIsNone(result['effective_plan'])
        self.assertEqual(self.called, ['diagnosis', 'preconditioner'])

    def test_preconditioner_reference_feedback_covers_reason_and_replacement_text(self):
        call = preconditioner.preconditioner_call(self.diagnosed, {'rounds': []})
        for field in ('reason', 'text'):
            invalid, corrected = decisions('REPLACE', 'KEEP'), decisions('REPLACE', 'KEEP')
            invalid['adjustments'][0][field] = 'See Evidence:P1:1.'
            corrected['adjustments'][0][field] = (
                'Update: u1 concerns amounts; preserve the requested field role. See `Evidence:P1:1`.')
            name = 'preconditioner_citations_' + field
            with self.subTest(field=field):
                path, result = self.run_call(name, call, self.generate(invalid, corrected))
                self.assertEqual(path.name, '002')
                error = stages.read(path.parent / '001/error.json')
                self.assertEqual(error['kind'], 'output_validation')
                for detail in (f'u1.{field}', 'text character 5', 'Evidence:P1:1', 'single-backtick'):
                    self.assertIn(detail, self.messages[-1][-1]['content'])
                self.assertEqual(result['preconditioner'], corrected)
                self.assertEqual(self.run_call(name, call, read_only=True)[1], result)
        self.assertEqual(self.called, ['preconditioner'] * 4)

    def test_legacy_replay_prompt_identity_is_rejected_before_request(self):
        from dataclasses import replace
        call = replay.replay_call(self.bundle)
        bad = replace(call, prompt_version='v29_2_docvqa_replay_v4')
        with self.assertRaises(ValueError):
            self.run_call('legacy-replay', bad, self.generate(self.knowledge))
        self.assertEqual(self.called, [])
        self.assertFalse((self.root / 'legacy-replay/attempts').exists())

    def test_replay_single_entry_errors_are_corrected_and_result_is_reusable_by_gate(self):
        from src.skill_evolution.v29_8 import gate
        items = self.knowledge['entries'][0]['knowledge']
        invalid = {'entries': [{'knowledge': items[:1]}, {'knowledge': items[1:]}]}
        path, result = self.run_replay('replay', generate=self.generate(invalid, self.knowledge))
        self.assertEqual(path.name, '002')
        self.assertTrue(result['replay_called'])
        self.assertEqual(gate.evaluate_gate(result)['selection']['selected_update_ids'], ['u1'])
        self.assertEqual(self.run_replay('replay', read_only=True)[1], result)
        self.assertEqual(self.called, ['replay', 'replay'])

    def test_replay_citation_feedback_points_to_token_and_accepts_prose_correction(self):
        invalid, corrected = deepcopy(self.knowledge), deepcopy(self.knowledge)
        invalid['entries'][0]['knowledge'][0]['text'] = 'See Evidence:P1:1.'
        corrected['entries'][0]['knowledge'][0]['text'] = (
            'Either implemented Update: u1 concerns amounts. See `Evidence:P1:1`.')
        path, result = self.run_replay('citation_feedback', generate=self.generate(invalid, corrected))
        self.assertEqual(path.name, '002')
        error = stages.read(path.parent / '001/error.json')
        self.assertEqual(error['kind'], 'output_validation')
        for detail in ('text character 5', 'Evidence:P1:1', 'single-backtick'):
            self.assertIn(detail, self.messages[1][-1]['content'])
        self.assertEqual(result['replay'], corrected)
        self.assertEqual(self.run_replay('citation_feedback', read_only=True)[1], result)
        self.assertEqual(self.called, ['replay', 'replay'])

    def test_no_flip_replay_has_no_model_request_or_prompt_artifacts(self):
        bundle = self.no_flips()
        with patch.object(replay, 'render_prompt', side_effect=AssertionError('Skip has no model prompt')):
            directory, result = self.run_replay('skip', bundle, self.generate())
            self.assertEqual(self.run_replay('skip', bundle, read_only=True)[1], result)
        self.assertFalse(result['replay_called'])
        self.assertEqual(result['knowledge'], [])
        self.assertEqual(result['replay'], {'entries': []})
        for name in ('attempts', 'identity.json', 'base_messages.json'): self.assertFalse((directory / name).exists())
        self.assertEqual(self.called, [])

    def test_skip_can_recover_a_partial_receipt_without_model_call(self):
        bundle = self.no_flips(); real = stages.freeze
        def fail(path, value, **kwargs):
            if path.name == 'result.json': raise KeyboardInterrupt()
            return real(path, value, **kwargs)
        with patch.object(stages, 'freeze', side_effect=fail):
            with self.assertRaises(KeyboardInterrupt): self.run_replay('skip', bundle, self.generate())
        with self.assertRaises(ValueError): self.run_replay('skip', bundle)
        _, result = self.run_replay('skip', bundle, resume=True)
        self.assertFalse(result['replay_called'])
        self.assertEqual(self.called, [])

    def test_skip_and_model_branches_cannot_be_switched_or_forged(self):
        bundle = self.no_flips()
        directory, _ = self.run_replay('skip', bundle)
        with self.assertRaises(ValueError): self.run_replay('skip', generate=self.generate(self.knowledge), resume=True)
        bad = stages.read(directory / 'result.json'); bad['replay_called'] = True
        stages.save(directory / 'result.json', bad)
        with self.assertRaises(ValueError): self.run_replay('skip', bundle, resume=True)
        self.assertEqual(self.called, [])

    def test_interrupted_initial_branch_write_requires_resume(self):
        bundle = self.no_flips(); directory = self.root / 'skip'
        directory.mkdir(); (directory / 'branch.tmp').write_text('{partial')
        with self.assertRaises(ValueError): self.run_replay('skip', bundle)
        with self.assertRaises(ValueError): self.run_replay('skip', bundle, resume=True, read_only=True)
        _, result = self.run_replay('skip', bundle, resume=True)
        self.assertFalse(result['replay_called'])
        self.assertFalse((directory / 'branch.tmp').exists())
        self.assertEqual(self.called, [])

    def test_completed_skip_does_not_repair_missing_evidence(self):
        bundle = self.no_flips(); directory, _ = self.run_replay('skip', bundle)
        (directory / 'input.json').unlink()
        with self.assertRaises(ValueError): self.run_replay('skip', bundle, resume=True)
        self.assertFalse((directory / 'input.json').exists())
        self.assertEqual(self.called, [])

    def test_skip_budget_and_policy_options_are_validated_and_frozen(self):
        bundle = self.no_flips()
        with self.assertRaises(ValueError): self.run_replay('bad', bundle, max_attempts=True)
        self.assertFalse((self.root / 'bad').exists())
        self.run_replay('skip', bundle)
        with self.assertRaises(ValueError): self.run_replay('skip', bundle, max_attempts=5, resume=True)

    def test_new_module_source_failure_is_not_output_feedback(self):
        call = editor.editor_call(self.prepared)
        def generate(*args):
            record = stages.read(self.parent_dir / 'actor/0001/trajectory.json')
            record['execution']['content'] = 'changed source'
            stages.save(self.parent_dir / 'actor/0001/trajectory.json', record)
            self.called.append('editor')
            return {'content': json.dumps(self.edits), 'finish_reason': 'stop'}
        with self.assertRaises((ValueError, stages.Stopped)): self.run_call('bad', call, generate)
        error = stages.read(self.root / 'bad/attempts/001/error.json')
        self.assertEqual(error['kind'], 'technical'); self.assertFalse(error['retryable'])
        self.assertNotIn('diagnostic', error)
        self.assertEqual(self.called, ['editor'])

    def test_mutated_call_input_messages_and_old_versions_fail_before_request(self):
        original = editor.editor_call(self.prepared)
        bads = [replace(original, prompt_version='v29_docvqa_editor_v1'),
                replace(original, contract_version='old')]
        bad = editor.editor_call(self.prepared); bad.messages[0]['content'] = 'forged prompt'; bads.append(bad)
        bad = editor.editor_call(self.prepared); bad.input['effective_plan']['goal'] = 'forged'; bads.append(bad)
        for index, call in enumerate(bads):
            with self.assertRaises(ValueError): self.run_call(f'bad-{index}', call, self.generate(self.edits))
            self.assertFalse((self.root / f'bad-{index}').exists())
        for name in ('gate', 'memory'):
            with self.assertRaises(ValueError):
                stages.run_stage(self.root / name, SimpleNamespace(name=name), call_config=self.calls['editor'], **self.options)
        self.assertEqual(self.called, [])

    def test_multiedit_archive_tampering_is_rejected_without_new_request(self):
        call = editor.editor_call(self.prepared)
        path, _ = self.run_call('editor', call, self.generate(self.edits))
        stages.save(path / 'edits.json', [])
        with self.assertRaises(ValueError): self.run_call('editor', call, self.generate(self.edits), resume=True)
        self.assertEqual(self.called, ['editor'])
