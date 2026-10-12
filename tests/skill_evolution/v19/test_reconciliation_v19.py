from copy import deepcopy

import pytest

from tests.skill_evolution.v19.test_separated_review_v19 import setup, case, review_input, review_response, inputs, response, current
from src.skill_evolution.v19.historical_review_v19 import validate_historical_reviews, build_memory_review_input
from src.skill_evolution.v19.current_diagnosis_v19 import validate_current_findings
from src.skill_evolution.v19.edit_tracking_v19 import encode
from src.skill_evolution.v19.memory_store_v19 import initialize_memory
from src.skill_evolution.v19.reconciliation_v19 import build_reconciliation_input, validate_reconciliation, reconciliation_editor_request, apply_reconciled_editor, ReconciliationResult, _catalog
from src.skill_evolution.v19.reconciliation_prompt_v19 import build_reconciliation_request
from src.skill_evolution.v19.reconciliation_evidence_v19 import selected_evidence_refs


def prepared(kwargs):
    _,_,review=review_input(kwargs)
    reviews=validate_historical_reviews(encode(review_response(review)),request=review)
    return build_reconciliation_input(contract_version='v19.3',review_request=review,historical_reviews=reviews)


def diagnosis(events,kind='MISSING',rules=()):
    analysis={'finding':'Conditional behavior observed within the stated scope.','evidence_refs':list(events),
              'supervision_refs':[],'unresolved':['Sampling and applicability remain uncertain.']}
    return {'success_analysis':analysis,'compliance_analysis':{
        'finding':'Public constraints remain applicable.','evidence_refs':[],'supervision_refs':[],'unresolved':[]},
        'skill_addressability':{'status':'ADDRESSABLE','reason':'A bounded observable choice can be guided.'},
        'parent_skill_gaps':[{'kind':kind,'gap':'Clarify the bounded behavior under observed conditions.',
            'evidence_refs':list(events),'related_rule_refs':list(rules),'source_dimensions':['SUCCESS']}]}


def decision(cf=(),hr=(),events=(),kind=None,rules=(),action='DEFER'):
    return {'current_finding_refs':list(cf),'historical_review_refs':list(hr),
        'current_finding_assessments':[{'finding_ref':f,'role':'DIRECT_BASIS' if kind else 'CONTEXT',
            'reason':'Explicitly considered within the observed scope.'} for f in cf],
        'decision':'PROPOSE' if kind else action,'reason':'Explicit disposition within observed scope.',
        'evidence_refs':list(events),'keep_rule_refs':list(rules) if action=='KEEP' and not kind else [],
        'conflict_resolution':[],
        'whole_rule_removal_reason':['Whole block lacks a retainable supported part; revision would retain the unsupported instruction.']*len(rules) if kind=='SHOULD_REMOVE' else [],
        'proposals':[diagnosis(list(events),kind,rules)] if kind else []}


def output(request,kind='MISSING'):
    data=request.payload['review_input'];f=data['current_findings'][0]
    rules=list(_catalog(request)['available_rule_refs'])[:1] if kind!='MISSING' else []
    decisions=[decision(cf=[f['finding_id']],events=f['evidence_refs'],kind=kind,rules=rules)]
    for r in request.payload['historical_reviews']['reviews']:
        decisions.append(decision(hr=[r['review_id']]))
    return {'schema_version':'reconciliation_response_v19.2','decisions':decisions}


@pytest.mark.parametrize('kind,operation',[('MISSING','ADD'),('NEEDS_REVISION','REPLACE'),('SHOULD_REMOVE','DELETE')])
def test_current_only_proposal_reuses_v18_compiler_and_editor(setup,kind,operation):
    r=prepared(setup[2]); result,value=validate_reconciliation(encode(output(r,kind)),request=r)
    assert [u.operation for u in value.plan.edit_units]==[operation]
    prompt=reconciliation_editor_request(result,request=r)
    raw=None if operation=='DELETE' else encode({'status':'EDITED','reason':'Authorized unit only.',
         'edits':[{'edit_unit_index':0,'text':'- New bounded rule'}]})
    assert (prompt is None)==(operation=='DELETE')
    applied=apply_reconciled_editor(raw,result=result,request=r)
    assert applied['candidate_skill'] is not None
    provenance=applied['edit_provenance'][0]
    assert provenance['current_finding_refs'] and not provenance['historical_review_refs']
    assert len(applied['reconciliation']['decisions'])==2


