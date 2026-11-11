"""ALFWorld native-retry preparation: real SDK, mock HTTP, no live tasks/models."""
from copy import deepcopy
from dataclasses import asdict
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from scripts.runs.skilladam.alfworld.native_retry import run_skilladam_alfworld_official_optimizer as app
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from skilladam.execution.contracts import GenerationRequest

EXPERIMENT = ROOT / 'experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/config'


def response(text='summary', finish='stop', tools=None):
    return {'id': 'offline', 'object': 'chat.completion', 'created': 0, 'model': 'offline',
            'choices': [{'index': 0, 'finish_reason': finish,
                         'message': {'role': 'assistant', 'content': text, 'tool_calls': tools}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}


class NativeRetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = app.bridge_module()
        cls.bridge.EXPERIMENT = EXPERIMENT
        cls.actor, cls.cfg = app.read(EXPERIMENT / 'actor.json'), app.read(EXPERIMENT / 'skilladam.json')
        cls.context = app.context_for(cls.bridge, cls.actor, cls.cfg)
        cls.original = app.read(app.SOURCE / 'skilladam.json')
        cls.original_output = resolve_experiment_path(app.read(app.SOURCE / 'source_config.json')['output_root'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)

    def backend(self, handler):
        backend = app.backend_type(self.bridge)(self.actor, self.cfg, self.output,
            api_key='offline-placeholder', http_transport=httpx.MockTransport(handler))
        def close():
            if backend.optimizer:
                backend.optimizer._client.close()
        self.addCleanup(close)
        return backend

    def request(self):
        return GenerationRequest('trajectory_compression', ({'role': 'user', 'content': 'summarize'},), self.context, {})

    def test_only_optimizer_route_and_output_binding_change(self):
        self.assertEqual(app.current_binding(self.cfg), app.desired_config(self.original, EXPERIMENT))
        self.assertEqual(self.cfg['native'], self.original['native'])
        self.assertEqual(self.cfg['python'], self.original['python'])
        expected_actor = app.read(app.SOURCE / 'actor.json')
        expected_actor['workers'] = 10
        self.assertEqual(self.actor, expected_actor)
        self.assertEqual((EXPERIMENT / 'actor.json').read_bytes(), (app.SOURCE / 'actor.json').read_bytes())
        expected_cfg = deepcopy(self.original)
        expected_cfg['optimizer_transport'].update(model='deepseek-flash',
            base_url='https://api.deepseek.com', api_key_env='ALFWORLD_OPTIMIZER_KEY')
        expected_cfg['output_root'] = self.cfg['output_root']
        self.assertEqual(self.cfg, expected_cfg)
        for name in ('initial_skill.md', 'optimization_items.json',
                     'splits/train/items.json', 'splits/val/items.json', 'splits/test/items.json'):
            self.assertEqual((EXPERIMENT / name).read_bytes(), (app.SOURCE / name).read_bytes())
        self.assertFalse(resolve_experiment_path(self.cfg['output_root']).exists())

    def test_sdk_429_recovers_with_same_payload(self):
        calls = []
        def handler(req):
            calls.append(json.loads(req.content))
            return httpx.Response(429, json={'error': {'message': 'offline'}}) if len(calls) == 1 else httpx.Response(200, json=response())
        backend = self.backend(handler)
        with patch('time.sleep'):
            self.assertEqual(backend.generate(self.request()).text, 'summary')
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(len(list(self.output.glob('model_calls/*/http_request_*.json'))), 2)

    def test_sdk_stops_at_three_requests_and_failure_cannot_silently_reset(self):
        calls = []
        def handler(req):
            calls.append(req)
            return httpx.Response(500, json={'error': {'message': 'offline'}})
        backend = self.backend(handler)
        with patch('time.sleep'), self.assertRaises(Exception):
            backend.generate(self.request())
        self.assertEqual(len(calls), 3)
        with self.assertRaisesRegex(ValueError, 'no silent retry reset'):
            backend.generate(self.request())
        self.assertEqual(len(calls), 3)

    def test_sdk_does_not_retry_authentication_error(self):
        calls = []
        def handler(req):
            calls.append(req)
            return httpx.Response(401, json={'error': {'message': 'offline'}})
        with patch('time.sleep'), self.assertRaises(Exception):
            self.backend(handler).generate(self.request())
        self.assertEqual(len(calls), 1)

    def test_truncation_passes_to_native_parser_without_resampling(self):
        calls = []
        def handler(req):
            calls.append(req)
            return httpx.Response(200, json=response('unfinished', 'length'))
        backend = self.backend(handler)
        self.assertEqual(backend.generate(self.request()).text, 'unfinished')
        self.assertEqual(len(calls), 1)

    def test_empty_output_fails_once_without_added_repair(self):
        calls = []
        def handler(req):
            calls.append(req)
            return httpx.Response(200, json=response(''))
        with self.assertRaises(Exception):
            self.backend(handler).generate(self.request())
        self.assertEqual(len(calls), 1)
        self.assertEqual(list(self.output.glob('model_calls/*/success.json')), [])

    def test_invalid_tool_arguments_fail_once_without_added_repair(self):
        calls = []
        def handler(req):
            calls.append(req)
            return httpx.Response(200, json=response(None, 'tool_calls', [{'id': 'x', 'type': 'function',
                'function': {'name': 'record_attempt', 'arguments': '{bad json'}}]))
        with self.assertRaises(Exception):
            self.backend(handler).generate(self.request())
        self.assertEqual(len(calls), 1)

    def test_success_cache_survives_new_backend_without_new_request(self):
        calls = []
        def handler(req):
            calls.append(req)
            return httpx.Response(200, json=response())
        backend = self.backend(handler)
        result = backend.generate(self.request())
        resumed = self.backend(handler)
        self.assertEqual(resumed.generate(self.request()), result)
        self.assertEqual(len(calls), 1)
        self.assertEqual(resumed.new_generations, 0)

    def test_all_69_historical_requests_change_only_model_and_url(self):
        seen = []
        def handler(req):
            seen.append((str(req.url), json.loads(req.content), req.extensions['timeout']))
            return httpx.Response(200, json=response())
        backend = self.backend(handler)
        paths = sorted((self.original_output / 'model_calls').glob('*/request.json'))
        self.assertEqual(len(paths), 69)
        stages = {}
        for path in paths:
            saved = app.read(path)
            body = deepcopy(saved['payload'])
            body.update(body.pop('extra_body', {}))
            body['model'] = 'deepseek-flash'
            backend.iteration = saved['iteration']
            req = GenerationRequest(saved['stage'], tuple(body['messages']), self.context,
                {'tools': body['tools']} if 'tools' in body else {})
            backend.generate(req)
            url, payload, timeout = seen[-1]
            self.assertEqual(payload, body, str(path))
            self.assertEqual(url, 'https://api.deepseek.com/chat/completions')
            self.assertEqual(timeout['connect'], 10)
            self.assertEqual(timeout['read'], 300)
            stages[saved['stage']] = stages.get(saved['stage'], 0) + 1
        self.assertEqual(len(seen), 69)
        self.assertEqual(stages, {'trajectory_compression': 57, 'iteration_patch': 6, 'momentum_update': 6})

    def test_completed_original_native_config_gate_context_and_actor_hooks_match(self):
        from skilladam.methods.skilladam import _profile_gate, _gate_signature
        saved = app.read(self.original_output / 'checkpoint.json')['run_signature']
        self.assertEqual(self.bridge.native_config(self.cfg).to_dict(), saved['post_decision']['run_config'])
        expected_context = deepcopy(saved['post_decision']['backend_context'])
        expected_context['workers'] = 10
        expected_context['model'] = 'deepseek-flash'
        self.assertEqual(asdict(self.context), expected_context)
        gate = _profile_gate(self.bridge.ALFWorldAdapter(EXPERIMENT / 'splits'), 'alfworld', None, 'main-result')
        self.assertEqual(_gate_signature(gate, 'alfworld', None, 'main-result'), saved['gate'])
        self.assertIs(app.backend_type(self.bridge).execute_batch, self.bridge.SharedBackend.execute_batch)

    def test_native_patch_application_keeps_three_attempts_and_feedback(self):
        from skilladam.core.feedback_loop import FeedbackLoop
        contexts = []
        def propose(context):
            contexts.append(context)
            return ('not a diff' if len(contexts) < 3 else
                    '--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-Original\n+Updated\n')
        loop = SimpleNamespace(config=self.bridge.native_config(self.cfg).feedback_loop)
        report, attempts, error = FeedbackLoop._generate_candidate(loop, iteration=0,
            current_skill='Original\n', batch=SimpleNamespace(training_case_ids=('task',)), edit_budget=4, propose_patch=propose)
        self.assertEqual(attempts, 3)
        self.assertFalse(error or report.all_failed)
        self.assertEqual(contexts[0].previous_patch_error, '')
        self.assertTrue(contexts[1].previous_patch_error and contexts[2].previous_patch_error)

    def test_optimizer_credentials_are_separate_from_actor(self):
        import os
        seen = []
        def handler(req):
            seen.append(req)
            return httpx.Response(200, json=response())
        backend = app.backend_type(self.bridge)(self.actor, self.cfg, self.output,
            http_transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-actor-key',
                                    'ALFWORLD_OPTIMIZER_KEY': 'offline-official-key'}):
            backend.generate(self.request())
        self.addCleanup(backend.optimizer._client.close)
        self.assertEqual(seen[0].headers['authorization'], 'Bearer offline-official-key')
        self.assertEqual(str(seen[0].url), 'https://api.deepseek.com/chat/completions')
        self.assertEqual(self.actor['model'], 'deepseek-v4.1-flash')
        self.assertEqual(self.actor['base_url'], 'http://llm-proxy.intra.xiaojukeji.com')

    def test_default_check_cannot_start_or_load_credentials(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
             patch.object(app, 'start', side_effect=AssertionError('training forbidden')), \
             patch('scripts.runs.alfworld.alfworld_aligned_common.configure_runtime', side_effect=AssertionError('credentials forbidden')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            app.main(['--experiment', str(EXPERIMENT)])
        self.assertEqual(json.loads(output.getvalue())['model_requests'], 0)
        self.assertFalse(resolve_experiment_path(self.cfg['output_root']).exists())


if __name__ == '__main__':
    unittest.main()
