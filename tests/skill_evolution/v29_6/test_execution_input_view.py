"""Request-local losslessness, evidence scope and frozen-journal recovery.

Only synthetic registered archives and authored method outputs are used.
Network and process access are forbidden, including during recovery.
"""
from copy import deepcopy
from dataclasses import replace
import json
from unittest.mock import patch

from src.skill_evolution.v29 import modules as legacy
from src.skill_evolution.v29.benchmarks.docvqa import protocol
from src.skill_evolution.v29_6 import diagnosis, preconditioner, config, stages
from src.skill_evolution.v29_6.facts import build_parent_bundle
from src.skill_evolution.v29_6 import execution_input_view as view
from tests.skill_evolution.v29.test_method import MethodBase, main_example
from .helpers import proposal
from .helpers import decisions, memory_view
from .helpers import offline


class ExecutionInputViewTests(MethodBase):
    def setUp(self):
        super().setUp()
        offline(self)
        self.records = self.parent()
        self.grouped = build_parent_bundle(self.records, 'R01')
        d = diagnosis.diagnosis_call(self.grouped)
        self.diagnosed = d.complete(proposal())
        self.memory = memory_view()
        p = preconditioner.preconditioner_call(self.diagnosed, self.memory)
        self.calls = {'diagnosis': d, 'preconditioner': p}
        self.outputs = {'diagnosis': proposal(),
                        'preconditioner': decisions()}
        self.raw = {'diagnosis': diagnosis.diagnosis_input(self.grouped),
                    'preconditioner': preconditioner.preconditioner_input(self.diagnosed, self.memory)}
        self.options = {'max_attempts': 6, 'max_input_chars': 1000000,
                        'max_message_utf8_bytes': 2000000, 'retry_delay_seconds': 0}
        self.budgets = config.pending_calls()
        for budget in self.budgets.values():
            budget.update(max_tokens=1000, timeout_seconds=1)

    def compact(self, name):
        return json.loads(self.calls[name].messages[1]['content'])

    def run_stage(self, name, directory, **kwargs):
        return stages.run_stage(directory, self.calls[name], call_config=self.budgets[name],
                                **self.options, **kwargs)

    def test_all_three_calls_restore_every_field_and_keep_full_archives(self):
        for name, call in self.calls.items():
            with self.subTest(module=name):
                original = deepcopy(self.raw[name])
                compact = self.compact(name)
                restored = view.restore_model_input(compact, module=name)
                self.assertEqual(restored, original)
                view.validate_model_input(compact, original=original, module=name)
                self.assertEqual(compact['parent'], original['parent'])
                self.assertEqual(set(compact), set(original) | {'shared_initial'})
                self.assertEqual(len(compact['shared_initial']['messages']), 1)
                self.assertLess(len(view.exact(compact)), len(view.exact(original)))
                for full, reduced, recovered in zip(original['runs'], compact['runs'], restored['runs']):
                    self.assertEqual(view.exact(full['initial']['messages']), view.exact(recovered['initial']['messages']))
                    self.assertEqual(view.exact(full['attempts'][0]['request_messages']),
                                     view.exact(recovered['attempts'][0]['request_messages']))
                    self.assertNotIn('request_messages', reduced['attempts'][0])
                    self.assertNotIn('raw_content', reduced['outcome']['answer'])
                    self.assertEqual(reduced['initial']['messages'][1:], full['initial']['messages'][1:])
                saved = call.input
                result = call.complete(self.outputs[name])
                self.assertEqual(saved['facts'], result['facts'])
                self.assertEqual(result['facts']['runs'], self.grouped['facts']['runs'])
                self.assertEqual(self.raw[name], original)
        self.assertEqual(self.compact('preconditioner')['memory'], self.memory)
        self.assertEqual(self.compact('preconditioner')['plan'], self.diagnosed['diagnosis']['plan'])

    def test_exact_text_metadata_message_order_and_empty_response_round_trip(self):
        # Codec edge cases only: these are deliberately not passed off as verified archives.
        for name in self.calls:
            raw = deepcopy(self.raw[name])
            raw['parent'] = '保留\r\n  \t"Parent"\r\n'
            for index, run in enumerate(raw['runs']):
                messages = run['initial']['messages']
                messages[0]['content'] = '完整 system\r\n空格  \t"引号"\n'
                messages[0]['name'] = 'original_system'
                messages[0]['metadata'] = {'nested': [1, None, 'Ω\r\n']}
                messages.insert(1, deepcopy(messages[0]))
                run['attempts'][0]['request_messages'] = deepcopy(messages)
                content = '' if index == 0 else '答案\r\n \t<answer>Ω</answer>\n'
                run['attempts'][0]['assistant']['content'] = content
                run['outcome']['answer']['raw_content'] = content
            before = deepcopy(raw)
            compact = view.model_input(raw, module=name)
            restored = view.restore_model_input(compact, module=name)
            self.assertEqual(restored, before)
            self.assertEqual(raw, before)
            self.assertEqual(len(compact['shared_initial']['messages']), 1)
            for run, expected in zip(restored['runs'], before['runs']):
                self.assertEqual(view.exact(run['initial']['messages']), view.exact(expected['initial']['messages']))
            compact['shared_initial']['messages']['system_1']['metadata']['nested'].append('mutation')
            self.assertEqual(raw, before)

    def test_different_systems_are_never_normalized_or_replaced_by_parent(self):
        for difference in ('line_endings', 'spaces', 'metadata', 'field_order'):
            raw = deepcopy(self.raw['diagnosis'])
            first = raw['runs'][0]['initial']['messages'][0]
            second = raw['runs'][1]['initial']['messages'][0]
            if difference == 'line_endings': second['content'] = first['content'].replace('\n', '\r\n')
            elif difference == 'spaces': second['content'] += ' '
            elif difference == 'metadata': second['metadata'] = {'original': True}
            else: raw['runs'][1]['initial']['messages'][0] = dict(reversed(list(second.items())))
            for run in raw['runs']:
                run['attempts'][0]['request_messages'] = deepcopy(run['initial']['messages'])
            compact = view.model_input(raw, module='diagnosis')
            self.assertEqual(len(compact['shared_initial']['messages']), 2)
            self.assertEqual(view.restore_model_input(compact, module='diagnosis'), raw)
            self.assertEqual(compact['parent'], raw['parent'])

    def test_none_parent_and_single_run_still_retain_complete_system(self):
        raw = deepcopy(self.raw['diagnosis']); raw['parent'] = None; raw['runs'] = raw['runs'][:1]
        compact = view.model_input(raw, module='diagnosis')
        self.assertIsNone(compact['parent'])
        self.assertEqual(compact['shared_initial']['messages']['system_1'], raw['runs'][0]['initial']['messages'][0])
        self.assertEqual(view.restore_model_input(compact, module='diagnosis'), raw)

    def test_duplicate_mismatches_fail_instead_of_discarding_information(self):
        for kind in ('request', 'raw_content', 'missing_request', 'missing_raw', 'context', 'two_rounds', 'missing_round'):
            raw = deepcopy(self.raw['diagnosis']); run = raw['runs'][0]; attempt = run['attempts'][0]
            if kind == 'request': attempt['request_messages'][0]['content'] += ' '
            elif kind == 'raw_content': run['outcome']['answer']['raw_content'] += '\r\n'
            elif kind == 'missing_request': del attempt['request_messages']
            elif kind == 'missing_raw': del run['outcome']['answer']['raw_content']
            elif kind == 'context': attempt['request_context'] = 'unknown'
            elif kind == 'two_rounds': run['attempts'].append(deepcopy(attempt))
            else: run['attempts'] = []
            before = deepcopy(raw)
            with self.subTest(kind=kind), self.assertRaises(ValueError): view.model_input(raw, module='diagnosis')
            self.assertEqual(raw, before)

    def test_malformed_or_noncanonical_compact_views_are_rejected(self):
        for kind in ('format', 'missing', 'unknown', 'extra', 'unused', 'user', 'inline', 'duplicate_request',
                     'duplicate_raw', 'bad_runs', 'bad_messages', 'extra_top', 'bad_pointer', 'bad_table'):
            value = self.compact('diagnosis'); run = value['runs'][0]
            table = value['shared_initial']['messages']
            if kind == 'format': value['shared_initial']['format'] = 'old'
            elif kind == 'missing': del value['shared_initial']
            elif kind == 'unknown': run['initial']['messages'][0]['shared_message'] = 'missing'
            elif kind == 'extra': run['initial']['messages'][0]['role'] = 'system'
            elif kind == 'unused': table['system_2'] = deepcopy(table['system_1'])
            elif kind == 'user': table['system_1']['role'] = 'user'
            elif kind == 'inline': run['initial']['messages'][0] = deepcopy(table['system_1'])
            elif kind == 'duplicate_request': run['attempts'][0]['request_messages'] = []
            elif kind == 'duplicate_raw': run['outcome']['answer']['raw_content'] = ''
            elif kind == 'bad_runs': value['runs'] = [None]
            elif kind == 'bad_messages': run['initial']['messages'] = [None]
            elif kind == 'extra_top': value['unknown'] = True
            elif kind == 'bad_pointer': run['initial']['messages'][0]['shared_message'] = []
            else: table['system_1'] = None
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                view.restore_model_input(value, module='diagnosis')
        with self.assertRaises(ValueError): view.model_input(self.compact('diagnosis'), module='diagnosis')

    def test_preconditioner_shares_only_plan_authorized_runs(self):
        plan = proposal(); plan['plan']['updates'][0]['basis'] = ['P1:1']
        plan['reason'] += ' P2:1 is not an additional Plan source.'
        saved = diagnosis.diagnosis_call(self.grouped).complete(plan)
        compact = preconditioner.model_input(saved, self.memory)
        self.assertEqual([r['ref'] for r in compact['runs']], ['P1'])
        self.assertEqual(view.restore_model_input(compact, module='preconditioner')['runs'],
                         [self.grouped['facts']['runs'][0]])
        self.assertEqual(compact['memory'], self.memory)
        self.assertNotIn('<answer>12 May 2021</answer>', view.exact(compact))
        self.assertEqual(len(saved['facts']['runs']), 2)

    def test_module_validators_compare_against_verified_complete_sources(self):
        validators = {
            'diagnosis': lambda v: diagnosis.validate_model_input(v, saved=self.grouped),
            'preconditioner': lambda v: preconditioner.validate_model_input(v, saved=self.diagnosed, memory=self.memory),
        }
        for name, validate in validators.items():
            validate(self.compact(name))
            for kind in ('parent', 'system', 'response', 'score', 'task'):
                compact = self.compact(name)
                if kind == 'parent': compact['parent'] += ' forged'
                elif kind == 'system': compact['shared_initial']['messages']['system_1']['content'] += ' forged'
                elif kind == 'response': compact['runs'][0]['attempts'][0]['assistant']['content'] += ' forged'
                elif kind == 'score': compact['runs'][0]['outcome']['score']['hard'] = 1
                else: compact['runs'][0]['task_id'] = 'unknown'
                with self.subTest(module=name, kind=kind), self.assertRaises(ValueError): validate(compact)


    def test_prompt_and_input_view_versions_are_explicit(self):
        self.assertEqual(config.execution_input_views(), {name: view.INPUT_VIEW for name in self.calls})
        for name, module in [('diagnosis', diagnosis), ('preconditioner', preconditioner)]:
            prompt = self.calls[name].messages[0]['content']
            for term in (view.INPUT_VIEW, view.FORMAT, 'shared_message', 'request_messages', 'raw_content',
                         'Top-level parent', 'not execution evidence IDs'):
                self.assertIn(term, prompt)
            self.assertIn(protocol.actor_base_protocol(), prompt)
            self.assertIn(protocol.execution_context(protocol.actor_config()), prompt)
            for old in (f'v29_docvqa_{name}_v1', f'v29_1_docvqa_{name}_v1'):
                with self.assertRaises(ValueError): module.render_prompt(protocol.actor_config(), prompt_version=old)
        for name in ('diagnosis', 'preconditioner'):
            with self.assertRaises(ValueError):
                stages._verified_call(replace(self.calls[name], prompt_version=f'v29_2_docvqa_{name}_v1'))

    def test_all_three_recover_completed_response_without_request_and_keep_full_journal(self):
        for name, call in self.calls.items():
            directory = self.root / f'recovery_{name}'; sent = []
            def generate(module, messages, path, cfg):
                sent.append(deepcopy(messages))
                self.assertEqual(messages, call.messages)
                return {'content': json.dumps(self.outputs[module]), 'finish_reason': 'stop'}
            with patch.object(stages, '_parse', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt): self.run_stage(name, directory, generate=generate)
            with patch.object(self.adapter, 'actor_batch', side_effect=AssertionError('No Actor recovery')):
                _, result = self.run_stage(name, directory, resume=True, generate=generate)
            self.assertEqual(len(sent), 1)
            self.assertEqual(stages.read(directory / 'input.json'), call.input)
            self.assertEqual(stages.read(directory / 'base_messages.json'), call.messages)
            self.assertEqual(stages.read(directory / 'identity.json')['input_view'], view.INPUT_VIEW)
            slot = directory / 'attempts/001'
            self.assertEqual(stages.read(slot / 'recovery.json'), {'additional_requests': 0})
            self.assertEqual(stages.read(slot / 'result.json')['facts'], result['facts'])
            self.assertEqual(result['facts'], self.grouped['facts'])
            before = {p: p.read_bytes() for p in directory.rglob('*') if p.is_file()}
            self.run_stage(name, directory, resume=True, read_only=True, generate=generate)
            self.assertEqual(before, {p: p.read_bytes() for p in directory.rglob('*') if p.is_file()})
            self.assertEqual(len(sent), 1)

    def test_resume_rejects_mixed_views_versions_and_forged_shared_references(self):
        for name in self.calls:
            directory = self.root / f'tamper_{name}'; sent = []
            def generate(module, *_):
                sent.append(module)
                return {'content': json.dumps(self.outputs[module]), 'finish_reason': 'stop'}
            self.run_stage(name, directory, generate=generate)
            for kind in ('old_view', 'missing_view', 'old_prompt', 'old_payload', 'shared_system', 'pointer'):
                identity = kind in ('old_view', 'missing_view', 'old_prompt')
                path = directory / ('identity.json' if identity else 'base_messages.json')
                before = path.read_bytes(); value = stages.read(path)
                if kind == 'old_view': value['input_view'] = 'complete_raw_runs_v1'
                elif kind == 'missing_view': del value['input_view']
                elif kind == 'old_prompt': value['prompt'] = f'v29_docvqa_{name}_v1'
                else:
                    compact = json.loads(value[1]['content'])
                    if kind == 'old_payload': compact = self.raw[name]
                    elif kind == 'shared_system': compact['shared_initial']['messages']['system_1']['content'] += ' changed'
                    else: compact['runs'][0]['initial']['messages'][0]['shared_message'] = 'missing'
                    value[1]['content'] = view.exact(compact)
                stages.save(path, value)
                with self.subTest(module=name, kind=kind), self.assertRaises(ValueError):
                    self.run_stage(name, directory, resume=True, generate=generate)
                self.assertEqual(len(sent), 1)
                path.write_bytes(before)

    def test_bounded_correction_keeps_compact_base_input_for_each_module(self):
        for name, call in self.calls.items():
            sent = []
            def generate(module, messages, *_):
                sent.append(deepcopy(messages))
                return {'content': '{}' if len(sent) == 1 else json.dumps(self.outputs[module]), 'finish_reason': 'stop'}
            self.run_stage(name, self.root / f'feedback_{name}', generate=generate)
            self.assertEqual([len(messages) for messages in sent], [2, 4])
            self.assertEqual(sent[0], call.messages)
            self.assertEqual(sent[1][:2], call.messages)
            self.assertEqual(view.restore_model_input(json.loads(sent[1][1]['content']), module=name), self.raw[name])
