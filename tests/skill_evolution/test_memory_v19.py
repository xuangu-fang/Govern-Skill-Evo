from pathlib import Path
import shutil

import pytest

from src.skill_evolution.edit_tracking_v19 import digest, encode
from src.skill_evolution.evolution_replay_v19 import run_parent_evolution, run_candidate_replay, _load, _save, _lock
from src.skill_evolution.attribution_v19 import run_attribution, build_attribution_input
from src.skill_evolution.memory_store_v19 import (
    MemoryRejected, initialize_memory, load_memory, commit_round_memory,
)
from src.skill_evolution.memory_retrieval_v19 import MemoryBudgetExceeded, retrieve_memory
from tests.skill_evolution.test_edit_tracking_v19 import case, value_for, ledger_for, link
from tests.skill_evolution.test_evolution_replay_v19 import Backend
from tests.skill_evolution.test_attribution_v19 import record, response, complete


def receipt(ledger, decision='ACCEPT'):
    data=ledger.payload
    return {'status':'COMPLETE','decision':decision,'run_id':data['run_id'],'round_id':data['round_id'],
            'parent_skill_sha256':data['parent_skill_ref']['sha256'],
            'candidate_skill_sha256':data['candidate_skill_ref']['sha256']}


def make_round(case, root, *, history=(), parent='- Parent\n', round_id='r1',
               decision='ACCEPT', specs=None, texts=None, links=(), effects=None):
    backend=Backend(parent)
    specs = [('MISSING', [])] if specs is None else specs
    texts = [(0, '- New rule ' + round_id)] if texts is None else texts
    ledger=ledger_for(value_for(case, parent, specs, round_id=round_id), texts, history=history, links=links)
    parent_dir,replay_dir,attr_dir=root/'parent',root/'candidate',root/'attribution'
    run_parent_evolution(run_id='test-run',round_id=round_id,parent_skill=parent,
                         backend=backend,artifact_dir=parent_dir)
    run_candidate_replay(ledger,backend=backend,parent_dir=parent_dir,artifact_dir=replay_dir,history=history)
    data=build_attribution_input(ledger,backend=backend,parent_dir=parent_dir,replay_dir=replay_dir,history=history)
    records = effects(data) if effects else [record(data,(0,1),'MIXED')]
    run_attribution(ledger,backend=backend,parent_dir=parent_dir,replay_dir=replay_dir,artifact_dir=attr_dir,
                    history=history,transport=lambda _:complete(response(*records)))
    return ledger,dict(backend=backend,parent_dir=parent_dir,replay_dir=replay_dir,
                       attribution_dir=attr_dir,gate_result=receipt(ledger,decision))


@pytest.fixture
def setup(case,tmp_path):
    root=tmp_path/'memory'
    initialize_memory(store_dir=root,run_id='test-run',initial_skill='- Parent\n')
    ledger,kwargs=make_round(case,tmp_path/'stage')
    return root,ledger,kwargs


def commit(setup,expected=None):
    root,ledger,kwargs=setup
    return commit_round_memory(ledger,store_dir=root,expected_head_ref=expected,**kwargs)


def test_empty_memory_idempotent_initialization_and_parent_rules(tmp_path):
    root=tmp_path/'memory'
    snap=initialize_memory(store_dir=root,run_id='run',initial_skill='- Rule\n')
    assert snap.head['revision']==0 and snap.head['memory_ref'] is None
    assert initialize_memory(store_dir=root,run_id='run',initial_skill='- Rule\n')==snap
    ctx=retrieve_memory(store_dir=root,current_parent='- Rule\n').payload
    assert ctx['selection']['complete_history'] and not ctx['rounds']
    assert ctx['current_rules'][0]['text']=='- Rule\n'
    with pytest.raises(MemoryRejected): initialize_memory(store_dir=root,run_id='other',initial_skill='- Rule\n')
    with pytest.raises(MemoryRejected): retrieve_memory(store_dir=root,current_parent='wrong')


