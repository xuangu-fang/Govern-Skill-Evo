"""v28.1 wiring acceptance. Synthetic replies test contracts, not model quality."""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v27.transport import RequestFailure
from src.skill_evolution.v28 import evolution, evaluation, modules, profiles, stages
from src.skill_evolution.v28.campaign import CampaignAdapter
from src.skill_evolution.v28.config import campaign_config, validate_config
from src.skill_evolution.v28.benchmarks.searchqa import actor, prompting, protocol as p, scoring
from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
from tests.skill_evolution.v28.runtime_support import Base, Transport, response, snapshot
from tests.skill_evolution.v28.campaign_support import CampaignDataset, Generator
from tests.skill_evolution.v28.test_method import diagnosis, keep, unnumbered

DOC = profiles.REVIEWED
CONFIG = p.ROOT / 'experiments/configs/v28_1_searchqa_train600_batch30_20261103.json'


@contextmanager
def no_hashes():
    # A failing stub proves that the exercised v28.1 path does not use digests.
    with ExitStack() as stack:
        for target in ('hashlib.sha256',
                       'src.skill_evolution.v28.benchmarks.searchqa.protocol.digest',
                       'src.skill_evolution.v28.benchmarks.searchqa.protocol.file_digest'):
            stack.enter_context(patch(target, side_effect=AssertionError('v28.1 must not hash')))
        yield


class PlainDataset(CampaignDataset):
    verify_hashes = False
    batch_size = 30

    def snapshot(self):
        return {'dataset_id': 'synthetic-v28.1', 'splits': deepcopy(self.splits),
                'batches': deepcopy(self.batches)}


def bind(*, rounds=2, size=2, test_size=2, accept=True):
    data = PlainDataset(rounds, size, test_size)
    transport = Transport(lambda m, _: response('<answer>New York City</answer>'
        if accept and 'Use the exact entity.' in m[0]['content'] else '<answer>New York</answer>'))
    transport.config = p.actor_config(30)
    adapter = CampaignAdapter(SearchQAActorAdapter(data, transport, profile=profiles.V28_1))
    config = campaign_config(adapter, initial_skill=stages.read(CONFIG)['initial_skill'])
    return data, transport, adapter, config


def fresh(data, transport=None):
    return CampaignAdapter(SearchQAActorAdapter(data, transport, profile=profiles.V28_1))


