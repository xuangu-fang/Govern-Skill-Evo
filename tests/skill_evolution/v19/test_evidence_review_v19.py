from copy import deepcopy
import json
from pathlib import Path

import pytest

from tests.skill_evolution.v19.test_issue_fusion_v19 import setup, case, review_input, review_response, current, output
from tests.skill_evolution.v19.test_attribution_v19 import complete
from src.skill_evolution.v19.edit_tracking_v19 import encode, parse, digest
from src.skill_evolution.v19.historical_review_v19 import validate_historical_reviews
from src.skill_evolution.v19.issue_fusion_v19 import build_issue_fusion_input, validate_issue_fusion
from src.skill_evolution.v19.evidence_review_v19 import build_evidence_review_case, build_evidence_review_input, validate_evidence_review, validate_evidence_review_result, EvidenceReviewResult, _neighborhood
from src.skill_evolution.v19.evidence_review_prompt_v19 import build_evidence_review_request
from src.skill_evolution.v19.evidence_review_run_v19 import run_evidence_review, run_evidence_reviews
from src.skill_evolution.v19.evidence_projection_v19 import expand


def cases(kwargs):
    _,_,review=review_input(kwargs)
    historical=validate_historical_reviews(encode(review_response(review)),request=review)
    fusion=build_issue_fusion_input(review_request=review,historical_reviews=historical)
    x=output(fusion)
    for i in x['issues']:i['decision']='PROPOSE'
    result=validate_issue_fusion(encode(x),request=fusion)
    return [build_evidence_review_case(fusion_input=fusion,fusion_result=result,review_request=review,
            historical_reviews=historical,issue_id=i['issue_id']) for i in result.payload['issues']]


def payload(request):
    data=parse(request['user_prompt'])
    if 'previous_raw_response' in data:return expand(data['original_input'])
    return expand(data)


def final(p,verdict='VERIFIED',kind='MISSING'):
    return {'proposal_id':p['proposal_id'],'verdict':verdict,
        'evidence_refs':list(p['events'])[:1] if verdict=='VERIFIED' else [],
        'counterevidence_refs':p['known_counterevidence_refs'],
        'reason':'Observed behavior supports a scoped change; alternatives remain uncertain.',
        'gap':{'kind':kind,'statement':'Under the observed condition, choose the available bounded behavior.',
               'related_rule_refs':list(p['rules'])[:1] if kind!='MISSING' else []} if verdict=='VERIFIED' else None}


def ask_context(p):
    r={'proposal_id':p['proposal_id'],'request':'MORE_CONTEXT','evidence_refs':[],
       'tool_refs':[],'rule_refs':[],'reason':'Need the omitted context before deciding.'}
    for field,directory,loaded in [('evidence_refs','event_directory','events'),('rule_refs','rule_directory','rules'),('tool_refs','tool_directory','tools')]:
        missing=set(p[directory])-set(p[loaded])
        if missing:r[field]=[sorted(missing)[0]];return r
    raise AssertionError('fixture needs unloaded context')


def test_scope_originals_and_independent_sources(setup):
    cs=cases(current(setup[0],round_id='r3',groups=3));a,b=cs[:2]
    r=build_evidence_review_input(a);p=r.payload
    assert p['proposal_id']!=build_evidence_review_input(b).payload['proposal_id']
    all_events={e['evidence_ref']:e for exp in a.payload['experiences'] for e in exp['events']}
    for ref,event in p['events'].items():assert {**event['event'],'evidence_ref':ref}==all_events[ref]
    assert set(a.payload['seed_refs'])<=set(p['events'])
    assert p['issue']['source_finding_refs']==a.payload['issue']['source_finding_refs']
    assert expand(parse(build_evidence_review_request(r)['user_prompt']))==p
    assert 'memory_context' not in p and 'experiences' not in p
    with pytest.raises(ValueError,match='budget'):build_evidence_review_request(r,max_input_tokens=1)


@pytest.mark.parametrize('verdict',['VERIFIED','NO_EDIT'])
def test_minimal_verdict_and_tamper_check(setup,verdict):
    r=build_evidence_review_input(cases(setup[2])[0]);x=final(r.payload,verdict)
    result=validate_evidence_review(encode(x),request=r)
    assert validate_evidence_review_result(result,request=r)==result
    p=result.payload;p['reason']='changed'
    with pytest.raises(ValueError,match='changed'):validate_evidence_review_result(EvidenceReviewResult(encode(p)),request=r)