def test_history_only_proposal_does_not_invent_current_support(setup):
    r=prepared(setup[2]);x=output(r);d=x['decisions'][0]
    x['decisions'][0]=decision(cf=d['current_finding_refs'],events=d['evidence_refs'])
    obj=r.payload['review_input']['historical_objects'][0]
    x['decisions'][1]=decision(hr=x['decisions'][1]['historical_review_refs'],events=sorted(set(obj['historical_event_refs']) & selected_evidence_refs(r))[:1],kind='MISSING')
    result,value=validate_reconciliation(encode(x),request=r)
    applied=apply_reconciled_editor(encode({'status':'EDITED','reason':'bounded','edits':[{'edit_unit_index':0,'text':'- Historical scoped hypothesis'}]}),result=result,request=r)
    assert applied['edit_provenance'][0]['current_finding_refs']==[]
    assert applied['edit_provenance'][0]['historical_review_refs']


def test_keep_defer_no_editor_and_no_candidate(setup):
    r=prepared(setup[2]);x=output(r);d=x['decisions'][0]
    x['decisions'][0]=decision(cf=d['current_finding_refs'],events=d['evidence_refs'],action='KEEP',rules=list(_catalog(r)['available_rule_refs'])[:1])
    result,value=validate_reconciliation(encode(x),request=r)
    assert not value.plan.edit_units and reconciliation_editor_request(result,request=r) is None
    assert apply_reconciled_editor(None,result=result,request=r)['status']=='NO_UPDATE'


@pytest.mark.parametrize('mutation',[
    lambda x:x['decisions'].pop(),
    lambda x:x['decisions'].append(deepcopy(x['decisions'][0])),
    lambda x:x['decisions'][0].update(current_finding_refs=['CF/unknown']),
    lambda x:x['decisions'][0].update(proposals=[]),
    lambda x:x['decisions'][0].update(evidence_refs=[]),
    lambda x:x['decisions'][1].update(decision='KEEP'),
    lambda x:x['decisions'][0]['proposals'][0]['success_analysis'].update(evidence_refs=[]),
    lambda x:x['decisions'][0]['proposals'][0]['parent_skill_gaps'][0].update(related_rule_refs=['RULE/stale']),
    lambda x:x['decisions'][1].update(proposals=[diagnosis(['invented'])]),
])
def test_invalid_dispositions_fail_closed(setup,mutation):
    r=prepared(setup[2]);x=output(r);mutation(x)
    with pytest.raises(ValueError):validate_reconciliation(encode(x),request=r)


def test_deletion_requires_explicit_whole_rule_reason(setup):
    r=prepared(setup[2]);x=output(r,'SHOULD_REMOVE');x['decisions'][0]['whole_rule_removal_reason']=[]
    with pytest.raises(ValueError,match='whole-rule'):validate_reconciliation(encode(x),request=r)


def test_mixed_review_counterevidence_cannot_be_dropped(setup):
    _,_,review=review_input(setup[2]);raw=review_response(review,'MIXED')
    reviews=validate_historical_reviews(encode(raw),request=review)
    r=build_reconciliation_input(contract_version='v19.3',review_request=review,historical_reviews=reviews)
    x=output(r);hr=reviews.payload['reviews'][0]
    with pytest.raises(ValueError,match='dropped'):validate_reconciliation(encode(x),request=r)
    x['decisions'][1]['evidence_refs']=hr['supporting_current_refs']+hr['contradicting_current_refs']
    with pytest.raises(ValueError,match='conflicting'):validate_reconciliation(encode(x),request=r)
    x['decisions'][1]['conflict_resolution']=['Both directions remain confounded; defer rather than treating repetition as proof.']
    validate_reconciliation(encode(x),request=r)


