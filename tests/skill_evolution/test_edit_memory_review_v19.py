from copy import deepcopy
import pytest
from tests.skill_evolution.test_separated_review_v19 import setup, case, review_input
from tests.skill_evolution.test_attribution_v19 import complete
from src.skill_evolution.edit_tracking_v19 import encode,parse
from src.skill_evolution.review_contract_v19 import MemoryReviewInput
from src.skill_evolution.edit_memory_review_v19 import build_edit_packets,packet_profile,run_edit_reviews,validate_packet,packet_wire,build_packet_request
from src.skill_evolution.issue_fusion_v19 import build_issue_fusion_input
from src.skill_evolution.evolution_replay_v19 import _load


def linked_request(setup):
    _,_,kwargs=setup
    request=review_input(kwargs)[2]
    p=request.payload
    # Explicit provenance link, never inferred by the packet builder.
    rule=p['historical_objects'][0]['current_binding']['current_rule_refs'][0]
    p['current_findings'][0]['related_rule_refs']=[rule]
    return MemoryReviewInput(encode(p))


def reply(packet,status='NOT_COVERED'):
    refs=list(packet.payload['current_evidence'])
    return {'schema_version':'historical_review_response_v19.1','reviews':[{
        'historical_object_id':o['historical_object_id'],'evidence_status':status,
        'supporting_current_refs':refs[:1] if status=='SUPPORTED' else [],'contradicting_current_refs':[],
        'context_current_refs':[], 'current_finding_refs':([f['finding_id'] for f in packet.payload['current_findings'] if set(refs[:1]) & set(f['evidence_refs'])] if status=='SUPPORTED' else []), 'historical_evidence_refs':[],
        'coverage_reason':'ASSESSED' if status=='SUPPORTED' else 'NO_RELEVANT_OBSERVATION',
        'reason':'No linked evidence is not evidence of resolution.','uncertainty':['Sampling.']}
        for o in packet.payload['historical_objects']]}


def test_packet_boundary_and_finding_coverage(setup):
    request=linked_request(setup);packets=build_edit_packets(request)
    assert len(packets)==len({o['edit_id'] for o in request.payload['historical_objects']})
    assert any(p.payload['current_findings'] for p in packets)
    for packet in packets:
        p=packet.payload
        assert not {'memory_context','generation_reviews','replay'} & set(p)
        for f in p['current_findings']:
            assert set(f['related_rule_refs']) & set(p['current_rules'])
        assert p['attribution']
        assert all(ref in request.payload['current_evidence'] for ref in p['current_evidence'])
    profile=packet_profile(request)
    assert profile['finding_count']==len(request.payload['current_findings'])
    assert profile['all_current_findings_retained_for_fusion']


def test_no_links_no_broadcast_and_no_outside_refs(setup):
    request=review_input(setup[2])[2]
    packets=build_edit_packets(request)
    assert all([f['finding_id'] for f in p.payload['current_findings']]==[f['finding_id'] for f in request.payload['current_findings']] for p in packets)
    assert all('event' not in e for p in packets for e in p.payload['current_evidence'].values())
    p=packets[0];raw=reply(p)
    raw['reviews'][0]['supporting_current_refs']=[next(iter(request.payload['current_evidence']))]
    raw['reviews'][0]['evidence_status']='SUPPORTED';raw['reviews'][0]['coverage_reason']='ASSESSED'
    with pytest.raises(ValueError,match='selected findings'):
        validate_packet(encode(raw),p)


def test_resume_isolated_failure_and_fusion(setup,tmp_path):
    request=linked_request(setup);packets=build_edit_packets(request);calls=[]
    # One valid response, then a transport failure; other edits must be retained.
    by_prompt={build_packet_request(p)['user_prompt']:p for p in packets}
    def transport(prepared):
        p=by_prompt[prepared['user_prompt']];calls.append(p.payload['edit_id'])
        if len(calls)==1:raise TimeoutError('synthetic interruption')
        return complete(encode(reply(p)))
    root=tmp_path/'reviews'
    with pytest.raises(ValueError,match='incomplete'):
        run_edit_reviews(request,artifact_dir=root,transport=transport)
    assert len(calls)==len(packets)
    before=len(calls)
    with pytest.raises(ValueError,match='incomplete'):
        run_edit_reviews(request,artifact_dir=root,transport=transport)
    assert len(calls)==before # uncertain request is never silently resent
    fresh=tmp_path/'fresh'
    def good(prepared):return complete(encode(reply(by_prompt[prepared['user_prompt']])))
    merged=run_edit_reviews(request,artifact_dir=fresh,transport=good)
    assert run_edit_reviews(request,artifact_dir=fresh,transport=lambda _:pytest.fail('rerun'))==merged
    fusion=build_issue_fusion_input(review_request=request,historical_reviews=merged)
    assert len(fusion.payload['current_findings'])==len(request.payload['current_findings'])
    assert len(fusion.payload['historical_reviews'])==len(request.payload['historical_objects'])


