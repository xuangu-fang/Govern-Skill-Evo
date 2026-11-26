"""Offline contract acceptance using completed, synthetic Actor archives only."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v27.memory_view import knowledge_only
from src.skill_evolution.v29 import modules
from src.skill_evolution.v29.method import DocVQAMethod
from src.skill_evolution.v29.benchmarks.docvqa import evidence, prompting, replay_input_view
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29.storage import read, save
from tests.skill_evolution.v29.test_actor import Base, Transport, response, FIVE, HIDDEN


def example(name, file):
    return read(FIVE / 'examples' / name / file)


def main_example(module, suffix='output'):
    return example('01_full_chain', f'{module}.{suffix}.json')


def user(call):
    return json.loads(call.messages[1]['content'])


class MethodBase(Base):
    def setUp(self):
        super().setUp()
        self.transport = Transport()
        self.adapter = DocVQAActorAdapter(self.dataset, self.transport)
        self.method = DocVQAMethod(self.adapter, archives=[])
        self.enterContext(self.method.using())
        self.tasks = ['synthetic:amount', 'synthetic:date']
        self.counter = 0
        self.candidate = (FIVE / 'examples/01_full_chain/candidate_skill.md').read_text()

    def batch(self, skill, contents, role, tasks=None):
        tasks = tasks or self.tasks
        self.counter += 1
        directory = self.root / f'batch-{self.counter}'
        file = self.root / f'skill-{self.counter}.md'
        file.write_text(skill)
        by_question = {self.dataset.case(t).payload['question']: c for t, c in zip(tasks, contents)}
        self.transport.generate = lambda messages, slot: response(by_question[messages[1]['content'][0]['text'].split('\n\n')[0]])
        records = self.adapter.actor_batch(tasks, file, directory, {'split': 'train', 'role': role})
        self.method.register_archive(directory)
        return records, directory

    def parent(self):
        self.parents, self.parent_dir = self.batch(self.skill, [
            'I will use the subtotal as the total.\n<answer>1,200</answer>', '<answer>12 May 2021</answer>'], 'parent')
        return self.parents

    def prepared(self, active=None):
        grouped = modules.grouping_call(self.parent(), 'R02').complete(main_example('grouping'))
        diagnosed = modules.diagnosis_call(grouped).complete(main_example('diagnosis'))
        return modules.preconditioner_call(diagnosed, active or memory.empty_memory()).complete(main_example('preconditioner'))

    def chain(self, active=None, *, candidate_date='12 May 2022'):
        prepared = self.prepared(active)
        edited = modules.editor_call(prepared).complete(main_example('editor'))
        self.children, self.child_dir = self.batch(edited['candidate_text'],
            ['<answer>1,320</answer>', f'<answer>{candidate_date}</answer>'], 'candidate')
        return evidence.build_replay_from_editor(edited, self.root / 'editor', self.parents, self.children, memory=active)

    def history(self):
        # Archive the earlier label-only comparison described in examples 03/06.
        self.dataset.rows['synthetic:old_amount'] = ('What is the amount?', ['100'], 'train')
        tasks = ['synthetic:amount', 'synthetic:old_amount']
        parents, _ = self.batch(self.skill, ['<answer>1,200</answer>', '<answer>90</answer>'], 'parent', tasks)
        rule = '- For an amount question, answer only from a field explicitly labeled for the requested amount role.\n'
        old_candidate = self.skill + rule
        children, _ = self.batch(old_candidate, ['I transcribed a label as "Total".\n<answer>1,200</answer>',
                                               '<answer>100</answer>'], 'candidate', tasks)
        from src.skill_evolution.v27.contracts.editor import actual_diff
        facts = self.method.build_facts(parents)
        edited = {**facts, 'editor_status': 'candidate', 'candidate_text': old_candidate,
                  'actual_diff': actual_diff(self.skill, old_candidate), 'effective_plan': {
                      'goal': 'Test the label-only proposal.', 'updates': [{'id': 'u1', 'text': rule, 'basis': ['P1:1']}],
                      'checks': []}}
        context = evidence.build_replay_from_editor(edited, self.root / 'historical-editor', parents, children)
        knowledge = example('03_history_revision', 'replay.input.json')['memory']['entries'][0]['knowledge']
        proposal = {'entries': [{'revises': [], 'knowledge': [
            {**k, 'evidence': [r.removeprefix('R01/') for r in k['evidence']]} for k in knowledge]}]}
        self.method.commit_memory(self.root / 'memory', context_id='R01', context=context, result=proposal)
        return self.method.load_memory(self.root / 'memory')

    def reviewed_replay(self, name, active=None):
        """Rebuild reviewed examples from actual local synthetic execution journals."""
        view = replay_input_view.restore_initial(example(name, 'replay.input.json'))
        by_ref = {r['ref']: r for r in view['runs']}
        tasks = [pair['task_id'] for pair in view['pairs']]
        for pair in view['pairs']:
            run = by_ref[pair['parent']]
            self.dataset.rows[pair['task_id']] = (run['initial']['task']['question'], run['outcome']['reference_answers'], 'train')
        from src.skill_evolution.v27.contracts.editor import apply_patch
        candidate = apply_patch(view['parent'], view['diff'])
        records = {}
        for side, skill in [('parent', view['parent']), ('candidate', candidate)]:
            contents = [by_ref[pair[side]]['attempts'][0]['assistant']['content'] for pair in view['pairs']]
            records[side], directory = self.batch(skill, contents, side, tasks)
            setattr(self, f'{side}_example_dir', directory)
        edited = {**self.method.build_facts(records['parent']), 'editor_status': 'candidate',
                  'candidate_text': candidate, 'actual_diff': view['diff'], 'effective_plan': view['plan']}
        return evidence.build_replay_from_editor(edited, self.root / name, records['parent'], records['candidate'], memory=active)

    def assert_reviewed_input(self, actual, expected):
        """Compare text exactly, allowing generated run IDs and synthetic image paths."""
        actual, expected = deepcopy(actual), deepcopy(expected)
        for value in (actual, expected):
            if 'shared_initial' in value:
                restored = replay_input_view.restore_initial(value)
                value.clear(); value.update(restored)
            value['runs'].sort(key=lambda r: r['ref'])
            for run in value['runs']:
                run['run_id'] = 'generated-offline-run'
                path = run['initial']['task']['image_path']
                run['initial']['task']['image_path'] = 'synthetic-image.png'
                for message in run['initial']['messages'] + run['attempts'][0].get('request_messages', []):
                    if message['role'] == 'user':
                        message['content'][1]['text'] = message['content'][1]['text'].replace(path, 'synthetic-image.png')
        self.assertEqual(actual, expected)


class FiveModuleTests(MethodBase):
    def test_complete_chain_prompts_boundaries_and_retain_memory(self):
        prepared = self.prepared()
        call = modules.editor_call(prepared)
        self.assertEqual(user(call), main_example('editor', 'input'))
        edited = call.complete_text(json.dumps(main_example('editor')))
        self.assertEqual(edited['candidate_text'], self.candidate)
        self.assertEqual(edited['effective_plan'], example('01_full_chain', 'effective_plan.json'))
        children, child_dir = self.batch(self.candidate, ['<answer>1,320</answer>', '<answer>12 May 2022</answer>'], 'candidate')
        bundle = evidence.build_replay_from_editor(edited, self.root / 'editor', self.parents, children)
        call = modules.replay_call(bundle)
        self.assertEqual(self.adapter.build_gate(self.parent_dir, child_dir)['result']['decision'], 'RETAIN')
        proposal = call.complete(main_example('replay'))['replay']
        self.method.commit_memory(self.root / 'memory', context_id='R02', context=bundle, result=proposal)
        active = self.method.load_memory(self.root / 'memory')
        self.assertEqual(active['entries'][0]['id'], 'M1')
        self.assertEqual(active['entries'][0]['knowledge'][0]['evidence'][0], 'R02/diff')
        for name in prompting.PROMPT_VERSIONS:
            self.assertEqual(prompting.render(name, bundle['background']), (FIVE / 'prompts' / f'{name}.md').read_text())
        model = json.dumps(user(call))
        for forbidden in (HIDDEN, 'image_url', 'data:image', 'reasoning_content', 'sources', 'pair_audit', 'gate_decision'):
            self.assertNotIn(forbidden, model)
        self.assertNotIn('basis', user(call)['plan']['updates'][0])
        for run in user(call)['runs']:
            self.assertNotIn('request_messages', run['attempts'][0])
        restored = replay_input_view.restore_model_input(user(call))
        original = evidence.model_input(bundle)
        self.assertEqual(restored, original)

    def test_grouping_diagnosis_preconditioner_inputs_and_exact_parent(self):
        group_call = modules.grouping_call(self.parent(), 'R1')
        grouped = group_call.complete(main_example('grouping'))
        dcall = modules.diagnosis_call(grouped)
        self.assertEqual(set(user(dcall)), {'parent', 'runs', 'grouping'})
        diagnosed = dcall.complete(main_example('diagnosis'))
        pcall = modules.preconditioner_call(diagnosed, memory.empty_memory())
        self.assertEqual(set(user(pcall)), {'parent', 'plan', 'runs', 'memory'})
        self.assertEqual([r['ref'] for r in user(pcall)['runs']], ['P1'])
        self.assertEqual(user(pcall)['parent'], self.skill)
        self.assertEqual(user(pcall)['memory'], {'format': 'memory_knowledge_only_v1', 'entries': []})
        for call, name in [(group_call, 'grouping'), (dcall, 'diagnosis'), (pcall, 'preconditioner')]:
            actual = user(call); expected = main_example(name, 'input')
            for got, want in zip(actual['runs'], expected['runs']):
                got['run_id'] = want['run_id']
                # Synthetic acceptance uses the same tiny image for every question.
                got['initial']['task']['image_path'] = want['initial']['task']['image_path']
                for msg in got['initial']['messages'] + got['attempts'][0]['request_messages']:
                    if msg['role'] == 'user':
                        msg['content'][1]['text'] = msg['content'][1]['text'].replace('images/amount.png', want['initial']['task']['image_path'])
            self.assertEqual(actual, expected)

    def test_plan_references_select_whole_runs_without_group_expansion(self):
        grouped = modules.grouping_call(self.parent(), 'R1').complete({'groups': [{
            'group_id': 'G1', 'members': ['P1', 'P2'], 'decision_problem': 'Compare response decisions.',
            'shared_basis': 'P1:1 answers an amount; P2:1 answers a date.', 'important_differences': []}]})
        plan = main_example('diagnosis'); plan['reason'] = 'A focused proposal.'
        plan['plan']['updates'][0]['basis'] = ['G1']
        with self.assertRaises(ValueError): modules.diagnosis_call(grouped).complete(plan)
        plan['plan']['updates'][0]['basis'] = ['G1', 'P1:1']
        diagnosed = modules.diagnosis_call(grouped).complete(plan)
        self.assertEqual([r['ref'] for r in user(modules.preconditioner_call(diagnosed, memory.empty_memory()))['runs']], ['P1'])
        plan['plan']['checks'][0]['question'] = 'Compare P2:outcome with its response.'
        diagnosed = modules.diagnosis_call(grouped).complete(plan)
        runs = user(modules.preconditioner_call(diagnosed, memory.empty_memory()))['runs']
        self.assertEqual([r['ref'] for r in runs], ['P1', 'P2'])
        self.assertEqual(runs[1]['attempts'][0]['assistant']['content'], '<answer>12 May 2021</answer>')

    def test_editor_isolated_and_output_states(self):
        prepared = self.prepared()
        call = modules.editor_call(prepared)
        self.assertEqual(set(user(call)), {'parent', 'plan'})
        for value, status in [(None, 'needs_revision'), ('', 'no_change')]:
            result = call.complete({'patch': value, 'reason': 'No applicable edit.'})
            self.assertEqual(result['editor_status'], status)
            self.assertIsNone(result['candidate_text'])
            with self.assertRaises(ValueError):
                evidence.build_replay_from_editor(result, self.root, self.parents, self.parents)
        for value in ('   ', 'not a patch', main_example('editor')['patch'].replace('several nearby', 'many nearby')):
            with self.assertRaises(ValueError): call.complete({'patch': value, 'reason': 'Invalid.'})
        with self.assertRaises(ValueError): call.complete_text('{"patch":"","patch":null,"reason":"x"}')

    def test_saved_inputs_are_detached_and_revalidated(self):
        prepared = self.prepared(); call = modules.editor_call(prepared)
        prepared['effective_plan']['goal'] = 'changed externally'
        call.input['effective_plan']['goal'] = 'changed visible copy'
        self.assertEqual(call.complete(main_example('editor'))['candidate_text'], self.candidate)
        broken = deepcopy(prepared)
        with self.assertRaises(ValueError): modules.editor_call(broken)
        result_path = self.parent_dir / 'actor/0001/result.json'
        saved = read(result_path); saved['content'] = 'changed'; save(result_path, saved)
        with self.assertRaises(ValueError): call.complete(main_example('editor'))

    def test_parent_only_references_and_complete_group_coverage(self):
        call = modules.grouping_call(self.parent(), 'R1')
        for ref in ('Q1:1', 'P1:2', 'R01/P1:1', 'R01/diff'):
            bad = main_example('grouping'); bad['groups'][0]['shared_basis'] += ' ' + ref
            with self.assertRaises(ValueError): call.complete(bad)
        bad = main_example('grouping'); bad['groups'].pop()
        with self.assertRaises(ValueError): call.complete(bad)
        grouped = call.complete(main_example('grouping'))
        for ref in ('Q1:1', 'P9:0', 'R01/P1:1', 'R01/diff'):
            bad = main_example('diagnosis'); bad['reason'] += ' ' + ref
            with self.assertRaises(ValueError): modules.diagnosis_call(grouped).complete(bad)

    def test_no_arbitrary_update_cap_and_no_method_budget(self):
        grouped = modules.grouping_call(self.parent(), 'R1').complete(main_example('grouping'))
        diagnosis = main_example('diagnosis')
        diagnosis['plan']['updates'] = [{**deepcopy(diagnosis['plan']['updates'][0]), 'id': f'u{i}'} for i in range(1, 5)]
        diagnosed = modules.diagnosis_call(grouped).complete(diagnosis)
        keep = main_example('preconditioner')
        keep['adjustments'] = [{**deepcopy(keep['adjustments'][0]), 'target': f'u{i}', 'reason': f'Keep `Update:u{i}`.'} for i in range(1, 5)]
        prepared = modules.preconditioner_call(diagnosed, memory.empty_memory()).complete(keep)
        self.assertEqual(len(prepared['effective_plan']['updates']), 4)
        self.assertFalse(hasattr(modules.editor_call(prepared), 'max_tokens'))
        with self.assertRaises(ValueError): prompting.render('verifier', prepared['background'])

    def redundant_saved(self):
        reviewed = example('05_diagnosis_no_change', 'diagnosis.input.json')
        run = reviewed['runs'][0]
        self.dataset.rows[run['task_id']] = (run['initial']['task']['question'], run['outcome']['reference_answers'], 'train')
        records, _ = self.batch(reviewed['parent'], [run['attempts'][0]['assistant']['content']], 'parent', [run['task_id']])
        return modules.grouping_call(records, 'R1').complete(reviewed['grouping'])

    def test_reviewed_diagnosis_stop_and_redundant_withdrawal(self):
        grouped = self.redundant_saved()
        no_change = modules.diagnosis_call(grouped).complete(example('05_diagnosis_no_change', 'diagnosis.output.json'))
        with self.assertRaises(ValueError): modules.preconditioner_call(no_change, memory.empty_memory())
        reviewed = example('04_preconditioner_redundancy', 'preconditioner.input.json')
        diagnosed = modules.diagnosis_call(grouped).complete({'decision': 'revise', 'reason': 'Propose explicit guidance.', 'plan': reviewed['plan']})
        call = modules.preconditioner_call(diagnosed, memory.empty_memory())
        self.assert_reviewed_input(user(call), reviewed)
        adjustments = example('04_preconditioner_redundancy', 'preconditioner.output.json')
        prepared = call.complete(adjustments)
        self.assertIsNone(prepared['effective_plan'])
        with self.assertRaises(ValueError): modules.editor_call(prepared)
        adjustments['checks'] = None
        with self.assertRaises(ValueError): call.complete(adjustments)

    def test_reviewed_scope_patch_history_and_exact_update_application(self):
        active = self.history()
        grouped = modules.grouping_call(self.parent(), 'R2').complete(main_example('grouping'))
        reviewed = example('06_preconditioner_scope', 'preconditioner.input.json')
        diagnosed = modules.diagnosis_call(grouped).complete({'decision': 'revise', 'reason': 'Test amount-role guidance.', 'plan': reviewed['plan']})
        call = modules.preconditioner_call(diagnosed, active)
        self.assert_reviewed_input(user(call), reviewed)
        adjustments = example('06_preconditioner_scope', 'preconditioner.output.json')
        prepared = call.complete(adjustments)
        self.assertEqual(prepared['effective_plan']['updates'][0]['text'], main_example('diagnosis')['plan']['updates'][0]['text'])
        self.assertEqual(prepared['effective_plan']['checks'], reviewed['plan']['checks'])
        for change in ('history', 'patch', 'focus', 'duplicate', 'checks'):
            bad = deepcopy(adjustments)
            if change == 'history': bad['adjustments'][0]['reason'] += ' `Evidence:R01/Q2:0`'
            elif change == 'patch': bad['adjustments'][0]['to']['patch'] = bad['adjustments'][0]['to']['patch'].replace('answer only', 'answer always')
            elif change == 'focus': bad['adjustments'][0]['focus'] = ['Z']
            elif change == 'duplicate': bad['adjustments'].append(deepcopy(bad['adjustments'][0]))
            else: bad['checks'] = [{'id': 'c1', 'update_ids': ['u999'], 'question': 'Compare.'}]
            with self.subTest(change=change), self.assertRaises(ValueError): call.complete(bad)

    def test_invalid_adjustment_is_atomic_and_does_not_change_saved_plan(self):
        grouped = modules.grouping_call(self.parent(), 'R1').complete(main_example('grouping'))
        diagnosed = modules.diagnosis_call(grouped).complete(main_example('diagnosis'))
        original = deepcopy(diagnosed)
        call = modules.preconditioner_call(diagnosed, memory.empty_memory())
        for bad in ({'adjustments': [], 'checks': None}, {'adjustments': main_example('preconditioner')['adjustments'], 'checks': 'invalid'}):
            with self.assertRaises(ValueError): call.complete(bad)
            self.assertEqual(diagnosed, original)
        self.assertEqual(call.complete(main_example('preconditioner'))['effective_plan'], example('01_full_chain', 'effective_plan.json'))


class ReplayAndMemoryTests(MethodBase):
    def test_history_whole_entry_revision_and_knowledge_only_scope(self):
        active = self.history()
        self.assertEqual(knowledge_only(active), example('03_history_revision', 'replay.input.json')['memory'])
        bundle = self.reviewed_replay('03_history_revision', active)
        self.assert_reviewed_input(user(modules.replay_call(bundle)), example('03_history_revision', 'replay.input.json'))
        proposal = example('03_history_revision', 'replay.output.json')
        result = modules.replay_call(bundle).complete(proposal)['replay']
        committed = self.method.commit_memory(self.root / 'memory', context_id='R02', context=bundle, result=result)
        current = self.method.load_memory(self.root / 'memory')
        self.assertEqual([e['id'] for e in current['entries']], ['M2'])
        self.assertEqual(current['entries'][0]['knowledge'][1], active['entries'][0]['knowledge'][1])
        self.assertEqual(committed['before_active_ids'], ['M1'])
        self.assertEqual(committed['after_active_ids'], ['M2'])
        self.assertTrue((self.root / 'memory/archive/R01.json').exists())
        self.assertEqual(self.method.commit_memory(self.root / 'memory', context_id='R02', context=bundle, result=result), committed)
        before = len(self.transport.seen)
        cold = DocVQAMethod(DocVQAActorAdapter(self.dataset), archives=sorted(self.root.glob('batch-*')))
        with cold.using(): self.assertEqual(cold.load_memory(self.root / 'memory'), current)
        self.assertEqual(len(self.transport.seen), before)

    def test_unshown_history_references_not_authorized_by_available_source(self):
        active = self.history(); bundle = self.chain(active); call = modules.replay_call(bundle)
        for where in ('evidence', 'text'):
            bad = example('03_history_revision', 'replay.output.json')
            item = bad['entries'][0]['knowledge'][0]
            if where == 'evidence': item['evidence'].append('R01/Q2:0')
            else: item['text'] += ' R01/Q2:0 establishes the task.'
            with self.assertRaises(ValueError): call.complete(bad)
        bad = example('03_history_revision', 'replay.output.json'); bad['entries'].append(deepcopy(bad['entries'][0]))
        with self.assertRaises(ValueError): call.complete(bad)

    def test_commit_interruption_recovery_and_stale_snapshot(self):
        bundle = self.chain(); result = main_example('replay'); directory = self.root / 'memory'
        write = memory.write_record
        def interrupt(path, data):
            if Path(path).name == 'active.json': raise KeyboardInterrupt()
            return write(path, data)
        with patch.object(memory, 'write_record', interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.method.commit_memory(directory, context_id='R1', context=bundle, result=result)
        self.assertEqual(self.method.load_memory(directory), memory.empty_memory())
        with self.assertRaises(ValueError): self.method.commit_memory(directory, context_id='R2', context=bundle, result=result)
        self.method.commit_memory(directory, context_id='R1', context=bundle, result=result)
        active_before = (directory / 'active.json').read_bytes()
        with self.assertRaises(ValueError): self.method.commit_memory(directory, context_id='R2', context=bundle, result=result)
        self.assertEqual((directory / 'active.json').read_bytes(), active_before)
        altered = deepcopy(result); altered['entries'][0]['knowledge'][0]['text'] += ' changed'
        with self.assertRaises(ValueError): self.method.commit_memory(directory, context_id='R1', context=bundle, result=altered)

    def test_replay_pairs_and_actual_candidate_cannot_be_replaced(self):
        bundle = self.chain()
        for key in ('candidate', 'payload', 'audit'):
            bad = deepcopy(bundle)
            if key == 'candidate': bad[key] += '\nnew rule'
            elif key == 'payload': bad[key]['pairs'][0]['candidate_result']['hard'] = 0
            else: bad[key]['candidate_records'] = bad[key]['parent_records']
            with self.assertRaises(ValueError): modules.replay_call(bad)
        with self.assertRaises(ValueError): self.method.build_facts(self.parents[:1])
        with self.assertRaises(ValueError): self.method.build_facts(list(reversed(self.parents)))
        fresh = DocVQAMethod(self.adapter, archives=[])
        with fresh.using():
            with self.assertRaises(ValueError): modules.grouping_call(self.parents, 'R1')

    def test_accept_also_accumulates_and_empty_replay_is_a_valid_commit(self):
        bundle = self.chain(candidate_date='12 May 2021')
        self.assertEqual(self.adapter.build_gate(self.parent_dir, self.child_dir)['result']['decision'], 'ACCEPT')
        proposal = {'entries': [{'revises': [], 'knowledge': [{'text': 'An amount answer improves with a conditional edit; causality is unresolved.',
                                                            'evidence': ['diff', 'P1:outcome', 'Q1:outcome']}]}]}
        self.method.commit_memory(self.root / 'memory', context_id='R1', context=bundle, result=proposal)
        active = self.method.load_memory(self.root / 'memory')
        next_bundle = self.chain(active)
        result = modules.replay_call(next_bundle).complete({'entries': []})['replay']
        self.method.commit_memory(self.root / 'memory', context_id='R2', context=next_bundle, result=result)
        self.assertEqual(self.method.load_memory(self.root / 'memory'), active)

    def test_entry_union_not_each_knowledge_requires_diff_and_execution(self):
        call = modules.replay_call(self.chain())
        proposal = {'entries': [{'revises': [], 'knowledge': [
            {'text': 'The diff adds a conditional rule.', 'evidence': ['diff']},
            {'text': 'One answer improved.', 'evidence': ['P1:outcome', 'Q1:outcome']}]}]}
        self.assertEqual(call.complete(proposal)['replay'], proposal)
        for item in proposal['entries'][0]['knowledge']:
            with self.assertRaises(ValueError): call.complete({'entries': [{'revises': [], 'knowledge': [item]}]})

    def test_reviewed_anls_only_case_retains_but_can_learn(self):
        bundle = self.reviewed_replay('02_anls_only')
        call = modules.replay_call(bundle)
        self.assert_reviewed_input(user(call), example('02_anls_only', 'replay.input.json'))
        pair = bundle['payload']['pairs'][0]
        self.assertEqual(pair['parent_result']['hard'], pair['candidate_result']['hard'])
        self.assertLess(pair['parent_result']['anls'], pair['candidate_result']['anls'])
        self.assertEqual(self.adapter.build_gate(self.parent_example_dir, self.candidate_example_dir)['result']['decision'], 'RETAIN')
        result = call.complete(example('02_anls_only', 'replay.output.json'))['replay']
        self.method.commit_memory(self.root / 'memory', context_id='R1', context=bundle, result=result)
        self.assertTrue(self.method.load_memory(self.root / 'memory')['entries'])

    def test_model_view_rejects_noncanonical_sharing_and_current_bad_reference(self):
        bundle = self.chain(); call = modules.replay_call(bundle)
        bad = user(call); bad['shared_initial']['messages']['unused'] = {'role': 'system', 'content': 'extra'}
        with self.assertRaises(ValueError): replay_input_view.restore_initial(bad)
        result = main_example('replay'); result['entries'][0]['knowledge'][0]['evidence'].append('Q1:2')
        with self.assertRaises(ValueError): call.complete(result)
        bad = deepcopy(bundle); bad['payload']['gate'] = 'ACCEPT'
        with self.assertRaises(ValueError): modules.replay_call(bad)

    def test_cold_memory_checks_committed_lineage_without_historical_actors(self):
        bundle = self.chain(); directory = self.root / 'memory'
        self.method.commit_memory(directory, context_id='R1', context=bundle, result=main_example('replay'))
        expected = self.method.load_memory(directory)
        path = directory / 'archive/R1.json'; original = read(path)
        changed = deepcopy(original); changed['after_active_ids'] = []; save(path, changed)
        with self.assertRaises(ValueError): self.method.load_memory(directory)
        save(path, original)
        # Historical response files are not dependencies of reading committed Knowledge.
        path = self.child_dir / 'actor/0001/attempts/001/response.json'
        path.unlink()
        self.assertEqual(self.method.load_memory(directory), expected)


    def test_test_archives_cannot_be_registered_as_optimization_context(self):
        self.adapter.actor_batch(['synthetic:test'], self.skill_file, self.root / 'evaluation',
                                 {'split': 'test', 'role': 'evaluation'}, final=True)
        with self.assertRaises(ValueError): self.method.register_archive(self.root / 'evaluation')

