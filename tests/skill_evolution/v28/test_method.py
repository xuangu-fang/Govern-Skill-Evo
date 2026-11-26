"""Offline five-module integration through real synthetic Actor journals."""
from copy import deepcopy
from contextlib import nullcontext
import json
import re
from unittest.mock import patch

from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v27.contracts.editor import actual_diff
from src.skill_evolution.v28 import modules, replay, validation
from src.skill_evolution.v28.method import SearchQAMethod
from src.skill_evolution.v28.benchmarks.searchqa import actor, facts, evidence, prompting, protocol as p
from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
from src.skill_evolution.v28.storage import read, save
from .runtime_support import Base, Dataset, Transport, response, HIDDEN, SKILL


def unnumbered(old, new):
    return re.sub(r'^@@ .* @@$', '@@', actual_diff(old, new), flags=re.M)


def diagnosis(count=3):
    return {'decision': 'revise', 'reason': 'P1:1 omits part of the entity.',
            'plan': {'goal': 'Answer with the context-supported entity.',
                     'updates': [{'id': f'u{i}', 'text': f'Apply entity check {i}.\n',
                                  'basis': ['G1', 'P1:1']} for i in range(1, count + 1)],
                     'checks': [{'id': 'c1', 'update_ids': ['u1'], 'question': 'Is the entity complete?'}]}}


def keep(count=3):
    return {'adjustments': [{'target': f'u{i}', 'focus': [], 'change': 'KEEP',
                            'reason': '`Evidence:P1:1` shows the observed omission.', 'to': None}
                           for i in range(1, count + 1)], 'checks': None}


def knowledge():
    return {'entries': [{'revises': [], 'knowledge': [
        {'text': 'The joint edit coincided with a complete entity answer in this pair.',
         'evidence': ['diff', 'P1:outcome', 'Q1:outcome']}]}]}


def payload(call):
    return json.loads(call.messages[1]['content'])