class OfflineTests(Base):
    def setUp(self):
        super().setUp()
        self.enterContext(no_hashes())

    def test_real_configuration_schedule_and_actual_prompt_dispatch(self):
        data = SearchQADataset(batch_size=30, verify_hashes=False)
        adapter = fresh(data)
        base, config = stages.read(DOC / 'baseline/campaign_config.json'), stages.read(CONFIG)
        expected = deepcopy(base)
        expected['method'].update(version=profiles.V28_1, prompts=profiles.prompt_versions(profiles.V28_1))
        self.assertEqual(expected, config)
        self.assertEqual(len(config['initial_skill']['text']), 104)
        self.assertEqual(config['initial_skill']['text'], (DOC / 'baseline/initial_skill.md').read_text())
        schedule = stages.read(DOC / 'baseline/schedule.json')
        self.assertEqual(data.batches, schedule['optimization_batches'])
        self.assertEqual(data.splits['test'], schedule['test_ids'])
        self.assertEqual([len(data.batches), len(data.batches[0]), len(data.splits['test'])], [20, 30, 1400])
        self.assertFalse(set(data.splits['train']) & set(data.splits['test']))
        with adapter.using():
            validate_config(config)
            for name in profiles.prompt_versions(profiles.V28_1):
                folder = 'prompts' if name in ('diagnosis', 'preconditioner') else 'baseline/prompts'
                self.assertEqual(prompting.render(name, adapter.actor_adapter._actor),
                                 (DOC / folder / f'{name}.md').read_text())
                self.assertEqual(prompting.prompt_identity(name)['prompt_version'], config['method']['prompts'][name])
            for mutate in (lambda c: c['batches'].reverse(), lambda c: c['method']['prompts'].update(diagnosis='old'),
                           lambda c: c['actor'].update(max_tokens=49152), lambda c: c.update(max_attempts=7)):
                bad = deepcopy(config); mutate(bad)
                self.reject(validate_config, bad)
        # Exact Actor messages against the archived templates on every task.
        system = (DOC / 'baseline/actor/actor_system.md').read_text().removesuffix('\n')
        user = (DOC / 'baseline/actor/actor_user.md').read_text().removesuffix('\n')
        skill = config['initial_skill']['text'].strip()
        for tid in data.splits['train'] + data.splits['test']:
            case = data.case(tid)
            expected_messages = [{'role': 'system', 'content': system.format(skill_section=skill + '\n\n')},
                                 {'role': 'user', 'content': user.format(**case.payload)}]
            self.assertEqual(p.messages(case.payload, config['initial_skill']['text']), expected_messages)

    def test_keep_modify_withdraw_conditions_survive_editor_projection(self):
        data, _, adapter, _ = bind(rounds=1)
        root = self.root / 'parents'
        records = adapter.actor_batch(data.batches[0], self.skill, root, {'split': 'train', 'role': 'parent'})
        adapter.register_archive(root)
        with adapter.using():
            call = modules.grouping_call(records, 'R1')
            saved = call.complete({'groups': [{'group_id': 'G1', 'members': ['P1', 'P2'],
                'decision_problem': 'Entity boundary', 'shared_basis': 'P1:1 and P2:1 omit a suffix.',
                'important_differences': []}]})
            proposal = diagnosis(4)
            original = 'When the question explicitly asks for a named location and context distinguishes it, prefer that entity; otherwise keep other interpretations.\n'
            proposal['plan']['updates'][0]['text'] = original
            saved = modules.diagnosis_call(saved).complete(proposal)
            call = modules.preconditioner_call(saved, memory.empty_memory())
            payload = json.loads(call.messages[1]['content'])
            self.assertNotIn('reason', payload)
            self.assertEqual(payload['plan'], proposal['plan'])
            all_kept = call.complete(keep(4))
            self.assertEqual(len(all_kept['effective_plan']['updates']), 4)
            revised = original.replace('prefer that entity', 'prefer that entity only when the passage explicitly supplies its full name')
            result = keep(4)
            result['adjustments'][0].update(focus=['S'], change='Narrow the visible trigger.', to={'patch': unnumbered(original, revised)})
            result['adjustments'][1].update(focus=['D'], change='Withdraw unsupported duplicate.', to=[])
            adjusted = call.complete(result)
            editor = modules.editor_call(adjusted)
            editor_input = json.loads(editor.messages[1]['content'])
            self.assertEqual(set(editor_input), {'parent', 'plan'})
            texts = [u['text'] for u in editor_input['plan']['updates']]
            self.assertEqual(texts, [revised, *[u['text'] for u in proposal['plan']['updates'][2:]]])
            candidate = editor_input['parent'] + '\n' + ''.join(texts) + 'Additional synthetic guidance.\n' * 1000
            saved = editor.complete({'patch': unnumbered(editor_input['parent'], candidate), 'reason': 'Implement the effective updates.'})
            self.assertEqual(saved['candidate_text'], candidate)
            self.assertGreater(len(candidate), 20000)
            # All-withdraw is valid and does not require an Editor call.
            withdrawn = keep(4)
            for item in withdrawn['adjustments']:
                item.update(focus=['D'], change='Withdraw unsupported update.', to=[])
            withdrawn['checks'] = []
            self.assertIsNone(call.complete(withdrawn)['effective_plan'])

    def test_full_chain_gate_memory_and_archive_only_audit(self):
        for accept in (True, False):
            data, transport, adapter, config = bind(accept=accept)
            root = self.root / f'chain_{accept}'; generator = Generator()
            with adapter.using():
                result = evolution.run_campaign(root, config=config, generate=generator)
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(generator.calls, ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'] * 2)
                self.assertEqual(transport.calls, 8)
                self.assertEqual(stages.read(root / 'initial_memory/active.json'), stages.read(DOC / 'baseline/initial_memory_active.json'))
                self.assertEqual(stages.read(root / 'rounds/R01/gate/result.json')['result']['decision'], 'ACCEPT' if accept else 'RETAIN')
                active = adapter.load_memory(root / result['state']['active_memory'])
                self.assertEqual(len(active['entries']), 2)
            before = snapshot(root)
            with fresh(data).using():
                final = evolution.final_parent(root)
                self.assertEqual('Use the exact entity.' in final.read_text(), accept)
            self.assertEqual(snapshot(root), before)

    def test_no_change_at_each_stage_continues(self):
        for branch in ('diagnosis', 'preconditioner', 'editor'):
            _, transport, adapter, config = bind()
            root = self.root / branch; generator = Generator(no_change=branch)
            with adapter.using():
                result = evolution.run_campaign(root, config=config, generate=generator)
                self.assertEqual(result['state'], {'next_round': 3, 'parent': 'initial_skill.md', 'active_memory': 'initial_memory'})
                self.assertEqual(transport.calls, 4)
                self.assertNotIn('replay', generator.calls)

    def test_complete_20_by_30_and_separate_1400_fixed_skill_test(self):
        data, transport, adapter, config = bind(rounds=20, size=30, test_size=1400)
        generator = Generator(no_change='diagnosis'); root = self.root / 'train'
        with adapter.using():
            result = evolution.run_campaign(root, config=config, generate=generator)
            self.assertEqual(result['state']['next_round'], 21)
            final = evolution.final_parent(root)
        self.assertEqual(transport.calls, 600)
        self.assertEqual(len(generator.calls), 40)
        before = snapshot(root)
        result = evaluation.run_evaluation(self.root / 'test', adapter=adapter.actor_adapter, skill_file=final)
        self.assertEqual((result['completed'], transport.calls), (1400, 2000))
        self.assertFalse(result['optimization_updates'])
        self.assertNotIn('skill_sha256', result)
        evaluation.run_evaluation(self.root / 'test', adapter=adapter.actor_adapter, skill_file=final, resume=True)
        self.assertEqual(transport.calls, 2000)
        self.assertEqual(evaluation.report_evaluation(self.root / 'test', adapter=fresh(data).actor_adapter), result)
        self.assertEqual(snapshot(root), before)
        self.assertFalse((self.root / 'test/state.json').exists())

    def test_resume_at_all_stage_and_publication_boundaries(self):
        for point in ('parent_runs', 'grouping', 'diagnosis', 'preconditioner', 'editor', 'candidate_runs',
                      'pairs', 'gate', 'replay', 'memory', 'memory_prepared', 'before_publish', 'after_publish'):
            with self.subTest(point=point):
                data, transport, adapter, config = bind(rounds=1, size=1)
                generator = Generator(); root = self.root / point
                def hook(stage):
                    if stage == point:
                        raise KeyboardInterrupt()
                with adapter.using(), self.assertRaises(KeyboardInterrupt):
                    evolution.run_campaign(root, config=config, generate=generator, hook=hook)
                with fresh(data, transport).using():
                    result = evolution.run_campaign(root, generate=generator, resume=True)
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(transport.calls, 2)
                self.assertEqual(generator.calls, ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'])

    def test_semantic_stop_and_six_method_attempts_do_not_publish_or_resample(self):
        for kind, count in (('semantic', 1), ('replay', 6)):
            _, transport, adapter, config = bind(rounds=1, size=1)
            generator = Generator(semantic_stop=kind == 'semantic', invalid_replay=kind == 'replay')
            root = self.root / kind
            with adapter.using():
                for resume in (False, True):
                    with self.assertRaises((stages.Stopped, ValueError)):
                        evolution.run_campaign(root, config=config, generate=generator, resume=resume)
                self.assertEqual(stages.read(root / 'state.json')['parent'], 'initial_skill.md')
                self.assertEqual(stages.read(root / 'state.json')['active_memory'], 'initial_memory')
            self.assertEqual(generator.calls.count('editor' if kind == 'semantic' else 'replay'), count)
            self.assertEqual(transport.calls, 1 if kind == 'semantic' else 2)

    def test_plain_actor_six_attempts_and_recovery(self):
        data, transport, adapter, _ = bind(rounds=1, size=1)
        case = data.case(data.batches[0][0]); config = transport.metadata()
        def generate(m, slot):
            if slot.name in ('001', '003'):
                raise RequestFailure('ConnectionError')
            return response(None, 'length') if slot.name != '006' else response('wrong answer')
        transport.fn = generate; root = self.root / 'mixed'
        result = actor.execute(case, None, root, transport, verify_hashes=False)
        self.assertEqual((transport.calls, result['api_requests'], result['metrics']['em']), (6, 6, 0))
        self.assertEqual(transport.seen, [transport.seen[0]] * 6)
        self.assertEqual(set(stages.read(root / 'attempts/001/error.json')), {'retryable', 'error', 'status'})
        self.assertEqual(actor.read_completed(case, None, root, config, verify_hashes=False), result)
        transport.fn = lambda m, d: response(None, 'length')
        root = self.root / 'exhausted'; before = transport.calls
        for _ in range(2):
            with self.assertRaises(RequestFailure):
                actor.execute(case, None, root, transport, verify_hashes=False)
        self.assertEqual(transport.calls - before, 6)
        self.assertFalse((root / 'result.json').exists())
        for archived in (True, False):
            root = self.root / f'interrupted_{archived}'; before = transport.calls
            def interrupt(m, slot):
                if archived:
                    stages.save(slot / 'response.json', response())
                raise KeyboardInterrupt()
            transport.fn = interrupt
            with self.assertRaises(KeyboardInterrupt):
                actor.execute(case, None, root, transport, verify_hashes=False)
            transport.fn = None
            result = actor.execute(case, None, root, transport, verify_hashes=False)
            self.assertEqual((transport.calls - before, result['api_requests']), (1, 1) if archived else (2, 2))

    def test_archive_only_restores_batch_and_rejects_missing_response(self):
        data, transport, adapter, _ = bind(rounds=1, size=1)
        root = self.root / 'batch'; role = {'split': 'train', 'role': 'parent'}
        expected = adapter.actor_batch(data.batches[0], self.skill, root, role)
        (root / 'records.json').unlink()
        self.assertEqual(fresh(data).actor_batch(data.batches[0], self.skill, root, role), expected)
        self.assertEqual(transport.calls, 1)
        folder = root / 'actor' / adapter.actor_adapter.task_key(data.batches[0][0])
        (folder / 'attempts/001/response.json').unlink()
        self.reject(fresh(data).actor_batch, data.batches[0], self.skill, root, role)

    def test_gate_uses_only_strict_em_improvement_and_complete_pairs(self):
        ids = ['a', 'b']
        def scores(values):
            return [{'task_id': tid, 'metrics': {'em': em, 'f1': f1}} for tid, (em, f1) in zip(ids, values)]
        parent = scores([(0, .9), (0, .9)])
        candidate = scores([(1, 1), (0, 0)])
        self.assertEqual(scoring.compare_scores(parent, candidate, ids)['decision'], 'ACCEPT')
        self.assertEqual(scoring.compare_scores(parent, scores([(0, 1), (0, 1)]), ids)['decision'], 'RETAIN')
        self.reject(scoring.compare_scores, parent, candidate[:1], ids)

    def test_cli_validate_without_credentials_or_requests(self):
        from src.skill_evolution.v28.cli import main
        with patch('src.skill_evolution.v28.cli.os.environ.get', wraps=os.environ.get) as env, patch('builtins.print'):
            main(['validate', '--config', str(CONFIG)])
            configured = self.root / 'config.json'
            main(['configure', '--profile', profiles.V28_1, '--batch-size', '30',
                  '--initial-skill', stages.read(CONFIG)['initial_skill']['source'], '--output', str(configured)])
            self.assertEqual(stages.read(configured), stages.read(CONFIG))
        self.assertNotIn('OPENAI_API_KEY', [call.args[0] for call in env.call_args_list])

    def test_cli_report_infers_plain_profile_from_test_plan(self):
        from src.skill_evolution.v28.cli import main
        data, _, adapter, _ = bind(rounds=1, size=1, test_size=1)
        root = self.root / 'test'
        expected = evaluation.run_evaluation(root, adapter=adapter.actor_adapter, skill_file=self.skill)
        with patch('src.skill_evolution.v28.benchmarks.searchqa.dataset.SearchQADataset', return_value=data) as factory, \
             patch('builtins.print'):
            main(['report', str(root)])
        factory.assert_called_once_with(None, batch_size=30, verify_hashes=False)
        self.assertEqual(stages.read(root / 'report.json'), expected)