@pytest.mark.parametrize('decision',['ACCEPT','RETAIN'])
def test_both_decisions_preserve_all_evidence_and_atomic_skill(setup,decision):
    root,ledger,kwargs=setup
    kwargs['gate_result']=receipt(ledger,decision)
    ref=commit(setup)
    snap=load_memory(root)
    assert snap.head['memory_ref']==ref and snap.head['revision']==1
    expected=ledger.source['candidate_skill'] if decision=='ACCEPT' else ledger.source['editor']['parent_skill']
    assert snap.head['retained_skill']==expected
    row=snap.rounds[0]
    assert len(row['record']['replay_pair_refs'])==3
    assert len(row['record']['edit_refs'])==len(ledger.payload['edits'])
    assert row['record']['gate_decision']==decision
    ctx=retrieve_memory(store_dir=root,current_parent=expected).payload
    assert len(ctx['rounds'][0]['replay']['pairs'])==3
    assert ctx['rounds'][0]['current_bindings'][0]['binding_status']==('EXACT' if decision=='ACCEPT' else 'ABSENT')
    assert ctx['rounds'][0]['attribution']['records'][0]['effect']=='MIXED'
    assert commit(setup)==ref
    assert load_memory(root).head['revision']==1


def test_archive_independent_of_stage_files_and_live_model_config(setup,monkeypatch):
    import src.skill_evolution.attribution_v19 as attribution
    root,ledger,kwargs=setup
    commit(setup)
    shutil.rmtree(kwargs['parent_dir'].parent)
    monkeypatch.setattr(attribution,'SYSTEM_PROMPT','A different future prompt')
    kwargs['backend'].version='future runtime'
    snap=load_memory(root)
    assert snap.head['retained_skill']==ledger.source['candidate_skill']
    assert retrieve_memory(store_dir=root,current_parent=snap.head['retained_skill'])


def test_two_round_chain_retain_and_no_model_calls_on_retrieval(setup,case,tmp_path):
    root,ledger,kwargs=setup
    first=commit(setup)
    snap=load_memory(root)
    second,kw=make_round(case,tmp_path/'second',history=snap.history,parent=snap.head['retained_skill'],
                         round_id='r2',decision='RETAIN',effects=lambda d:[record(d)])
    second_ref=commit_round_memory(second,store_dir=root,expected_head_ref=first,**kw)
    current=load_memory(root)
    assert current.head['revision']==2 and current.head['memory_ref']==second_ref
    assert current.head['retained_skill']==snap.head['retained_skill']
    before=kw['backend'].calls.copy()
    context=retrieve_memory(store_dir=root,current_parent=current.head['retained_skill']).payload
    assert kw['backend'].calls==before
    assert len(context['rounds'])==2
    reasons={r for u in context['selection']['units'] for r in u['retrieval_reasons']}
    assert 'NEGATIVE_EVIDENCE_WITH_CURRENT_BINDING' in reasons
    assert 'UNPROMOTED_POTENTIAL_BENEFIT' in reasons
    assert context['resolution_status']=='NOT_AUTOMATICALLY_INFERRED_FROM_GATE_OR_FOLLOWUP'
    # An old round retry must never roll the head back.
    assert commit(setup)==first
    assert load_memory(root).head==current.head


@pytest.mark.parametrize('mutation',[
    lambda g:g.update(status='INCOMPLETE'), lambda g:g.update(decision='NO_UPDATE'),
    lambda g:g.update(round_id='other'),lambda g:g.update(candidate_skill_sha256='0'*64),
    lambda g:g.update(monitor_score=1.0),lambda g:g.pop('parent_skill_sha256'),
])
def test_invalid_gate_never_advances_head(setup,mutation):
    root,ledger,kwargs=setup
    mutation(kwargs['gate_result'])
    with pytest.raises(MemoryRejected): commit(setup)
    assert load_memory(root).head['revision']==0


def test_conflicting_repeat_and_stale_new_round_rejected(setup,case,tmp_path):
    root,ledger,kwargs=setup
    first=commit(setup)
    kwargs['gate_result']=receipt(ledger,'RETAIN')
    with pytest.raises(MemoryRejected): commit(setup)
    snap=load_memory(root)
    second,kw=make_round(case,tmp_path/'second',history=snap.history,parent=snap.head['retained_skill'],round_id='r2')
    with pytest.raises(MemoryRejected,match='stale'):
        commit_round_memory(second,store_dir=root,expected_head_ref=None,**kw)
    assert load_memory(root).head['memory_ref']==first


def test_incomplete_attribution_cannot_commit(setup):
    root,_,kwargs=setup
    _save(kwargs['attribution_dir']/'validation.json',{'status':'INCOMPLETE'})
    with pytest.raises(ValueError): commit(setup)
    assert load_memory(root).head['revision']==0


