from dataclasses import replace
from pathlib import Path

import pytest

from src.skill_evolution.v19.edit_tracking_v19 import encode, parse, digest, validate_edit_ledger, EditLedger
from src.skill_evolution.v19.memory_store_v19 import initialize_memory, load_memory, commit_round_memory, MemoryRejected
from src.skill_evolution.v19.evolution_replay_v19 import run_parent_evolution, load_parent_experiences, _load, _save
from src.skill_evolution.v17.experience_cards_v17 import build_experience_cards
from src.skill_evolution.v17.experience_grouping_contract_v17 import bind_grouping_result
from src.skill_evolution.v19.memory_diagnosis_v19 import build_memory_diagnosis_inputs, validate_memory_diagnosis_response
from src.skill_evolution.v19.memory_generation_prompt_v19 import build_memory_diagnosis_request
from src.skill_evolution.v19.memory_generation_v19 import run_memory_generation, load_memory_generation
from src.skill_evolution.v15.information_boundary_v15 import _seal
from tests.skill_evolution.v19.test_memory_v19 import case, make_round
from tests.skill_evolution.v19.test_evolution_replay_v19 import Backend
from tests.skill_evolution.v19.test_attribution_v19 import complete, record


def current(root,round_id='r2',all_success=False,groups=1):
    snap=load_memory(root/'memory')
    backend=Backend(snap.head['retained_skill'])
    if all_success:
        backend.label_mutator=lambda x:x.update(success=True,compliant=True)
    parent=root/('parent-'+round_id)
    run_parent_evolution(run_id='test-run',round_id=round_id,parent_skill=snap.head['retained_skill'],
                         backend=backend,artifact_dir=parent)
    sources,scope=load_parent_experiences(run_id='test-run',round_id=round_id,parent_skill=snap.head['retained_skill'],
                                         backend=backend,artifact_dir=parent)
    members=[s.ref.task_ref for s in sources]
    parts=[members] if groups==1 else [[m] for m in members]
    grouping=bind_grouping_result(build_experience_cards(sources,scope=scope).payload,{'groups':[
        {'group_id':f'G{i}', 'decision_problem':'Visible request handling','members':part,
         'shared_basis':'Observed change requests','important_differences':[]} for i,part in enumerate(parts)]},scope=scope)
    return dict(store_dir=root/'memory',backend=backend,parent_dir=parent,round_id=round_id,grouping_result=grouping)


@pytest.fixture
def setup(case,tmp_path):
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    old,kw=make_round(case,tmp_path/'r1')
    commit_round_memory(old,store_dir=tmp_path/'memory',expected_head_ref=None,**kw)
    return tmp_path,old,current(tmp_path)


def expand_projection(payload):
    # Test consumer follows the published wire references, not private input.json.
    from copy import deepcopy
    payload = deepcopy(payload)
    if 'representation_version' not in payload:
        return payload
    bodies = payload.pop('event_bodies')
    def expand(value):
        if isinstance(value, list): return [expand(v) for v in value]
        if isinstance(value, dict):
            if 'event_body_ref' in value:
                return {**bodies[value['event_body_ref']], 'evidence_ref': value['evidence_ref']}
            return {k: expand(v) for k, v in value.items()}
        return value
    payload = expand(payload)
    experiences = {e['experience_ref']: e for e in payload['experiences']}
    contexts = {c['context_ref']: c for c in payload['contexts']}
    for row in payload['memory_context']['rounds']:
        replay = row['replay']
        replay['contexts'] = [contexts[r] for r in replay.pop('context_refs')]
        for pair in replay['pairs']:
            for role in ('parent', 'candidate'):
                exp = experiences[pair[role]['experience_ref']]
                pair[role] = {k: exp[k] for k in ('context_ref', 'events', 'role', 'skill_ref',
                                                 'supervision', 'trajectory_ref')}
    for exp in payload['experiences']:
        exp.pop('experience_ref')
    payload.pop('representation_version')
    payload.pop('canonical_payload_sha256')
    payload.pop('memory_review_requirements')
    payload.pop('diagnosis_contract_summary')
    return payload


