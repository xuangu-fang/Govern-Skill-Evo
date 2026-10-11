"""Synthetic engineering checks; these are not evidence of method effectiveness."""
from collections import Counter
from dataclasses import replace
import pytest

from tests.skill_evolution.test_campaign_v19 import Evolution,Monitor
from tests.skill_evolution.test_separated_campaign_v19 import transports as upstream_transports
from tests.skill_evolution.test_attribution_v19 import complete
from src.skill_evolution.campaign_v19 import campaign_config,run_campaign_v19
from src.skill_evolution.edit_tracking_v19 import encode,parse,validate_edit_ledger,EditLedger
from src.skill_evolution.evidence_projection_v19 import expand
from src.skill_evolution.memory_store_v19 import load_memory
from src.skill_evolution.evolution_replay_v19 import _load


def transports(calls):
    base=upstream_transports(calls)
    def payload(request):
        for secret in ('PRIVATE-MONITOR','NEVER_LEARN_MONITOR_SECRET','PRIVATE_EXPECTED_ACTION'):
            assert secret not in request['user_prompt']
        value=parse(request['user_prompt'])
        table=value.get('repeated_text',{})
        def restore(v):
            if isinstance(v,dict) and set(v)=={'shared_text_ref'}:return table[v['shared_text_ref']]
            if isinstance(v,dict):return {k:restore(x) for k,x in v.items() if k!='repeated_text'}
            if isinstance(v,list):return [restore(x) for x in v]
            return v
        return expand(restore(value))
    def fusion(request):
        calls['fusion']+=1;p=payload(request)
        return complete(encode({'schema_version':'issue_fusion_response_v19.1','issues':[{
            'source_finding_refs':[f['finding_id'] for f in p['current_findings']],
            'historical_refs':[r['review_id'] for r in p['historical_reviews']],
            'issue_statement':'Conditional observed choice.','decision':'PROPOSE','reason':'One independent problem.',
            'related_rule_refs':[]}], 'unassociated_findings':[]}))
    def local(request):
        calls['local']+=1;p=payload(request)
        targets=sorted({ref for h in p['historical_objects'] for ref in h['current_binding']['current_rule_refs']})
        return complete(encode({'proposal_id':p['proposal_id'],'verdict':'VERIFIED',
            'evidence_refs':[next(iter(p['events']))],'counterevidence_refs':p['known_counterevidence_refs'],
            'reason':'Observed bounded evidence; opposing observations remain tentative.',
            'gap':{'kind':'NEEDS_REVISION' if targets else 'MISSING',
                   'statement':'Conditional observed choice can improve.','related_rule_refs':targets}}))
    def memory_review(request):
        calls['review']+=1
        p=payload(request)
        # This fixture intentionally has no current-rule references. The scoped
        # packet must not broadcast unrelated current events to historical edits.
        assert all('event' not in e for e in p['current_evidence'].values())
        assert p['edit_attempt']
        return complete(encode({'schema_version':'historical_review_response_v19.1','reviews':[{
            'historical_object_id':o['historical_object_id'],'evidence_status':'NOT_COVERED',
            'supporting_current_refs':[],'contradicting_current_refs':[],'context_current_refs':[],
            'current_finding_refs':[],'historical_evidence_refs':[],
            'coverage_reason':'NO_RELEVANT_OBSERVATION','reason':'No explicit current provenance link.',
            'uncertainty':['Unmatched findings still enter Fusion.']} for o in p['historical_objects']]}))
    return replace(base,issue_fusion=fusion,evidence_review=local,memory_review=memory_review)


@pytest.fixture
def setup(tmp_path):
    calls=Counter()
    return dict(output=tmp_path/'campaign',config=campaign_config(attribution_protocol='legacy',pilot=True,max_workers=2,generation_protocol='local'),
        run_id='engineering-run',initial_skill='- Parent\n',evolution_backend=Evolution(),
        monitor_backend=Monitor(),transports=transports(calls)),calls


@pytest.mark.parametrize('gate,relation',[('ACCEPT','REVISES'),('RETAIN','RETRIES')])
def test_local_two_rounds_and_resume(setup,gate,relation):
    kw,calls=setup;kw['monitor_backend']=Monitor(gate)
    result=run_campaign_v19(**kw)
    assert result['status']=='COMPLETE' and result['committed_rounds']==2
    assert result['cross_round_links'][0]['relation']==relation
    snap=load_memory(kw['output']/'memory')
    assert all('evidence_reviews' in r['generation_reviews'] for r in snap.rounds)
    assert {r['evidence_status'] for r in snap.rounds[1]['generation_reviews']['historical_reviews']}=={'NOT_COVERED'}
    for secret in ('PRIVATE-MONITOR','NEVER_LEARN_MONITOR_SECRET','PRIVATE_EXPECTED_ACTION'):
        assert secret not in encode(snap.rounds)
    before=calls.copy();assert run_campaign_v19(**kw,resume=True)==result;assert calls==before
    assert calls['fusion']==calls['local']==2 and calls['reconciliation']==0


@pytest.mark.parametrize('stage',['ISSUE_FUSION','EVIDENCE_REVIEW','COMPILE','EDITOR','BEFORE_COMMIT','AFTER_COMMIT'])
def test_local_resume_stage(setup,stage):
    kw,calls=setup
    def stop(name,round_id):
        if name==stage and round_id=='round-02':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kw,event_hook=stop)
    assert run_campaign_v19(**kw,resume=True)['committed_rounds']==2
    assert calls['fusion']==calls['local']==2 and calls['editor']==2