def test_interruption_before_head_is_invisible_and_recovers(setup,monkeypatch):
    import src.skill_evolution.memory_store_v19 as store
    root,ledger,kwargs=setup
    original=store._durable_save
    def fail(path,value):
        if Path(path)==root/'head.json': raise KeyboardInterrupt()
        return original(path,value)
    monkeypatch.setattr(store,'_durable_save',fail)
    with pytest.raises(KeyboardInterrupt): commit(setup)
    assert load_memory(root).head['revision']==0
    assert not retrieve_memory(store_dir=root,current_parent='- Parent\n').payload['rounds']
    assert len(list((root/'rounds').iterdir()))==1
    monkeypatch.setattr(store,'_durable_save',original)
    commit(setup)
    assert load_memory(root).head['revision']==1
    assert len(list((root/'rounds').iterdir()))==1


def test_interruption_after_head_is_idempotent(setup,monkeypatch):
    import src.skill_evolution.memory_store_v19 as store
    root,_,_=setup
    original=store._durable_save
    def fail(path,value):
        result=original(path,value)
        if Path(path)==root/'head.json': raise KeyboardInterrupt()
        return result
    monkeypatch.setattr(store,'_durable_save',fail)
    with pytest.raises(KeyboardInterrupt): commit(setup)
    assert load_memory(root).head['revision']==1
    monkeypatch.setattr(store,'_durable_save',original)
    commit(setup)
    assert load_memory(root).head['revision']==1


@pytest.mark.parametrize('name',['record.json','ledger.json','candidate/learner/pairs.json',
                                 'attribution/response.json','gate.json','audit.json'])
def test_corrupt_archive_is_not_consumed(setup,name):
    root,_,_=setup
    ref=commit(setup)
    path=root/'rounds'/ref['sha256']/name
    path.write_text('{}')
    with pytest.raises(MemoryRejected): load_memory(root)


def test_head_skill_tampering_rejected(setup):
    root,_,_=setup
    commit(setup)
    head=_load(root/'head.json');head['retained_skill']='forged';_save(root/'head.json',head)
    with pytest.raises(MemoryRejected): load_memory(root)


def test_unsafe_head_path_is_rejected(setup):
    root,_,_=setup
    head=_load(root/'head.json');head['memory_ref']={'artifact_id':'MEMORY/x','sha256':'../../elsewhere'}
    _save(root/'head.json',head)
    with pytest.raises(MemoryRejected): load_memory(root)


def test_context_safe_immutable_and_all_counterevidence_retained(setup):
    root,ledger,_=setup
    commit(setup)
    context=retrieve_memory(store_dir=root,current_parent=ledger.source['candidate_skill'])
    for private in ('PRIVATE-', 'HIDDEN_', 'private_database', 'expected_action', 'user_prompt', 'seed', 'monitor_score'):
        assert private not in context.payload_json
    data=context.payload
    assert len(data['rounds'][0]['attribution']['records'][0]['observations'])==2
    assert len(data['rounds'][0]['replay']['pairs'])==3
    data['rounds'].clear()
    assert context.payload['rounds']


def test_budget_does_not_truncate_evidence(setup):
    root,ledger,_=setup
    commit(setup)
    current=ledger.source['candidate_skill']
    with pytest.raises(MemoryBudgetExceeded): retrieve_memory(store_dir=root,current_parent=current,max_chars=100)
    context=retrieve_memory(store_dir=root,current_parent=current,max_chars=1000000)
    assert len(context.payload_json)<=1000000
    assert len(context.payload['rounds'][0]['replay']['pairs'])==3


def test_retrieval_priorities_exclusions_and_explicit_edit(setup,case,tmp_path):
    root,ledger,_=setup
    first=commit(setup)
    snap=load_memory(root)
    second,kw=make_round(case,tmp_path/'second',history=snap.history,parent=snap.head['retained_skill'],
                         round_id='r2',decision='RETAIN',effects=lambda d:[record(d)])
    commit_round_memory(second,store_dir=root,expected_head_ref=first,**kw)
    context=retrieve_memory(store_dir=root,current_parent=snap.head['retained_skill'],max_rounds=1).payload
    assert context['rounds'][0]['memory_record']['round_id']=='r1'
    assert not context['selection']['complete_history']
    assert next(u for u in context['selection']['units'] if not u['selected'])['exclusion_reason']=='ROUND_BUDGET'
    explicit=retrieve_memory(store_dir=root,current_parent=snap.head['retained_skill'],max_rounds=1,
                             edit_ids=(second.payload['edits'][0]['edit_id'],)).payload
    assert explicit['rounds'][0]['memory_record']['round_id']=='r2'
    with pytest.raises(MemoryRejected):
        retrieve_memory(store_dir=root,current_parent=snap.head['retained_skill'],edit_ids=('EDIT/unknown',))