def test_budget_prevents_dispatch_without_truncation(setup,tmp_path,monkeypatch):
    import src.skill_evolution.edit_memory_review_v19 as module
    request=linked_request(setup)
    monkeypatch.setattr(module,'MAX_INPUT_TOKENS',1)
    with pytest.raises(ValueError,match='incomplete'):
        run_edit_reviews(request,artifact_dir=tmp_path/'run',transport=lambda _:pytest.fail('over-budget call'))
    assert _load(tmp_path/'run/status.json')['completed_edits']==0
    assert not list((tmp_path/'run').glob('*/review/request.json'))


def test_aliases_expand_before_validation(setup):
    packet=next(p for p in build_edit_packets(linked_request(setup)) if p.payload['current_evidence'])
    raw=reply(packet,'SUPPORTED');prefixes=packet_wire(packet.payload)['reference_prefixes']
    ref=raw['reviews'][0]['supporting_current_refs'][0]
    for alias,prefix in prefixes.items():
        if ref.startswith(prefix):raw['reviews'][0]['supporting_current_refs']=[alias+ref[len(prefix):]];break
    result=validate_packet(encode(raw),packet)
    assert result.payload['reviews'][0]['supporting_current_refs']==[ref]

@pytest.mark.parametrize('status',['SUPPORTED','CONTRADICTED','MIXED','NOT_COVERED'])
def test_status_semantics_preserved(setup,status):
    data=linked_request(setup).payload
    data['current_findings'][0]['evidence_refs']=list(data['current_evidence'])[:2]
    packet=next(p for p in build_edit_packets(MemoryReviewInput(encode(data))) if p.payload['current_evidence'])
    refs=list(packet.payload['current_evidence']);assert len(refs)>=2
    raw=reply(packet)
    for row in raw['reviews']:
        row['evidence_status']=status
        row['supporting_current_refs']=refs[:1] if status in ('SUPPORTED','MIXED') else []
        row['contradicting_current_refs']=refs[1:2] if status in ('CONTRADICTED','MIXED') else []
        row['coverage_reason']='NO_RELEVANT_OBSERVATION' if status=='NOT_COVERED' else 'ASSESSED'
        row['current_finding_refs']=[packet.payload['current_findings'][0]['finding_id']] if status!='NOT_COVERED' else []
    assert {r['evidence_status'] for r in validate_packet(encode(raw),packet).payload['reviews']}=={status}


def test_all_attribution_polarities_survive(setup):
    request=linked_request(setup)
    for packet in build_edit_packets(request):
        p=packet.payload
        required={ref for attr in p['attribution'] for obs in attr['observations']
                  for field in ('parent_evidence_refs','candidate_evidence_refs') for ref in obs[field]}
        assert required == set(p['historical_evidence_refs'])
        assert not p['historical_evidence']
        assert all('uncertainty' in attr and 'alternative_explanations' in attr for attr in p['attribution'])
        raw=reply(packet);raw['reviews'][0]['historical_evidence_refs']=['PAIR/not-loaded/PARENT/E0001']
        with pytest.raises(ValueError,match='historical evidence outside'):
            validate_packet(encode(raw),packet)


