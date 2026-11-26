"""SearchQA-specific contracts, exact evidence views and append-only publication."""
from copy import deepcopy
import json
from unittest.mock import patch

from src.skill_evolution.v28.benchmarks.searchqa import scoring
from src.skill_evolution.v28_4 import facts, diagnosis as d, preconditioner as p, editor as e
from src.skill_evolution.v28_4 import replay as r, gate, memory, execution_input_view as view, replay_input_view as rv
from src.skill_evolution.v28_4 import evolution as ev
from tests.skill_evolution.v28.runtime_support import Base, HIDDEN, snapshot
from .support import bind, Generator, no_hashes
from .test_editor import offline


class ContractsTests(Base):
    def setUp(self):
        super().setUp(); offline(self); self.enterContext(no_hashes())
        self.data, self.transport, self.adapter, self.config = bind(self.root, rounds=1, size=3)
        self.skill.write_text(self.config['initial_skill']['text'])
        self.enterContext(self.adapter.using())
        self.generator = Generator()
        folder = self.root / 'parent_runs'
        self.parents = self.adapter.actor_batch(self.data.batches[0], self.skill, folder, {'split': 'train', 'role': 'parent'})
        self.adapter.register_archive(folder)
        self.saved = facts.build_parent_bundle(self.parents, 'R01')
        self.diagnosed = self.complete(d.diagnosis_call(self.saved))

    def complete(self, call):
        output = self.generator(call.name, call.messages, self.root / 'R01/x/attempts/001', self.config['module_calls'][call.name])
        return call.complete_text(output['content'])

    def adjusted(self):
        return self.complete(p.preconditioner_call(self.diagnosed, {'rounds': []}))

    def bundle(self):
        edited = self.complete(e.editor_call(self.adjusted()))
        skill = self.root / 'candidate.md'; skill.write_bytes(edited['candidate_text'].encode())
        folder = self.root / 'candidate_runs'
        candidates = self.adapter.actor_batch(self.data.batches[0], skill, folder, {'split': 'train', 'role': 'candidate'})
        self.adapter.register_archive(folder)
        return r.build_replay_from_editor(edited, self.parents, candidates)

    def test_exact_full_context_and_content_only_shared_view(self):
        for module, call, canonical in (
            ('diagnosis', d.diagnosis_call(self.saved), d.diagnosis_input(self.saved)),
            ('preconditioner', p.preconditioner_call(self.diagnosed, {'rounds': []}), p.preconditioner_input(self.diagnosed, {'rounds': []}))):
            visible = json.loads(call.messages[1]['content'])
            self.assertEqual(view.restore_model_input(visible, module=module), canonical)
            self.assertNotIn(HIDDEN, json.dumps(visible)); self.assertIn('[DOC] Context 0', json.dumps(visible))
            self.assertEqual(len(visible['runs']), 1 if module == 'preconditioner' else 3)
            bad = deepcopy(visible); bad['shared_initial']['messages']['unused'] = {'role': 'system', 'content': 'unused'}
            self.reject(view.restore_model_input, bad, module=module)
        self.assertNotIn('reason', p.preconditioner_input(self.diagnosed, {'rounds': []}))

    def test_no_checks_and_reference_permissions(self):
        call = d.diagnosis_call(self.saved)
        valid = deepcopy(self.diagnosed['diagnosis'])
        for mutate in (lambda x: x['plan'].update(checks=[]),
                       lambda x: x['plan']['updates'][0].update(basis=['P99:1']),
                       lambda x: x.update(reason='Compare P1/Q1'),
                       lambda x: x['plan']['updates'][0].update(text='Compare R03/P1:1'),
                       lambda x: x['plan']['updates'][0].update(text='Use Memory:M1 as evidence')):
            bad = deepcopy(valid); mutate(bad); self.reject(call.complete, bad)
        valid['plan']['updates'][0]['text'] += ' Compare P1/P3 and P1:1/P3:outcome.'
        saved = call.complete(valid)
        self.assertEqual([x['ref'] for x in p.preconditioner_input(saved, {'rounds': []})['runs']], ['P1', 'P3'])

    def test_keep_replace_withdraw_preserve_ids_goal_basis_and_exact_text(self):
        call = p.preconditioner_call(self.diagnosed, {'rounds': []})
        original = self.diagnosed['diagnosis']['plan']
        text = 'When the context distinguishes an entity, preserve its full name.\n  Keep explicit exceptions.\r\n'
        output = {'adjustments': [{'target': 'u2', 'action': 'WITHDRAW', 'text': None, 'reason': 'Redundant.'},
                                  {'target': 'u1', 'action': 'REPLACE', 'text': text, 'reason': 'P1:1 supports this scope.'}]}
        saved = call.complete(output); effective = saved['effective_plan']
        self.assertEqual(effective, {'goal': original['goal'], 'updates': [{**original['updates'][0], 'text': text}]})
        payload = json.loads(e.editor_call(saved).messages[1]['content'])
        self.assertEqual(payload['plan']['updates'], [{'id': 'u1', 'text': text}])
        self.assertEqual(set(payload), {'parent', 'plan'})
        for action, value in (('KEEP', text), ('WITHDRAW', text), ('REPLACE', None), ('REPLACE', ''), ('MODIFY', text)):
            bad = deepcopy(output); bad['adjustments'][1].update(action=action, text=value)
            self.reject(call.complete, bad)
        for target in ('u3', 'u2'):
            bad = deepcopy(output); bad['adjustments'][1]['target'] = target; self.reject(call.complete, bad)
        bad = deepcopy(output); bad['checks'] = []; self.reject(call.complete, bad)

    def test_replay_projection_and_native_float_em(self):
        bundle = self.bundle(); call = r.replay_call(bundle); compact = json.loads(call.messages[1]['content'])
        restored = rv.restore_model_input(compact)
        self.assertEqual(restored, r.replay_input(bundle))
        self.assertEqual(set(compact), {'parent', 'diff', 'plan', 'edits', 'pairs', 'runs', 'shared_initial'})
        self.assertEqual(len(compact['pairs']), 3)
        for pair in compact['pairs']:
            self.assertEqual(set(pair['parent_result']), {'status', 'model_rounds', 'tool_calls', 'api_requests', 'em', 'f1'})
            self.assertIs(type(pair['parent_result']['em']), float)
        self.assertTrue(all(set(x) == {'id', 'text'} for x in compact['plan']['updates']))
        self.assertTrue(all(set(x) == {'update_id', 'patch'} for x in compact['edits']))
        self.assertNotIn(HIDDEN, json.dumps(compact))
        self.assertNotIn('memory', compact)

    def test_replay_exact_coverage_single_container_and_update_permissions(self):
        bundle = self.bundle(); call = r.replay_call(bundle)
        saved = self.complete(call); out = saved['replay']
        mutations = [lambda x: x.update(entries=[]),
            lambda x: x['entries'].append(deepcopy(x['entries'][0])),
            lambda x: x['entries'][0]['knowledge'].pop(),
            lambda x: x['entries'][0]['knowledge'].append(deepcopy(x['entries'][0]['knowledge'][0])),
            lambda x: x['entries'][0]['knowledge'][0].update(update_id='u99'),
            lambda x: x['entries'][0]['knowledge'][0].update(task_id='unknown'),
            lambda x: x['entries'][0]['knowledge'][0].update(revises=[]),
            lambda x: x['entries'][0]['knowledge'][0].update(text='Observe P99:1'),
            lambda x: x['entries'][0]['knowledge'][0].update(text='Observe P2:1')]
        for mutate in mutations:
            bad = deepcopy(out); mutate(bad); self.reject(call.complete, bad)
        for item in out['entries'][0]['knowledge']: item['update_id'] = None
        result = gate.evaluate_gate(call.complete(out))
        self.assertEqual([(x['G'], x['L'], x['gate_decision']) for x in result['decisions']], [(0, 0, 'Defer')] * 2)

    def test_net_positive_mixed_evidence_defers_and_history_is_not_a_vote(self):
        self.generator.attribution = 'conflict'
        receipt = self.complete(r.replay_call(self.bundle()))
        result = gate.evaluate_gate(receipt)
        self.assertEqual([(x['G'], x['L'], x['gate_decision']) for x in result['decisions']], [(2, 1, 'Defer'), (0, 0, 'Defer')])
        self.assertEqual(result['selected_execution_source'], 'parent')
        prepared = memory.prepare_append(ev.EMPTY_MEMORY, replayed=receipt, gate_result=result)
        state = memory.commit_memory(self.root / 'memory', prepared, expected_head=None)
        self.assertEqual(len(state['memory']['rounds'][0]['entries']), 3)
        self.assertEqual(state['head'], '000001')
        before = snapshot(self.root / 'memory')
        self.assertEqual(memory.commit_memory(self.root / 'memory', prepared, expected_head=None), state)
        self.assertEqual(snapshot(self.root / 'memory'), before)
        self.reject(memory.commit_memory, self.root / 'memory', prepared, expected_head='000001')

    def test_memory_load_checks_chain_without_historical_source_access(self):
        receipt = self.complete(r.replay_call(self.bundle())); result = gate.evaluate_gate(receipt)
        prepared = memory.prepare_append(ev.EMPTY_MEMORY, replayed=receipt, gate_result=result)
        root = self.root / 'memory'; expected = memory.commit_memory(root, prepared, expected_head=None)
        with patch.object(memory, '_prepare', side_effect=AssertionError('No historical recomputation')), \
             patch.object(self.adapter, 'source_record', side_effect=AssertionError('No historical Actor access')):
            self.assertEqual(memory.load_memory(root), expected)
        path = root / 'commits/000001.json'; original = path.read_bytes()
        for mutation in (lambda x: x.update(sequence=2),
                         lambda x: x.update(previous_head='000001'),
                         lambda x: x['selection'].update(selected_update_ids=['unknown'])):
            value = json.loads(original); mutation(value); path.write_bytes(memory._bytes(value))
            self.reject(memory.load_memory, root); path.write_bytes(original)
        head = root / 'HEAD.json'; original_head = head.read_bytes(); head.unlink()
        self.reject(memory.load_memory, root); head.write_bytes(original_head)

    def test_current_commit_source_mutation_stops_publication(self):
        receipt = self.complete(r.replay_call(self.bundle())); result = gate.evaluate_gate(receipt)
        prepared = memory.prepare_append(ev.EMPTY_MEMORY, replayed=receipt, gate_result=result)
        root = self.root / 'memory'; original = memory._freeze
        def corrupt(path, data):
            original(path, data)
            if path.parent.name == 'sources': path.write_bytes(path.read_bytes() + b' ')
        with patch.object(memory, '_freeze', side_effect=corrupt):
            self.reject(memory.commit_memory, root, prepared, expected_head=None)
        self.assertIsNone(memory._read_head(root))

    def test_full_batch_validation_rejects_forged_scores(self):
        bundle = self.bundle()
        for value in (True, 0.5, 2):
            bad = deepcopy(bundle); bad['payload']['pairs'][0]['parent_result']['em'] = value
            self.reject(r.replay_call, bad)
        source = self.root / 'parent_runs' / 'actor' / self.adapter.actor_adapter.task_key(self.data.batches[0][0]) / 'trajectory.json'
        source.unlink()
        self.reject(r.replay_call, bundle)

    def test_native_em_and_f1_are_not_interchangeable(self):
        self.assertEqual(scoring.score('<answer>the New York City!</answer>', ['New York City'])[1], {'em': 1.0, 'f1': 1.0})
        self.assertEqual(scoring.score('<answer>City New York</answer>', ['New York City'])[1], {'em': 0.0, 'f1': 1.0})
