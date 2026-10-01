from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from tests.skill_evolution.test_reconciliation_v19 import setup,prepared,output,decision,diagnosis
from tests.skill_evolution.test_separated_review_v19 import case,review_input,review_response
from src.skill_evolution.review_contract_v19 import MemoryReviewInput,HistoricalReviews
from src.skill_evolution.historical_review_v19 import validate_historical_reviews
from src.skill_evolution.reconciliation_v19 import build_reconciliation_input,validate_reconciliation,_catalog
from src.skill_evolution.reconciliation_evidence_v19 import evidence_view,selected_evidence_refs
from src.skill_evolution.reconciliation_prompt_v19 import build_reconciliation_request
from src.skill_evolution.reconciliation_profile_v19 import profile_request
from src.skill_evolution.evidence_projection_v19 import expand
from src.skill_evolution.edit_tracking_v19 import encode


def rebuild(request,extra=()):
    p=request.payload
    return build_reconciliation_input(contract_version='v19.3',review_request=MemoryReviewInput(encode(p['review_input'])),
        historical_reviews=HistoricalReviews(encode(p['historical_reviews'])),additional_evidence_refs=extra)


def test_reference_view_preserves_exact_evidence_and_all_findings(setup):
    r=prepared(setup[2]); original=r.payload_json
    view=evidence_view(r); full=r.payload; catalog=_catalog(r)
    assert view['review_input']['current_findings']==full['review_input']['current_findings']
    assert view['historical_reviews']['reviews']==full['historical_reviews']['reviews']
    assert 'raw_response' not in view['historical_reviews']
    assert 'memory_context' not in view['review_input']
    assert set(view['events'])==selected_evidence_refs(r)
    for exp in catalog['experiences']:
        for event in exp['events']:
            ref=event['evidence_ref']
            if ref not in view['events']:continue
            loaded=view['events'][ref]; identity=view['trajectories'][loaded['trajectory_id']]
            assert {**loaded['event'],'evidence_ref':ref}==event
            for field in ('origin','role','source_round_id','skill_ref','task_ref','trajectory_ref','context_ref'):
                assert identity[field]==exp[field]
            assert identity['supervision']==exp['supervision']
    assert r.payload_json==original
    assert expand(json.loads(build_reconciliation_request(r)['user_prompt']))==view


def test_history_polarities_uncertainty_bindings_and_paired_labels_remain(setup):
    _,_,review=review_input(setup[2]); raw=review_response(review,'MIXED')
    hr=validate_historical_reviews(encode(raw),request=review)
    r=build_reconciliation_input(contract_version='v19.3',review_request=review,historical_reviews=hr)
    view=evidence_view(r)
    for item in hr.payload['reviews']:
        for field in ('supporting_current_refs','contradicting_current_refs','context_current_refs','historical_evidence_refs'):
            assert set(item[field])<=set(view['events'])
    for obj,old in zip(view['review_input']['historical_objects'],r.payload['review_input']['historical_objects']):
        assert obj['historical_judgment']==old['historical_judgment']
        assert obj['current_binding']==old['current_binding']
        assert 'historical_event_refs' not in obj
        for observation in obj['observations']:
            assert set(observation['supervision_refs'])<={t['supervision']['supervision_ref'] for t in view['trajectories'].values()}
            assert set(observation['parent_evidence_refs']+observation['candidate_evidence_refs'])<=set(view['events'])


def test_unloaded_history_citation_rejected_until_explicitly_loaded(setup):
    r=prepared(setup[2]); x=output(r);d=x['decisions'][0]
    x['decisions'][0]=decision(cf=d['current_finding_refs'],events=d['evidence_refs'])
    obj=r.payload['review_input']['historical_objects'][0]
    ref=next(ref for ref in obj['historical_event_refs'] if ref not in selected_evidence_refs(r))
    x['decisions'][1]=decision(hr=x['decisions'][1]['historical_review_refs'],events=[ref],kind='MISSING')
    with pytest.raises(ValueError,match='not loaded'):validate_reconciliation(encode(x),request=r)
    supplemented=rebuild(r,[ref])
    assert supplemented.input_ref!=r.input_ref
    assert supplemented.payload['review_input']==r.payload['review_input']
    assert set(evidence_view(supplemented)['events'])==set(evidence_view(r)['events'])|{ref}
    result,_=validate_reconciliation(encode(x),request=supplemented)
    assert result.payload['additional_evidence_refs']==[ref]
    with pytest.raises(ValueError,match='unknown refs'):rebuild(r,['PRIVATE/unknown'])
    with pytest.raises(ValueError,match='duplicate'):rebuild(r,[ref,ref])


