from copy import deepcopy

import pytest

from tests.skill_evolution.test_reconciliation_v19 import setup,case,prepared,output,multi_output,decision
from src.skill_evolution.review_contract_v19 import MemoryReviewInput,HistoricalReviews
from src.skill_evolution.edit_tracking_v19 import encode
from src.skill_evolution.reconciliation_v19 import build_reconciliation_input,validate_reconciliation,reconciliation_editor_request
from src.skill_evolution.reconciliation_evidence_v19 import evidence_view,selected_evidence_refs
from src.skill_evolution.reconciliation_prompt_v19 import build_reconciliation_request


def current_input(old):
    p=old.payload
    return build_reconciliation_input(review_request=MemoryReviewInput(encode(p['review_input'])),
        historical_reviews=HistoricalReviews(encode(p['historical_reviews'])))


def accountable(d):
    """Synthetic model response, never used to modify real model output."""
    d=deepcopy(d);refs=d['current_finding_refs']+d['historical_review_refs']
    action=d['decision']
    d['issue_dispositions']=[{'source_ref':r,'issue':'Observed conditional behavior.',
        'disposition':{'PROPOSE':'ADDRESSED','KEEP':'PRESERVED','DEFER':'DEFERRED'}[action],
        'reason':'This issue is explicitly handled by the stated decision.'} for r in refs]
    d['merge_justification']=['Same observed choice and scope, compatible treatment.'] if len(refs)>1 else []
    d['defer_basis']=[{'category':'UNCERTAIN_APPLICABILITY','reason':'Observation does not establish transfer.',
                          'required_information':'A matched observation in the proposed scope.'}] if action=='DEFER' else []
    d['feasibility_checks']=[{'requirement':'Use the already observed information to make the stated behavioral choice.',
        'status':'SUPPORTED','evidence_refs':d['evidence_refs'],'tool_refs':[],
        'availability_before_action':'The visible observation precedes the proposed choice.',
        'limitations_and_counterevidence':'No guarantee of future outcomes; scope remains conditional.',
        'reason':'The proposal requires no new tool or hidden information.'}] if action=='PROPOSE' else []
    return d


def response(x):
    return {'schema_version':'reconciliation_response_v19.4','decisions':[accountable(d) for d in x['decisions']]}


def test_multiple_independent_proposals_compile_without_batch_quota(setup):
    old,x,_=multi_output(setup);r=current_input(old);x=response(x)
    # Independent ADD proposals must survive as two units rather than a quota.
    for d in x['decisions'][:2]:
        gap=d['proposals'][0]['parent_skill_gaps'][0];gap['kind']='MISSING';gap['related_rule_refs']=[]
    result,value=validate_reconciliation(encode(x),request=r)
    assert len(value.plan.edit_units)==2
    prompt=reconciliation_editor_request(result,request=r)
    assert 'feasibility_checks' in prompt['user_prompt']


@pytest.mark.parametrize('mutation,expected',[
    (lambda d:d.update(feasibility_checks=[]),'feasibility checks'),
    (lambda d:d['feasibility_checks'][0].update(status='UNKNOWN'),'unknown prerequisite'),
    (lambda d:d['feasibility_checks'][0].update(status='UNAVAILABLE'),'unknown prerequisite'),
    (lambda d:d['feasibility_checks'][0].update(tool_refs=['TOOL/invented']),'unknown tool'),
    (lambda d:d['feasibility_checks'][0].update(evidence_refs=['hidden']),'unloaded evidence'),
    (lambda d:d['issue_dispositions'][0].update(disposition='CONTEXT_ONLY'),'observed problem'),
    (lambda d:d.update(issue_dispositions=[]),'cover each declared source'),
])
def test_proposal_preconditions_and_problem_disposition_fail_closed(setup,mutation,expected):
    old=prepared(setup[2]);r=current_input(old);x=response(output(old));mutation(x['decisions'][0])
    with pytest.raises(ValueError,match=expected):validate_reconciliation(encode(x),request=r)


