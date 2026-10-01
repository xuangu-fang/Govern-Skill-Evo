from copy import deepcopy

import pytest

from tests.skill_evolution.test_memory_generation_v19 import setup, current, case
from src.skill_evolution.edit_tracking_v19 import encode, parse
from src.skill_evolution.memory_store_v19 import load_memory, initialize_memory
from src.skill_evolution.current_diagnosis_v19 import (
    build_current_diagnosis_inputs, validate_current_findings, validate_current_batch)
from src.skill_evolution.historical_review_v19 import (
    build_memory_review_input, validate_historical_reviews, resolve_current_evidence)
from src.skill_evolution.review_contract_v19 import CurrentFindings
from src.skill_evolution.review_prompt_v19 import build_current_diagnosis_request, build_historical_review_request


def inputs(kwargs):
    parent = load_memory(kwargs['store_dir']).head['retained_skill']
    return build_current_diagnosis_inputs(run_id='test-run', parent_skill=parent,
        **{k: v for k, v in kwargs.items() if k != 'store_dir'})


def response(request, kind='OBSERVED_PROBLEM'):
    exp = request.payload['experiences'][0]
    return {'schema_version': 'current_findings_response_v19.1', 'summary': 'Current behavior and limits.',
        'findings': [{'kind': kind, 'statement': 'The observed choice remains uncertain.',
            'applicability': 'Only the observed requests.', 'dimensions': ['SUCCESS'],
            'evidence_refs': [exp['events'][0]['evidence_ref']],
            'supervision_refs': [exp['supervision']['supervision_ref']],
            'policy_refs': [], 'related_rule_refs': [], 'uncertainty': ['Sampling confounding.']}]}


def review_input(kwargs):
    requests = inputs(kwargs)
    findings = [validate_current_findings(encode(response(r)), request=r) for r in requests]
    return requests, findings, build_memory_review_input(store_dir=kwargs['store_dir'],
        current_requests=requests, current_findings=findings)


def review_response(request, status='NOT_COVERED'):
    refs = list(request.payload['current_evidence'])
    return {'schema_version': 'historical_review_response_v19.1', 'reviews': [
        {'historical_object_id': o['historical_object_id'], 'evidence_status': status,
         'supporting_current_refs': refs[:1] if status in ('SUPPORTED','MIXED') else [],
         'contradicting_current_refs': refs[1:2] if status in ('CONTRADICTED','MIXED') else [],
         'context_current_refs': [], 'current_finding_refs': [], 'historical_evidence_refs': [],
         'coverage_reason': 'NO_RELEVANT_OBSERVATION' if status=='NOT_COVERED' else 'ASSESSED',
         'reason': 'Current evidence assessed within the historical scope.',
         'uncertainty': ['Not causal proof.']} for o in request.payload['historical_objects']]}


def test_current_inputs_never_retrieve_or_route_memory(setup, monkeypatch):
    _, _, kwargs = setup
    def fail(*args, **kwargs): raise AssertionError('Memory used for current discovery')
    import src.skill_evolution.memory_retrieval_v19 as retrieval
    import src.skill_evolution.memory_allocation_v19 as allocation
    monkeypatch.setattr(retrieval, 'retrieve_memory', fail)
    monkeypatch.setattr(allocation, 'allocate_memory', fail)
    request = inputs(kwargs)[0]
    assert all(e['origin']=='CURRENT_PARENT' for e in request.payload['experiences'])
    assert 'memory_context' not in request.payload
    prompt = build_current_diagnosis_request(request)
    assert 'historical_objects' not in parse(prompt['user_prompt'])
    for marker in ('PRIVATE-', 'HIDDEN_', 'monitor_score', 'private_database'):
        assert marker not in prompt['user_prompt']


@pytest.mark.parametrize('kind',['OBSERVED_PROBLEM','EFFECTIVE_BEHAVIOR','COUNTEREVIDENCE','UNCERTAINTY'])
def test_findings_are_stable_immutable_and_not_edit_proposals(setup, kind):
    r = inputs(setup[2])[0]; raw = encode(response(r, kind))
    result = validate_current_findings(raw, request=r)
    assert result == validate_current_findings(raw, request=r)
    changed = result.payload; changed['findings'][0]['statement'] = 'Changed'
    assert result.payload != changed
    assert result.payload['findings'][0]['finding_id'].startswith('CF/')
    invalid = response(r,kind); invalid['findings'][0]['evidence_status']='SUPPORTED'
    with pytest.raises(ValueError): validate_current_findings(encode(invalid),request=r)


@pytest.mark.parametrize('field',['evidence_refs','policy_refs','supervision_refs','related_rule_refs'])
def test_current_wrong_or_historical_refs_rejected(setup,field):
    r=inputs(setup[2])[0]; raw=response(r);raw['findings'][0][field]=['PAIR/old/PARENT/E0001']
    with pytest.raises(ValueError,match='invalid'):validate_current_findings(encode(raw),request=r)


def test_complete_batch_and_tampered_findings_rejected(setup):
    root,_,_=setup; kwargs=current(root,round_id='r3',groups=3)
    rs,fs,review=review_input(kwargs)
    assert len(review.payload['current_findings'])==3
    assert len(review.payload['current_evidence'])==15
    with pytest.raises(ValueError): validate_current_batch(rs[:2],fs[:2])
    data=fs[0].payload;data['findings'][0]['statement']='tampered'
    with pytest.raises(ValueError,match='changed'):validate_current_batch(rs,[CurrentFindings(encode(data)),*fs[1:]])
    with pytest.raises(ValueError):validate_current_batch(rs,[fs[0],fs[0],fs[2]])


