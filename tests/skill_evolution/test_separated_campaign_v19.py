from collections import Counter
from pathlib import Path

import pytest

from tests.skill_evolution.test_campaign_v19 import Evolution,Monitor,transports as legacy_transports
from tests.skill_evolution.test_reconciliation_v19 import decision
from tests.skill_evolution.test_reconciliation_decision_v19 import accountable
from tests.skill_evolution.test_attribution_v19 import complete
from src.skill_evolution.campaign_v19 import CampaignTransports,campaign_config,run_campaign_v19
from src.skill_evolution.edit_tracking_v19 import encode,parse,EditLedger,validate_edit_ledger
from src.skill_evolution.memory_store_v19 import load_memory
from src.skill_evolution.evolution_replay_v19 import _load
from src.skill_evolution.evidence_projection_v19 import project,expand


def transports(calls):
    legacy=legacy_transports(calls)
    def payload(request,key):
        calls[key]+=1
        raw=request['user_prompt']
        for secret in ('PRIVATE-MONITOR','NEVER_LEARN_MONITOR_SECRET','PRIVATE_EXPECTED_ACTION'):
            assert secret not in raw
        return expand(parse(raw))
    def current(request):
        data=payload(request,'current')
        exp=data['experiences'][0]
        event=next(e for e in exp['events'] if e['event_type']=='tool_call')
        return complete(encode({'schema_version':'current_findings_response_v19.1','summary':'Observed current behavior.',
            'findings':[{'kind':'OBSERVED_PROBLEM','statement':'Observed conditional choice can improve.',
                'applicability':'Observed public context only.','dimensions':['SUCCESS'],
                'evidence_refs':[event['evidence_ref']],'supervision_refs':[], 'policy_refs':[],
                'related_rule_refs':[],'uncertainty':['Sampling and confounding.']}]}))
    def review(request):
        data=payload(request,'review')
        events=[ref for ref,e in data['current_evidence'].items() if e['event']['event_type']=='tool_call']
        reviews=[]
        for index,obj in enumerate(data['historical_objects']):
            # Exercise both response shapes; outcome labels do not determine review status.
            uncertain=index % 2 == 1
            reviews.append({'historical_object_id':obj['historical_object_id'],
                'evidence_status':'NOT_COVERED' if uncertain else 'MIXED',
                'supporting_current_refs':[] if uncertain else events[:1],
                'contradicting_current_refs':[] if uncertain else events[1:2],
                'context_current_refs':events[:1] if uncertain else [],'current_finding_refs':[],
                'historical_evidence_refs':[],
                'coverage_reason':'INSUFFICIENT_EVIDENCE' if uncertain else 'ASSESSED',
                'reason':'Preserve both uncertainty and opposing observations.', 'uncertainty':['No causal proof.']})
        return complete(encode({'schema_version':'historical_review_response_v19.1','reviews':reviews}))
    def reconcile(request):
        data=payload(request,'reconciliation');input_=data['review_input']
        fs=input_['current_findings'];rs=data['historical_reviews']['reviews']
        refs={ref for f in fs for ref in f['evidence_refs']}
        refs.update(ref for r in rs for field in ('supporting_current_refs','contradicting_current_refs','context_current_refs') for ref in r[field])
        bound=input_['historical_objects'][0]['current_binding'] if input_['historical_objects'] else None
        kind='NEEDS_REVISION' if bound and bound['current_rule_refs'] else 'MISSING'
        rules=bound['current_rule_refs'] if kind=='NEEDS_REVISION' else []
        d=decision(cf=[f['finding_id'] for f in fs],hr=[r['review_id'] for r in rs],events=sorted(refs),kind=kind,rules=rules)
        d['conflict_resolution']=['Retain bounded observations and opposing evidence; propose a limited revision.'] if rs else []
        return complete(encode({'schema_version':'reconciliation_response_v19.4','decisions':[accountable(d)]}))
    return CampaignTransports(grouping=legacy.grouping,diagnosis=current,editor=legacy.editor,
        attribution=legacy.attribution,memory_review=review,reconciliation=reconcile)


@pytest.fixture
def setup(tmp_path):
    calls=Counter()
    return dict(output=tmp_path/'campaign',config=campaign_config(attribution_protocol='legacy',pilot=True,max_workers=2,generation_protocol='separated'),
        run_id='engineering-run',initial_skill='- Parent\n',evolution_backend=Evolution(),
        monitor_backend=Monitor(),transports=transports(calls)),calls


@pytest.mark.parametrize('gate,relation',[('ACCEPT','REVISES'),('RETAIN','RETRIES')])
def test_two_rounds_persist_decisions_and_reuse_without_model_calls(setup,gate,relation):
    kw,calls=setup;kw['monitor_backend']=Monitor(gate)
    result=run_campaign_v19(**kw)
    assert result['committed_rounds']==2 and result['status']=='COMPLETE'
    assert result['cross_round_links'][0]['relation']==relation
    snap=load_memory(kw['output']/'memory')
    assert all('generation_reviews' in r for r in snap.rounds)
    audit=snap.history[1].ledger.source['generation_audit']
    assert audit['review_input']['memory_context']['rounds'][0]['generation_reviews']['current_findings']
    assert {r['evidence_status'] for r in snap.rounds[1]['generation_reviews']['historical_reviews']}=={'MIXED','NOT_COVERED'}
    before=calls.copy()
    assert run_campaign_v19(**kw,resume=True)==result
    assert calls==before=={'grouping':2,'current':2,'reconciliation':2,'editor':2,'attribution':2,'review':1}
    for secret in ('PRIVATE-MONITOR','NEVER_LEARN_MONITOR_SECRET','PRIVATE_EXPECTED_ACTION'):
        assert secret not in encode(snap.rounds)


