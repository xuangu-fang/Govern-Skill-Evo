from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from tests.skill_evolution.test_separated_review_v19 import setup,case,review_input,review_response,current
from src.skill_evolution.historical_review_v19 import validate_historical_reviews
from src.skill_evolution.review_contract_v19 import MemoryReviewInput,HistoricalReviews
from src.skill_evolution.edit_tracking_v19 import encode
from src.skill_evolution.issue_fusion_v19 import (build_issue_fusion_input,validate_issue_fusion,
    validate_issue_fusion_result,IssueFusionInput,IssueFusionResult)
from src.skill_evolution.issue_fusion_prompt_v19 import build_issue_fusion_request
from src.skill_evolution.evidence_projection_v19 import expand


def prepared(kwargs):
    _,_,review=review_input(kwargs)
    hr=validate_historical_reviews(encode(review_response(review)),request=review)
    return build_issue_fusion_input(review_request=review,historical_reviews=hr)


def issue(cf=(),hr=(),decision='PROPOSE'):
    return {'source_finding_refs':list(cf),'historical_refs':list(hr),
        'issue_statement':'Observed choice may need a bounded improvement.',
        'decision':decision,'reason':'Needs local evidence review before deciding a change.',
        'related_rule_refs':[]}


def output(r):
    p=r.payload
    return {'schema_version':'issue_fusion_response_v19.1',
        'issues':[issue(cf=[f['finding_id']]) for f in p['current_findings']]+
                 [issue(hr=[h['review_id']],decision='NO_EDIT') for h in p['historical_reviews']],
        'unassociated_findings':[]}


def test_current_and_history_only_issues_keep_provenance_without_edit_authority(setup):
    r=prepared(setup[2]);raw=encode(output(r));a=validate_issue_fusion(raw,request=r)
    assert validate_issue_fusion_result(a,request=r)==a
    assert a==validate_issue_fusion(raw,request=r)
    assert a.payload['issues'][0]['issue_id'].startswith('ISSUE/')
    assert a.payload['issues'][1]['historical_refs']
    assert 'NOT_VERIFIED' in a.payload['authority']
    assert not {'gap','plan','candidate_skill'} & set(a.payload)


@pytest.mark.parametrize('mutation',[
    lambda x:x['issues'].pop(0),
    lambda x:x['issues'].pop(),
    lambda x:x['issues'][0].update(source_finding_refs=['CF/unknown']),
    lambda x:x['issues'][0].update(related_rule_refs=['RULE/stale']),
    lambda x:x['issues'].append(deepcopy(x['issues'][0])),
    lambda x:x['issues'][0].update(gap={'kind':'MISSING'}),
    lambda x:x['issues'][0].update(decision='VERIFIED'),
    lambda x:x['issues'][0].update(source_finding_refs=[]),
])
def test_invalid_outputs_fail_closed(setup,mutation):
    r=prepared(setup[2]);x=output(r);mutation(x)
    with pytest.raises(ValueError):validate_issue_fusion(encode(x),request=r)


def test_evidence_can_support_multiple_issues_without_own_disposition(setup):
    r=prepared(current(setup[0],round_id='r3',groups=3));p=r.payload
    p['current_findings'][2]['kind']='COUNTEREVIDENCE'
    r=IssueFusionInput(encode(p));x=output(r)
    evidence=x['issues'].pop(2)['source_finding_refs'][0]
    for d in x['issues'][:2]:d['source_finding_refs'].append(evidence)
    result=validate_issue_fusion(encode(x),request=r)
    assert sum(evidence in d['source_finding_refs'] for d in result.payload['issues'])==2
    assert len(result.payload['issues'])==3


def test_unassociated_evidence_needs_reason_but_problem_cannot_be_dropped(setup):
    r=prepared(setup[2]);x=output(r);ref=x['issues'].pop(0)['source_finding_refs'][0]
    x['unassociated_findings']=[{'finding_ref':ref,'reason':'No related issue in this batch.'}]
    with pytest.raises(ValueError,match='observed problem'):validate_issue_fusion(encode(x),request=r)
    p=r.payload;p['current_findings'][0]['kind']='EFFECTIVE_BEHAVIOR';r=IssueFusionInput(encode(p))
    validate_issue_fusion(encode(x),request=r)
    x['issues'].append(issue(cf=[ref]))
    with pytest.raises(ValueError,match='used'):validate_issue_fusion(encode(x),request=r)