def raw_for(payload,*,kind='NEEDS_REVISION',relation='REVISES',defer=False):
    payload = expand_projection(payload)
    memory=payload['memory_context']
    historical=memory['rounds']
    reviews=[]
    evidence=[]
    supervision=[]
    rules=[]
    if historical:
        pair=historical[0]['replay']['pairs'][0]
        evidence=[next(e['evidence_ref'] for e in pair[role]['events'] if e['event_type']=='tool_call')
                  for role in ('parent','candidate')]
        supervision=[pair[role]['supervision']['supervision_ref'] for role in ('parent','candidate')]
        rules=historical[0]['current_bindings'][0]['current_rule_refs']
        for row in historical:
            for edit in row['edits']:
                reviews.append({'edit_id':edit['edit_id'],'decision':'DEFER' if defer else 'USE',
                    'relation':'NONE' if defer else relation, 'gap_indices':[] if defer else [0],
                    'evidence_refs':[] if defer else evidence,
                    'reason':'Reassess paired behavior against current scope; package decision is not evidence.'})
    else:
        e=payload['experiences'][0]
        evidence=[next(x['evidence_ref'] for x in e['events'] if x['event_type']=='tool_call')]
        supervision=[e['supervision']['supervision_ref']]
    diagnosis={'success_analysis':{'finding':'Conditional choice could be improved within observed scope.',
        'evidence_refs':evidence,'supervision_refs':supervision,'unresolved':['Sampling and other edits remain confounded.']},
        'compliance_analysis':{'finding':'Keep applicable public constraints.','evidence_refs':[],
                               'supervision_refs':[],'unresolved':[]},
        'skill_addressability':{'status':'NOT_ADDRESSABLE' if defer else 'ADDRESSABLE',
                               'reason':'No supported current change.' if defer else 'Reauthorize an executable conditional correction.'},
        'parent_skill_gaps':[] if defer else [{'kind':kind,'gap':'Retain useful conditions and revise the unsupported scope.',
            'evidence_refs':evidence,'related_rule_refs':[] if kind=='MISSING' else rules,
            'source_dimensions':['SUCCESS']}]}
    return encode({'schema_version':'memory_diagnosis_response_v19.1','diagnosis':diagnosis,'memory_review':reviews})


def editor(request):
    units=parse(request['user_prompt'])['edit_units']
    return complete(encode({'status':'EDITED','reason':'Preserve scope and apply authorized corrections.',
        'edits':[{'edit_unit_index':u['edit_unit_index'],'text':'- Revised conditional guidance'} for u in units]}))


def run(kwargs,path,diagnose=None,edit=editor,**extra):
    return run_memory_generation(**kwargs,artifact_dir=path,
        diagnosis_transport=diagnose or (lambda r:complete(raw_for(parse(r['user_prompt'])))),
        editor_transport=edit,**extra)


def test_accepted_bad_edit_revised_and_ledger_remains_restorable(setup):
    root,old,kwargs=setup
    before=load_memory(kwargs['store_dir'])
    result=run(kwargs,root/'generation')
    assert result.status=='EDITED' and '- Parent\n' in result.candidate_skill
    assert '- Revised conditional guidance' in result.candidate_skill
    assert '- New rule r1' not in result.candidate_skill
    edit=result.ledger.payload['edits'][0]
    assert edit['operation']=='REPLACE'
    assert edit['related_history'][0]['prior_edit_id']==old.payload['edits'][0]['edit_id']
    assert edit['related_history'][0]['relation']=='REVISES'
    assert edit['source_gap_refs'] and edit['related_history'][0]['basis_refs']
    validate_edit_ledger(result.ledger,history=before.history)
    assert load_memory_generation(**kwargs,artifact_dir=root/'generation')==result
    assert load_memory(kwargs['store_dir']).head==before.head
    evidence=result.ledger.payload['evidence']
    assert all(e['resolved']['origin']=='COMMITTED_HISTORICAL_OBSERVATION' for e in evidence)
    assert {e['resolved']['role'] for e in evidence}=={'PARENT','CANDIDATE'}


def test_rejected_good_edit_retried_as_new_add(case,tmp_path):
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    old,kw=make_round(case,tmp_path/'r1',decision='RETAIN',effects=lambda d:[record(d)])
    commit_round_memory(old,store_dir=tmp_path/'memory',expected_head_ref=None,**kw)
    kwargs=current(tmp_path,all_success=True)
    result=run(kwargs,tmp_path/'generation',diagnose=lambda r:complete(raw_for(parse(r['user_prompt']),
                                                                          kind='MISSING',relation='RETRIES')))
    edit=result.ledger.payload['edits'][0]
    assert edit['operation']=='ADD'
    assert edit['edit_id']!=old.payload['edits'][0]['edit_id']
    assert edit['related_history'][0]['relation']=='RETRIES'
    assert result.candidate_skill.startswith('- Parent\n')


