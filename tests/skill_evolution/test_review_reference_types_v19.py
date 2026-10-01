from copy import deepcopy
import pytest
from tests.skill_evolution.test_evidence_review_v19 import setup,case,cases,final,payload
from tests.skill_evolution.test_attribution_v19 import complete
from src.skill_evolution.edit_tracking_v19 import encode,parse
from src.skill_evolution.evidence_review_v19 import (EvidenceReviewInput,EvidenceReviewCase,build_evidence_review_input,
    validate_evidence_review,final_schema_for_input,FINAL_SCHEMA)
from src.skill_evolution.evidence_review_run_v19 import run_evidence_review


def request_for(setup):
    c=cases(setup[2])[0]
    return c,build_evidence_review_input(c,input_version='v19.3')


def test_no_targets_limits_schema_without_mutating_shared_contract(setup):
    _,r=request_for(setup);p=r.payload;p['rules']={};r=EvidenceReviewInput(encode(p))
    before=deepcopy(FINAL_SCHEMA);s=final_schema_for_input(r)['properties']['gap']['anyOf'][1]['properties']
    assert s['kind']['enum']==['MISSING'] and s['related_rule_refs']['maxItems']==0
    assert FINAL_SCHEMA==before
    out=final(p);out['gap'].update(kind='NEEDS_REVISION',related_rule_refs=[])
    with pytest.raises(ValueError,match='revision/removal is not authorized'):validate_evidence_review(encode(out),request=r)


def test_loaded_targets_are_only_allowed_schema_refs(setup):
    c,r=request_for(setup);p=r.payload;p['rules']=c.payload['rules'];assert p['rules']
    r=EvidenceReviewInput(encode(p));schema=final_schema_for_input(r)['properties']['gap']['anyOf'][1]['properties']
    assert schema['related_rule_refs']['items']['enum']==sorted(p['rules'])
    for kind in ('MISSING','NEEDS_REVISION','SHOULD_REMOVE'):
        out=final(p,kind=kind)
        assert validate_evidence_review(encode(out),request=r).payload['gap']['kind']==kind


def test_policy_mistaken_for_event_and_parent_target_reported_together(setup):
    _,r=request_for(setup);p=r.payload
    # Generic synthetic policy; no Pilot-specific identifiers or business rules.
    ref='POLICY/context/digest/L42';p['policies'][ref]={'text':'Ask for the missing required value.'}
    p['rules']={};r=EvidenceReviewInput(encode(p));out=final(p)
    out['evidence_refs'].append(ref);out['gap'].update(kind='NEEDS_REVISION',related_rule_refs=[ref])
    raw=encode(out)
    with pytest.raises(ValueError) as exc:validate_evidence_review(raw,request=r)
    errors=parse(str(exc.value).split(': ',1)[1])
    policy_errors=[e for e in errors if e.get('ref')==ref]
    assert {e['expected_type'] for e in policy_errors}=={'EVENT','PARENT_SKILL_RULE'}
    assert all(e['actual_type']=='VISIBLE_POLICY' for e in policy_errors)
    assert any(e['field']=='gap.kind' for e in errors)
    assert encode(out)==raw  # Validator never changes mutation kind or targets.


def test_unknown_and_wrong_type_references_are_distinguished(setup):
    _,r=request_for(setup);p=r.payload;ref=next(iter(p['events']));out=final(p)
    out['gap'].update(kind='NEEDS_REVISION',related_rule_refs=[ref,'UNKNOWN/rule'])
    with pytest.raises(ValueError) as exc:validate_evidence_review(encode(out),request=r)
    errors=parse(str(exc.value).split(': ',1)[1]);types={e['ref']:e['actual_type'] for e in errors if 'ref' in e}
    assert types[ref]=='EVENT' and types['UNKNOWN/rule']=='UNKNOWN_OR_UNLOADED'


def test_repair_receives_all_independent_reference_errors(setup,tmp_path):
    c,r=request_for(setup);data=c.payload;ref=next(iter(data['policies']))
    data['findings'][0]['policy_refs']=[ref];c=EvidenceReviewCase(encode(data));calls=[]
    def transport(req):
        calls.append(req);p=payload(req)
        if len(calls)==1:
            out=final(p);ref=next(iter(p['policies']))
            out['evidence_refs'].append(ref);out['gap'].update(kind='NEEDS_REVISION',related_rule_refs=[ref])
            return complete(encode(out))
        feedback=parse(req['user_prompt'])['validation_error']['message']
        assert 'gap.related_rule_refs' in feedback and 'evidence_refs[' in feedback and 'VISIBLE_POLICY' in feedback
        return complete(encode(final(p,verdict='NO_EDIT')))
    result=run_evidence_review(c,output=tmp_path/'review',transport=transport)
    assert result.payload['verdict']=='NO_EDIT' and len(calls)==2