def test_cross_round_links_form_indivisible_evidence_unit(setup,case,tmp_path):
    root,ledger,_=setup
    first=commit(setup)
    snap=load_memory(root)
    second,kw=make_round(case,tmp_path/'second',history=snap.history,parent=snap.head['retained_skill'],
                         round_id='r2',specs=[('NEEDS_REVISION',[1])],texts=[(0,'- Revised')],
                         links=(link(ledger),))
    commit_round_memory(second,store_dir=root,expected_head_ref=first,**kw)
    current=load_memory(root).head['retained_skill']
    with pytest.raises(MemoryBudgetExceeded): retrieve_memory(store_dir=root,current_parent=current,max_rounds=1)
    context=retrieve_memory(store_dir=root,current_parent=current,max_rounds=2).payload
    assert len(context['selection']['units'])==1 and len(context['rounds'])==2
    binding=context['rounds'][0]['current_bindings'][0]
    assert binding['related_followups'][0]['edit_id']==second.payload['edits'][0]['edit_id']
    assert binding['binding_status']=='UNRESOLVED'


def test_delete_all_content_keeps_empty_retained_skill(case,tmp_path):
    root=tmp_path/'memory'
    initialize_memory(store_dir=root,run_id='test-run',initial_skill='- Parent\n')
    ledger,kwargs=make_round(case,tmp_path/'stage',specs=[('SHOULD_REMOVE',[0])],texts=[])
    commit_round_memory(ledger,store_dir=root,expected_head_ref=None,**kwargs)
    assert load_memory(root).head['retained_skill']==''
    context=retrieve_memory(store_dir=root,current_parent='').payload
    binding=context['rounds'][0]['current_bindings'][0]
    assert binding['binding_subject']=='DELETED_TARGETS' and binding['binding_status']=='ABSENT'


def test_lock_refuses_parallel_writer(setup):
    root,_,_=setup
    with _lock(root):
        with pytest.raises(ValueError): commit(setup)
    assert load_memory(root).head['revision']==0


@pytest.mark.parametrize('budget',[0,-1,True,1.5])
def test_invalid_budget(setup,budget):
    root,_,_=setup
    with pytest.raises(MemoryRejected): retrieve_memory(store_dir=root,current_parent='- Parent\n',max_chars=budget)