def test_all_success_current_group_still_reviews_history(setup):
    root,old,_=setup
    kwargs=current(root,round_id='r3',all_success=True)
    request=build_memory_diagnosis_inputs(**kwargs)[0]
    experiences=request.learner_payload['experiences']
    assert all(e['supervision']['success'] for e in experiences if e['origin']=='CURRENT_PARENT')
    assert any(not e['supervision']['success'] for e in experiences if e['origin']!='CURRENT_PARENT')
    result=run(kwargs,root/'success-review')
    assert result.ledger is not None


def test_defer_reaches_no_update_only_after_review(setup):
    root,old,kwargs=setup
    def forbidden(_): raise AssertionError('Editor should not run')
    result=run(kwargs,root/'noop',diagnose=lambda r:complete(raw_for(parse(r['user_prompt']),defer=True)),edit=forbidden)
    assert result.status=='NO_UPDATE' and result.candidate_skill is None and result.ledger is None
    assert parse(result.audit_json)['diagnoses'][0]['provenance']['memory_response']


def test_empty_memory_still_generates_from_current_evidence(tmp_path):
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    kwargs=current(tmp_path,round_id='r1')
    result=run(kwargs,tmp_path/'generation',diagnose=lambda r:complete(raw_for(parse(r['user_prompt']),kind='MISSING')))
    assert result.ledger.payload['edits'][0]['related_history']==[]
    validate_edit_ledger(result.ledger)


@pytest.mark.parametrize('mutate',[
    lambda o,p:o.update(memory_review=[]),
    lambda o,p:o['memory_review'].append(o['memory_review'][0]),
    lambda o,p:o['memory_review'][0].update(edit_id='EDIT/unknown'),
    lambda o,p:o['memory_review'][0].update(gap_indices=[True]),
    lambda o,p:o['memory_review'][0].update(evidence_refs=o['memory_review'][0]['evidence_refs'][:1]),
    lambda o,p:o['memory_review'][0].update(evidence_refs=[p['memory_context']['rounds'][0]['attribution']['records'][0]['attribution_id']]),
    lambda o,p:o['memory_review'][0].update(decision='DEFER',relation='NONE',gap_indices=[]),
    lambda o,p:o['memory_review'][0].update(relation='RETRIES'),
    lambda o,p:o['diagnosis']['parent_skill_gaps'][0].update(related_rule_refs=['RULE/old/L1']),
    lambda o,p:o['diagnosis']['parent_skill_gaps'][0].update(evidence_refs=o['memory_review'][0]['evidence_refs'][:1]),
    lambda o,p:o['memory_review'][0].update(gate_decision='ACCEPT'),
])
def test_invalid_memory_review_and_old_targets_rejected(setup,mutate):
    _,_,kwargs=setup
    request=build_memory_diagnosis_inputs(**kwargs)[0]
    payload=request.learner_payload
    output=parse(raw_for(payload));mutate(output,payload)
    with pytest.raises(ValueError):validate_memory_diagnosis_response(encode(output),request=request)


def test_input_keeps_identity_and_no_private_fields(setup):
    _,_,kwargs=setup
    request=build_memory_diagnosis_inputs(**kwargs)[0]
    payload=request.learner_payload
    assert len(payload['experiences'])==9
    assert len(payload['available_evidence_refs'])==45
    for private in ('PRIVATE-', 'HIDDEN_', 'private_database', 'expected_action', 'monitor_score'):
        assert private not in encode(payload)
    assert set(payload['available_rule_refs'])==set(build_memory_diagnosis_inputs(**kwargs)[0].learner_payload['available_rule_refs'])
    assert any(v['origin']=='CURRENT_PARENT' for v in payload['available_evidence_refs'].values())
    assert 'SHOULD_REMOVE' in build_memory_diagnosis_request(request)['system_prompt']


def test_complete_groups_and_input_budget_are_enforced(setup):
    root,_,_=setup
    kwargs=current(root,round_id='r3',groups=3)
    requests=build_memory_diagnosis_inputs(**kwargs)
    assert len(requests)==4  # Equal tool/context overlap is not resolved by group order.
    assert all(not r.learner_payload['memory_context']['rounds'] for r in requests[:3])
    assert len(requests[-1].learner_payload['memory_context']['rounds'])==1
    assert all(len([e for e in r.learner_payload['experiences'] if e['origin']=='CURRENT_PARENT'])==1 for r in requests[:3])
    assert all(e['origin']!='CURRENT_PARENT' for e in requests[-1].learner_payload['experiences'])
    with pytest.raises(ValueError):build_memory_diagnosis_inputs(**kwargs,max_input_chars=100)
    kwargs['grouping_result']['groups'].pop()
    with pytest.raises(ValueError):build_memory_diagnosis_inputs(**kwargs)


