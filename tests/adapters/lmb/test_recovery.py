"""Interrupt real native control flow, using synthetic Actors and generations only."""
from dataclasses import replace
import difflib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from skilladam.execution.contracts import GenerationResult, ToolCall
from skilladam.types import UsageRecord
from src.adapters.lmb import skilladam as m
from src.adapters.lmb.recovery import Recovery
from tests.adapters.lmb.test_skilladam import SyntheticDataset
from tests.skill_evolution.v27.support import SKILL, Transport, response


class Interrupted(RuntimeError):
    pass


class Generations:
    def __init__(self):
        self.requests = []
        self.pending_momentum = False
        self.fail_patch = False
        self.revision = 0

    def generate(self, request):
        self.requests.append(request)
        if request.stage == 'momentum_update':
            if self.pending_momentum:
                raise Interrupted('Momentum request has no saved response')
            return GenerationResult('', tool_calls=(ToolCall('report_problem', {
                'label': 'synthetic-condition', 'description': 'Synthetic condition check.',
                'evidence': 'Synthetic fixture only.', 'failure_type': 'condition_miss',
                'inherited_from_iteration': True}),))
        if self.fail_patch:
            raise Interrupted('Patch request has no saved response')
        text = request.messages[-1]['content']
        skill = text.split('# Current Skill\n\n', 1)[1].split('\n\n# Ordered', 1)[0].strip() + '\n'
        candidate = skill + f"Check condition {request.metadata['iteration']}.\n"
        diff = ''.join(difflib.unified_diff(skill.splitlines(True), candidate.splitlines(True),
                                           fromfile='a/SKILL.md', tofile='b/SKILL.md'))
        return GenerationResult(json.dumps({'reasoning': f'Synthetic reasoning {self.revision}', 'patch': diff}))


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, _, _, cls.native, cls.context, _ = m.prepare()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sleep = patch('src.skill_evolution.v27.benchmarks.lmb.actor.time.sleep')
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def fixture(self, name='run', count=10):
        root = self.root / name
        root.mkdir()
        dataset = SyntheticDataset(root, count)
        generation = Generations()
        transport = Transport(fn=lambda messages, folder: response(
            '<answer>A</answer>' if 'validation_candidate' in str(folder) else '<answer>B</answer>'))
        native = replace(self.native, optimization_case_ids=tuple(dataset.splits['train']),
            feedback_loop=replace(self.native.feedback_loop, max_iterations=count // 10, min_iterations=1))

        def runner(cls=m.Runner):
            backend = m.Backend(dataset, transport, generation, self.context, root / 'rollouts', {'fixture': True})
            return cls(config=native, adapter=m.NativeAdapter(root), backend=backend,
                       context=self.context, output_dir=root / 'native')

        def run(*, cls=m.Runner, resume=False):
            return runner(cls).run(cases=m.native_cases(dataset), initial_skill=SKILL, resume=resume)

        return root, dataset, generation, transport, runner, run

    def test_request_and_failed_response_corruption_blocks_all_resume_requests(self):
        from tests.skill_evolution.v27.archive_fixture import interrupted_batch, corruptions, damage, snapshot
        from src.skill_evolution.v27.benchmarks.lmb import adapter as adapter_module
        root,dataset,g,t,_,run=self.fixture()
        ids=list(dataset.rows);t.fn=interrupted_batch(ids[0],ids[-1])
        with self.assertRaises(KeyboardInterrupt):run()
        folder=root/'rollouts/iter_000/training/actor/actor'/m.p.digest(ids[-1])
        self.assertEqual(json.loads((folder/'result.json').read_text())['api_requests'],2)
        before=(t.calls,len(g.requests));t.fn=None
        for name,operation in corruptions():
            with self.subTest(file=name,operation=str(operation)):
                path=folder/name;saved=path.read_bytes();damage(path,operation)
                damaged=snapshot(root)
                with patch.object(adapter_module,'ThreadPoolExecutor',side_effect=AssertionError('Workers started')):
                    with self.assertRaises((ValueError,OSError)):run(resume=True)
                self.assertEqual((t.calls,len(g.requests)),before)
                self.assertEqual(snapshot(root),damaged)
                path.write_bytes(saved)
        run(resume=True)
        self.assertTrue((root/'native/final_skill.md').is_file())
        after=(t.calls,len(g.requests));self.assertGreater(after[0],before[0])
        # The completed training tasks remain cached; only its unfinished task is sent.
        self.assertEqual(t.calls-before[0],21)
        run(resume=True);self.assertEqual((t.calls,len(g.requests)),after)

    def test_first_iteration_gate_interruption_reuses_patch_and_training(self):
        root, _, g, t, _, run = self.fixture()
        class Crash(m.Runner):
            def _evaluate_skill(self, skill, cases, *, stage):
                if stage == 'validation_rollout':
                    raise Interrupted('Before first Gate')
                return super()._evaluate_skill(skill, cases, stage=stage)
        with self.assertRaises(Interrupted):
            run(cls=Crash)
        self.assertEqual(m.read(root / 'native/checkpoint.json')['next_iteration'], 0)
        self.assertEqual((t.calls, len(g.requests)), (10, 1))
        g.revision = 1  # A fresh patch response would differ and conflict with the saved artifact.
        result = run(resume=True)
        self.assertIn('Check condition 0.', result.final_skill)
        self.assertEqual((t.calls, len(g.requests)), (30, 2))
        self.assertEqual([r.stage for r in g.requests], ['iteration_patch', 'momentum_update'])

    def test_second_iteration_candidate_interruption_reuses_all_results(self):
        root, _, g, t, _, run = self.fixture(count=20)
        class Crash(m.Runner):
            def _evaluate_skill(self, skill, cases, *, stage):
                result = super()._evaluate_skill(skill, cases, stage=stage)
                if self._active_iteration == 1 and stage == 'validation_rollout' and self._validation_rollout_counts.get(1, 0) == 1:
                    raise Interrupted('After second candidate archive')
                return result
        with self.assertRaises(Interrupted):
            run(cls=Crash)
        self.assertEqual((t.calls, len(g.requests)), (60, 3))
        patch_file = root / 'native/iterations/iter_001/patch_attempt_01.json'
        before = patch_file.read_bytes()
        g.revision = 1
        result = run(resume=True)
        self.assertIn('Check condition 1.', result.final_skill)
        self.assertEqual((t.calls, len(g.requests)), (60, 4))
        self.assertEqual(patch_file.read_bytes(), before)
        rows = [json.loads(line) for line in (root / 'native/usage.jsonl').read_text().splitlines()]
        self.assertEqual(sum(row['requests'] for row in rows), 60)  # Mock optimizer has no usage records.
        ledger = (root / 'native/usage.jsonl').read_bytes()
        run(resume=True)
        self.assertEqual((root / 'native/usage.jsonl').read_bytes(), ledger)
        self.assertEqual((t.calls, len(g.requests)), (60, 4))

    def test_saved_results_before_completion_receipt_are_reused(self):
        original = Recovery.complete
        scenarios = (
            ('rollouts', 'training', (10, 0)),
            ('generations', 'iteration_patch_01', (10, 1)),
            ('generations', 'momentum_update_00', (30, 2)),
        )
        for kind, stage, expected_before in scenarios:
            with self.subTest(kind=kind, stage=stage):
                root, _, g, t, _, run = self.fixture(stage)
                key = 'iter_000/' + stage

                def interrupt(recovery, receipt_kind, receipt_key, value):
                    if (receipt_kind, receipt_key) == (kind, key):
                        raise Interrupted('Saved result, before completion receipt')
                    return original(recovery, receipt_kind, receipt_key, value)

                with patch.object(Recovery, 'complete', interrupt), self.assertRaises(Interrupted):
                    run()
                self.assertEqual((t.calls, len(g.requests)), expected_before)
                receipt_file = root / 'recovery' / (kind + '.json')
                self.assertIsNone(m.read(receipt_file)[key]['completion'])
                saved_file = (root / 'rollouts' / key / 'actor/records.json' if kind == 'rollouts'
                              else root / 'recovery/generations' / (key + '.json'))
                saved = saved_file.read_bytes()
                g.revision = 99  # Regenerating the patch would produce a different response.
                result = run(resume=True)
                self.assertIn('Check condition 0.', result.final_skill)
                self.assertEqual((t.calls, len(g.requests)), (30, 2))
                self.assertEqual([r.stage for r in g.requests], ['iteration_patch', 'momentum_update'])
                self.assertEqual(saved_file.read_bytes(), saved)
                self.assertEqual(m.read(receipt_file)[key]['completion'], m.p.digest(m.read(saved_file)))
                ledger = (root / 'native/usage.jsonl').read_bytes()
                run(resume=True)
                self.assertEqual((t.calls, len(g.requests)), (30, 2))
                self.assertEqual((root / 'native/usage.jsonl').read_bytes(), ledger)

    def test_accept_then_retain_resume_matches_uninterrupted_state_and_usage(self):
        results = []
        for interrupted in (False, True):
            root, _, g, t, _, run = self.fixture(f'accept_retain_{interrupted}', count=20)
            t.fn = lambda messages, directory: response(
                '<answer>A</answer>' if '/iter_000/validation_candidate/' in str(directory)
                else '<answer>B</answer>')
            generate = g.generate

            def with_usage(request):
                return replace(generate(request), usage=(UsageRecord(
                    input_tokens=31, output_tokens=7, total_tokens=38,
                    reasoning_tokens=3, requests=1),))

            g.generate = with_usage
            if interrupted:
                class Crash(m.Runner):
                    def _evaluate_skill(self, skill, cases, *, stage):
                        result = super()._evaluate_skill(skill, cases, stage=stage)
                        if (self._active_iteration == 1 and stage == 'validation_rollout'
                                and self._validation_rollout_counts.get(1, 0) == 1):
                            raise Interrupted('After second candidate archive')
                        return result

                with self.assertRaises(Interrupted):
                    run(cls=Crash)
                self.assertEqual((t.calls, len(g.requests)), (60, 3))
                g.revision = 99
                result = run(resume=True)
            else:
                result = run()
            ledger_file = root / 'native/usage.jsonl'
            ledger = ledger_file.read_bytes()
            rows = [json.loads(line) for line in ledger.splitlines()]
            iterations = [i.to_dict() for i in result.feedback_loop.iterations]
            self.assertEqual([i['accepted'] for i in iterations], [True, False])
            self.assertIn('Check condition 0.', result.final_skill)
            self.assertNotIn('Check condition 1.', result.final_skill)
            self.assertEqual((t.calls, len(g.requests)), (60, 4))
            self.assertEqual(sum(row['requests'] for row in rows), 64)
            self.assertEqual(sum(row['total_tokens'] for row in rows), 60 * 30 + 4 * 38)
            results.append({'skill': result.final_skill, 'iterations': iterations,
                            'momentum': result.momentum.to_dict(), 'usage': rows})
            resumed = run(resume=True)
            self.assertEqual((t.calls, len(g.requests)), (60, 4))
            self.assertEqual(ledger_file.read_bytes(), ledger)
            self.assertEqual(resumed.final_skill, result.final_skill)
            # Native terminal resume restores problems, but not the in-memory iteration cursor.
            # Full Momentum equality above applies to the interrupted active iteration.
            self.assertEqual(resumed.momentum.to_dict()['problems'], result.momentum.to_dict()['problems'])
            self.assertEqual([i.to_dict() for i in resumed.feedback_loop.iterations], iterations)
        self.assertEqual(results[0], results[1])

    def test_response_saved_before_native_patch_artifact_is_reused(self):
        root, _, g, t, _, run = self.fixture()
        from skilladam.execution.store import RunStore
        original = RunStore.write_json
        def interrupted(store, name, value):
            if str(name).endswith('patch_attempt_01.json'):
                raise Interrupted('Before native patch artifact')
            return original(store, name, value)
        with patch.object(RunStore, 'write_json', interrupted), self.assertRaises(Interrupted):
            run()
        self.assertEqual((t.calls, len(g.requests)), (10, 1))
        g.revision = 1
        run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), (30, 2))

    def test_pending_momentum_recovers_without_repeating_gate(self):
        _, _, g, t, _, run = self.fixture()
        g.pending_momentum = True
        with self.assertRaises(Interrupted):
            run()
        g.pending_momentum = False
        result = run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), (30, 3))
        self.assertIn('synthetic-condition', result.momentum.problems)

    def test_saved_momentum_response_before_checkpoint_update_is_reused(self):
        _, _, g, t, _, run = self.fixture()
        class Crash(m.Runner):
            def _generate_momentum(self, context):
                super()._generate_momentum(context)
                raise Interrupted('After durable response, before native checkpoint')
        with self.assertRaises(Interrupted):
            run(cls=Crash)
        result = run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), (30, 2))
        self.assertIn('synthetic-condition', result.momentum.problems)

    def test_momentum_apply_interruption_keeps_native_checkpoint_semantics(self):
        _, _, g, t, _, run = self.fixture()
        class Crash(m.Runner):
            def _apply_momentum(self, context, generation):
                super()._apply_momentum(context, generation)
                raise Interrupted('After Momentum applied, before checkpoint commit')
        with self.assertRaises(Interrupted):
            run(cls=Crash)
        result = run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), (30, 2))
        self.assertEqual(list(result.momentum.problems), ['synthetic-condition'])

    def test_global_corruption_blocks_pending_momentum_and_terminal_resume(self):
        for terminal in (False, True):
            for damage in ('result', 'response', 'records', 'stage', 'registry'):
                with self.subTest(terminal=terminal, damage=damage):
                    root, _, g, t, _, run = self.fixture(f'{terminal}_{damage}')
                    if terminal:
                        run()
                    else:
                        g.pending_momentum = True
                        with self.assertRaises(Interrupted):
                            run()
                        g.pending_momentum = False
                    stage = root / 'rollouts/iter_000/validation_candidate'
                    if damage == 'stage':
                        shutil.rmtree(stage)
                    elif damage == 'registry':
                        (root / 'recovery/rollouts.json').unlink()
                    elif damage == 'records':
                        (stage / 'actor/records.json').unlink()
                    else:
                        pattern = 'actor/actor/*/result.json' if damage == 'result' else 'actor/actor/*/attempts/*/response.json'
                        next(stage.glob(pattern)).unlink()
                    before = (t.calls, len(g.requests))
                    final = root / 'native/final_skill.md'
                    content = final.read_bytes() if final.exists() else None
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        run(resume=True)
                    self.assertEqual((t.calls, len(g.requests)), before)
                    self.assertEqual(final.read_bytes() if final.exists() else None, content)

    def test_previous_iteration_corruption_blocks_next_iteration(self):
        root, _, g, t, _, run = self.fixture(count=20)
        class Crash(m.Runner):
            def _propose_patch(self, context):
                if context.iteration == 1:
                    raise Interrupted('Before next iteration')
                return super()._propose_patch(context)
        with self.assertRaises(Interrupted):
            run(cls=Crash)
        next((root / 'rollouts/iter_000/training').glob('actor/actor/*/result.json')).unlink()
        before = (t.calls, len(g.requests))
        with self.assertRaises(ValueError):
            run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), before)

    def test_genuinely_interrupted_actor_only_retries_pending_case(self):
        root, dataset, g, t, _, run = self.fixture()
        target = m.p.digest(dataset.splits['train'][-1])
        normal = t.fn
        def interrupt(messages, directory):
            if '/training/' in str(directory) and target in str(directory):
                raise Interrupted('One response missing; other workers complete')
            return normal(messages, directory)
        t.fn = interrupt
        with self.assertRaises(Interrupted):
            run()
        self.assertEqual((t.calls, len(g.requests)), (10, 0))
        completed = list((root / 'rollouts/iter_000/training').glob('actor/actor/*/result.json'))
        self.assertEqual(len(completed), 9)
        before = {str(f): f.read_bytes() for f in completed}
        t.fn = normal
        run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), (31, 2))
        self.assertEqual(before, {str(f): f.read_bytes() for f in completed})

    def test_unknown_optimizer_request_can_resume(self):
        _, _, g, t, _, run = self.fixture()
        g.fail_patch = True
        with self.assertRaises(Interrupted):
            run()
        self.assertEqual((t.calls, len(g.requests)), (10, 1))
        g.fail_patch = False
        run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), (30, 3))

    def test_actor_response_saved_before_result_reuses_response(self):
        _, _, g, t, _, run = self.fixture()
        from src.skill_evolution.v27.benchmarks.lmb import actor
        original = actor.freeze
        def interrupt(path, value, **kwargs):
            if path.name == 'result.json':
                raise Interrupted('Response saved; result not yet committed')
            return original(path, value, **kwargs)
        with patch.object(actor, 'freeze', interrupt), self.assertRaises(Interrupted):
            run()
        self.assertEqual((t.calls, len(g.requests)), (10, 0))
        run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), (30, 2))

    def test_corrupt_completed_actor_blocks_other_pending_tasks(self):
        root, dataset, g, t, _, run = self.fixture()
        target = m.p.digest(dataset.splits['train'][-1])
        normal = t.fn
        def interrupt(messages, directory):
            if '/training/' in str(directory) and target in str(directory):
                raise Interrupted('One pending Actor')
            return normal(messages, directory)
        t.fn = interrupt
        with self.assertRaises(Interrupted):
            run()
        next((root / 'rollouts/iter_000/training').glob('actor/actor/*/result.json')).unlink()
        t.fn = normal
        before = (t.calls, len(g.requests))
        with self.assertRaises(ValueError):
            run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), before)

    def test_bootstrap_interruption_can_resume_without_request(self):
        _, _, g, t, _, run = self.fixture()
        from skilladam.core.feedback_loop import CheckpointStore
        with patch.object(CheckpointStore, 'save_payload', side_effect=Interrupted('Before initial checkpoint')), self.assertRaises(Interrupted):
            run()
        self.assertEqual((t.calls, len(g.requests)), (0, 0))
        run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), (30, 2))

    def test_native_patch_attempts_and_retry_payload_are_preserved(self):
        root, _, g, t, _, run = self.fixture()
        original = g.generate
        def generate(request):
            if request.stage == 'iteration_patch' and request.metadata['patch_attempt'] == 1:
                g.requests.append(request)
                return GenerationResult(json.dumps({'reasoning': 'Synthetic bad patch.',
                    'patch': '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-missing text\n+new text\n'}))
            return original(request)
        g.generate = generate
        class Crash(m.Runner):
            def _evaluate_skill(self, skill, cases, *, stage):
                if stage == 'validation_rollout':
                    raise Interrupted('After native patch retries')
                return super()._evaluate_skill(skill, cases, stage=stage)
        with self.assertRaises(Interrupted):
            run(cls=Crash)
        self.assertEqual([r.metadata.get('patch_attempt') for r in g.requests], [1, 2])
        self.assertIn('# Previous Patch Error', g.requests[1].messages[-1]['content'])
        g.revision = 1
        result = run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), (30, 3))
        self.assertEqual(result.feedback_loop.iterations[0].patch_attempts, 2)

    def test_production_entrypoint_checks_archives_before_requests(self):
        _, dataset, g, t, make_runner, _ = self.fixture()
        cfg = m.read(m.DEFAULT_CONFIG)
        native = make_runner().config
        output = self.root / 'experiments/baselines/lmb_skilladam/frontdoor'
        prepared = (cfg, dataset, SKILL, native, self.context, {'fixture': True})
        with patch.object(m, 'ROOT', self.root.resolve()), patch.object(m, 'prepare', return_value=prepared), \
             patch.object(m, 'generation_transport', return_value=g), patch.object(m, 'ChatTransport', return_value=t), \
             patch('dotenv.load_dotenv'), patch.dict('os.environ', {'OPENAI_API_KEY': 'synthetic'}):
            g.pending_momentum = True
            with self.assertRaises(Interrupted):
                m.run('unused.json', output)
            g.pending_momentum = False
            next((output / 'rollouts/iter_000/training').glob('actor/actor/*/result.json')).unlink()
            before = (t.calls, len(g.requests))
            with self.assertRaises(ValueError):
                m.run('unused.json', output, resume=True)
            self.assertEqual((t.calls, len(g.requests)), before)
            self.assertFalse((output / 'native/final_skill.md').exists())

    def test_missing_completed_optimizer_response_is_not_regenerated(self):
        root, _, g, t, _, run = self.fixture()
        g.pending_momentum = True
        with self.assertRaises(Interrupted):
            run()
        (root / 'recovery/generations/iter_000/iteration_patch_01.json').unlink()
        before = (t.calls, len(g.requests))
        with self.assertRaises(ValueError):
            run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), before)

    def test_first_checkpoint_bootstrap_before_any_request(self):
        root, _, g, t, _, run = self.fixture()
        class Crash(m.Runner):
            def _propose_patch(self, context):
                raise Interrupted('Before first request')
        with self.assertRaises(Interrupted):
            run(cls=Crash)
        self.assertEqual((t.calls, len(g.requests)), (0, 0))
        self.assertEqual(m.read(root / 'native/checkpoint.json')['next_iteration'], 0)
        run(resume=True)
        self.assertEqual((t.calls, len(g.requests)), (30, 2))

    def test_prompt_and_compression_methods_remain_upstream(self):
        from skilladam.methods.skilladam import SkillAdamRunner
        for name in ('_condense', '_propose_patch', '_generate_momentum', '_apply_momentum',
                     '_build_sampler', '_reset_optimizer_context_if_needed'):
            self.assertIs(getattr(m.Runner, name), getattr(SkillAdamRunner, name))
