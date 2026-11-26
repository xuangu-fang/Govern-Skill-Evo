"""Replay wire-view changes must preserve facts, permissions and durable retries."""
from copy import deepcopy
import json
from unittest.mock import Mock, patch

from . import test_offline as original
from .support import Dataset, Transport, config, replay
from src.skill_evolution.v27 import modules, stages
from src.skill_evolution.v27.config import method_config, validate_config
from src.skill_evolution.v27.benchmark import using_benchmark
from src.skill_evolution.v27.benchmarks.lmb.adapter import LMBAdapter
from src.skill_evolution.v27.benchmarks.lmb import evidence, prompting, protocol as p
from src.skill_evolution.v27.benchmarks.lmb import replay_input_view as view


def restore(value):
    return view.restore_model_input(value)


class ReplayDedupIntegrationTests(original.Base):
    def test_previous_capacity_stress_now_fits_without_changing_limits(self):
        from . import capacity_fixture
        profile = json.loads(capacity_fixture.PROFILE_PATH.read_text())
        profile['stress_content_chars_per_run'] = 16384
        profile_path = self.root/'old_stress_profile.json'
        profile_path.write_text(json.dumps(profile))
        with patch.object(capacity_fixture, 'PROFILE_PATH', profile_path):
            fixture = capacity_fixture.build(self.root/'old_stress', stress=True)
        report = fixture['report']['modules']['replay']
        self.assertTrue(report['fits_frozen_limits'])
        self.assertGreater(report['context_estimate_headroom'], 0)
        wire = json.loads(fixture['calls']['replay'].messages[1]['content'])
        self.assertEqual(len(wire['runs']), 20)
        for run in wire['runs']:
            self.assertEqual(len(run['attempts'][0]['assistant']['content']), 16384)
        self.assertEqual(restore(wire), evidence.model_input(fixture['calls']['replay'].input))

    def stage_arguments(self):
        adapter = LMBAdapter(Dataset(self.root/'data'), Transport(), gate_metric=p.EM_GATE)
        cfg = config(adapter)
        return {'call_config': cfg['module_calls']['replay'], 'max_attempts': 6,
                'max_input_chars': 1000000, 'max_message_utf8_bytes': 2000000}

    def test_only_replay_wire_view_changes_and_bundle_is_immutable(self):
        saved, bundle = self.edited(3)
        before = deepcopy(bundle)
        call = modules.replay_call(bundle)
        wire = json.loads(call.messages[1]['content'])
        self.assertEqual(restore(wire), evidence.model_input(bundle))
        self.assertEqual(bundle, before)
        self.assertEqual(call.input, before)
        self.assertEqual(len(wire['pairs']), 3)
        self.assertEqual(len(wire['runs']), 6)
        for run in call.input['payload']['runs']:
            self.assertEqual(run['attempts'][0]['request_messages'], run['initial']['messages'])
        for run in wire['runs']:
            self.assertNotIn('request_messages', run['attempts'][0])
            self.assertNotIn('raw_content', run['outcome']['answer'])
        for msgs in (modules.diagnosis_call(saved).messages,
                     modules.preconditioner_call(saved, bundle['payload']['memory']).messages):
            payload = json.loads(msgs[1]['content'])
            self.assertNotIn('shared_initial', payload)
            self.assertIn('request_messages', payload['runs'][0]['attempts'][0])

    def test_prompt_and_frozen_method_identify_the_new_view(self):
        self.assertEqual(method_config()['replay_input_view'], view.INPUT_VIEW)
        self.assertEqual(prompting.prompt_identity('replay')['input_view'], view.INPUT_VIEW)
        self.assertEqual(prompting.PROMPT_VERSIONS['replay'], 'v27_lmb_replay_v8')
        for name in ('grouping', 'diagnosis', 'preconditioner', 'editor'):
            self.assertEqual(prompting.PROMPT_VERSIONS[name], f'v27_lmb_{name}_v6')
            self.assertEqual(prompting.prompt_identity(name)['input_view'], p.MODEL_INPUT_VIEW)
        prompt = prompting.render('replay', p.background(p.ACTOR))
        for text in ('shared_initial', 'duplicate request_messages is omitted',
                     'Shared table keys are not evidence IDs', 'initial.task remains supplied'):
            self.assertIn(text, prompt)
        adapter = LMBAdapter(Dataset(self.root/'data'), Transport(), gate_metric=p.EM_GATE)
        with using_benchmark(adapter):
            cfg = config(adapter)
            validate_config(cfg)
            cfg['method']['replay_input_view'] = p.INPUT_VIEW
            with self.assertRaises(ValueError):
                validate_config(cfg)

    def test_output_uses_original_evidence_permissions(self):
        _, bundle = self.edited(2)
        call = modules.replay_call(bundle)
        self.assertEqual(call.complete(replay()), {'replay': replay()})
        for ref in ('system_1', 'pair_1_user_1', 'P99:0'):
            bad = replay()
            bad['entries'][0]['knowledge'][0]['evidence'].append(ref)
            with self.subTest(reference=ref), self.assertRaises(ValueError):
                call.complete(bad)

    def test_invalid_pairs_rejected_before_projection(self):
        _, bundle = self.edited(2)
        for mutate in (lambda b: b['payload']['pairs'][0].update(candidate='Q2'),
                       lambda b: b['payload']['runs'][0]['attempts'][0]['request_messages'][0].update(content='changed')):
            bad = deepcopy(bundle)
            mutate(bad)
            with patch.object(view, 'model_input', wraps=view.model_input) as project:
                with self.assertRaises(ValueError):
                    modules.replay_call(bad)
                project.assert_not_called()

    def test_full_archive_shared_send_and_read_only_resume(self):
        _, bundle = self.edited(2)
        call = modules.replay_call(bundle)
        folder = self.root/'replay'
        generator = Mock(return_value={'content': json.dumps(replay()), 'finish_reason': 'stop'})
        kwargs = self.stage_arguments()
        first = stages.run_stage(folder, call, generate=generator, **kwargs)
        generator.assert_called_once()
        sent = generator.call_args.args[1]
        self.assertEqual(restore(json.loads(sent[1]['content'])), evidence.model_input(bundle))
        self.assertEqual(stages.read(folder/'input.json'), bundle)
        self.assertEqual(stages.read(folder/'attempts/001/messages.json'), sent)
        forbidden = Mock(side_effect=AssertionError('resume must not generate'))
        resumed = stages.run_stage(folder, call, generate=forbidden, resume=True, read_only=True, **kwargs)
        forbidden.assert_not_called()
        self.assertEqual(resumed, first)

    def test_validation_retry_keeps_shared_base_and_budget(self):
        _, bundle = self.edited(2)
        call = modules.replay_call(bundle)
        folder = self.root/'retry'
        generator = Mock(side_effect=[{'content': '{}', 'finish_reason': 'stop'},
                                      {'content': json.dumps(replay()), 'finish_reason': 'stop'}])
        kwargs = self.stage_arguments()
        stages.run_stage(folder, call, generate=generator, **kwargs)
        self.assertEqual(generator.call_count, 2)
        for args in generator.call_args_list:
            self.assertEqual(args.args[1][:2], call.messages)
        self.assertEqual(generator.call_args.args[1][-2]['content'], '{}')
        self.assertEqual(stages.read(folder/'identity.json')['max_attempts'], 6)
        self.assertEqual(len(list((folder/'attempts').iterdir())), 2)
        forbidden = Mock(side_effect=AssertionError('invalid frozen state must not generate'))
        with self.assertRaises(ValueError):
            stages.run_stage(folder, call, generate=forbidden, resume=True, **{**kwargs, 'max_attempts': 5})
        messages = stages.read(folder/'attempts/002/messages.json')
        wire = json.loads(messages[1]['content'])
        wire['shared_initial']['messages']['system_1']['content'] += ' changed'
        messages[1]['content'] = json.dumps(wire)
        stages.save(folder/'attempts/002/messages.json', messages)
        with self.assertRaises(ValueError):
            stages.run_stage(folder, call, generate=forbidden, resume=True, **kwargs)
        forbidden.assert_not_called()