def test_editor_sees_authorized_lineage_not_whole_memory(setup):
    root,old,kwargs=setup
    seen=[]
    def inspect(request):
        payload=parse(request['user_prompt']);seen.append(payload)
        assert 'memory_context' not in payload
        assert payload['edit_units'][0]['memory_lineage'][0]['historical_edit']['edit_id']==old.payload['edits'][0]['edit_id']
        assert all('origin' in e for e in payload['edit_units'][0]['evidence_catalog'].values()
                   if e['reference_type']=='TRAJECTORY')
        return editor(request)
    run(kwargs,root/'generation',edit=inspect)
    assert len(seen)==1


def test_completed_resume_no_models(setup):
    root,_,kwargs=setup
    result=run(kwargs,root/'generation')
    def forbidden(_):raise AssertionError('no new call')
    assert run(kwargs,root/'generation',diagnose=forbidden,edit=forbidden,resume=True)==result
    with pytest.raises(ValueError):run(kwargs,root/'generation')


def test_transport_failure_never_no_update_or_automatic_retry(setup):
    root,_,kwargs=setup
    calls=[]
    def fail(_):calls.append(1);raise RuntimeError('PRIVATE_PROVIDER')
    with pytest.raises(RuntimeError):run(kwargs,root/'failed',diagnose=fail)
    assert _load(root/'failed/validation.json')['status']=='INCOMPLETE'
    with pytest.raises(ValueError):run(kwargs,root/'failed',diagnose=fail,resume=True)
    assert calls==[1]
    assert 'PRIVATE_PROVIDER' not in (root/'failed/validation.json').read_text()


def test_invalid_diagnosis_stops_before_editor(setup):
    root,_,kwargs=setup
    def forbidden(_):raise AssertionError('no editor on invalid diagnosis')
    with pytest.raises(ValueError):run(kwargs,root/'failed',diagnose=lambda _:complete('{}'),edit=forbidden)
    assert not (root/'failed/generation.json').exists()


def test_editor_unable_is_not_candidate(setup):
    root,_,kwargs=setup
    result=run(kwargs,root/'unable',edit=lambda _:complete(encode({'status':'UNABLE','reason':'unsupported','edits':[]})))
    assert result.status=='UNABLE' and result.ledger is None and result.candidate_skill is None


def test_removed_cross_round_links_rejected_by_ledger_restore(setup):
    root,_,kwargs=setup
    result=run(kwargs,root/'generation')
    source=result.ledger.source;source['related_history']=[]
    with pytest.raises(ValueError):
        validate_edit_ledger(EditLedger(encode(source),result.ledger.output_json),history=load_memory(kwargs['store_dir']).history)


def test_resume_after_final_write_interruption_reuses_responses(setup,monkeypatch):
    import src.skill_evolution.v19.memory_generation_v19 as generation
    root,_,kwargs=setup
    original=generation._save
    def fail(path,value):
        if path.name=='generation.json':raise KeyboardInterrupt()
        original(path,value)
    monkeypatch.setattr(generation,'_save',fail)
    with pytest.raises(KeyboardInterrupt):run(kwargs,root/'interrupted')
    monkeypatch.setattr(generation,'_save',original)
    def forbidden(_):raise AssertionError('saved response must be reused')
    assert run(kwargs,root/'interrupted',diagnose=forbidden,edit=forbidden,resume=True).ledger


def test_committed_round_cannot_be_reused_as_next_round(setup):
    _,_,kwargs=setup
    kwargs['round_id']='r1'
    with pytest.raises(ValueError):build_memory_diagnosis_inputs(**kwargs)


def test_generated_ledger_runs_through_existing_replay_attribution_and_memory(setup):
    from src.skill_evolution.v19.evolution_replay_v19 import run_candidate_replay
    from src.skill_evolution.v19.attribution_v19 import build_attribution_input, run_attribution
    from src.skill_evolution.v19.memory_retrieval_v19 import retrieve_memory
    from tests.skill_evolution.v19.test_memory_v19 import receipt
    from tests.skill_evolution.v19.test_attribution_v19 import response
    root,old,kwargs=setup
    before=load_memory(kwargs['store_dir'])
    generated=run(kwargs,root/'generation')
    replay=root/'r2-replay'; attribution=root/'r2-attribution'
    run_candidate_replay(generated.ledger,backend=kwargs['backend'],parent_dir=kwargs['parent_dir'],
                         artifact_dir=replay,history=before.history)
    data=build_attribution_input(generated.ledger,backend=kwargs['backend'],parent_dir=kwargs['parent_dir'],
                                 replay_dir=replay,history=before.history)
    run_attribution(generated.ledger,backend=kwargs['backend'],parent_dir=kwargs['parent_dir'],
                    replay_dir=replay,artifact_dir=attribution,history=before.history,
                    transport=lambda _:complete(response(record(data,(0,1),'MIXED'))))
    commit_round_memory(generated.ledger,store_dir=kwargs['store_dir'],expected_head_ref=before.head['memory_ref'],
        backend=kwargs['backend'],parent_dir=kwargs['parent_dir'],replay_dir=replay,
        attribution_dir=attribution,gate_result=receipt(generated.ledger))
    after=load_memory(kwargs['store_dir'])
    assert after.head['revision']==2
    context=retrieve_memory(store_dir=kwargs['store_dir'],current_parent=after.head['retained_skill']).payload
    assert len(context['rounds'])==2
    assert context['rounds'][0]['current_bindings'][0]['related_followups'][0]['relation']=='REVISES'