@pytest.mark.parametrize('mutation',[
    lambda x:x.update(proposal_id='another issue'),
    lambda x:x.update(evidence_refs=['unseen']),
    lambda x:x.update(evidence_refs=[]),
    lambda x:x['gap'].update(kind='REPLACE'),
    lambda x:x['gap'].update(related_rule_refs=['RULE/stale']),
    lambda x:x.update(feasibility_checks=[]),
    lambda x:x.update(gap=None),
    lambda x:x.update(verdict='NO_EDIT'),
])
def test_invalid_output_never_becomes_verified(setup,mutation):
    r=build_evidence_review_input(cases(setup[2])[0]);x=final(r.payload);mutation(x)
    with pytest.raises(ValueError):validate_evidence_review(encode(x),request=r)


def test_context_is_explicit_scoped_and_bounded(setup):
    case_=cases(setup[2])[0];r=build_evidence_review_input(case_);x=ask_context(r.payload)
    assert validate_evidence_review(encode(x),request=r)==x
    r2=build_evidence_review_input(case_,context_round=1,additional_evidence_refs=x['evidence_refs'],
        additional_rule_refs=x['rule_refs'],additional_tool_refs=x['tool_refs'])
    assert r2.input_ref!=r.input_ref and r2.payload['issue']==r.payload['issue']
    assert set(r.payload['events'])<=set(r2.payload['events'])
    with pytest.raises(ValueError,match='exhausted'):validate_evidence_review(encode(x),request=r2)
    with pytest.raises(ValueError):build_evidence_review_input(case_,context_round=1,additional_evidence_refs=['OTHER/private'])
    with pytest.raises(ValueError):build_evidence_review_input(case_,context_round=2)


def test_known_counterevidence_cannot_disappear(setup):
    cs=cases(setup[2]);p=cs[0].payload
    from src.skill_evolution.v19.evidence_review_v19 import EvidenceReviewCase
    p['known_counterevidence_refs']=p['seed_refs'][:1]
    r=build_evidence_review_input(EvidenceReviewCase(encode(p)));x=final(r.payload)
    x['counterevidence_refs']=[]
    with pytest.raises(ValueError,match='counterevidence'):validate_evidence_review(encode(x),request=r)


def test_tool_call_return_closure_and_neighbor_window():
    es=[{'evidence_ref':str(i),'event_type':'message','step':i} for i in range(8)]
    es[1].update(event_type='tool_call',tool_name='lookup')
    es[5].update(event_type='tool_result',tool_name='lookup')
    assert _neighborhood(es,{'1'})=={'0','1','2','5'}
    assert '1' in _neighborhood(es,{'5'})
    assert '7' not in _neighborhood(es,{'1'})


def test_completed_response_resume_never_calls_model_again(setup,tmp_path):
    c=cases(setup[2])[0];calls=[]
    def transport(req):calls.append(req);return complete(encode(final(payload(req))))
    r=run_evidence_review(c,output=tmp_path/'review',transport=transport)
    assert run_evidence_review(c,output=tmp_path/'review',transport=transport,resume=True)==r
    assert len(calls)==1
    assert json.loads((tmp_path/'review/status.json').read_text())['status']=='COMPLETE'
    (tmp_path/'review/result.json').write_text('{}')
    with pytest.raises(ValueError,match='checksum'):run_evidence_review(c,output=tmp_path/'review',transport=transport,resume=True)
    assert len(calls)==1


def test_more_context_is_rejected_and_repair_returns_final_only(setup,tmp_path):
    c=cases(setup[2])[0];calls=[]
    def transport(req):
        p=payload(req);calls.append(req)
        assert 'context_requests_remaining' not in p
        return complete(encode({'request':'MORE_CONTEXT'}) if len(calls)==1 else encode(final(p)))
    r=run_evidence_review(c,output=tmp_path/'review',transport=transport)
    assert len(calls)==2 and not (tmp_path/'review/context-request-0.json').exists()
    assert not (tmp_path/'review/review-1').exists()
    assert run_evidence_review(c,output=tmp_path/'review',transport=transport,resume=True)==r
    assert len(calls)==2


def test_single_contract_repair_is_audited(setup,tmp_path):
    c=cases(setup[2])[0];calls=[]
    def transport(req):
        calls.append(req)
        return complete('{}' if len(calls)==1 else encode(final(payload(req))))
    r=run_evidence_review(c,output=tmp_path/'review',transport=transport)
    assert len(calls)==2 and (tmp_path/'review/review-0/contract_rejection.json').exists()
    assert run_evidence_review(c,output=tmp_path/'review',transport=transport,resume=True)==r
    assert len(calls)==2