def test_changed_result_cannot_reach_editor(setup):
    r=prepared(setup[2]);result,_=validate_reconciliation(encode(output(r)),request=r)
    p=result.payload;p['decisions'][0]['reason']='changed'
    with pytest.raises(ValueError,match='changed'):reconciliation_editor_request(ReconciliationResult(encode(p)),request=r)
    assert build_reconciliation_request(r)['input_budget']


def test_merge_sources_preserves_both_and_unique_events(setup):
    r=prepared(setup[2]);x=output(r)
    x['decisions'][0]['historical_review_refs']=x['decisions'].pop()['historical_review_refs']
    obj=r.payload['review_input']['historical_objects'][0]
    event=sorted(set(obj['historical_event_refs']) & selected_evidence_refs(r))[0]
    d=x['decisions'][0];d['evidence_refs'].append(event)
    d['proposals']=[diagnosis(d['evidence_refs'])]
    result,_=validate_reconciliation(encode(x),request=r)
    applied=apply_reconciled_editor(encode({'status':'EDITED','reason':'scoped','edits':[{'edit_unit_index':0,'text':'- Supported scoped revision'}]}),result=result,request=r)
    assert applied['edit_provenance'][0]['current_finding_refs']
    assert applied['edit_provenance'][0]['historical_review_refs']


def test_empty_current_and_history_is_no_update(tmp_path):
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    kwargs=current(tmp_path);rs=inputs(kwargs)
    fs=[validate_current_findings(encode({'schema_version':'current_findings_response_v19.1','summary':'No supported finding.','findings':[]}),request=r) for r in rs]
    review=build_memory_review_input(store_dir=kwargs['store_dir'],current_requests=rs,current_findings=fs)
    reviews=validate_historical_reviews(encode(review_response(review)),request=review)
    r=build_reconciliation_input(contract_version='v19.3',review_request=review,historical_reviews=reviews)
    result,_=validate_reconciliation(encode({'schema_version':'reconciliation_response_v19.2','decisions':[]}),request=r)
    assert apply_reconciled_editor(None,result=result,request=r)['status']=='NO_UPDATE'


def multi_output(setup):
    root,_,_=setup;r=prepared(current(root,round_id='r3',groups=3))
    rule=list(_catalog(r)['available_rule_refs'])[0]
    fs=r.payload['review_input']['current_findings']
    ds=[decision(cf=[f['finding_id']],events=f['evidence_refs'],kind='NEEDS_REVISION',rules=[rule]) for f in fs[:2]]
    ds.append(decision(cf=[fs[2]['finding_id']],events=fs[2]['evidence_refs']))
    ds.extend(decision(hr=[h['review_id']]) for h in r.payload['historical_reviews']['reviews'])
    return r,{'schema_version':'reconciliation_response_v19.2','decisions':ds},rule


def test_compiler_merges_same_target_and_preserves_all_provenance(setup):
    r,x,_=multi_output(setup);result,value=validate_reconciliation(encode(x),request=r)
    assert len(value.plan.edit_units)==1 and len(value.plan.edit_units[0].supporting_gap_refs)==2
    prompt=reconciliation_editor_request(result,request=r)
    from src.skill_evolution.v19.edit_tracking_v19 import parse
    package=parse(prompt['user_prompt'])['edit_units'][0]
    assert len(package['reconciliation_provenance'])==2
    applied=apply_reconciled_editor(encode({'status':'EDITED','reason':'bounded','edits':[{'edit_unit_index':0,'text':'- Combined scoped guidance'}]}),result=result,request=r)
    assert len(applied['edit_provenance'][0]['current_finding_refs'])==2
    assert len(applied['edit_provenance'][0]['decision_refs'])==2


def test_replace_delete_conflict_is_not_silently_resolved(setup):
    r,x,rule=multi_output(setup);d=x['decisions'][1]
    x['decisions'][1]=decision(cf=d['current_finding_refs'],events=d['evidence_refs'],kind='SHOULD_REMOVE',rules=[rule])
    with pytest.raises(ValueError,match='MIXED_OPERATION_TARGET_CONFLICT'):validate_reconciliation(encode(x),request=r)