def test_whole_rule_removal_reauthorized_no_editor_model(setup):
    root,_,kwargs=setup
    def forbidden(_):raise AssertionError('pure DELETE needs no editor call')
    result=run(kwargs,root/'delete',diagnose=lambda r:complete(raw_for(parse(r['user_prompt']),
                      kind='SHOULD_REMOVE',relation='REVERTS')),edit=forbidden)
    assert result.status=='APPLIED_DETERMINISTIC'
    assert '- New rule r1' not in result.candidate_skill
    assert result.ledger.payload['edits'][0]['operation']=='DELETE'
    assert result.ledger.payload['edits'][0]['related_history'][0]['relation']=='REVERTS'


def test_restore_deleted_guidance_requires_new_missing_gap(case,tmp_path):
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    old,kw=make_round(case,tmp_path/'r1',specs=[('SHOULD_REMOVE',[0])],texts=[])
    commit_round_memory(old,store_dir=tmp_path/'memory',expected_head_ref=None,**kw)
    kwargs=current(tmp_path)
    result=run(kwargs,tmp_path/'generation',diagnose=lambda r:complete(raw_for(parse(r['user_prompt']),
                    kind='MISSING',relation='REVERTS')))
    assert result.candidate_skill=='- Revised conditional guidance\n'
    assert result.ledger.payload['edits'][0]['operation']=='ADD'
    assert result.ledger.payload['edits'][0]['related_history'][0]['relation']=='REVERTS'


def test_success_only_current_and_history_can_explicitly_no_issue(tmp_path):
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    kwargs=current(tmp_path,round_id='r1',all_success=True)
    def diagnose(request):
        out=parse(raw_for(parse(request['user_prompt']),defer=True))
        out['diagnosis']['skill_addressability']['status']='NO_ISSUE'
        return complete(encode(out))
    assert run(kwargs,tmp_path/'noop',diagnose=diagnose).status=='NO_UPDATE'


def test_bad_editor_cannot_modify_unauthorized_units(setup):
    root,_,kwargs=setup
    def bad(_):return complete(encode({'status':'EDITED','reason':'extra edit',
        'edits':[{'edit_unit_index':0,'text':'authorized'},{'edit_unit_index':1,'text':'unauthorized'}]}))
    with pytest.raises(ValueError):run(kwargs,root/'bad-editor',edit=bad)
    assert not (root/'bad-editor/generation.json').exists()


def test_saved_response_corruption_and_prompt_drift_are_rejected(setup,monkeypatch):
    import src.skill_evolution.v19.memory_generation_prompt_v19 as prompt
    root,_,kwargs=setup
    run(kwargs,root/'done')
    monkeypatch.setattr(prompt,'MEMORY_INSTRUCTIONS',prompt.MEMORY_INSTRUCTIONS+' changed')
    with pytest.raises(ValueError):load_memory_generation(**kwargs,artifact_dir=root/'done')


def test_rehashed_generated_candidate_tampering_rejected(setup):
    from src.skill_evolution.v19.evolution_replay_v19 import _file_digest
    root,_,kwargs=setup
    run(kwargs,root/'done')
    path=root/'done/generation.json'
    output=_load(path);output['candidate_skill']='forged';_save(path,output)
    marker=_load(root/'done/validation.json');marker['files']['generation.json']=_file_digest(path)
    _save(root/'done/validation.json',marker)
    with pytest.raises(ValueError):load_memory_generation(**kwargs,artifact_dir=root/'done')


def test_changed_memory_head_during_model_call_blocks_publication(setup,monkeypatch):
    import src.skill_evolution.v19.memory_generation_v19 as generation
    root,_,kwargs=setup
    original=generation._check_head
    def changed(*_):raise MemoryRejected('memory advanced during generation')
    monkeypatch.setattr(generation,'_check_head',changed)
    with pytest.raises(ValueError):run(kwargs,root/'stale')
    assert not (root/'stale/generation.json').exists()
    assert _load(root/'stale/validation.json')['status']=='INCOMPLETE'