def test_failed_repair_stops_and_resume_does_not_call_again(setup,tmp_path):
    c=cases(setup[2])[0];calls=[]
    def transport(req):calls.append(req);return complete('{}')
    for resume in (False,True):
        with pytest.raises(ValueError):run_evidence_review(c,output=tmp_path/'review',transport=transport,resume=resume)
    assert len(calls)==2 and not (tmp_path/'review/result.json').exists()


def test_repeated_more_context_stops_after_one_repair(setup,tmp_path):
    c=cases(setup[2])[0];calls=[]
    def transport(req):
        calls.append(req)
        return complete(encode({'request':'MORE_CONTEXT'}))
    for resume in (False,True):
        with pytest.raises(ValueError,match='final verdict'):
            run_evidence_review(c,output=tmp_path/'review',transport=transport,resume=resume)
    assert len(calls)==2 and not (tmp_path/'review/review-1').exists()


def test_timeout_leaves_pending_and_does_not_block_siblings(setup,tmp_path):
    cs=cases(current(setup[0],round_id='r3',groups=3))[:2];failed=cs[0].payload['issue']['issue_id'];calls=[]
    def transport(req):
        p=payload(req);calls.append(p['proposal_id'])
        if p['proposal_id']==failed:raise TimeoutError('network timeout')
        return complete(encode(final(p)))
    report=run_evidence_reviews(cs,output=tmp_path/'reviews',transport=transport)
    assert report['status']=='INCOMPLETE' and list(report['incomplete'])==[failed]
    assert len(report['results'])==1 and len(calls)==2
    again=run_evidence_reviews(cs,output=tmp_path/'reviews',transport=transport,resume=True)
    assert len(calls)==2 and again['status']=='INCOMPLETE'
    assert not (tmp_path/'reviews'/digest(failed)/'result.json').exists()


def test_budget_failure_dispatches_nothing_and_keeps_pending(setup,tmp_path):
    c=cases(setup[2])[0];calls=[]
    with pytest.raises(ValueError,match='budget'):
        run_evidence_review(c,output=tmp_path/'review',transport=lambda r:calls.append(r),max_input_tokens=1)
    assert not calls and not (tmp_path/'review/result.json').exists()


def test_explicit_timeout_retry_of_final_repair_reuses_original_response(setup,tmp_path):
    c=cases(setup[2])[0];calls=[]
    def transport(req):
        calls.append(req)
        if len(calls)==1:return complete('{}')
        if len(calls)==2:raise TimeoutError('response missing')
        return complete(encode(final(payload(req))))
    with pytest.raises(TimeoutError):run_evidence_review(c,output=tmp_path/'review',transport=transport)
    result=run_evidence_review(c,output=tmp_path/'review',transport=transport,resume=True,retry_incomplete=True)
    assert result.payload['verdict']=='VERIFIED' and len(calls)==3
    assert (tmp_path/'review/failed-attempts/review-0-repair-001-attempt-001/call/request.json').exists()
    assert run_evidence_review(c,output=tmp_path/'review',transport=transport,resume=True)==result
    assert len(calls)==3


def test_explicit_retry_cannot_bypass_failed_contract_repair(setup,tmp_path):
    c=cases(setup[2])[0];calls=[]
    def transport(req):calls.append(1);return complete('{}')
    with pytest.raises(ValueError):run_evidence_review(c,output=tmp_path/'review',transport=transport)
    with pytest.raises(ValueError,match='incomplete call'):
        run_evidence_review(c,output=tmp_path/'review',transport=transport,resume=True,retry_incomplete=True)
    assert len(calls)==2


def test_repair_prompt_obeys_same_input_budget(setup,tmp_path):
    c=cases(setup[2])[0];r=build_evidence_review_input(c,input_version='v19.3')
    base=build_evidence_review_request(r)['input_budget']['proxy_input_tokens'];calls=[]
    def transport(req):calls.append(1);return complete('invalid '*2000)
    with pytest.raises(ValueError,match='budget'):
        run_evidence_review(c,output=tmp_path/'review',transport=transport,max_input_tokens=base+10)
    assert len(calls)==1 and not (tmp_path/'review/result.json').exists()