def test_empty_inputs_and_multiple_proposals_are_allowed(setup):
    r=prepared(current(setup[0],round_id='r3',groups=3));x=output(r)
    assert len([d for d in validate_issue_fusion(encode(x),request=r).payload['issues'] if d['decision']=='PROPOSE'])==3
    p=r.payload;p['current_findings']=[];p['historical_reviews']=[]
    r=IssueFusionInput(encode(p))
    assert validate_issue_fusion(encode(output(r)),request=r).payload['issues']==[]


def test_request_boundary_budget_and_result_tampering(setup):
    r=prepared(setup[2]);prompt=build_issue_fusion_request(r)
    from src.skill_evolution.issue_fusion_v19 import fusion_wire_payload
    assert expand(json.loads(prompt['user_prompt']))==fusion_wire_payload(r)
    with pytest.raises(ValueError,match='stage input budget'):build_issue_fusion_request(r,max_input_tokens=1)
    result=validate_issue_fusion(encode(output(r)),request=r);p=result.payload
    p['issues'][0]['decision']='NO_EDIT'
    with pytest.raises(ValueError,match='changed'):validate_issue_fusion_result(IssueFusionResult(encode(p)),request=r)
    from src.skill_evolution.reconciliation_v19 import reconciliation_editor_request
    with pytest.raises((ValueError,KeyError,AttributeError)):
        reconciliation_editor_request(result,request=r)


def test_upstream_raw_review_tampering_rejected(setup):
    _,_,review=review_input(setup[2]);hr=validate_historical_reviews(encode(review_response(review)),request=review)
    p=hr.payload;p['reviews'][0]['reason']='tampered'
    with pytest.raises(ValueError,match='stale'):build_issue_fusion_input(review_request=review,historical_reviews=HistoricalReviews(encode(p)))


def test_real_input_retains_all_semantic_findings_without_raw_evidence():
    f=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/v19_reconciliation_failure.json.gz').read_bytes()))['input']
    review=MemoryReviewInput(encode(f['review_input']));hr=HistoricalReviews(encode(f['historical_reviews']))
    before=review.payload_json;r=build_issue_fusion_input(review_request=review,historical_reviews=hr)
    prompt=build_issue_fusion_request(r)
    assert len(r.payload['current_findings'])==41
    for slim,full in zip(r.payload['current_findings'],review.payload['current_findings']):
        assert all(slim[k]==full[k] for k in slim)
    def keys(v):
        if isinstance(v,dict):return set(v)|set().union(*(keys(x) for x in v.values()))
        if isinstance(v,list):return set().union(*(keys(x) for x in v))
        return set()
    assert not {'events','experiences','current_evidence','memory_context','public_tools',
                'visible_policy','raw_response','historical_event_refs','evidence_refs'} & keys(r.payload)
    assert prompt['input_budget']['proxy_input_tokens']<20000
    assert review.payload_json==before


@pytest.mark.parametrize('size',[64000,64001,65853,100000,128000])
def test_fusion_observation_threshold_accepts_initial_and_repair(size):
    from src.skill_evolution.issue_fusion_prompt_v19 import check_fusion_budget
    for kind in ('initial','repair'):
        prompt={'input_budget':{'proxy_input_tokens':size},'kind':kind}
        assert check_fusion_budget(prompt) is prompt
        assert prompt['input_budget']['observation_threshold']==64000
        assert prompt['input_budget']['above_observation_threshold']==(size>64000)
        assert prompt['input_budget']['engineering_limit']==128000
    with pytest.raises(ValueError,match='stage input budget'):
        check_fusion_budget({'input_budget':{'proxy_input_tokens':128001}})


def test_shared_history_view_keeps_limits_and_provenance_without_discovery_bodies():
    from src.skill_evolution.memory_consumption_v19 import historical_object_view
    judgment={'effect':'MIXED','uncertainty':'Not causal proof','negative':'Task completion regressed'}
    other={'attribution_id':'ATTR/other','effect':'UNKNOWN','uncertainty':'Unresolved'}
    obj={'edit_id':'EDIT/a','attribution_id':'ATTR/a','historical_judgment':judgment,
         'joint_edit_ids':['EDIT/a','EDIT/b'],'edit':{'after_text':'Attempted behavior'},
         'edit_attempt':{'attempt':{'after_text':'Attempted behavior'},
            'source_findings':[{'finding_id':'CF/a','statement':'Archived body','evidence_refs':['EVENT/a']}],
            'problems':[{'issue_id':'ISSUE/a','statement':'Problem scope'}],
            'gate_decision':'RETAIN','results':[{'attribution_id':'ATTR/a',**judgment},other]}}
    before=deepcopy(obj);slim=historical_object_view(obj)
    assert obj==before
    assert slim['historical_judgment']==judgment
    assert slim['joint_edit_ids']==['EDIT/a','EDIT/b']
    assert slim['edit_attempt']['source_finding_refs']==['CF/a']
    assert slim['edit_attempt']['other_results']==[other]
    assert slim['edit_attempt']['gate_decision']=='RETAIN'
    assert not {'source_findings','attempt','results'} & set(slim['edit_attempt'])
    obj['edit_attempt']['source_findings'][0]['statement']='Large archived body '*10000
    assert historical_object_view(obj)==slim