def test_one_audited_repair_per_edit(setup,tmp_path):
    request=linked_request(setup);packets=build_edit_packets(request)
    by_prompt={build_packet_request(p)['user_prompt']:p for p in packets}
    pending=None;calls=[]
    def transport(prepared):
        nonlocal pending
        calls.append(prepared['prompt_version'])
        if prepared['prompt_version'].endswith('-repair-001'):
            return complete(encode(reply(pending)))
        pending=by_prompt[prepared['user_prompt']]
        raw=reply(pending);raw['reviews'][0]['historical_evidence_refs']=['PAIR/unknown/E1']
        return complete(encode(raw))
    root=tmp_path/'repair'
    run_edit_reviews(request,artifact_dir=root,transport=transport)
    assert len(calls)==2*len(packets)
    assert len(list(root.glob('*/review/contract_rejection.json')))==len(packets)
    assert len(list(root.glob('*/review-repair-001/response.json')))==len(packets)
    run_edit_reviews(request,artifact_dir=root,transport=lambda _:pytest.fail('repair rerun'))


def test_historical_summary_preserves_all_observations_and_results(setup):
    request=linked_request(setup)
    before=request.payload_json
    for packet in build_edit_packets(request):
        p=packet.payload
        row=next(r for r in request.payload['memory_context']['rounds']
                 if any(e['edit_id']==p['edit_id'] for e in r['edits']))
        assert p['attribution']==[a for a in row['attribution']['records'] if p['edit_id'] in a['edit_ids']]
        ids={o['pair_id'] for a in p['attribution'] for o in a['observations']}
        assert set(p['historical_pair_outcomes'])==ids
        for pair in row['replay']['pairs']:
            if pair['pair_id'] in ids:
                assert p['historical_pair_outcomes'][pair['pair_id']]['outcome_transition']==pair['outcome_transition']
        assert all(set(v)=={'pair_id','role'} for v in p['historical_evidence_refs'].values())
        # Archive pointers remain valid provenance, not loaded raw event assertions.
        raw=reply(packet)
        for item,obj in zip(raw['reviews'],p['historical_objects']):
            item['historical_evidence_refs']=obj['historical_event_refs'][:1]
        assert validate_packet(encode(raw),packet)
    assert request.payload_json==before


def test_historical_body_growth_does_not_expand_packet(setup):
    request=linked_request(setup);data=request.payload
    marker='ARCHIVED_RAW_CONTENT_ONLY_'
    for row in data['memory_context']['rounds']:
        for pair in row['replay']['pairs']:
            for role in ('parent','candidate'):
                for event in pair[role]['events']:
                    event['content']=marker*10000
    changed=MemoryReviewInput(encode(data))
    for original,large in zip(build_edit_packets(request),build_edit_packets(changed)):
        a,b=original.payload,large.payload
        assert marker not in encode(packet_wire(b))
        a.pop('source_input_ref');b.pop('source_input_ref')
        assert a==b


def test_missing_archived_reference_is_still_rejected(setup):
    data=linked_request(setup).payload
    for row in data['memory_context']['rounds']:
        for pair in row['replay']['pairs']:
            for role in ('parent','candidate'):pair[role]['events']=[]
    with pytest.raises(ValueError,match='missing attribution evidence'):
        build_edit_packets(MemoryReviewInput(encode(data)))


def test_absent_rejected_edit_can_associate_and_reach_fusion(setup,tmp_path):
    request=review_input(setup[2])[2]
    p=request.payload
    for obj in p['historical_objects']:
        obj['current_binding']['current_rule_refs']=[]
        obj['current_binding']['descendant_rule_refs']=[]
    for row in p['memory_context']['rounds']:
        row['memory_record']['gate_decision']='RETAIN'
    from src.skill_evolution.memory_experience_v19 import project_attempts
    p['edit_attempts']=project_attempts(p['memory_context'])
    request=MemoryReviewInput(encode(p))
    packets=build_edit_packets(request)
    assert all(not packet.payload['current_rules'] for packet in packets)
    prompts={build_packet_request(packet)['user_prompt']:packet for packet in packets}
    def transport(prepared):
        packet=prompts[prepared['user_prompt']]
        return complete(encode(reply(packet,'SUPPORTED')))
    result=run_edit_reviews(request,artifact_dir=tmp_path/'associated',transport=transport)
    fusion=build_issue_fusion_input(review_request=request,historical_reviews=result)
    assert all(r['current_finding_refs'] for r in fusion.payload['historical_reviews'])
    assert all(r['edit_attempt']['gate_decision']=='RETAIN' for r in fusion.payload['historical_reviews'])
    assert all(r['historical_judgment'] for r in fusion.payload['historical_reviews'])
    assert all('results' not in r['edit_attempt'] for r in fusion.payload['historical_reviews'])


