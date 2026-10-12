import pytest
from tests.skill_evolution.v19.test_evidence_review_v19 import setup, case, cases, final
from src.skill_evolution.v19.review_packet_v19 import policy_paragraph_refs
from src.skill_evolution.v19.evidence_review_v19 import EvidenceReviewCase, build_evidence_review_input, validate_evidence_review
from src.skill_evolution.v19.evidence_review_prompt_v19 import build_evidence_review_request
from src.skill_evolution.v19.evidence_projection_v19 import expand
from src.skill_evolution.v19.edit_tracking_v19 import encode, parse


def test_policy_paragraph_stops_at_blank_or_heading_and_preserves_context():
    texts={1:'# One\n',2:'first line\n',3:'continuation\n',5:'second paragraph\n',6:'# Next\n',7:'other\n'}
    policies={f'P/{i}':{'line':i,'text':t,'context_ref':'C1','policy_digest':'sha'} for i,t in texts.items()}
    policies['OTHER/3']={**policies['P/3'],'context_ref':'C2'}
    assert policy_paragraph_refs(policies,{'P/2'})=={'P/1','P/2','P/3'}
    assert policy_paragraph_refs(policies,{'P/5'})=={'P/5'}


def test_one_packet_preserves_seeds_and_has_no_control_fields(setup):
    c=cases(setup[2])[0];request=build_evidence_review_input(c,input_version='v19.3');p=request.payload
    assert set(c.payload['seed_refs'])<=set(p['events'])
    assert set(c.payload['known_counterevidence_refs'])<=set(p['events'])
    assert not any(k.endswith('_directory') or k=='context_requests_remaining' for k in p)
    prompt=build_evidence_review_request(request)
    assert 'MORE_CONTEXT' not in encode(prompt['response_format'])
    assert expand(parse(prompt['user_prompt']))==p
    assert prompt['max_completion_tokens']==24000
    for verdict in ('VERIFIED','NO_EDIT'):
        result=validate_evidence_review(encode(final(p,verdict=verdict)),request=request)
        assert result.payload['verdict']==verdict
    with pytest.raises(ValueError,match='final verdict'):
        validate_evidence_review('{"request":"MORE_CONTEXT"}',request=request)
    with pytest.raises(ValueError,match='no context supplement'):
        build_evidence_review_input(c,input_version='v19.3',context_round=1)


def test_policy_named_tool_is_loaded_without_model_request(setup):
    p=cases(setup[2])[0].payload
    tool_ref,tool=next(iter(p['tools'].items()));name=tool['definition']['function']['name']
    policy_ref='POLICY/synthetic/L1'
    p['policies'][policy_ref]={'context_ref':tool['context_ref'],'policy_digest':'synthetic',
        'line':1,'text':f'Before acting, use {name}.\n','reference_type':'VISIBLE_POLICY'}
    assert p['findings'];p['findings'][0]['policy_refs']=[policy_ref]
    request=build_evidence_review_input(EvidenceReviewCase(encode(p)),input_version='v19.3')
    assert tool_ref in request.payload['tools']
    refs={e['evidence_ref'] for exp in p['experiences'] if exp['context_ref']==tool['context_ref']
          for e in exp['events'] if e.get('tool_name')==name}
    assert refs<=set(request.payload['events'])
    # This generic test uses a fixture-selected tool, not a Pilot-specific name.


def test_history_association_does_not_expand_all_raw_events(setup):
    from copy import deepcopy
    p=cases(setup[2])[0].payload
    original=deepcopy(p)
    # An archived observation can describe a different pair without making its
    # entire replay mandatory for this issue.
    extra=deepcopy(p['experiences'][0])
    extra['events']=[{'evidence_ref':'PAIR/unrelated/PARENT/E1',
        'event_type':'message','step':1,'content':'unrelated archived behavior'}]
    p['experiences'].append(extra)
    p['seed_refs'].append('PAIR/unrelated/PARENT/E1')
    observation={'parent_evidence_refs':['PAIR/unrelated/PARENT/E1'],
        'candidate_evidence_refs':[],'behavior_comparison':'Keep this historical limitation.'}
    p['historical_observations'].append(observation)
    archive=EvidenceReviewCase(encode(p))
    request=build_evidence_review_input(archive,input_version='v19.3')
    assert 'PAIR/unrelated/PARENT/E1' not in request.payload['events']
    assert observation in request.payload['historical_observations']
    assert archive.payload==p  # No mutation of canonical evidence.
    assert request.payload['case_ref']==archive.case_ref
    # A known counterexample is mandatory even without a Review citation.
    p['known_counterevidence_refs'].append('PAIR/unrelated/PARENT/E1')
    counter=build_evidence_review_input(EvidenceReviewCase(encode(p)),input_version='v19.3')
    assert 'PAIR/unrelated/PARENT/E1' in counter.payload['events']
    assert original['experiences']==p['experiences'][:-1]


def test_all_explicit_review_citations_and_counterevidence_survive(setup):
    from src.skill_evolution.v19.review_packet_v19 import scoped_case
    for c in cases(setup[2]):
        selected=scoped_case(c).payload
        packet=build_evidence_review_input(c,input_version='v19.3').payload
        assert set(selected['seed_refs'])<=set(packet['events'])
        assert set(c.payload['known_counterevidence_refs'])<=set(packet['events'])
        for h in packet['historical_objects']:
            assert 'reason' not in h  # Exists once in historical_reviews.
            if 'edit_attempt' in h:
                assert 'source_findings' not in h['edit_attempt']
        # A declared historical reference without a body is never citeable.
        x=final(packet);x['evidence_refs']=['PAIR/unloaded/PARENT/E1']
        with pytest.raises(ValueError,match='UNKNOWN_OR_UNLOADED'):
            validate_evidence_review(encode(x),request=build_evidence_review_input(c,input_version='v19.3'))


def test_unloaded_historical_counterevidence_blocks_verified(setup):
    from copy import deepcopy
    p=cases(setup[2])[0].payload
    exp=deepcopy(p['experiences'][0]);ref='PAIR/oversized/PARENT/E1'
    exp['origin']='HISTORICAL_PARENT'
    exp['events']=[{'evidence_ref':ref,'event_type':'message','step':1,
                    'content':'unabridged counterexample '*10000}]
    p['experiences'].append(exp);p['known_counterevidence_refs'].append(ref)
    packet=build_evidence_review_input(EvidenceReviewCase(encode(p)),input_version='v19.3')
    assert packet.payload['memory_consumption']['omitted_counterevidence_count']==1
    with pytest.raises(ValueError,match='VERIFIED forbidden'):
        validate_evidence_review(encode(final(packet.payload)),request=packet)
    validate_evidence_review(encode(final(packet.payload,verdict='NO_EDIT')),request=packet)