def test_defer_requires_concrete_obstacle_not_a_quota(setup):
    old=prepared(setup[2]);r=current_input(old);x=response(output(old))
    x['decisions'][1]['defer_basis'][0]['category']='BATCH_PROPOSAL_LIMIT'
    with pytest.raises(ValueError):validate_reconciliation(encode(x),request=r)
    x['decisions'][1]['defer_basis']=[]
    with pytest.raises(ValueError,match='DEFER requires'):validate_reconciliation(encode(x),request=r)


def test_merging_needs_explicit_common_issue_and_preserves_each_source(setup):
    old,x,_=multi_output(setup);r=current_input(old)
    a,b=x['decisions'][:2]
    a['current_finding_refs']+=b['current_finding_refs']
    a['current_finding_assessments']+=b['current_finding_assessments']
    a['evidence_refs']+=b['evidence_refs']
    a['proposals'][0]['parent_skill_gaps'][0]['evidence_refs']=a['evidence_refs']
    a['proposals'][0]['success_analysis']['evidence_refs']=a['evidence_refs']
    x['decisions'].pop(1);x=response(x)
    validate_reconciliation(encode(x),request=r)
    x['decisions'][0]['merge_justification']=[]
    with pytest.raises(ValueError,match='merged sources'):validate_reconciliation(encode(x),request=r)


def test_full_context_closure_restores_uncited_tool_results_without_changing_findings(setup):
    from src.skill_evolution.reconciliation_v19 import _catalog
    old=prepared(setup[2]);r=current_input(old);before=r.payload_json;view=evidence_view(r)
    seeds=selected_evidence_refs(r);catalog=_catalog(r)
    expected={e['evidence_ref'] for exp in catalog['experiences']
              if seeds & {e['evidence_ref'] for e in exp['events']} for e in exp['events']}
    assert set(view['events'])==expected
    assert expected-seeds  # Not just the original excerpts.
    assert view['review_input']['current_findings']==old.payload['review_input']['current_findings']
    assert all(v['loaded_event_count']==v['available_event_count'] for v in view['trajectories'].values() if v['loaded_event_count'])
    assert r.payload_json==before
    prompt=build_reconciliation_request(r)
    assert prompt['prompt_version']=='reconciliation-v19.4'
    assert prompt['response_format']['json_schema']['schema']['properties']['schema_version']['enum']==['reconciliation_response_v19.4']


def test_real_previous_valid_response_is_not_silently_promoted_to_new_contract():
    import gzip,json
    from pathlib import Path
    root=Path(__file__).parent/'fixtures'
    old=json.loads(gzip.decompress((root/'v19_reconciliation_failure.json.gz').read_bytes()))['input']
    raw=json.loads(gzip.decompress((root/'v19_reconciliation_semantic_review.json.gz').read_bytes()))['raw_response']
    r=build_reconciliation_input(review_request=MemoryReviewInput(encode(old['review_input'])),
        historical_reviews=HistoricalReviews(encode(old['historical_reviews'])))
    with pytest.raises(ValueError,match='feasibility_checks'):
        validate_reconciliation(raw,request=r)
    view=evidence_view(r)
    from src.skill_evolution.reconciliation_v19 import _catalog
    catalog=_catalog(r)
    # Every omitted return/message in every selected source is restored, without
    # selecting a particular tool, domain, outcome or Pilot error by name.
    for exp in catalog['experiences']:
        if any(e['evidence_ref'] in selected_evidence_refs(r) for e in exp['events']):
            assert all(e['evidence_ref'] in view['events'] for e in exp['events'])
    expected=[(c['context_ref'],tool) for c in catalog['contexts'] if c['context_ref'] in view['contexts'] for tool in c['public_tools']]
    assert sorted(encode(v) for v in view['available_tool_refs'].values())==sorted(encode({'context_ref':c,'definition':t}) for c,t in expected)