def test_keep_cannot_conflict_with_modification(setup):
    r,x,rule=multi_output(setup);d=x['decisions'][1]
    x['decisions'][1]=decision(cf=d['current_finding_refs'],events=d['evidence_refs'],action='KEEP',rules=[rule])
    with pytest.raises(ValueError,match='KEEP conflicts'):validate_reconciliation(encode(x),request=r)


def test_unrelated_analysis_evidence_is_rejected(setup):
    r=prepared(setup[2]);x=output(r)
    event=next(ref for ref in r.payload['review_input']['current_evidence'] if ref not in x['decisions'][0]['evidence_refs'])
    x['decisions'][0]['proposals'][0]['success_analysis']['evidence_refs'].append(event)
    with pytest.raises(ValueError,match='outside source'):validate_reconciliation(encode(x),request=r)


def test_keep_cannot_preserve_an_absent_rejected_candidate(case,tmp_path):
    from tests.skill_evolution.v19.test_memory_v19 import make_round
    from src.skill_evolution.v19.memory_store_v19 import commit_round_memory
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    old,kw=make_round(case,tmp_path/'r1',decision='RETAIN')
    commit_round_memory(old,store_dir=tmp_path/'memory',expected_head_ref=None,**kw)
    r=prepared(current(tmp_path));x=output(r)
    x['decisions'][1].update(decision='KEEP',keep_rule_refs=list(_catalog(r)['available_rule_refs'])[:1])
    with pytest.raises(ValueError,match='cannot KEEP absent'):validate_reconciliation(encode(x),request=r)


def test_reconciliation_output_budget_and_repair_are_96000_only(setup):
    from src.skill_evolution.v19.memory_generation_v19 import _prepared
    from src.skill_evolution.v19.memory_generation_prompt_v19 import build_memory_diagnosis_repair_request, diagnosis_budget
    from src.skill_evolution.v19.review_prompt_v19 import build_current_diagnosis_request, build_historical_review_request
    from src.skill_evolution.v19.edit_tracking_v19 import parse
    rs,_,review=review_input(setup[2])
    request=build_reconciliation_request(prepared(setup[2]))
    original=_prepared(request)
    assert original['max_completion_tokens']==96000
    assert request['input_budget']['output_reserve']==96000
    baseline=diagnosis_budget(request['system_prompt'],request['user_prompt'],request['response_format'])
    assert request['input_budget']['reserved_tokens']==baseline['reserved_tokens']+72000
    repair=_prepared(build_memory_diagnosis_repair_request(original,'{}',{'message':'synthetic rejection'}))
    assert repair['max_completion_tokens']==96000 and repair['input_budget']['output_reserve']==96000
    assert original['timeout_seconds']==repair['timeout_seconds']==300
    for other in (build_current_diagnosis_request(rs[0]),build_historical_review_request(review)):
        assert _prepared(other)['max_completion_tokens']==24000
        assert other['input_budget']['output_reserve']==24000


@pytest.mark.parametrize('role',['COUNTEREVIDENCE','CONTEXT'])
def test_non_supporting_merged_finding_is_retained_without_gap_support(setup,role):
    r,x,_=multi_output(setup)
    first,second=x['decisions'][:2]
    first['current_finding_refs']+=second['current_finding_refs']
    first['current_finding_assessments'] += [{**a,'role':role,
        'reason':'Limits scope of this proposal; it is not affirmative support.'}
        for a in second['current_finding_assessments']]
    first['evidence_refs']+=second['evidence_refs']
    first['proposals'][0]['success_analysis']['evidence_refs']=list(first['evidence_refs'])
    x['decisions'].pop(1)
    result,value=validate_reconciliation(encode(x),request=r)
    assert value.plan.edit_units
    assert result.payload['decisions'][0]['current_finding_assessments'][1]['role']==role
    first['current_finding_assessments'][1]['role']='DIRECT_BASIS'
    with pytest.raises(ValueError,match='DIRECT_BASIS.*gap missing shared event'):
        validate_reconciliation(encode(x),request=r)