@pytest.mark.parametrize('status',['SUPPORTED','CONTRADICTED','MIXED','NOT_COVERED'])
def test_review_status_exact_coverage_and_preserved_findings(setup,status):
    _,fs,r=review_input(setup[2]);before=[f.payload_json for f in fs]
    out=validate_historical_reviews(encode(review_response(r,status)),request=r)
    assert {v['evidence_status'] for v in out.payload['reviews']}=={status}
    assert [f.payload_json for f in fs]==before
    assert out.payload['reviews'][0]['review_id'].startswith('HR/')
    assert r.payload['historical_objects'][0]['historical_judgment']['uncertainty']
    assert build_historical_review_request(r)['input_budget']


@pytest.mark.parametrize('mutation',[
    lambda x,r:x['reviews'].clear(),
    lambda x,r:x['reviews'].append(deepcopy(x['reviews'][0])),
    lambda x,r:x['reviews'][0].update(decision='PROPOSE'),
    lambda x,r:x['reviews'][0].update(evidence_status='SUPPORTED'),
    lambda x,r:x['reviews'][0].update(supporting_current_refs=[next(iter(r.payload['historical_event_catalog']))]),
    lambda x,r:x['reviews'][0].update(current_finding_refs=['CF/invented']),
    lambda x,r:x['reviews'][0].update(historical_object_id='HO/invented'),
])
def test_invalid_reviews_fail_closed(setup,mutation):
    _,_,r=review_input(setup[2]);x=review_response(r);mutation(x,r)
    with pytest.raises(ValueError):validate_historical_reviews(encode(x),request=r)


def test_uncovered_insufficient_distinguished_and_unsummarized_events_available(setup):
    _,fs,r=review_input(setup[2]);x=review_response(r)
    used={ref for f in fs for item in f.payload['findings'] for ref in item['evidence_refs']}
    ref=next(ref for ref in r.payload['current_evidence'] if ref not in used)
    x['reviews'][0].update(coverage_reason='INSUFFICIENT_EVIDENCE',context_current_refs=[ref])
    validate_historical_reviews(encode(x),request=r)
    assert resolve_current_evidence(r,[ref])[0]['event']['evidence_ref']==ref
    x['reviews'][0]['context_current_refs']=[]
    with pytest.raises(ValueError):validate_historical_reviews(encode(x),request=r)


def test_empty_memory_current_only_findings_need_no_status(tmp_path):
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    _,fs,r=review_input(current(tmp_path))
    assert fs[0].payload['findings'] and r.payload['historical_objects']==[]
    assert validate_historical_reviews(encode(review_response(r)),request=r).payload['reviews']==[]


def test_no_findings_still_exposes_all_current_trajectories(setup):
    kwargs=setup[2];rs=inputs(kwargs)
    fs=[validate_current_findings(encode({'schema_version':'current_findings_response_v19.1',
         'summary':'No supported finding.', 'findings':[]}),request=r) for r in rs]
    review=build_memory_review_input(store_dir=kwargs['store_dir'],current_requests=rs,current_findings=fs)
    assert not review.payload['current_findings']
    assert len(review.payload['current_evidence'])==15
    assert review.payload['historical_objects']


def test_each_historical_judgment_has_own_identity_even_for_one_edit(case,tmp_path):
    from tests.skill_evolution.test_memory_v19 import make_round
    from tests.skill_evolution.test_attribution_v19 import record
    from src.skill_evolution.memory_store_v19 import commit_round_memory
    initialize_memory(store_dir=tmp_path/'memory',run_id='test-run',initial_skill='- Parent\n')
    old,kw=make_round(case,tmp_path/'r1',effects=lambda d:[record(d,(0,),'BENEFICIAL'),
                                                         record(d,(2,),'NO_OBSERVED_EFFECT')])
    commit_round_memory(old,store_dir=tmp_path/'memory',expected_head_ref=None,**kw)
    _,_,r=review_input(current(tmp_path))
    objects=r.payload['historical_objects']
    assert len(objects)==2 and len({o['edit_id'] for o in objects})==1
    assert len({o['historical_object_id'] for o in objects})==2
    x=review_response(r); x['reviews'].pop()
    with pytest.raises(ValueError,match='coverage incomplete'):validate_historical_reviews(encode(x),request=r)


def test_findings_from_other_round_cannot_be_mixed(setup):
    root,_,kwargs=setup
    rs,fs,_=review_input(kwargs)
    next_requests=inputs(current(root,round_id='r3'))
    with pytest.raises(ValueError,match='stale'):validate_current_batch(next_requests,fs)


def test_review_finding_links_require_shared_current_events(setup):
    _,fs,r=review_input(setup[2]);x=review_response(r,'SUPPORTED')
    finding=fs[0].payload['findings'][0]
    x['reviews'][0]['current_finding_refs']=[finding['finding_id']]
    x['reviews'][0]['supporting_current_refs']=finding['evidence_refs']
    validate_historical_reviews(encode(x),request=r)
    x['reviews'][0]['supporting_current_refs']=[next(ref for ref in r.payload['current_evidence']
                                                  if ref not in finding['evidence_refs'])]
    with pytest.raises(ValueError,match='shared current evidence'):validate_historical_reviews(encode(x),request=r)