def test_loading_context_does_not_authorize_unrelated_current_evidence(setup):
    r=prepared(setup[2]);x=output(r)
    ref=next(ref for ref in r.payload['review_input']['current_evidence'] if ref not in selected_evidence_refs(r))
    r=rebuild(r,[ref]);x['decisions'][0]['evidence_refs'].append(ref)
    x['decisions'][0]['proposals']=[diagnosis(x['decisions'][0]['evidence_refs'])]
    with pytest.raises(ValueError,match='outside declared sources'):validate_reconciliation(encode(x),request=r)


def test_context_policy_is_complete_and_not_repeated(setup):
    r=prepared(setup[2]);view=evidence_view(r);catalog=_catalog(r)
    contexts={t['context_ref'] for t in view['trajectories'].values()}
    expected={ref for ref,p in catalog['available_policy_refs'].items() if p['context_ref'] in contexts}
    assert set(view['available_policy_refs'])==expected
    assert all(view['available_policy_refs'][ref]['text']==catalog['available_policy_refs'][ref]['text'] for ref in expected)
    assert all('visible_policy' not in c for c in view['contexts'].values())
    assert view['review_input']['current_skill']==r.payload['review_input']['current_skill']
    assert view['available_rule_refs']==catalog['available_rule_refs']


def test_real_pilot_projection_is_smaller_without_changing_evidence():
    fixture=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/v19_reconciliation_failure.json.gz').read_bytes()))
    p=fixture['input'];before=deepcopy(p)
    r=build_reconciliation_input(contract_version='v19.3',review_request=MemoryReviewInput(encode(p['review_input'])),
        historical_reviews=HistoricalReviews(encode(p['historical_reviews'])))
    view=evidence_view(r);request=build_reconciliation_request(r);profile=profile_request(request)
    assert profile['proxy_input_tokens']==request['input_budget']['proxy_input_tokens']
    assert len(view['review_input']['current_findings'])==41
    assert len(view['events'])==237 < len(p['review_input']['current_evidence'])==832
    assert sum(row['section_proxy_tokens'] for row in profile['sections'].values())+profile['section_serialization_residual']==profile['user_prompt_tokens']
    assert not profile['duplicate_representation']['redundant_identity_occurrences']
    assert 'PRIVATE_EXPECTED_ACTION' not in request['user_prompt']
    assert p==before


def test_profiler_counts_shared_wire_bodies_once():
    from src.skill_evolution.review_prompt_v19 import _request
    from src.skill_evolution.review_contract_v19 import CURRENT_SCHEMA
    text='shared exact original content '*50
    request=_request({'first':text,'second':text},'System.',CURRENT_SCHEMA,'profile-test')
    report=profile_request(request)
    assert report['sections']['shared_bodies']['body_count']==1
    assert report['sections']['first']['body_count']==report['sections']['second']['body_count']==0
    assert report['proxy_input_tokens']==request['input_budget']['proxy_input_tokens']


def test_v2_audit_remains_valid_but_cannot_be_dispatched_as_new_request(setup):
    r=prepared(setup[2]);p=r.payload
    old=build_reconciliation_input(review_request=MemoryReviewInput(encode(p['review_input'])),
        historical_reviews=HistoricalReviews(encode(p['historical_reviews'])),contract_version='v19.2')
    result,_=validate_reconciliation(encode(output(old)),request=old)
    assert 'reconciliation_input_version' not in result.payload
    with pytest.raises(ValueError,match='new model dispatch'):
        build_reconciliation_request(old)