def test_local_audit_tamper(setup):
    kw,_=setup;run_campaign_v19(**kw)
    ledger=load_memory(kw['output']/'memory').history[0].ledger
    source=ledger.source;source['generation_audit']['evidence_reviews'][0]['result']['reason']='changed'
    with pytest.raises(ValueError):validate_edit_ledger(EditLedger(encode(source),ledger.output_json))


def test_incomplete_does_not_reach_editor(setup):
    kw,calls=setup
    def fail(request):raise TimeoutError('synthetic')
    kw['transports']=replace(kw['transports'],evidence_review=fail)
    with pytest.raises(ValueError,match='incomplete local reviews'):run_campaign_v19(**kw)
    assert calls['editor']==0 and load_memory(kw['output']/'memory').head['revision']==0


def test_no_findings_no_update(setup):
    kw,calls=setup
    kw['transports']=replace(kw['transports'],diagnosis=lambda r:complete(encode({
        'schema_version':'current_findings_response_v19.1','summary':'No finding.','findings':[]})))
    result=run_campaign_v19(**kw)
    assert result['stop_reason']=='NO_UPDATE' and result['committed_rounds']==0
    assert calls['editor']==calls['fusion']==calls['local']==0


def test_reused_upstream_stops_before_editor_and_resumes_without_calls(setup,tmp_path):
    from src.skill_evolution.local_generation_v19 import run_local_reviews
    kw,calls=setup
    def stop(name,round_id):
        if name=='ISSUE_FUSION':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kw,event_hook=stop)
    upstream=_load(kw['output']/'round-01/generation/local-reviews/upstream.json')
    args=dict(upstream=upstream,output=tmp_path/'oneoff',fusion_transport=kw['transports'].issue_fusion,
              evidence_review_transport=kw['transports'].evidence_review)
    audit,value=run_local_reviews(**args)
    assert value.plan.edit_units and calls['editor']==0
    assert _load(args['output']/'status.json')['stage']=='BEFORE_EDITOR'
    before=calls.copy();assert run_local_reviews(**args,resume=True)==(audit,value);assert calls==before
    assert not (args['output']/'editor').exists()
    assert load_memory(kw['output']/'memory').head['revision']==0


def test_missing_proposal_blocks_restore(setup):
    from src.skill_evolution.local_generation_v19 import restore_local_audit
    kw,_=setup;run_campaign_v19(**kw)
    audit=load_memory(kw['output']/'memory').history[0].ledger.source['generation_audit']
    audit['evidence_reviews']=[]
    with pytest.raises(ValueError,match='every PROPOSE'):restore_local_audit(encode(audit))


def test_no_edit_verdict_never_enters_editor(setup):
    kw,calls=setup
    def reject(request):
        p=expand(parse(request['user_prompt']))
        return complete(encode({'proposal_id':p['proposal_id'],'verdict':'NO_EDIT','evidence_refs':[],
            'counterevidence_refs':p['known_counterevidence_refs'],'reason':'Insufficient support.','gap':None}))
    kw['transports']=replace(kw['transports'],evidence_review=reject)
    result=run_campaign_v19(**kw)
    assert result['stop_reason']=='NO_UPDATE' and result['committed_rounds']==0 and calls['editor']==0


def test_explicit_reuse_imports_completed_results_without_calls(setup,tmp_path):
    from src.skill_evolution.local_generation_v19 import run_local_reviews
    kw,calls=setup
    def stop(name,round_id):
        if name=='EDITOR':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kw,event_hook=stop)
    source=kw['output']/'round-01/generation/local-reviews'
    upstream=_load(source/'upstream.json');before=calls.copy()
    def forbidden(request):raise AssertionError('completed source must be reused')
    args=dict(upstream=upstream,output=tmp_path/'imported',reuse_from=source,
        fusion_transport=forbidden,evidence_review_transport=forbidden)
    audit,value=run_local_reviews(**args)
    assert value.plan.edit_units and calls==before
    assert _load(args['output']/'reuse-receipt.json')['proposal_ids']
    assert run_local_reviews(**args,resume=True)==(audit,value)
    assert not (args['output']/'proposals').exists()


def test_fusion_only_reruns_completed_review_under_v3(setup,tmp_path):
    from src.skill_evolution.local_generation_v19 import run_local_reviews
    kw,calls=setup
    def stop(name,round_id):
        if name=='EDITOR':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kw,event_hook=stop)
    source=kw['output']/'round-01/generation/local-reviews'
    def forbidden(request):raise AssertionError('Fusion must be reused')
    before=calls.copy()
    args=dict(upstream=_load(source/'upstream.json'),output=tmp_path/'fusion-only',reuse_from=source,
        reuse_completed_reviews=False,fusion_transport=forbidden,evidence_review_transport=kw['transports'].evidence_review)
    audit,value=run_local_reviews(**args)
    assert calls['local']==before['local']+1 and calls['fusion']==before['fusion']
    assert all(row['input_version']=='v19.3' for row in audit['evidence_reviews'])
    assert _load(args['output']/'reuse-receipt.json')['proposal_ids']==[]
    assert _load(args['output']/'reuse-receipt.json')['mode']=='FUSION_ONLY_ALL_REVIEWS_RERUN'
    before=calls.copy()
    assert run_local_reviews(**args,resume=True)==(audit,value) and calls==before
    with pytest.raises(ValueError,match='checkpoint changed'):
        run_local_reviews(**{**args,'reuse_completed_reviews':True},resume=True)