def test_review_tamper_in_ledger_provenance_rejected(setup):
    root,_,kwargs=setup
    result=run(kwargs,root/'generation')
    source=result.ledger.source
    entry=source['editor']['sources'][0]
    output=parse(entry['provenance']['memory_response']);output['memory_review']=[]
    entry['provenance']['memory_response']=encode(output)
    entry['provenance']['memory_response_sha256']=digest(encode(output))
    with pytest.raises(ValueError):
        validate_edit_ledger(EditLedger(encode(source),result.ledger.output_json),history=load_memory(kwargs['store_dir']).history)


def test_manifest_drift_rejected_before_generation(setup):
    _,_,kwargs=setup
    kwargs['backend'].seed+=1
    with pytest.raises(ValueError,match='manifest'):build_memory_diagnosis_inputs(**kwargs)


def test_memory_budget_failure_is_not_silent_no_update(setup):
    root,_,kwargs=setup
    with pytest.raises(ValueError):run(kwargs,root/'no-budget',max_memory_chars=100)
    assert not (root/'no-budget').exists()


def test_rejected_delete_can_be_retried_only_with_new_removal_gap(case,tmp_path):
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    old,kw=make_round(case,tmp_path/'r1',decision='RETAIN',specs=[('SHOULD_REMOVE',[0])],texts=[])
    commit_round_memory(old,store_dir=tmp_path/'memory',expected_head_ref=None,**kw)
    kwargs=current(tmp_path)
    result=run(kwargs,tmp_path/'retry-delete',diagnose=lambda r:complete(raw_for(parse(r['user_prompt']),
                kind='SHOULD_REMOVE',relation='RETRIES')))
    assert result.candidate_skill==''
    assert result.ledger.payload['edits'][0]['related_history'][0]['relation']=='RETRIES'


def test_rejected_replace_can_revise_original_current_target(case,tmp_path):
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    old,kw=make_round(case,tmp_path/'r1',decision='RETAIN',specs=[('NEEDS_REVISION',[0])],texts=[(0,'- Unaccepted revision')])
    commit_round_memory(old,store_dir=tmp_path/'memory',expected_head_ref=None,**kw)
    kwargs=current(tmp_path)
    def diagnose(request):
        payload=parse(request['user_prompt'])
        output=parse(raw_for(payload,relation='RETRIES'))
        output['diagnosis']['parent_skill_gaps'][0]['related_rule_refs']=list(payload['available_rule_refs'])
        return complete(encode(output))
    result=run(kwargs,tmp_path/'retry-replace',diagnose=diagnose)
    assert result.ledger.payload['edits'][0]['operation']=='REPLACE'
    assert result.ledger.payload['edits'][0]['related_history'][0]['relation']=='RETRIES'


def test_multiple_current_groups_do_not_multiply_historical_support(setup):
    root,_,_=setup
    kwargs=current(root,round_id='r3',groups=3)
    result=run(kwargs,root/'multi',diagnose=lambda r:complete(raw_for(
        parse(r['user_prompt']),defer=not parse(r['user_prompt'])['memory_context']['rounds'])))
    assert len(result.ledger.payload['edits'])==1
    edit=result.ledger.payload['edits'][0]
    assert len(edit['source_gap_refs'])==1
    assert len(edit['related_history'])==1
    assert len(edit['related_history'][0]['basis_refs'])==2


def test_new_process_restores_memory_generated_ledger(setup):
    import subprocess
    import sys
    from src.skill_evolution.v19.edit_tracking_store_v19 import save_edit_ledger
    root,_,kwargs=setup
    result=run(kwargs,root/'generation')
    snapshot=load_memory(kwargs['store_dir'])
    save_edit_ledger(result.ledger,artifact_dir=root/'ledger',history=snapshot.history)
    output=subprocess.run([sys.executable,'-c',
        'import sys;from src.skill_evolution.v19.memory_store_v19 import load_memory;'
        'from src.skill_evolution.v19.edit_tracking_store_v19 import load_edit_ledger;'
        's=load_memory(sys.argv[1]);l=load_edit_ledger(sys.argv[2],history=s.history);'
        'print(l.payload["edits"][0]["related_history"][0]["relation"])',
        str(kwargs['store_dir']),str(root/'ledger')],capture_output=True,text=True,check=True,
        cwd=Path(__file__).resolve().parents[3])
    assert output.stdout.strip()=='REVISES'


