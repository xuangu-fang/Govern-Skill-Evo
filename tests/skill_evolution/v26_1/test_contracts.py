from copy import deepcopy
import json
import pytest
from .support import make, batch, diagnosed, edited, response
from src.skill_evolution.v26_1 import facts, diagnosis as d, preconditioner as pc, editor, replay, gate, memory
from src.skill_evolution.v26_1 import execution_input_view as codec
from src.skill_evolution.v26_1.evidence import run_references


def test_formal_multiturn_hidden_data_and_lossless_scope(tmp_path):
    method, provider, cfg = make(tmp_path / 'fixture')
    provider.scripts['UID0007'] = [response(calls=[('glob', {'pattern': '*'}),
        ('read', {'path': 'treasury_bulletin_2011_03.txt', 'start': 1, 'limit': 2})]), response('1000')]
    with method.using():
        records = batch(method, tmp_path / 'parent')
        saved = facts.build_parent_bundle(records, 'R1')
        view = d.diagnosis_input(saved); wire = d.model_input(saved)
        assert codec.restore_model_input(wire, module='diagnosis') == view
        assert 'shared_initial' not in wire
        encoded = json.dumps(wire)
        for forbidden in ('HIDDEN_REASONING_SENTINEL', 'GOLD_ONLY_SENTINEL', 'reference_answers', 'UNOBSERVED_PAGE_SENTINEL'):
            assert forbidden not in encoded
        run = next(r for r in view['runs'] if r['task_id'] == 'UID0007')
        assert len(run['attempts']) == 2 and len(run['attempts'][0]['tools']) == 2
        assert run['attempts'][1]['request_messages'][-1]['role'] == 'tool'
        assert run['ref'] + ':1_t2' in run_references(run)
        broken = deepcopy(wire); broken['runs'][0]['outcome']['answer'] = 'tampered'
        with pytest.raises(ValueError): codec.validate_model_input(broken, original=view, module='diagnosis')
        refs = [r['ref'] for r in view['runs']]
        proposal = {'decision': 'revise', 'reason': f'Reason only {refs[1]}', 'plan': {
            'goal': f'Goal {refs[2]}', 'updates': [{'id': 'u1', 'text': f'Counterexample {refs[3]}', 'basis': [refs[0]]}]}}
        out = d.diagnosis_call(saved).complete(proposal)
        selected = pc.preconditioner_input(out, {'rounds': []})
        assert [r['ref'] for r in selected['runs']] == [refs[0], refs[2], refs[3]]
        assert set(selected) == {'parent', 'plan', 'runs', 'memory'}
        assert codec.restore_model_input(pc.model_input(out, {'rounds': []}), module='preconditioner') == selected


@pytest.mark.parametrize('ref', ['P99', 'Q1', 'R03/P1', 'R03/diff', '`Group:G1`', '`Check:c1`',
                                 '`Memory:M1`', '`Update:u1`', 'Evidence:P1', '``Evidence:P1``'])
def test_diagnosis_reference_rejections(tmp_path, ref):
    method, _, _ = make(tmp_path / 'fixture')
    with method.using():
        records = batch(method, tmp_path / 'parent')
        call = d.diagnosis_call(facts.build_parent_bundle(records, 'R1'))
        with pytest.raises(ValueError): call.complete({'decision': 'no_change', 'reason': ref, 'plan': None})
        call.complete({'decision': 'no_change', 'reason': 'Evidence: returned text P1/P3', 'plan': None})


def test_preconditioner_actions_permissions_and_editor_projection(tmp_path):
    method, _, _ = make(tmp_path / 'fixture')
    with method.using():
        _, saved = diagnosed(method, tmp_path / 'parent')
        mem = {'rounds': [{'round_id': 'old', 'source_updates': [{'id': 'old_u', 'text': 'Old', 'gate_decision': 'Defer'}],
                          'entries': [{'id': 'M1', 'knowledge': {'task_id': 'old_task', 'update_id': None, 'text': 'Past P99'}}]}]}
        call = pc.preconditioner_call(saved, mem)
        value = {'adjustments': [{'target': 'u2', 'action': 'WITHDRAW', 'text': None, 'reason': '`Memory:M1`'},
                               {'target': 'u1', 'action': 'REPLACE', 'text': 'Revised text', 'reason': '`Evidence:P1:1` and `Update:u1`'}]}
        result = call.complete(value)
        assert saved['diagnosis']['plan']['updates'][0]['text'] == 'Change alpha'
        assert result['effective_plan']['updates'] == [{**saved['diagnosis']['plan']['updates'][0], 'text': 'Revised text'}]
        assert result['effective_plan']['goal'] == saved['diagnosis']['plan']['goal']
        assert set(editor.editor_input(result)) == {'parent', 'plan'}
        assert set(editor.editor_input(result)['plan']['updates'][0]) == {'id','text'}
        for change in ('Q1', 'P4', 'old/P1', '`Memory:M2`', '`Check:c1`'):
            bad = deepcopy(value); bad['adjustments'][0]['reason'] = change
            with pytest.raises(ValueError): call.complete(bad)
        for mutate in ('missing', 'duplicate', 'unchanged_replace', 'keep_text'):
            bad = deepcopy(value)
            if mutate == 'missing': bad['adjustments'].pop()
            if mutate == 'duplicate': bad['adjustments'].append(deepcopy(bad['adjustments'][0]))
            if mutate == 'unchanged_replace': bad['adjustments'][1]['text'] = 'Change alpha'
            if mutate == 'keep_text': bad['adjustments'][1]['action'] = 'KEEP'
            with pytest.raises(ValueError): call.complete(bad)