@pytest.mark.parametrize('stage',['MEMORY_REVIEW','RECONCILIATION','EDITOR','BEFORE_COMMIT','AFTER_COMMIT'])
def test_resume_stage_interrupt_reuses_completed_calls_and_commits(setup,stage):
    kw,calls=setup
    def interrupt(name,round_id):
        if name==stage and round_id=='round-02':raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):run_campaign_v19(**kw,event_hook=interrupt)
    assert run_campaign_v19(**kw,resume=True)['committed_rounds']==2
    assert calls=={'grouping':2,'current':2,'reconciliation':2,'editor':2,'attribution':2,'review':1}


def test_generation_audit_tamper_rejected_on_ledger_restore(setup):
    kw,_=setup;run_campaign_v19(**kw)
    snap=load_memory(kw['output']/'memory');ledger=snap.history[0].ledger
    source=ledger.source;source['generation_audit']['current_findings'][0]['findings'][0]['statement']='tampered'
    with pytest.raises(ValueError):validate_edit_ledger(EditLedger(encode(source),ledger.output_json))


def test_projection_roundtrip_and_tamper():
    event={'event_type':'message','evidence_ref':'CURRENT/one','content':'Large body '*1000}
    data={'events':[event,{**event,'evidence_ref':'CURRENT/two'}],'policy':'Policy '*1000}
    wire=project(data)
    assert expand(wire)==data and len(wire['event_bodies'])==1
    wire['text_bodies'][next(iter(wire['text_bodies']))]='tampered'
    with pytest.raises(ValueError):expand(wire)


def test_uncertain_current_request_stops_without_silent_resend(setup):
    kw,calls=setup
    original=kw['transports'];count=[]
    def fail(request):count.append(1);raise TimeoutError('synthetic transport failure')
    kw['transports']=CampaignTransports(grouping=original.grouping,diagnosis=fail)
    with pytest.raises(TimeoutError):run_campaign_v19(**kw)
    with pytest.raises(ValueError,match='uncertain model call'):run_campaign_v19(**kw,resume=True)
    assert len(count)==1 and load_memory(kw['output']/'memory').head['revision']==0


def test_one_contract_repair_is_saved_and_reused(setup):
    kw,calls=setup;original=kw['transports'];seen=[]
    def current(request):
        seen.append(request)
        if len(seen)==1:return complete('{}')
        if 'repair-001' in request['prompt_version']:
            value=parse(request['user_prompt'])
            return original.diagnosis({**request,'user_prompt':encode(value['original_input'])})
        return original.diagnosis(request)
    kw['transports']=CampaignTransports(grouping=original.grouping,diagnosis=current,
        editor=original.editor,attribution=original.attribution,memory_review=original.memory_review,reconciliation=original.reconciliation)
    run_campaign_v19(**kw)
    path=kw['output']/'round-01/generation/current-000-repair-001/response_complete.json'
    assert path.exists()
    before=len(seen);run_campaign_v19(**kw,resume=True);assert len(seen)==before


def test_editor_contract_repair_is_bounded_and_audited(setup):
    kw,_=setup;original=kw['transports'];calls=[]
    def editor(request):
        calls.append(request)
        if len(calls)==1:return complete('{}')
        if 'repair-001' in request['prompt_version']:
            data=parse(request['user_prompt'])
            return original.editor({**request,'user_prompt':encode(data['original_input'])})
        return original.editor(request)
    kw['transports']=CampaignTransports(grouping=original.grouping,diagnosis=original.diagnosis,
        editor=editor,attribution=original.attribution,memory_review=original.memory_review,reconciliation=original.reconciliation)
    assert run_campaign_v19(**kw)['committed_rounds']==2
    assert (kw['output']/'round-01/generation/editor-repair-001/response_complete.json').exists()


def test_repair_still_invalid_stops_without_third_call(setup):
    kw,_=setup;original=kw['transports'];calls=[]
    def invalid(request):calls.append(1);return complete('{}')
    kw['transports']=CampaignTransports(grouping=original.grouping,diagnosis=invalid)
    with pytest.raises(ValueError):run_campaign_v19(**kw)
    with pytest.raises(ValueError):run_campaign_v19(**kw,resume=True)
    assert len(calls)==2 and load_memory(kw['output']/'memory').head['revision']==0


def test_separated_no_update_keeps_review_artifacts_without_fake_commit(setup):
    kw,_=setup;original=kw['transports']
    def no_findings(request):
        return complete(encode({'schema_version':'current_findings_response_v19.1','summary':'No supported finding.','findings':[]}))
    kw['transports']=CampaignTransports(grouping=original.grouping,diagnosis=no_findings)
    result=run_campaign_v19(**kw)
    assert result['stop_reason']=='NO_UPDATE' and result['committed_rounds']==0
    assert (kw['output']/'round-01/generation/historical-reviews.json').exists()
    assert (kw['output']/'round-01/generation/reconciliation-result.json').exists()