def test_multiple_independent_errors_are_reported_without_mutation(setup):
    r,x,_=multi_output(setup)
    x['decisions'][0]['evidence_refs']*=2
    x['decisions'][1]['proposals'][0]['success_analysis']['evidence_refs']=[]
    original=deepcopy(x)
    with pytest.raises(ValueError) as exc:validate_reconciliation(encode(x),request=r)
    assert 'duplicate values' in str(exc.value)
    assert 'decision 1: gap closure' in str(exc.value)
    assert 'missing_from_declared_analyses' in str(exc.value)
    assert x==original


def test_v1_audit_can_be_revalidated_but_not_accepted_as_new_output(setup):
    from src.skill_evolution.v19.reconciliation_v19 import ReconciliationInput
    r=prepared(setup[2]);x=output(r)
    x['schema_version']='reconciliation_response_v19.1'
    for d in x['decisions']:d.pop('current_finding_assessments')
    old=r.payload;old['schema_version']='reconciliation_input_v19.1'
    result,_=validate_reconciliation(encode(x),request=ReconciliationInput(encode(old)))
    assert result.payload['raw_response']==encode(x)
    with pytest.raises(ValueError):validate_reconciliation(encode(x),request=r)


def test_real_pilot_responses_keep_duplicates_and_missing_support_visible():
    import gzip,json
    from pathlib import Path
    from src.skill_evolution.v19.reconciliation_v19 import ReconciliationInput
    fixture=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/v19_reconciliation_failure.json.gz').read_bytes()))
    request=ReconciliationInput(encode(fixture['input']))
    for index,raw in enumerate(fixture['raw_responses']):
        with pytest.raises(ValueError) as exc:validate_reconciliation(raw,request=request)
        message=str(exc.value)
        assert 'decision 0: proposal lost merged current finding evidence' in message
        if index==0:assert 'duplicate values' in message
    # Replay saved data under the new schema only as a negative migration test:
    # code must not invent roles to make a previously rejected response pass.
    revised=request.payload;revised['schema_version']='reconciliation_input_v19.2'
    with pytest.raises(ValueError,match='current_finding_assessments'):
        validate_reconciliation(fixture['raw_responses'][1],request=ReconciliationInput(encode(revised)))


@pytest.mark.parametrize('mutation',[
    lambda d:d.update(current_finding_assessments=[]),
    lambda d:d['current_finding_assessments'].append(deepcopy(d['current_finding_assessments'][0])),
    lambda d:d['current_finding_assessments'][0].update(finding_ref='CF/undeclared'),
    lambda d:d['current_finding_assessments'][0].update(role='CONTEXT'),
    lambda d:d['current_finding_assessments'][0].update(reason=''),
])
def test_roles_cannot_bypass_source_accountability(setup,mutation):
    r=prepared(setup[2]);x=output(r);mutation(x['decisions'][0])
    with pytest.raises(ValueError):validate_reconciliation(encode(x),request=r)


def test_aggregate_feedback_uses_exactly_one_audited_repair(setup,tmp_path):
    import json
    from src.skill_evolution.v19.separated_generation_v19 import _contract_call
    from tests.skill_evolution.v19.test_attribution_v19 import complete
    r,x,_=multi_output(setup)
    x['decisions'][0]['evidence_refs']*=2
    x['decisions'][1]['proposals'][0]['success_analysis']['evidence_refs']=[]
    raw=encode(x);calls=[]
    def transport(request):
        calls.append(request)
        if len(calls)==2:
            feedback=json.loads(request['user_prompt'])
            assert feedback['previous_raw_response']==raw
            assert 'duplicate values' in feedback['validation_error']['message']
            assert 'decision 1: gap closure' in feedback['validation_error']['message']
        return complete(raw)
    path=tmp_path/'reconciliation-call'
    for _ in range(2):
        with pytest.raises(ValueError):
            _contract_call(path,build_reconciliation_request(r),
                           lambda text:validate_reconciliation(text,request=r),transport)
    assert len(calls)==2
    for name in ('reconciliation-call','reconciliation-call-repair-001'):
        assert json.loads((tmp_path/name/'response.json').read_text())['raw_response']==raw
        assert (tmp_path/name/'contract_rejection.json').exists()