def prepare_replay(method, provider, tmp, *, parent_answers, candidate_answers, patches=None):
    tasks = method.dataset.splits['train']
    provider.scripts = {task: [response(answer)] for task,answer in zip(tasks,parent_answers)}
    parents, e = edited(method, tmp / 'source', patches=patches)
    provider.scripts = {task: [response(answer)] for task,answer in zip(tasks,candidate_answers)}
    candidates = batch(method, tmp / 'candidate', role='candidate', skill=e['candidate_text'])
    return replay.build_replay_from_editor(e, parents, candidates), e


def test_replay_selective_gate_and_memory(tmp_path):
    method, provider, _ = make(tmp_path / 'fixture')
    with method.using():
        bundle, e = prepare_replay(method, provider, tmp_path, parent_answers=['0','1000','0','1000'],
                                  candidate_answers=['1000','0','0','1000'])
        view = replay.replay_input(bundle)
        assert len(view['pairs']) == 2 and len(bundle['payload']['pairs']) == 4
        assert codec.restore_model_input(replay.model_input(bundle), module='replay') == view
        assert all(set(pair['parent_result']) == {'status','model_rounds','tool_calls','api_requests','em','f1'} for pair in view['pairs'])
        event = {pair['task_id']: pair for pair in view['pairs']}
        def knowledge(tid, uid):
            return {'task_id': tid, 'update_id': uid, 'text': f"Compare {event[tid]['parent']}:1/{event[tid]['candidate']}:1 and `Evidence:diff`"}
        output = {'entries': [{'knowledge': [knowledge('a','u2'), knowledge('UID0007','u1')]}]}
        receipt = replay.replay_call(bundle).complete(output)
        assert [k['task_id'] for k in receipt['knowledge']] == [p['task_id'] for p in view['pairs']]
        result = gate.evaluate_gate(receipt)
        assert [item['gate_decision'] for item in result['decisions']] == ['Retain','Reject']
        assert result['selection']['selected_text'] == 'ALPHA\nbeta\ngamma\n'
        assert result['selected_execution_source'] is None
        empty = memory.load_memory(tmp_path / 'memory')
        prepared = memory.prepare_append(empty, replayed=receipt, gate_result=result)
        state = memory.commit_memory(tmp_path / 'memory', prepared, expected_head=None)
        assert len(state['head'].split('-')[1]) == 64
        assert [x['id'] for x in state['memory']['rounds'][0]['entries']] == ['M1','M2']
        assert [u['gate_decision'] for u in state['memory']['rounds'][0]['source_updates']] == ['Retain','Reject']
        assert memory.commit_memory(tmp_path / 'memory', prepared, expected_head=None) == state
        for mutation in ('missing','duplicate','wrong_task','cross_pair','history','empty_knowledge','unknown_update'):
            bad=deepcopy(output)
            if mutation=='missing': bad['entries'][0]['knowledge'].pop()
            if mutation=='duplicate': bad['entries'][0]['knowledge'].append(deepcopy(bad['entries'][0]['knowledge'][0]))
            if mutation=='wrong_task': bad['entries'][0]['knowledge'][0]['task_id']='b'
            if mutation=='cross_pair': bad['entries'][0]['knowledge'][0]['text']=event['UID0007']['parent']
            if mutation=='history': bad['entries'][0]['knowledge'][0]['text']='old/P1'
            if mutation=='empty_knowledge': bad['entries'][0]['knowledge']=[]
            if mutation=='unknown_update': bad['entries'][0]['knowledge'][0]['update_id']='other'
            with pytest.raises(ValueError): replay.replay_call(bundle).complete(bad)


@pytest.mark.parametrize('parents,candidates,uid,expected', [
    (['0']*4,['1000']*4,'u1','Retain'), (['1000']*4,['0']*4,'u1','Reject'),
    (['0','0','0','1000'],['1000','1000','1000','0'],'u1','Defer'),
    (['0']*4,['1000']*4,None,'Defer'), (['0']*4,['0']*4,None,'Defer'), (['1000 extra']*4,['0']*4,None,'Defer')])
def test_gate_branches(tmp_path, parents, candidates, uid, expected):
    method, provider, _ = make(tmp_path / 'fixture')
    with method.using():
        bundle, _ = prepare_replay(method, provider, tmp_path, parent_answers=parents, candidate_answers=candidates)
        view = replay.replay_input(bundle)
        call = replay.replay_call(bundle)
        receipt = call.complete({'entries':[{'knowledge':[{'task_id':p['task_id'],'update_id':uid,'text':'Observed'} for p in view['pairs']]}]}) if call else replay.skip_replay(bundle)
        result=gate.evaluate_gate(receipt)
        assert result['decisions'][0]['gate_decision']==expected
        assert result['decisions'][1]['gate_decision']=='Defer'
        if expected != 'Retain': assert result['selected_execution_source'] == 'parent'
        if call is None: assert receipt['replay_called'] is False and receipt['replay']=={'entries':[]}


def test_no_modification_update_cannot_receive_event(tmp_path):
    method, provider, _ = make(tmp_path / 'fixture')
    with method.using():
        bundle, _ = prepare_replay(method, provider, tmp_path, parent_answers=['0']*4,candidate_answers=['1000']*4,
                                  patches=['@@\n-alpha\n+ALPHA\n',''])
        output={'entries':[{'knowledge':[{'task_id':p['task_id'],'update_id':'u2','text':'Observed'} for p in replay.replay_input(bundle)['pairs']]}]}
        with pytest.raises(ValueError): replay.replay_call(bundle).complete(output)
        for item in output['entries'][0]['knowledge']: item['update_id']='u1'
        result=gate.evaluate_gate(replay.replay_call(bundle).complete(output))
        assert result['decisions'][1]['gate_decision'] is None
        assert result['selected_execution_source']=='candidate'