def test_new_process_can_load_without_live_backend(setup):
    import subprocess
    import sys
    root,_,_=setup
    commit(setup)
    result=subprocess.run([sys.executable,'-c',
        'import sys; from src.skill_evolution.memory_store_v19 import load_memory; '
        'from src.skill_evolution.memory_retrieval_v19 import retrieve_memory; '
        's=load_memory(sys.argv[1]); '
        'c=retrieve_memory(store_dir=sys.argv[1],current_parent=s.head["retained_skill"]); '
        'print(s.head["revision"],len(c.payload["rounds"]))',str(root)],
        cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='1 1'


def test_snapshot_copy_interruption_does_not_publish(setup,monkeypatch):
    import src.skill_evolution.memory_store_v19 as store
    root,_,_=setup
    original=store.shutil.copyfile
    calls=[]
    def fail(source,target):
        calls.append(1)
        if len(calls)==4: raise OSError('interrupted copy')
        return original(source,target)
    monkeypatch.setattr(store.shutil,'copyfile',fail)
    with pytest.raises(OSError): commit(setup)
    assert load_memory(root).head['revision']==0
    assert list((root/'pending').iterdir())
    monkeypatch.setattr(store.shutil,'copyfile',original)
    commit(setup)
    assert load_memory(root).head['revision']==1


def test_retain_then_retry_preserves_original_decision_and_evidence(case,tmp_path):
    root=tmp_path/'memory'
    initialize_memory(store_dir=root,run_id='test-run',initial_skill='- Parent\n')
    first,kw=make_round(case,tmp_path/'first',decision='RETAIN',effects=lambda d:[record(d)])
    ref=commit_round_memory(first,store_dir=root,expected_head_ref=None,**kw)
    history=load_memory(root).history
    second,kw2=make_round(case,tmp_path/'second',history=history,round_id='r2',
                          texts=[(0,'- New rule r1')],links=(link(first,relation='RETRIES'),))
    commit_round_memory(second,store_dir=root,expected_head_ref=ref,**kw2)
    snap=load_memory(root)
    ctx=retrieve_memory(store_dir=root,current_parent=snap.head['retained_skill']).payload
    old=ctx['rounds'][0]
    assert old['memory_record']['gate_decision']=='RETAIN'
    assert old['attribution']['records'][0]['effect']=='BENEFICIAL'
    assert old['current_bindings'][0]['binding_status']=='EXACT'
    assert old['current_bindings'][0]['related_followups'][0]['relation']=='RETRIES'
    assert len(ctx['selection']['units'])==1


def test_partial_binding_updates_without_explicit_semantic_link(case,tmp_path):
    root=tmp_path/'memory'
    initialize_memory(store_dir=root,run_id='test-run',initial_skill='- Parent\n')
    first,kw=make_round(case,tmp_path/'first',texts=[(0,'- A\n\n- B')])
    ref=commit_round_memory(first,store_dir=root,expected_head_ref=None,**kw)
    snap=load_memory(root)
    second,kw2=make_round(case,tmp_path/'second',history=snap.history,parent=snap.head['retained_skill'],
                          round_id='r2',specs=[('SHOULD_REMOVE',[1])],texts=[])
    commit_round_memory(second,store_dir=root,expected_head_ref=ref,**kw2)
    current=load_memory(root).head['retained_skill']
    ctx=retrieve_memory(store_dir=root,current_parent=current).payload
    assert ctx['rounds'][0]['current_bindings'][0]['binding_status']=='PARTIAL'
    assert ctx['rounds'][0]['current_bindings'][0]['structural_changes']
    assert len(ctx['selection']['units'])==1


def test_query_matches_visible_text_including_chinese(case,tmp_path):
    root=tmp_path/'memory'
    initialize_memory(store_dir=root,run_id='test-run',initial_skill='- Parent\n')
    ledger,kw=make_round(case,tmp_path/'first',texts=[(0,'- 修改订单前验证用户授权')])
    commit_round_memory(ledger,store_dir=root,expected_head_ref=None,**kw)
    ctx=retrieve_memory(store_dir=root,current_parent=ledger.source['candidate_skill'],query='用户授权').payload
    unit=ctx['selection']['units'][0]
    assert 'LEXICAL_QUERY_MATCH' in unit['retrieval_reasons']
    assert unit['lexical_overlap']>0


def test_character_budget_selects_whole_round_with_explicit_exclusion(setup,case,tmp_path):
    root,_,_=setup
    ref=commit(setup)
    snap=load_memory(root)
    second,kw=make_round(case,tmp_path/'second',history=snap.history,parent=snap.head['retained_skill'],
                         round_id='r2',decision='RETAIN',effects=lambda d:[record(d)])
    commit_round_memory(second,store_dir=root,expected_head_ref=ref,**kw)
    one=retrieve_memory(store_dir=root,current_parent=snap.head['retained_skill'],max_rounds=1)
    budget=len(one.payload_json)+200
    limited=retrieve_memory(store_dir=root,current_parent=snap.head['retained_skill'],max_chars=budget)
    assert len(limited.payload_json)<=budget
    assert len(limited.payload['rounds'])==1
    assert len(limited.payload['rounds'][0]['replay']['pairs'])==3
    assert any(u['exclusion_reason']=='CHARACTER_BUDGET' for u in limited.payload['selection']['units'])


def test_evolution_manifest_drift_blocks_new_round(setup,case,tmp_path):
    root,_,_=setup
    ref=commit(setup)
    snap=load_memory(root)
    second,kw=make_round(case,tmp_path/'second',history=snap.history,parent=snap.head['retained_skill'],round_id='r2')
    kw['backend'].tasks.reverse()
    with pytest.raises(ValueError):
        commit_round_memory(second,store_dir=root,expected_head_ref=ref,**kw)
    assert load_memory(root).head['revision']==1