class MethodTests(Base):
    def setUp(self):
        super().setUp()
        self.dataset = Dataset(2)
        self.transport = Transport(lambda messages, _: response(
            '<answer>New York City</answer>' if 'Use the exact entity.' in messages[0]['content']
            else '<answer>New York</answer>'))
        self.adapter = SearchQAActorAdapter(self.dataset, self.transport)
        self.tasks = list(self.dataset.rows)
        self.parent_dir, self.candidate_dir = self.root / 'parent', self.root / 'candidate'
        self.candidate_text = SKILL + '\nUse the exact entity.'
        self.candidate_file = self.root / 'candidate.md'
        self.candidate_file.write_text(self.candidate_text)
        self.parents = self.adapter.actor_batch(self.tasks, self.skill, self.parent_dir,
                                               {'split': 'train', 'role': 'parent'})
        self.candidates = self.adapter.actor_batch(self.tasks, self.candidate_file, self.candidate_dir,
                                                  {'split': 'train', 'role': 'candidate'})
        self.method = SearchQAMethod(self.adapter, archives=[self.parent_dir, self.candidate_dir])
        scope = self.method.using()
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.calls = []

    def diagnosed(self, count=3):
        call = modules.grouping_call(self.parents, 'synthetic_round1'); self.calls.append(call)
        saved = call.complete({'groups': [{'group_id': 'G1', 'members': ['P1', 'P2'],
            'decision_problem': 'Entity boundaries', 'shared_basis': 'P1:1 and P2:1 omit the entity suffix.',
            'important_differences': []}]})
        call = modules.diagnosis_call(saved); self.calls.append(call)
        return call.complete(diagnosis(count))

    def edited(self, active_memory=None):
        saved = self.diagnosed()
        call = modules.preconditioner_call(saved, active_memory or memory.empty_memory()); self.calls.append(call)
        saved = call.complete(keep())
        call = modules.editor_call(saved); self.calls.append(call)
        return call.complete({'patch': unnumbered(SKILL, self.candidate_text), 'reason': 'Implement the entity checks.'})

    def bundle(self, active_memory=None, candidates=None):
        saved = self.edited(active_memory)
        return evidence.build_replay_from_editor(saved, self.root / 'editor', self.parents,
            self.candidates if candidates is None else candidates, memory=active_memory)

    def historical_bundle(self):
        root = self.root / 'replay_history'
        self.method.commit_memory(root, context_id='R1', context=self.bundle(), result=knowledge())
        return self.bundle(self.method.load_memory(root))

    def test_grouping_and_bundle_reuse_without_changing_evidence(self):
        saved = self.edited()
        before = deepcopy(saved)
        actions = [lambda: modules.grouping_call(self.parents, 'R1'),
                   lambda: evidence.build_replay_from_editor(saved, self.root / 'editor', self.parents, self.candidates)]
        for action, uncached_count, cached_count, batches in zip(actions, (12, 18), (2, 4), (1, 2)):
            with patch.object(validation, 'operation', side_effect=lambda _: nullcontext()), \
                 patch.object(actor, 'read_completed', wraps=actor.read_completed) as completed:
                baseline = action()
                self.assertEqual(completed.call_count, uncached_count)
            with patch.object(actor, 'read_completed', wraps=actor.read_completed) as completed, \
                 patch.object(self.adapter, '_signature', wraps=self.adapter._signature) as signatures:
                for _ in range(2):
                    completed.reset_mock(); signatures.reset_mock()
                    result = action()
                    self.assertEqual(completed.call_count, cached_count)
                    self.assertEqual(signatures.call_count, batches)
                    self.assertIsNone(validation.current())
                    if isinstance(result, modules.Call):
                        self.assertEqual(result.messages, baseline.messages)
                        self.assertEqual(result.input, baseline.input)
                    else:
                        self.assertEqual(result, baseline)
        self.assertEqual(saved, before)

    def test_grouping_and_bundle_reuse_existing_outer_scope(self):
        saved = self.edited()
        with patch.object(actor, 'read_completed', wraps=actor.read_completed) as completed:
            with validation.operation(self.adapter) as outer:
                modules.grouping_call(self.parents, 'R1')
                evidence.build_replay_from_editor(saved, self.root / 'editor', self.parents, self.candidates)
                self.assertIs(validation.current(), outer)
                self.assertEqual(completed.call_count, 4)
        self.assertIsNone(validation.current())

    def test_grouping_and_bundle_reject_post_validation_archive_changes(self):
        saved = self.edited()
        path = self.parent_dir / 'actor' / p.digest(self.tasks[0]) / 'attempts/001/response.json'
        original = path.read_bytes()
        for target, name, action in (
            (prompting, 'grouping_messages', lambda: modules.grouping_call(self.parents, 'R1')),
            (evidence, 'validate_payload', lambda: evidence.build_replay_from_editor(
                saved, self.root / 'editor', self.parents, self.candidates)),
        ):
            function = getattr(target, name)
            def mutate(*args, **kwargs):
                result = function(*args, **kwargs)
                path.write_bytes(original + b' ')
                return result
            try:
                with patch.object(target, name, side_effect=mutate):
                    self.reject(action)
                self.assertIsNone(validation.current())
            finally:
                path.write_bytes(original)

    def test_grouping_and_bundle_invalid_inputs_release_scope(self):
        saved = self.edited()
        self.reject(modules.grouping_call, self.parents[:1], 'R1')
        self.assertIsNone(validation.current())
        self.reject(evidence.build_replay_from_editor, saved, self.root / 'editor', self.parents, self.candidates[:1])
        self.assertIsNone(validation.current())

    def test_replay_scopes_reuse_each_batch_and_expire_between_local_steps(self):
        bundle = self.historical_bundle()
        with patch.object(p, '_implementation_identity', wraps=p._implementation_identity) as identity, \
             patch.object(self.adapter, '_signature', wraps=self.adapter._signature) as signature, \
             patch.object(actor, 'read_completed', wraps=actor.read_completed) as completed:
            call = modules.replay_call(bundle)
            self.assertEqual((identity.call_count, signature.call_count, completed.call_count), (1, 2, 4))
            self.assertIsNone(validation.current())
            for _ in range(2):
                identity.reset_mock(); signature.reset_mock(); completed.reset_mock()
                self.assertEqual(call.complete(knowledge()), {'replay': knowledge()})
                self.assertEqual((identity.call_count, signature.call_count, completed.call_count), (1, 2, 2))
                self.assertIsNone(validation.current())

    def test_replay_revalidates_history_after_model_wait(self):
        call = modules.replay_call(self.historical_bundle())
        path = self.parent_dir / 'actor' / p.digest(self.tasks[0]) / 'attempts/001/response.json'
        raw = read(path); raw['choices'][0]['message']['content'] = 'changed during model wait'
        save(path, raw)
        self.reject(call.complete, knowledge())
        self.assertIsNone(validation.current())

    def test_replay_local_scopes_reject_mutations_after_validation(self):
        bundle = self.historical_bundle()
        path = self.parent_dir / 'actor' / p.digest(self.tasks[0]) / 'attempts/001/response.json'
        original = path.read_bytes()
        call = modules.replay_call(bundle)
        for target, name, action in ((prompting, 'replay_messages', lambda: modules.replay_call(bundle)),
                                     (replay, 'validate_result', lambda: call.complete(knowledge()))):
            function = getattr(target, name)
            def mutate(*args, **kwargs):
                result = function(*args, **kwargs)
                path.write_bytes(original + b' ')
                return result
            try:
                with patch.object(target, name, side_effect=mutate):
                    self.reject(action)
                self.assertIsNone(validation.current())
            finally:
                path.write_bytes(original)

    def test_replay_invalid_output_releases_scope(self):
        call = modules.replay_call(self.historical_bundle())
        self.reject(call.complete, {'entries': 'invalid'})
        self.assertIsNone(validation.current())
        self.assertEqual(call.complete(knowledge()), {'replay': knowledge()})

    def test_five_module_chain_views_and_no_update_cap(self):
        bundle = self.bundle()
        call = modules.replay_call(bundle); self.calls.append(call)
        self.assertEqual(call.complete(knowledge()), {'replay': knowledge()})
        expected = [set(x.split()) for x in ('parent runs', 'parent runs grouping',
                    'parent plan runs memory', 'parent plan', 'parent diff plan pairs runs memory shared_initial')]
        for call, keys in zip(self.calls, expected):
            self.assertEqual(set(payload(call)), keys)
            self.assertNotIn(HIDDEN, json.dumps(call.messages))
            self.assertNotIn('reasoning_content', json.dumps(payload(call)))
        self.assertEqual([c.name for c in self.calls], list(prompting.PROMPT_VERSIONS))
        pre, editor, replay_view = map(payload, self.calls[2:])
        self.assertEqual([r['ref'] for r in pre['runs']], ['P1'])  # G1 also includes P2; no expansion.
        self.assertEqual(len(editor['plan']['updates']), 3)
        self.assertEqual(set(pre['memory']), {'format', 'entries'})
        self.assertEqual(set(replay_view['memory']), {'format', 'entries'})
        self.assertEqual([r['ref'] for r in replay_view['runs']], ['P1', 'Q1', 'P2', 'Q2'])
        self.assertEqual(set(replay_view['plan']['updates'][0]), {'id', 'text'})
        self.assertNotIn('gate', replay_view)
        self.assertNotIn('reference_answers', json.dumps(editor))
        self.assertEqual(modules.REVIEW_POLICY, 'disabled_v1')
        self.reject(prompting.render, 'verifier', p.ACTOR)

    def test_facts_keep_full_text_and_gold_only_in_outcome(self):
        saved = facts.build_facts(self.parents)
        run = saved['facts']['runs'][0]
        self.assertEqual(run['initial']['task'], self.dataset.case(self.tasks[0]).payload)
        self.assertEqual(run['initial']['messages'], self.parents[0]['execution']['initial_messages'])
        self.assertEqual(run['attempts'][0]['request_messages'], run['initial']['messages'])
        self.assertEqual(run['outcome']['score'], {'em': 0.0, 'f1': 0.8})
        self.assertEqual(run['outcome']['reference_answers'], ['New York City'])
        self.assertNotIn('reference_answers', json.dumps(run['initial']))
        self.assertNotIn('New York City', json.dumps(run['initial']['messages']))
        self.assertNotIn('usage_records', json.dumps(run))
        self.assertEqual(facts.run_references(run), {'P1', 'P1:0', 'P1:1', 'P1:outcome'})

    def test_failed_attempts_never_become_visible_rounds(self):
        transport = Transport(lambda _, slot: response('FAILED_ATTEMPT_SENTINEL', 'length')
                              if slot.name < '006' else response('<answer>New York</answer>'))
        adapter = SearchQAActorAdapter(self.dataset, transport)
        directory = self.root / 'retried'
        records = adapter.actor_batch(self.tasks, self.skill, directory, {'split': 'train', 'role': 'parent'})
        with SearchQAMethod(adapter, archives=[directory]).using():
            call = modules.grouping_call(records, 'retried_round')
            view = payload(call)
            self.assertNotIn('FAILED_ATTEMPT_SENTINEL', json.dumps(view))
            self.assertNotIn(HIDDEN, json.dumps(view))
            for run in view['runs']:
                self.assertEqual(len(run['attempts']), 1)
                self.assertEqual(run['outcome']['api_requests'], 6)
                self.assertEqual(run['outcome']['model_rounds'], 1)

    def test_full_context_whitespace_braces_and_multiple_gold_preserved(self):
        dataset = Dataset(1)
        row = dataset.rows[self.tasks[0]]
        row['context'] = '  {literal}\\n' + '原文\n' * 3000 + '\nEND_SENTINEL  '
        row['answers'] = ['New York City', 'NYC']
        adapter = SearchQAActorAdapter(dataset, Transport())
        directory = self.root / 'long_context'
        records = adapter.actor_batch([self.tasks[0]], self.skill, directory, {'split': 'train', 'role': 'parent'})
        with SearchQAMethod(adapter, archives=[directory]).using():
            run = facts.build_facts(records)['facts']['runs'][0]
            self.assertEqual(run['initial']['task']['context'], row['context'])
            self.assertIn(row['context'], run['initial']['messages'][1]['content'])
            self.assertEqual(run['outcome']['reference_answers'], row['answers'])

    def test_fact_tampering_and_parent_lineage_rejected(self):
        saved = facts.build_facts(self.parents)
        changes = [lambda r: r['outcome']['score'].update(em=1.0),
                   lambda r: r['outcome'].update(reference_answers=['New York']),
                   lambda r: r['attempts'][0]['assistant'].update(content='invented'),
                   lambda r: r['initial']['task'].update(context='truncated'),
                   lambda r: r.update(run_id='unknown'),
                   lambda r: r['outcome'].update(hidden='extra')]
        for change in changes:
            with self.subTest(change=change):
                run = deepcopy(saved['facts']['runs'][0]); change(run)
                self.reject(facts.validate_run, run)
        saved['facts']['parent'] = 'Changed Parent'
        self.reject(prompting.grouping_messages, saved)
        self.reject(facts.build_facts, self.parents[:1])
        self.reject(modules.grouping_call, self.candidates, 'wrong_role')

    def test_grouping_coverage_and_direct_evidence(self):
        call = modules.grouping_call(self.parents, 'r1')
        good = {'groups': [{'group_id': 'G1', 'members': ['P1', 'P2'], 'decision_problem': 'Entity',
                           'shared_basis': 'P1:1 P2:1', 'important_differences': []}]}
        call.complete(good)
        for mutate in (lambda g: g.update(members=['P1']), lambda g: g.update(shared_basis='P1:0 P2:outcome'),
                       lambda g: g.update(shared_basis='P1:1 P2:1 Q1:1')):
            bad = deepcopy(good); mutate(bad['groups'][0]); self.reject(call.complete, bad)

    def test_diagnosis_unknown_references_and_no_change(self):
        saved = self.diagnosed()
        call = modules.diagnosis_call(saved)
        self.assertIsNone(call.complete({'decision': 'no_change', 'reason': 'No justified change.', 'plan': None})['diagnosis']['plan'])
        bad = diagnosis(); bad['plan']['updates'][0]['basis'] = ['G1']
        self.reject(call.complete, bad)
        bad = diagnosis(); bad['plan']['updates'][0]['basis'] = ['P1:2']
        self.reject(call.complete, bad)
        bad = diagnosis(); bad['reason'] = 'Q7:1 justifies this.'
        self.reject(call.complete, bad)

    def test_preconditioner_keep_modify_withdraw_and_checks(self):
        saved = self.diagnosed()
        call = modules.preconditioner_call(saved, memory.empty_memory())
        self.assertEqual(call.complete(keep())['effective_plan'], saved['diagnosis']['plan'])
        result = keep()
        result['adjustments'][0].update(focus=['S'], change='Narrow the entity check.',
            to={'patch': unnumbered(diagnosis()['plan']['updates'][0]['text'], 'Check the requested entity.\n')})
        effective = call.complete(result)['effective_plan']
        self.assertEqual(effective['updates'][0]['text'], 'Check the requested entity.\n')
        self.assertEqual(effective['updates'][0]['basis'], ['G1', 'P1:1'])
        result = keep()
        for adjustment in result['adjustments']:
            adjustment.update(focus=['D'], change='Withdraw this instruction.', to=[])
        self.reject(call.complete, result)  # Existing Check would refer to removed u1.
        result['checks'] = []
        stopped = call.complete(result)
        self.assertIsNone(stopped['effective_plan'])
        self.reject(modules.editor_call, stopped)

    def test_preconditioner_rejects_scope_expansion(self):
        call = modules.preconditioner_call(self.diagnosed(), memory.empty_memory())
        for mutate in (lambda x: x['adjustments'][0].update(target='u4'),
                       lambda x: x['adjustments'][0].update(reason='`Evidence:P2:1` was not directly supplied.'),
                       lambda x: x['adjustments'][0].update(reason='`Evidence:R0/P1:1` supports this.'),
                       lambda x: x['adjustments'][0].update(focus=['S']),
                       lambda x: x.update(goal='new goal')):
            bad = keep(); mutate(bad); self.reject(call.complete, bad)

    def test_editor_exact_patch_stops_and_actual_diff(self):
        saved = modules.preconditioner_call(self.diagnosed(), memory.empty_memory()).complete(keep())
        call = modules.editor_call(saved)
        for value, status in [('', 'no_change'), (None, 'needs_revision')]:
            stopped = call.complete({'patch': value, 'reason': 'No faithful change.'})
            self.assertEqual(stopped['editor_status'], status)
            self.reject(evidence.build_replay_from_editor, stopped, self.root, self.parents, self.candidates)
        self.reject(call.complete, {'patch': actual_diff(SKILL, self.candidate_text), 'reason': 'Numbered patch.'})
        self.reject(call.complete, {'patch': unnumbered('wrong source', 'new text'), 'reason': 'Wrong source.'})
        edited = call.complete({'patch': unnumbered(SKILL, self.candidate_text), 'reason': 'Exact edit.'})
        self.assertIn('@@ -', edited['actual_diff'])
        self.assertEqual(set(modules.output_files(call, edited, edited['editor'])), {'patch.diff', 'candidate.md', 'actual.diff'})

    def test_replay_pair_and_audit_tampering(self):
        bundle = self.bundle()
        for mutate in (lambda x: x['payload']['pairs'][0].update(candidate='Q2'),
                       lambda x: x['payload']['runs'][1]['outcome']['score'].update(f1=0.2),
                       lambda x: x['payload'].update(gate={'decision': 'ACCEPT'}),
                       lambda x: x.update(candidate='different Skill'),
                       lambda x: x['pair_audit'][0].update(verified=False),
                       lambda x: x['audit']['parent_records'][0]['provenance'].update(scorer='different')):
            bad = deepcopy(bundle); mutate(bad); self.reject(modules.replay_call, bad)
        self.reject(evidence.build_replay_from_editor, self.edited(), self.root, self.parents, self.candidates[:1])

    def test_shared_replay_stage_persists_full_input_and_resumes_without_generation(self):
        from src.skill_evolution.v28 import stages
        from src.skill_evolution.v28.campaign import CampaignAdapter
        from .campaign_support import bind
        bundle = self.bundle(); before = deepcopy(bundle)
        bound = CampaignAdapter(self.adapter)
        for archive in (self.parent_dir, self.candidate_dir): bound.register_archive(archive)
        scope = bound.using(); scope.__enter__(); self.addCleanup(scope.__exit__, None, None, None)
        call = modules.replay_call(bundle)
        self.assertEqual(call.input, before)
        self.assertEqual(bundle, before)
        self.assertIn('shared_initial', payload(call))
        self.assertNotIn('request_messages', payload(call)['runs'][0]['attempts'][0])
        _, _, _, config = bind(rounds=1, batch_size=1)
        options = dict(call_config=config['module_calls']['replay'], max_attempts=6,
                       max_input_chars=1000000, max_message_utf8_bytes=2000000)
        seen = []
        def generate(name, messages, directory, settings):
            seen.append(deepcopy(messages))
            result = knowledge()
            if len(seen) == 1:
                result['entries'][0]['knowledge'][0]['evidence'] = ['diff', 'pair_1_user_1']
            return {'content': json.dumps(result), 'finish_reason': 'stop'}
        root = self.root / 'replay_stage'
        selected, result = stages.run_stage(root, call, generate=generate, **options)
        self.assertEqual(selected.name, '002')
        self.assertEqual(result, {'replay': knowledge()})
        self.assertEqual(stages.read(root / 'input.json'), before)
        self.assertEqual(stages.read(root / 'base_messages.json'), call.messages)
        self.assertEqual(seen[0], call.messages)
        self.assertEqual(seen[1][:2], call.messages)
        stages.run_stage(root, call, resume=True, read_only=True, **options)
        self.assertEqual(len(seen), 2)
        old_identity = prompting.prompt_identity('replay')
        old_identity['prompt_version'] = 'v28_searchqa_replay_v1'
        with patch.object(prompting, 'prompt_identity', return_value=old_identity):
            self.reject(stages.run_stage, root, call, resume=True, read_only=True, **options)

    def test_replay_knowledge_contract_and_exact_refs(self):
        call = modules.replay_call(self.bundle())
        self.assertEqual(call.complete({'entries': []}), {'replay': {'entries': []}})
        for refs in (['diff'], ['P1:outcome'], ['diff', 'Q9:1'], ['diff', 'Q1:1_t1'],
                     ['diff', 'pair_1_user_1'], ['diff', 'system_1']):
            bad = knowledge(); bad['entries'][0]['knowledge'][0]['evidence'] = refs
            self.reject(call.complete, bad)
        bad = knowledge(); bad['entries'][0]['knowledge'][0]['id'] = 'k1'; self.reject(call.complete, bad)
        union = {'entries': [{'revises': [], 'knowledge': [
            {'text': 'Edit.', 'evidence': ['diff']}, {'text': 'Observed content.', 'evidence': ['Q1:1']}]}]}
        call.complete(union)

    def test_memory_commit_recovery_whole_entry_revision_and_history_scope(self):
        bundle = self.bundle(); root = self.root / 'memory'
        first = self.method.commit_memory(root, context_id='R1', context=bundle, result=knowledge())
        self.assertEqual(first, self.method.commit_memory(root, context_id='R1', context=bundle, result=knowledge()))
        restored = SearchQAMethod(SearchQAActorAdapter(self.dataset), archives=[self.parent_dir, self.candidate_dir])
        calls = self.transport.calls
        with restored.using():
            active = restored.load_memory(root)
            self.assertEqual(active['entries'][0]['id'], 'M1')
            next_bundle = self.bundle(active)
            call = modules.replay_call(next_bundle)
            view = payload(call)
            self.assertNotIn('sources', view['memory'])
            self.assertIn('R1/Q1:outcome', json.dumps(view['memory']))
            bad = knowledge(); bad['entries'][0]['knowledge'][0]['evidence'] = ['diff', 'R1/Q1:1']
            self.reject(call.complete, bad)  # Same archived run, not an exposed historical reference.
            bad = knowledge(); bad['entries'][0]['knowledge'][0]['text'] = 'R1/Q1:1 establishes this.'
            self.reject(call.complete, bad)
            result = knowledge(); result['entries'][0]['revises'] = ['M1']
            result['entries'][0]['knowledge'][0]['evidence'] = ['diff', 'R1/Q1:outcome']
            restored.commit_memory(root, context_id='R2', context=next_bundle, result=result)
            self.assertEqual([e['id'] for e in restored.load_memory(root)['entries']], ['M2'])
            self.assertTrue((root / 'archive/R1.json').exists())
        self.assertEqual(calls, self.transport.calls)

    def test_memory_rejects_forged_archive(self):
        bundle = self.bundle(); root = self.root / 'memory'
        self.method.commit_memory(root, context_id='R1', context=bundle, result=knowledge())
        archived = read(root / 'archive/R1.json')
        archived['context']['audit']['candidate_records'][0]['execution']['content'] = 'forged'
        save(root / 'archive/R1.json', archived)
        self.reject(self.method.load_memory, root)

    def test_retain_gate_still_allows_replay_memory(self):
        other = SearchQAActorAdapter(self.dataset, Transport(lambda *_: response('<answer>New York</answer>')))
        directory = self.root / 'retained_candidate'
        candidates = other.actor_batch(self.tasks, self.candidate_file, directory, {'split': 'train', 'role': 'candidate'})
        with SearchQAMethod(other, archives=[self.parent_dir, directory]).using() as method:
            gate = other.build_gate(self.parents, candidates, self.tasks, parent_skill=SKILL,
                candidate_skill=self.candidate_text, parent_directory=self.parent_dir, candidate_directory=directory)
            self.assertEqual(gate['result']['decision'], 'RETAIN')
            bundle = self.bundle(candidates=candidates)
            result = modules.replay_call(bundle).complete(knowledge())['replay']
            method.commit_memory(self.root / 'retained_memory', context_id='retained', context=bundle, result=result)
            self.assertEqual(len(method.load_memory(self.root / 'retained_memory')['entries']), 1)

    def test_original_archive_change_rejected_before_method_generation(self):
        folder = self.parent_dir / 'actor' / p.digest(self.tasks[0])
        (folder / 'trajectory.json').unlink()
        self.reject(modules.grouping_call, self.parents, 'r1')

    def test_test_split_and_unregistered_archives_rejected(self):
        test_adapter = SearchQAActorAdapter(Dataset(1, 'test'), Transport())
        root = self.root / 'test'
        test_adapter.actor_batch([self.tasks[0]], self.skill, root, {'split': 'test', 'role': 'evaluation'}, final=True)
        self.reject(SearchQAMethod, test_adapter, archives=[root])
        with SearchQAMethod(self.adapter, archives=[]).using():
            self.reject(facts.build_facts, self.parents)

    def test_prompt_bytes_versions_and_no_v25_2_additions(self):
        approved = p.ROOT / 'docs/methods/v28/five_module_draft_20261101/prompts'
        for name, version in prompting.PROMPT_VERSIONS.items():
            text = prompting.render(name, p.ACTOR)
            original = (approved / f'{name}.md').read_text()
            if name == 'replay':
                # Only the two input-description sections change; learning rules stay exact.
                old_sections, sections = original.split('\n## '), text.split('\n## ')
                self.assertEqual(len(sections), len(old_sections))
                for old, new in zip(old_sections, sections):
                    if old.startswith(('SearchQA execution and evidence boundary\n',
                                       'Establish intervention and verified comparisons\n')):
                        continue
                    self.assertEqual(old, new)
                self.assertIn('shared_initial', text)
                self.assertIn('duplicate request_messages is omitted', text)
            else:
                self.assertEqual(text, original)
            self.assertEqual(prompting.prompt_identity(name)['prompt_version'], version)
            self.assertIn(p.actor_base_protocol(), text)
            self.assertIn(p.execution_context(p.ACTOR), text)
        self.assertEqual(len(diagnosis()['plan']['updates']), 3)
        self.assertNotIn('at most two', prompting.render('diagnosis', p.ACTOR).lower())
        with patch.object(p, 'file_digest', return_value='tampered'):
            self.assertEqual(p.implementation_identity(), {
                'prompt': {'profile': p.PROMPT_PROFILE}, 'scorer': p.SCORER_PROFILE, 'gate': p.GATE_PROFILE})