def test_wire_projection_preserves_all_evidence_and_hypotheses(setup):
    from copy import deepcopy
    _, _, kwargs = setup
    request = build_memory_diagnosis_inputs(**kwargs)[0]
    original = request.learner_payload
    before = encode(original)
    wire = parse(build_memory_diagnosis_request(request)['user_prompt'])
    restored = expand_projection(wire)
    for key in ('available_evidence_refs', 'available_supervision_refs'):
        restored[key] = original[key]  # These indexes are tested separately below.
    assert restored == original
    assert encode(request.learner_payload) == before
    events = {e['evidence_ref']: (x, wire['event_bodies'][e['event_body_ref']])
              for x in wire['experiences'] for e in x['events']}
    assert set(events) == set(original['available_evidence_refs'])
    for ref, catalog in original['available_evidence_refs'].items():
        experience, body = events[ref]
        assert all((body['step'] if key == 'step' else experience[key]) == val
                   for key, val in catalog.items())
    labels = {e['supervision']['supervision_ref']: e for e in wire['experiences']}
    assert set(labels) == set(original['available_supervision_refs'])
    for ref, catalog in original['available_supervision_refs'].items():
        assert all((0 if key == 'level' else labels[ref][key]) == val for key, val in catalog.items())
    assert len(set(map(encode, wire['event_bodies'].values()))) == len(wire['event_bodies'])
    assert wire['canonical_payload_sha256'] == digest(before)
    broken = deepcopy(original)
    broken['memory_context']['rounds'][0]['replay']['pairs'][0]['parent']['events'][0]['content'] = 'different'
    from src.skill_evolution.v19.memory_generation_prompt_v19 import diagnosis_projection
    with pytest.raises(ValueError, match='differs'): diagnosis_projection(broken)


def test_wire_budget_blocks_before_any_transport(setup, monkeypatch):
    import src.skill_evolution.v19.memory_generation_prompt_v19 as prompt
    root, _, kwargs = setup
    monkeypatch.setattr(prompt, 'DIAGNOSIS_CONTEXT_LIMIT', 1)
    def forbidden(_): raise AssertionError('must not send a request')
    with pytest.raises(ValueError, match='no request sent'):
        run(kwargs, root/'over-budget', diagnose=forbidden, edit=forbidden)
    assert not (root/'over-budget/diagnosis-000').exists()
    assert load_memory(kwargs['store_dir']).head['revision'] == 1


def test_pilot_current_success_history_failure_and_duplicate_review_regression(setup):
    # Reproduces both failures in the first real round-02 response; validators
    # must keep rejecting them, rather than normalizing saved model output.
    root, _, _ = setup
    kwargs = current(root, round_id='r3', all_success=True)
    request = build_memory_diagnosis_inputs(**kwargs)[0]
    call = build_memory_diagnosis_request(request)
    wire = parse(call['user_prompt'])
    summary = wire['diagnosis_contract_summary']
    assert summary['counts']['CURRENT_PARENT']['failure_or_violation'] == 0
    assert summary['counts']['COMMITTED_HISTORICAL_OBSERVATION']['failure_or_violation'] > 0
    assert summary['no_issue_allowed_by_supervision'] is False
    ids = [e['edit_id'] for row in request.learner_payload['memory_context']['rounds'] for e in row['edits']]
    assert wire['memory_review_requirements']['expected_edit_ids'] == ids
    assert wire['memory_review_requirements']['expected_count'] == len(ids)
    assert 'If all supplied success and compliant labels are true' not in call['system_prompt']
    assert 'current group all successful, historical failures present' in call['system_prompt']
    assert 'Review unit\nis EDIT, not attribution' in call['system_prompt']
    output = parse(raw_for(wire, defer=True))
    output['diagnosis']['skill_addressability']['status'] = 'NO_ISSUE'
    output['memory_review'].append(dict(output['memory_review'][0], reason='Duplicate historical edit'))
    with pytest.raises(ValueError, match='NO_ISSUE contradicts'):
        validate_memory_diagnosis_response(encode(output), request=request)
    output['diagnosis']['skill_addressability']['status'] = 'NOT_ADDRESSABLE'
    with pytest.raises(ValueError, match='duplicate reviewed edit'):
        validate_memory_diagnosis_response(encode(output), request=request)
    output['memory_review'].pop()
    validate_memory_diagnosis_response(encode(output), request=request)