def test_new_fusion_version_and_exact_legacy_validation(setup):
    _,_,review=review_input(setup[2])
    hr=validate_historical_reviews(encode(review_response(review)),request=review)
    new=build_issue_fusion_input(review_request=review,historical_reviews=hr)
    old=build_issue_fusion_input(review_request=review,historical_reviews=hr,legacy=True)
    assert new.payload['schema_version']=='issue_fusion_input_v19.2'
    assert new.input_ref!=old.input_ref
    archived=validate_issue_fusion(encode(output(old)),request=old)
    assert validate_issue_fusion_result(archived,request=old)==archived
    with pytest.raises(ValueError,match='changed'):
        validate_issue_fusion_result(archived,request=new)


def test_short_refs_roundtrip_repair_and_strict_types(setup):
    from src.skill_evolution.issue_fusion_v19 import fusion_reference_map
    from src.skill_evolution.contract_repair_v19 import build_repair
    r=prepared(setup[2]);canonical=output(r)
    aliases=fusion_reference_map(r);reverse={v:k for k,v in aliases.items()}
    wire=deepcopy(canonical)
    for item in wire['issues']:
        for field in ('source_finding_refs','historical_refs','related_rule_refs'):
            item[field]=[reverse[x] for x in item[field]]
    assert validate_issue_fusion(encode(wire),request=r,wire=True)==validate_issue_fusion(encode(canonical),request=r)
    prompt=build_issue_fusion_request(r)
    repaired=build_repair(prompt,encode(wire),ValueError('unknown F reference: F99'))
    assert repaired['reference_map']==aliases
    assert json.loads(repaired['user_prompt'])['original_input']==json.loads(prompt['user_prompt'])
    for bad in ('F99','H01',canonical['issues'][0]['source_finding_refs'][0]):
        broken=deepcopy(wire);broken['issues'][0]['source_finding_refs']=[bad]
        with pytest.raises(ValueError,match='unknown F reference'):
            validate_issue_fusion(encode(broken),request=r,wire=True)
    broken=deepcopy(wire);broken['issues'].pop(0)
    with pytest.raises(ValueError,match='coverage incomplete'):
        validate_issue_fusion(encode(broken),request=r,wire=True)


def test_short_rule_and_unassociated_refs_restore_canonical_ids(setup):
    from src.skill_evolution.issue_fusion_v19 import fusion_reference_map, fusion_wire_payload
    p=prepared(setup[2]).payload
    p['current_findings'][0]['kind']='EFFECTIVE_BEHAVIOR'
    rule='RULE/'+'a'*64+'/L1-1'
    p['available_rule_refs']={rule:'A loaded rule.'}
    p['current_findings'][0]['related_rule_refs']=[rule]
    r=IssueFusionInput(encode(p));mapping=fusion_reference_map(r)
    wire=fusion_wire_payload(r)
    assert wire['current_findings'][0]['related_rule_refs']==['R01']
    assert wire['available_rule_refs']=={'R01':'A loaded rule.'}
    response={'schema_version':'issue_fusion_response_v19.1',
        'issues':[issue(hr=[h['review_id']],decision='NO_EDIT') for h in wire['historical_reviews']],
        'unassociated_findings':[{'finding_ref':'F01','reason':'No related issue.'}]}
    response['issues'][0]['related_rule_refs']=['R01']
    result=validate_issue_fusion(encode(response),request=r,wire=True)
    assert result.payload['issues'][0]['related_rule_refs']==[rule]
    assert result.payload['unassociated_findings'][0]['finding_ref']==mapping['F01']
    assert validate_issue_fusion_result(result,request=r)==result