def test_legacy_packet_and_summary_growth_boundary(setup):
    request=review_input(setup[2])[2]
    p=request.payload
    original=build_edit_packets(request)
    for item in p['current_evidence'].values():
        item['event']['test_large_raw_body']='archived only '*10000
    for row in p['memory_context']['rounds']:
        for pair in row['replay']['pairs']:
            for role in ('parent','candidate'):
                for event in pair[role]['events']:
                    event['test_large_raw_body']='archived only '*10000
    enlarged=build_edit_packets(MemoryReviewInput(encode(p)))
    for a,b in zip(original,enlarged):
        left=a.payload;right=b.payload
        left.pop('source_input_ref');right.pop('source_input_ref')
        assert left==right
    legacy=request.payload
    legacy.pop('memory_protocol');legacy.pop('edit_attempts')
    assert all(not packet.payload['current_evidence'] for packet in build_edit_packets(MemoryReviewInput(encode(legacy))))


def test_new_memory_semantics_hide_legacy_effects_without_mutating_archive(setup):
    request=review_input(setup[2])[2]
    assert request.payload['memory_protocol']=='issue_memory_v19.2'
    for row in request.payload['memory_context']['rounds']:
        assert all('effect' not in record for record in row['attribution']['records'])
    for obj in request.payload['historical_objects']:
        assert 'effect' not in obj['historical_judgment']
    for packet in build_edit_packets(request):
        assert all('effect' not in record for record in packet.payload['attribution'])
        assert 'specific historical behavior' in __import__('src.skill_evolution.edit_memory_review_v19',fromlist=['build_packet_request']).build_packet_request(packet)['system_prompt']
    from src.skill_evolution.memory_store_v19 import load_memory
    snapshot=load_memory(setup[2]['store_dir'])
    assert all('effect' in record for row in snapshot.rounds for record in row['attribution']['records'])


def test_absent_attempt_recurrence_keeps_association_without_effect_judgment(setup):
    request=review_input(setup[2])[2]
    p=request.payload
    for obj in p['historical_objects']:
        obj['current_binding'].update(binding_status='ABSENT',current_rule_refs=[],descendant_rule_refs=[])
    packet=build_edit_packets(MemoryReviewInput(encode(p)))[0]
    f=packet.payload['current_findings'][0]
    raw=reply(packet)
    for row in raw['reviews']:
        row.update(coverage_reason='INSUFFICIENT_EVIDENCE',
                   context_current_refs=f['evidence_refs'],current_finding_refs=[f['finding_id']],
                   reason='The problem recurred without the attempted rule. This does not test its effectiveness.')
    result=validate_packet(encode(raw),packet)
    for row in result.payload['reviews']:
        assert row['evidence_status']=='NOT_COVERED'
        assert row['current_finding_refs']==[f['finding_id']]
        assert not row['supporting_current_refs'] and not row['contradicting_current_refs']
    from src.skill_evolution.memory_consumption_v19 import REVIEW_COMPARISON
    prompt=build_packet_request(packet)
    assert REVIEW_COMPARISON in prompt['system_prompt']
    assert prompt['prompt_version'].endswith('-claim-comparison-1')


def test_absent_attempt_can_still_have_independent_counterevidence(setup):
    request=review_input(setup[2])[2];p=request.payload
    for obj in p['historical_objects']:
        obj['current_binding'].update(binding_status='ABSENT',current_rule_refs=[],descendant_rule_refs=[])
    packet=build_edit_packets(MemoryReviewInput(encode(p)))[0]
    f=packet.payload['current_findings'][0];raw=reply(packet)
    for row in raw['reviews']:
        row.update(evidence_status='CONTRADICTED',coverage_reason='ASSESSED',
                   contradicting_current_refs=f['evidence_refs'],current_finding_refs=[f['finding_id']],
                   reason='Current tool evidence independently contradicts the attempted execution capability claim.')
    assert all(r['evidence_status']=='CONTRADICTED' for r in validate_packet(encode(raw),packet).payload['reviews'])