@pytest.mark.parametrize('kind',['NEEDS_REVISION','SHOULD_REMOVE'])
def test_revision_and_removal_require_loaded_parent_targets(setup,kind):
    c=cases(setup[2])[0];r=build_evidence_review_input(c);x=final(r.payload,kind=kind)
    with pytest.raises(ValueError,match='requires targets'):validate_evidence_review(encode(x),request=r)
    rule=next(iter(r.payload['rule_directory']))
    r2=build_evidence_review_input(c,context_round=1,additional_rule_refs=[rule])
    result=validate_evidence_review(encode(final(r2.payload,kind=kind)),request=r2)
    assert result.payload['gap']['related_rule_refs']==[rule]


def test_no_edit_issue_and_changed_fusion_cannot_be_reviewed(setup):
    _,_,review=review_input(setup[2])
    h=validate_historical_reviews(encode(review_response(review)),request=review)
    f=build_issue_fusion_input(review_request=review,historical_reviews=h)
    result=validate_issue_fusion(encode(output(f)),request=f)
    history_issue=result.payload['issues'][-1]
    with pytest.raises(ValueError,match='only PROPOSE'):
        build_evidence_review_case(fusion_input=f,fusion_result=result,review_request=review,historical_reviews=h,issue_id=history_issue['issue_id'])
    from src.skill_evolution.v19.issue_fusion_v19 import IssueFusionInput
    p=f.payload;p['parent_skill_sha256']='changed'
    with pytest.raises(ValueError,match='binding mismatch'):
        build_evidence_review_case(fusion_input=IssueFusionInput(encode(p)),fusion_result=result,review_request=review,historical_reviews=h,issue_id=result.payload['issues'][0]['issue_id'])


def test_historical_review_preserves_both_polarities_and_only_local_memory(setup):
    _,_,review=review_input(setup[2])
    h=validate_historical_reviews(encode(review_response(review,'MIXED')),request=review)
    f=build_issue_fusion_input(review_request=review,historical_reviews=h)
    x=output(f);x['issues'][-1]['decision']='PROPOSE'
    result=validate_issue_fusion(encode(x),request=f)
    c=build_evidence_review_case(fusion_input=f,fusion_result=result,review_request=review,historical_reviews=h,issue_id=result.payload['issues'][-1]['issue_id'])
    p=build_evidence_review_input(c).payload
    r=h.payload['reviews'][0]
    assert set(r['supporting_current_refs']+r['contradicting_current_refs'])<=set(p['events'])
    assert set(r['contradicting_current_refs'])<=set(p['known_counterevidence_refs'])
    assert p['findings']==[] and len(p['historical_reviews'])==1
    assert 'memory_context' not in encode(p)
    assert 'PRIVATE_EXPECTED_ACTION' not in encode(p)


def test_attempt_history_reaches_only_related_local_reviews(setup):
    cs=cases(setup[2])
    history_cases=[case for case in cs if case.payload['historical_objects']]
    assert history_cases
    for case_ in cs:
        request=build_evidence_review_input(case_)
        assert request.payload['historical_objects']==case_.payload['historical_objects']
        for obj in request.payload['historical_objects']:
            attempt=obj['edit_attempt']
            assert attempt['edit_id']==obj['edit_id']
            assert attempt['results']
            assert attempt['source_gap_refs']
        if not case_.payload['historical_objects']:
            assert not request.payload['historical_objects']


def test_retry_decision_contract_is_shared_without_new_output_states(setup):
    from src.skill_evolution.v19.evidence_review_prompt_v19 import build_evidence_review_request
    from src.skill_evolution.v19.memory_consumption_v19 import REUSE_LIMITATIONS, REUSE_VERIFICATION
    from src.skill_evolution.v19.issue_fusion_prompt_v19 import build_issue_fusion_request
    from tests.skill_evolution.v19.test_issue_fusion_v19 import prepared
    fusion=build_issue_fusion_request(prepared(setup[2]))
    assert REUSE_LIMITATIONS in fusion['system_prompt']
    assert REUSE_VERIFICATION not in fusion['system_prompt']
    for case_ in cases(setup[2]):
        request=build_evidence_review_input(case_,input_version='v19.3')
        prompt=build_evidence_review_request(request)
        assert REUSE_LIMITATIONS in prompt['system_prompt']
        assert REUSE_VERIFICATION in prompt['system_prompt']
        assert prompt['prompt_version'].endswith('-limitation-aware-1')
        from src.skill_evolution.v19.evidence_review_v19 import final_schema_for_input
        assert prompt['response_format']['json_schema']['schema']==final_schema_for_input(request)