def test_policy_valid_in_diagnosis_but_forbidden_in_review(setup):
    _, _, kwargs = setup
    request = build_memory_diagnosis_inputs(**kwargs)[0]
    output = parse(raw_for(request.learner_payload))
    policy = next(iter(request.learner_payload['available_policy_refs']))
    output['diagnosis']['success_analysis']['evidence_refs'].append(policy)
    output['diagnosis']['parent_skill_gaps'][0]['evidence_refs'].append(policy)
    validate_memory_diagnosis_response(encode(output), request=request)
    output['memory_review'][0]['evidence_refs'].append(policy)
    with pytest.raises(ValueError) as exc:
        validate_memory_diagnosis_response(encode(output), request=request)
    assert 'memory_review[0]' in str(exc.value)
    assert output['memory_review'][0]['edit_id'] in str(exc.value)
    assert policy in str(exc.value)
    prompt = build_memory_diagnosis_request(request)
    assert prompt['prompt_version'] == 'memory-diagnosis-v19.6'
    assert 'INVALID review.evidence_refs' in prompt['system_prompt']
    assert 'NOT a copy of all the linked gap' in prompt['system_prompt']


def test_actual_pilot_gap_closure_regression():
    from src.skill_evolution.v19.memory_diagnosis_v19 import gap_closure_issues
    root = Path(__file__).parent/'fixtures/v19_gap_closure'
    output = parse(parse((root/'response.json').read_text()))
    d = output['diagnosis']
    events = {r for g in d['parent_skill_gaps'] for r in g['evidence_refs'] if r.startswith(('PAIR/','CURRENT/'))}
    issues = gap_closure_issues(d, events)
    expected = parse((root/'expected.json').read_text())
    assert issues == [{**expected, 'analyses_without_shared_event':[]}]


def test_each_declared_dimension_requires_shared_event(setup):
    from src.skill_evolution.v19.memory_diagnosis_v19 import gap_closure_issues
    _, _, kwargs = setup
    req = build_memory_diagnosis_inputs(**kwargs)[0]
    out = parse(raw_for(req.learner_payload))
    gap = out['diagnosis']['parent_skill_gaps'][0]
    gap['source_dimensions'].append('COMPLIANCE')
    with pytest.raises(ValueError, match='analyses_without_shared_event.*compliance_analysis'):
        validate_memory_diagnosis_response(encode(out), request=req)


def test_contract_repair_once_then_resume_without_calls(setup):
    root, _, kwargs = setup
    calls=[]
    def diagnosis(call):
        calls.append(call)
        if len(calls)==1: return complete('{}')
        body=parse(call['user_prompt'])
        assert body['previous_raw_response']=='{}'
        assert body['validation_error']['message']=='invalid v19 Diagnosis response'
        return complete(raw_for(body['original_input']))
    result=run(kwargs,root/'repaired',diagnose=diagnosis)
    assert len(calls)==2 and result.status=='EDITED'
    assert (root/'repaired/diagnosis-000/contract_rejection.json').exists()
    assert (root/'repaired/diagnosis-000-repair-001/response_complete.json').exists()
    def forbidden(_):raise AssertionError('no calls during resume')
    assert run(kwargs,root/'repaired',diagnose=forbidden,edit=forbidden,resume=True)==result


def test_repair_failure_stops_no_third_call_on_resume(setup):
    root, _, kwargs=setup
    calls=[]
    def invalid(call):calls.append(call);return complete('{}')
    def forbidden(_):raise AssertionError('Editor must not run')
    for resume in (False,True):
        with pytest.raises(ValueError,match='invalid v19 Diagnosis response'):
            run(kwargs,root/'two-invalid',diagnose=invalid,edit=forbidden,resume=resume)
    assert len(calls)==2
    assert (root/'two-invalid/diagnosis-000-repair-001/contract_rejection.json').exists()


def test_repair_transport_interruption_never_automatically_retried(setup):
    root, _, kwargs=setup
    calls=[]
    def diagnosis(call):
        calls.append(call)
        if len(calls)==1:return complete('{}')
        raise TimeoutError('uncertain repair request')
    with pytest.raises(TimeoutError):run(kwargs,root/'repair-timeout',diagnose=diagnosis)
    with pytest.raises(ValueError,match='uncertain model call'):
        run(kwargs,root/'repair-timeout',diagnose=diagnosis,resume=True)
    assert len(calls)==2


def test_repair_runs_full_memory_validation(setup):
    root, _, kwargs=setup
    def diagnosis(call):
        body=parse(call['user_prompt'])
        if 'previous_raw_response' not in body:return complete('{}')
        out=parse(raw_for(body['original_input']))
        out['memory_review'].append(out['memory_review'][0])
        return complete(encode(out))
    with pytest.raises(ValueError,match='duplicate reviewed edit'):
        run(kwargs,root/'invalid-repair',diagnose=diagnosis)
